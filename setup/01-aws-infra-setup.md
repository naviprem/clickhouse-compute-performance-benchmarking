# Infra setup

- [x] Create IAM Administrator User

1. **Login to AWS Console**
   - Go to <https://console.aws.amazon.com>
   - Sign in with your root account

2. **Navigate to IAM**
   - Search for "IAM" in the AWS Console search bar
   - Click on "IAM" (Identity and Access Management)

3. **Create New User**
   - Click "Users" in the left sidebar
   - Click "Create user" button
   - Enter username: `clickhouse-demo-admin`
   - Click "Next"

4. **Set Permissions**
   - Select "Attach policies directly"
   - Search and select: `AdministratorAccess`
   - Click "Next"
   - Review and click "Create user"

- [x] Create Access Keys

1. **Generate Access Key**
   - Click on the newly created user `clickhouse-demo-admin`
   - Go to "Security credentials" tab
   - Scroll to "Access keys" section
   - Click "Create access key"

2. **Select Use Case**
   - Choose "Command Line Interface (CLI)"
   - Check the confirmation checkbox
   - Click "Next"

3. **Set Description (Optional)**
   - Description tag: "ClickHouse benchmarking demo"
   - Click "Create access key"

4. **Download Credentials**
   - **IMPORTANT**: Copy both:
     - Access key ID
     - Secret access key
   - Click "Download .csv file" (recommended)
   - Store securely - you won't see the secret again!
   - Click "Done"

- [x] Install AWS CLI

```bash
# Install AWS CLI v2 via Homebrew
brew install awscli

# Verify installation
aws --version
```

- [x] Configure AWS profile

```bash
# Start interactive configuration
aws configure --profile clickhouse-demo

# When prompted, enter:
# AWS Access Key ID: 
# AWS Secret Access Key: 
# Default region name: us-east-1
# Default output format: json

# Test the credentials
aws sts get-caller-identity --profile clickhouse-demo

# Set Environment Variable
export AWS_PROFILE=clickhouse-demo
```

---

- [x] Create S3 Bucket

```bash
# Set variables
export BUCKET_NAME="clickhouse-demo-metrics-np-2025"  # Change this!
export AWS_REGION="us-east-1"

# Create bucket
aws s3api create-bucket \
  --bucket $BUCKET_NAME \
  --region $AWS_REGION \
  --profile clickhouse-demo

# Enable versioning for data recovery (optional)
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled \
  --profile clickhouse-demo

# Create raw/ prefix for JSON files
aws s3api put-object \
  --bucket $BUCKET_NAME \
  --key raw/ \
  --profile clickhouse-demo

# Create processed/ prefix for Parquet files
aws s3api put-object \
  --bucket $BUCKET_NAME \
  --key processed/ \
  --profile clickhouse-demo

# Verify structure
aws s3 ls s3://$BUCKET_NAME/ --profile clickhouse-demo

# Apply lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket $BUCKET_NAME \
  --lifecycle-configuration file://infra/iam/policies/s3-lifecycle-policy.json \
  --profile clickhouse-demo

# Verify
aws s3api get-bucket-lifecycle-configuration \
  --bucket $BUCKET_NAME \
  --profile clickhouse-demo
```

---

- [x] Install eksctl & kubectl

```bash
# Install using Homebrew
brew tap weaveworks/tap
brew install weaveworks/tap/eksctl

# Verify installation
eksctl version

# Install using Homebrew
brew install kubectl

# Verify installation
kubectl version --client
```

- [x] Create EKS Cluster

```bash
# Create cluster (takes 15-20 minutes)
eksctl create cluster -f infra/eks/eks-cluster-config.yaml --profile clickhouse-demo

# Associate OIDC provider with the existing cluster
eksctl utils associate-iam-oidc-provider \
  --cluster clickhouse-demo-np \
  --region us-east-1 \
  --approve \
  --profile clickhouse-demo

# Verify kubectl is configured
kubectl get nodes

# Check cluster info
kubectl cluster-info

# Check namespaces
kubectl get namespaces

# To clean up
eksctl delete cluster --region=us-east-1 --name=clickhouse-demo-cluster
```

