kubectl delete service s3-data
kubectl delete service s3-metadata
kubectl delete service s3-front
kubectl delete service zenko-prod-lb
kubectl delete service cache
kubectl delete service quorum
kubectl delete service queue
kubectl delete service backbeat-producer
kubectl delete deployment s3-data
kubectl delete deployment s3-metadata
kubectl delete deployment s3-front
kubectl delete deployment zenko-prod-lb
kubectl delete deployment cache
kubectl delete deployment quorum
kubectl delete deployment queue
kubectl delete deployment backbeat-producer
kubectl delete pv s3-data-pv
kubectl delete pv s3-metadata-pv
kubectl delete pv quorum-data-pv
kubectl delete pv quorum-datalog-pv
kubectl delete pv queue-journal-pv
kubectl delete pvc s3-data-pv-claim
kubectl delete pvc s3-metadata-pv-claim
kubectl delete pvc quorum-data-pv-claim
kubectl delete pvc quorum-datalog-pv-claim
kubectl delete pvc queue-journal-pv-claim
kubectl delete secret s3-creds
