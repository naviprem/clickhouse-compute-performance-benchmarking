# Dashboard UI Setup

- Build and push backend image

```bash
cd apps/dashboard/backend

# Authenticate with ECR (if not done already)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Create backend repository (one-time only)
aws ecr create-repository \
  --repository-name dashboard-backend \
  --region us-east-1 \
  --profile clickhouse-demo

# Build
docker buildx build --platform linux/amd64 -t dashboard-backend:latest .

# Tag
docker tag dashboard-backend:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/dashboard-backend:latest

# Push
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/dashboard-backend:latest
```

- Build and Push Frontend Image

```bash
cd apps/dashboard/frontend

# Authenticate with ECR (if not done already)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

# Create frontend repository (one-time only)
aws ecr create-repository \
  --repository-name dashboard-frontend \
  --region us-east-1 \
  --profile clickhouse-demo

# Build
docker buildx build \
  --build-arg REACT_APP_API_URL=http://dashboard-backend:3001 \
  --platform linux/amd64 \
  -t dashboard-frontend:latest .

# Tag
docker tag dashboard-frontend:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/dashboard-frontend:latest

# Push
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/dashboard-frontend:latest
```

- Deploy to Kubernetes

```bash
# deploy Backend
kubectl apply -f infra/kubernetes/dashboard/backend-deployment.yaml

# Deploy Frontend
kubectl apply -f infra/kubernetes/dashboard/frontend-deployment.yaml

# Check pod status
kubectl get pods -n clickhouse | grep dashboard

# Check services
kubectl get svc -n clickhouse | grep dashboard

# View backend logs
kubectl logs -n clickhouse -l app=dashboard-backend --tail=50

# Stream backend logs
kubectl logs -n clickhouse -l app=dashboard-backend -f

# Check for ClickHouse connection errors
kubectl logs -n clickhouse -l app=dashboard-backend | grep -i error

# View frontend logs
kubectl logs -n clickhouse -l app=dashboard-frontend --tail=50

# Stream frontend logs
kubectl logs -n clickhouse -l app=dashboard-frontend -f
```

- Get LoadBalancer URL

```bash
kubectl get svc dashboard-frontend -n clickhouse -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

- Test Backend API

```bash
# Get backend service port-forward
kubectl port-forward -n clickhouse svc/dashboard-backend 3001:3001 &

# Test health endpoint
curl http://localhost:3001/health

# Test metrics list
curl http://localhost:3001/api/metrics/list

# Test Option 1 query
curl -X POST http://localhost:3001/api/metrics/option1 \
  -H "Content-Type: application/json" \
  -d '{
    "metricName": "system.cpu.usage",
    "startTime": "2025-11-11 00:00:00",
    "endTime": "2025-11-11 23:59:59"
  }'
```

- Test Frontend

```bash
# Port-forward frontend
kubectl port-forward -n clickhouse svc/dashboard-frontend 8080:80

# Open in browser
open http://localhost:8080
```