- [x] Create Namespaces for Project

```bash
# [x] Create namespace for ClickHouse
kubectl create namespace clickhouse

# Create namespace for monitoring
kubectl create namespace monitoring

# Create namespace for metrics pipeline
kubectl create namespace metrics-pipeline

# Verify
kubectl get namespaces
```

- [x] Create IAM Ploicy for S3 Access

```bash
# Create policy
aws iam create-policy \
  --policy-name ClickHousePipelineS3Access \
  --policy-document file://infra/iam/policies/pipeline-s3-policy.json

POLICY_ARN="$(aws iam list-policies --scope Local \
  --query "Policies[?PolicyName=='ClickHousePipelineS3Access'] | [0].Arn" \
  --output text \
  --profile clickhouse-demo)"
echo "$POLICY_ARN"

```

- Create Kubernetes service accounts with IRSA:

```bash

# Create service account for OTEL Collector
eksctl create iamserviceaccount \
  --cluster=${CLUSTER_NAME} \
  --namespace=clickhouse \
  --name=otel-collector-sa \
  --attach-policy-arn=${POLICY_ARN} \
  --approve \
  --override-existing-serviceaccounts

# Create service account for Parquet Converter
eksctl create iamserviceaccount \
  --cluster=${CLUSTER_NAME} \
  --namespace=clickhouse \
  --name=parquet-converter-sa \
  --attach-policy-arn=${POLICY_ARN} \
  --approve \
  --override-existing-serviceaccounts

# Verify IRSA role
kubectl describe sa otel-collector-sa -n clickhouse

# To delete a service account
kubectl delete serviceaccount otel-collector-sa -n clickhouse
```

- Save Configuration for Later

```bash
# Save important variables
cat > setup-env.sh <<EOF
#!/bin/bash
export AWS_PROFILE=clickhouse-demo
export AWS_REGION=us-east-1
export BUCKET_NAME=$BUCKET_NAME
export CLUSTER_NAME=clickhouse-demo-cluster
export POLICY_ARN=$POLICY_ARN

echo "Environment variables loaded:"
echo "AWS_PROFILE: \$AWS_PROFILE"
echo "AWS_REGION: \$AWS_REGION"
echo "BUCKET_NAME: \$BUCKET_NAME"
echo "CLUSTER_NAME: \$CLUSTER_NAME"
echo "POLICY_ARN: \$POLICY_ARN"
EOF

# Make it executable
chmod +x setup-env.sh

# Add to .gitignore to avoid committing sensitive info
echo "setup-env.sh" >> .gitignore

# Use it in future sessions
source setup-env.sh
```

- Cleanup (When Finished with Demo)

```bash
# Delete service accounts
eksctl delete iamserviceaccount --name otel-collector-sa --namespace metrics-pipeline --cluster clickhouse-demo-cluster --profile clickhouse-demo
eksctl delete iamserviceaccount --name parquet-converter-sa --namespace metrics-pipeline --cluster clickhouse-demo-cluster --profile clickhouse-demo
eksctl delete iamserviceaccount --name clickhouse-sa --namespace clickhouse --cluster clickhouse-demo-cluster --profile clickhouse-demo

# Delete EKS cluster
eksctl delete cluster --name clickhouse-demo-cluster --profile clickhouse-demo

# Empty and delete S3 bucket
aws s3 rm s3://$BUCKET_NAME --recursive --profile clickhouse-demo
aws s3api delete-bucket --bucket $BUCKET_NAME --profile clickhouse-demo

# Delete IAM policy
aws iam delete-policy --policy-arn $POLICY_ARN --profile clickhouse-demo

# Delete IAM user access keys
aws iam list-access-keys --user-name clickhouse-demo-admin --profile clickhouse-demo
aws iam delete-access-key --user-name clickhouse-demo-admin --access-key-id <KEY_ID> --profile clickhouse-demo

# Delete IAM user
aws iam detach-user-policy --user-name clickhouse-demo-admin --policy-arn arn:aws:iam::aws:policy/AdministratorAccess --profile clickhouse-demo
aws iam delete-user --user-name clickhouse-demo-admin --profile clickhouse-demo
```
