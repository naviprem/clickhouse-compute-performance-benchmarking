# Clickhouse Infra setup

- Add ClickHouse Helm Repository

```bash
# Add the ClickHouse Helm chart repository
helm repo add clickhouse https://docs.altinity.com/clickhouse-operator/

# Update Helm repositories
helm repo update

# Verify the repo was added
helm search repo clickhouse
```

- Create Kubernetes service accounts with IRSA for option 1:

```bash
# Create service account for Parquet Converter
eksctl create iamserviceaccount \
  --cluster=${CLUSTER_NAME} \
  --namespace=clickhouse \
  --name=clickhouse-option1-sa \
  --attach-policy-arn=${POLICY_ARN} \
  --approve \
  --override-existing-serviceaccounts

# Verify IRSA role
kubectl describe sa clickhouse-option1-sa -n clickhouse

# To delete a service account
kubectl delete serviceaccount clickhouse-option1-sa -n clickhouse
```

- Setup infra for Option 1

```bash
# Create service account with IRSA for S3 access
# kubectl apply -f infra/kubernetes/clickhouse-option1/serviceaccount.yaml

# Create minimal configuration for S3 querying
kubectl apply -f infra/kubernetes/clickhouse-option1/configmap.yaml

# Create stateless deployment (no persistent storage)
kubectl apply -f infra/kubernetes/clickhouse-option1/deployment.yaml

# Create ClusterIP service
kubectl apply -f infra/kubernetes/clickhouse-option1/service.yaml
```

- Verify Option 1 Deployment

```bash
# Wait for deployment to be ready
kubectl wait --for=condition=ready pod -l app=clickhouse-option1 -n clickhouse --timeout=180s

# Check deployment status
kubectl get deployment clickhouse-option1 -n clickhouse

# Check pod status
kubectl get pods -l app=clickhouse-option1 -n clickhouse

# Check service
kubectl get svc clickhouse-option1 -n clickhouse

# Test connectivity
kubectl exec -it -n clickhouse $(kubectl get pod -l app=clickhouse-option1 -n clickhouse -o jsonpath='{.items[0].metadata.name}') -- clickhouse-client --query="SELECT 'Option 1 is ready!'"
```

- Create Kubernetes service accounts with IRSA for option 1 (optional):

```bash
# Create service account for Parquet Converter
eksctl create iamserviceaccount \
  --cluster=${CLUSTER_NAME} \
  --namespace=clickhouse \
  --name=clickhouse-option2-sa \
  --attach-policy-arn=${POLICY_ARN} \
  --approve \
  --override-existing-serviceaccounts

# Verify IRSA role
kubectl describe sa clickhouse-option2-sa -n clickhouse

# To delete a service account
kubectl delete serviceaccount clickhouse-option2-sa -n clickhouse
```

- Setup infra for Option 2

```bash
# Create service account (no IRSA needed for Option 2, but included for consistency)
# kubectl apply -f infra/kubernetes/clickhouse-option2/serviceaccount.yaml

# Create configuration optimized for data storage
kubectl apply -f infra/kubernetes/clickhouse-option2/configmap.yaml

# Create stateful deployment with persistent storage
kubectl apply -f infra/kubernetes/clickhouse-option2/statefulset.yaml

# Create ClusterIP service
kubectl apply -f infra/kubernetes/clickhouse-option2/service.yaml

# create gp3 storage class
kubectl apply -f infra/kubernetes/storageclass-gp3.yaml

# Install EBS CSI driver
helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
helm repo update
helm install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver

```

- Verify Option 2 Deployment

```bash
# To verify that aws-ebs-csi-driver has started, run:
kubectl get pod -n default -l "app.kubernetes.io/name=aws-ebs-csi-driver,app.kubernetes.io/instance=aws-ebs-csi-driver"

# Verify storageclass
kubectl get storageclass

# Wait for statefulset to be ready (this may take 2-3 minutes)
kubectl wait --for=condition=ready pod -l app=clickhouse-option2 -n clickhouse --timeout=300s

# Check statefulset status
kubectl get statefulset clickhouse-option2 -n clickhouse

# Check pod status
kubectl get pods -l app=clickhouse-option2 -n clickhouse

# Check persistent volume claim
kubectl get pvc -n clickhouse

# Check service
kubectl get svc clickhouse-option2 -n clickhouse

# Test connectivity
kubectl exec -it -n clickhouse clickhouse-option2-0 -- clickhouse-client --query="SELECT 'Option 2 is ready!'"
```

- Create Schema for Option 1 (S3 External Table)

```bash
# Get Option 1 pod name
OPTION1_POD=$(kubectl get pod -l app=clickhouse-option1 -n clickhouse -o jsonpath='{.items[0].metadata.name}')

kubectl exec -i -n clickhouse $OPTION1_POD -- clickhouse-client --multiquery < infra/sql/option1-schema.sql
```

- Create Schema for Option 2 (MergeTree Table)

```bash
# Apply schema to Option 2
kubectl exec -i -n clickhouse clickhouse-option2-0 -- clickhouse-client --multiquery < infra/sql/option2-schema.sql

# You might have to run each query from the sql file separately, like so...
kubectl exec -n clickhouse clickhouse-option2-0 -- clickhouse-client --database metrics_ingested --query ""
```

- Create LoadBalancer Service for External Access

```bash
# Apply LoadBalancers
kubectl apply -f infra/kubernetes/clickhouse-option1/loadbalancer.yaml
kubectl apply -f infra/kubernetes/clickhouse-option2/loadbalancer.yaml

# Wait for LoadBalancers to get external IPs (takes 2-3 minutes)
kubectl get svc -n clickhouse -w
# Press Ctrl+C when both show EXTERNAL-IP

# Get external endpoints
export OPTION1_HOST=$(kubectl get svc clickhouse-option1-external -n clickhouse -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
export OPTION2_HOST=$(kubectl get svc clickhouse-option2-external -n clickhouse -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "Option 1 Host: $OPTION1_HOST"
echo "Option 2 Host: $OPTION2_HOST"

# Test external access
curl "http://${OPTION1_HOST}:8123/?query=SELECT%20version()"
curl "http://${OPTION2_HOST}:8123/?query=SELECT%20version()"
```

- Create AWS secret

```bash
kubectl create secret generic aws-credentials \
  -n clickhouse \
  --from-literal=access_key_id=YOUR_ACCESS_KEY \
  --from-literal=secret_access_key=YOUR_SECRET_KEY
```

- Test Queries on Both Instances

```bash
# Test Option 1 (will fail until we have Parquet data in S3)
echo "Testing Option 1 (S3 External Table):"
kubectl exec -it -n clickhouse $OPTION1_POD -- clickhouse-client --query="
USE metrics_s3;
SELECT count(*) FROM otel_metrics_s3;
" || echo "Expected: No data in S3 yet - will work after Phase 3"

echo ""

kubectl exec -n clickhouse $OPTION1_POD -- clickhouse-client --database metrics_s3 --query "SELECT count() FROM otel_metrics_s3"

# Test Option 2 (should work with sample data)
echo "Testing Option 2 (MergeTree Table):"
kubectl exec -it -n clickhouse clickhouse-option2-0 -- clickhouse-client --query="
USE metrics_ingested;
SELECT
    metric_name,
    count() as count,
    avg(metric_value) as avg_value
FROM otel_metrics
GROUP BY metric_name;
"
```
