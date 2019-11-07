import logging
import time
import pytest
import zenko_e2e.conf as conf
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from ..fixtures import *
from .. import util

_log = logging.getLogger('cosmos')  # pylint: disable=invalid-name

MD5_HASHES = {
    "file1": "e61d15de7ad98164bad4394b818510a9",  # 1KB
    "file2": "18bcf93f4a001b4cdfc3fc702847864f",  # 1MB
    "file3": "b4bf46b4640547ab96e75b24170242c1",  # 10MB
    "file4": "1baecec7b7c658357288ac736b6e95a6",  # 100MB
}


@pytest.fixture
def kube():
    return client.ApiClient(config.load_incluster_config())


@pytest.fixture
def kube_batch(kube):
    return client.BatchV1Api(kube)


@pytest.fixture
def kube_corev1(kube):
    return client.CoreV1Api(kube)


@pytest.fixture
def enable_ingest(kube, location):
    api_instance = client.CustomObjectsApi(kube)
    body = {"spec": {"rclone": {"triggerIngestion": True}}}
    return api_instance.patch_namespaced_custom_object(
        'zenko.io',
        'v1alpha1',
        conf.K8S_NAMESPACE,
        'cosmoses',
        location,
        body
    )


@pytest.fixture
def get_job(kube_batch, location):
    # label = {"cosmos": location}
    label = 'cosmos={}'.format(location)
    _log.debug("label %s", label)
    return kube_batch.list_namespaced_job(
        conf.K8S_NAMESPACE,
        label_selector=label
    )


@pytest.fixture
def compare_versions(objkey, aws_target_bucket, zenko_bucket):
    src_obj = aws_target_bucket.Object(objkey)
    dst_obj = zenko_bucket.Object(objkey)
    if src_obj.version_id != dst_obj.metadata['version-id']:
        return False
    src_hash = util.get_object_hash(aws_target_bucket, objkey)
    zenko_bucket.put_object(Key=objkey)
    dst_hash = util.get_object_hash(
        zenko_bucket, objkey, versionid=dst_obj.version_id)
    if src_hash != dst_hash:
        return False
    return True


# Timeout has been increased to 180 because of setup time but really shouldn't
# be increased any further. Please investigate possible regressions or test
# refactor before increasing the timeout any further.
@pytest.fixture
def wait_for_job(kube_batch, location, timeout=90):
    _timestamp = time.time()
    while time.time() - _timestamp < timeout:
        try:
            enable_ingest(kube(), location)
            job_name = get_job(kube_batch, location)
            _log.debug("job_name %s", job_name)
            _log.debug("job items %s", job_name.items)
            state = kube_batch.read_namespaced_job_status(
                job_name.items[0], conf.K8S_NAMESPACE)
            if state.status.succeeded:
                _log.debug("Finished with status %s", state.status.succeeded)
                break
        except IndexError:
            # When the job hasn't yet been created, there is an index error
            pass
        except ApiException as err:
            _log.error("Exception when calling job status %s", err)
        _log.info("Waiting for job completion")
        time.sleep(1)
    else:
        _log.error('Initial ingestion did not complete in time')
    return state


@pytest.mark.conformance
def test_cosmos_nfs_ingest(nfs_loc, nfs_loc_bucket, kube_batch):
    util.mark_test('SOFS-NFS OOB INGESTION')
    job = wait_for_job(kube_batch, nfs_loc)
    assert job.status.succeeded

    for (key, md5) in MD5_HASHES.items():
        _log.debug("Checking object %s with hash %s", key, md5)
        assert util.get_object_hash(nfs_loc_bucket, key) == md5


@pytest.mark.conformance
def test_cosmos_aws_ingest(aws_target_bucket, zenko_bucket, kube_batch, testfile, objkey): # noqa pylint: disable=dangerous-default-value,too-many-arguments
    util.mark_test('AWS OOB INGESTION')
    aws_target_bucket.put_object(
        Body=testfile,
        Key=objkey,
    )
    zenko_bucket = aws_loc_bucket(zenko_bucket, ingest=True)
    # Wait for initial ingestion
    job = wait_for_job(kube_batch, conf.AWS_BACKEND)
    assert job.status.succeeded
    # Validate ingestion
    assert util.check_object(
        objkey, testfile, zenko_bucket, aws_target_bucket)
    # Validate versioning
    assert compare_versions(objkey, aws_target_bucket, zenko_bucket)


@pytest.mark.conformance
def test_cosmos_ceph_ingest(ceph_target_bucket, zenko_bucket, kube_batch, testfile, objkey): # noqa pylint: disable=dangerous-default-value,too-many-arguments
    util.mark_test('CEPH OOB INGESTION')
    ceph_target_bucket.put_object(
        Body=testfile,
        Key=objkey,
    )
    zenko_bucket = ceph_loc_bucket(zenko_bucket, ingest=True)
    job = wait_for_job(kube_batch, conf.CEPH_BACKEND)
    assert job.status.succeeded
    assert util.check_object(
        objkey, testfile, zenko_bucket, ceph_target_bucket)
    assert compare_versions(objkey, ceph_target_bucket, zenko_bucket)
