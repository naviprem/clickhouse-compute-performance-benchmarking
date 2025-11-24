# App Setup

- [x] Build and push Metrics Generator Docker image:

```bash
export AWS_ACCOUNT_ID=<ACCOUNT_ID>

# CD into metrics generator app directory
cd apps/metrics-generator

# Set your Docker repository (replace with your ECR/DockerHub)
METRICS_GENERATOR_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/metrics-generator"
echo ${METRICS_GENERATOR_IMAGE}

# Build image
docker buildx build --platform linux/amd64 -t metrics-generator:latest .

# Tag for repository
docker tag metrics-generator:latest ${METRICS_GENERATOR_IMAGE}:latest

# Push to ECR (authenticate first)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${METRICS_GENERATOR_IMAGE}

# Create repo (one-time only)
aws ecr create-repository --repository-name metrics-generator --region us-east-1

# Push
docker push ${METRICS_GENERATOR_IMAGE}:latest

# Back to root directory
cd ../..
```

- [x] Deploy Metrics Generator

```bash
# Update image in deployment.yaml with your Docker repository
kubectl apply -f infra/kubernetes/metrics-generator/deployment.yaml

# To delete the current deployment
kubectl delete deployment metrics-generator -n clickhouse

# To restart 
kubectl rollout restart deployment/metrics-generator -n clickhouse

# Watch rollout
kubectl rollout status deployment/metrics-generator -n clickhouse

# Verify
kubectl get pods -n clickhouse -l app=metrics-generator
kubectl logs -n clickhouse -l app=metrics-generator --tail=50
kubectl logs -n clickhouse metrics-generator-7cdc8bfd94-dcbsf --tail=20
```

- [x] Create Kubernetes service accounts with IRSA:

```bash

# Create service account for OTEL Collector
eksctl create iamserviceaccount \
  --cluster=${CLUSTER_NAME} \
  --namespace=clickhouse \
  --name=otel-collector-sa \
  --attach-policy-arn=${POLICY_ARN} \
  --approve \
  --override-existing-serviceaccounts

# Verify IRSA role
kubectl describe sa otel-collector-sa -n clickhouse

# To delete a service account
kubectl delete serviceaccount otel-collector-sa -n clickhouse
```

- [x] Create OTEL Collector configuration:

```bash
# Deploy OTEL Collector
kubectl apply -f infra/kubernetes/otel-collector/configmap.yaml
kubectl apply -f infra/kubernetes/otel-collector/daemonset.yaml
kubectl apply -f infra/kubernetes/otel-collector/service.yaml

# Verify deployment
kubectl get pods -n clickhouse -l app=otel-collector
kubectl get svc -n clickhouse otel-collector
kubectl logs -n clickhouse -l app=otel-collector --tail=50

# Restart OTEL collector to reload config
kubectl rollout restart daemonset/otel-collector -n clickhouse
kubectl rollout status daemonset/otel-collector -n clickhouse

# To delete
kubectl delete pods -n clickhouse -l app=otel-collector

# View sidecar logs
kubectl logs -n clickhouse -l app=otel-collector -c s3-sync --tail=30

# Verify S3 files after ~2 minutes
aws s3 ls s3://clickhouse-demo-metrics-np-2025/raw/ --recursive

# To check is files exist in log directory
kubectl exec -n clickhouse otel-collector-htgzj -c s3-sync -- ls -lah /var/log/otel/
kubectl exec -n clickhouse otel-collector-nj79c -c s3-sync -- ls -lah /var/log/otel/
kubectl exec -n clickhouse otel-collector-ssfwn -c s3-sync -- ls -lah /var/log/otel/

# Check other OTEL Collector pod for metrics
kubectl logs -n clickhouse otel-collector-894kq -c otel-collector --tail=20 | grep -i metric
kubectl logs -n clickhouse otel-collector-cjtbd -c otel-collector --tail=20 | grep -i metric
kubectl logs -n clickhouse otel-collector-k27hs -c otel-collector --tail=20 | grep -i metric

# Check if files are being written
kubectl exec -n clickhouse otel-collector-894kq -c s3-sync -- ls -lh /var/log/otel/
kubectl exec -n clickhouse otel-collector-cjtbd -c s3-sync -- ls -lh /var/log/otel/
kubectl exec -n clickhouse otel-collector-k27hs -c s3-sync -- ls -lh /var/log/otel/


```

- [x] Build and push Parquet Converter Docker image:

```bash
# CD into Parquet Converter app directory
cd apps/parquet-converter

# Set your Docker repository (replace with your ECR/DockerHub)
PARQUET_CONVERTER_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/parquet-converter"
echo ${PARQUET_CONVERTER_IMAGE}

# Build image
docker buildx build --platform linux/amd64 -t parquet-converter:latest .

# Tag for repository
docker tag parquet-converter:latest ${PARQUET_CONVERTER_IMAGE}:latest

# Push to ECR (authenticate first)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${PARQUET_CONVERTER_IMAGE}

# Create repo (one-time only)
aws ecr create-repository --repository-name parquet-converter --region us-east-1

# Push
docker push ${PARQUET_CONVERTER_IMAGE}:latest

cd ../..
```

- Create Kubernetes service accounts with IRSA:

```bash
# Create service account for Parquet Converter
eksctl create iamserviceaccount \
  --cluster=${CLUSTER_NAME} \
  --namespace=clickhouse \
  --name=parquet-converter-sa \
  --attach-policy-arn=${POLICY_ARN} \
  --approve \
  --override-existing-serviceaccounts

# Verify IRSA role
kubectl describe sa parquet-converter-sa -n clickhouse

# To delete a service account
kubectl delete serviceaccount parquet-converter-sa -n clickhouse
```

- Deploy Parquet Converter CronJob

```bash

# Deploy
kubectl apply -f infra/kubernetes/parquet-converter/cronjob.yaml

# Verify
kubectl get cronjobs -n clickhouse
kubectl get pods -n clickhouse -l app=parquet-converter

# Delete the existing cronjob
kubectl delete cronjob parquet-converter -n clickhouse

# Manually trigger a job for testing
kubectl create job --from=cronjob/parquet-converter parquet-converter-manual -n clickhouse

# Check job logs
kubectl logs -n clickhouse job/parquet-converter-manual
```
