# Implementation Plan: ClickHouse Compute Performance Benchmarking

## Project Overview

Compare ClickHouse query performance between:

- **Option 1**: Direct S3 data querying (External Tables with Parquet files)
- **Option 2**: Data ingestion into ClickHouse via Lambda

**Cloud Strategy**: Run on AWS initially, but maintain cloud-agnostic architecture for portability to Azure/GCP.

## Architecture Components

### Common Components (Both Options)

1. **Data Generation Application**
   - Application generating OTEL metrics
   - Deployed on Kubernetes (AWS EKS initially)

2. **OTEL Collector**
   - Export metrics as JSON files to S3
   - Deployed on Kubernetes (AWS EKS)

3. **JSON to Parquet Converter Service (NEW)**
   - **Initial Implementation**: Python/PyArrow on Kubernetes
   - Converts JSON files to Parquet format
   - Implements Hive-style partitioning (year/month/day/hour)
   - Deployed as Kubernetes CronJob or event-triggered
   - **Cloud Agnostic**: Works with S3, GCS, Azure Blob
   - **Migration Path**: Can upgrade to Spark if data volumes require

4. **ClickHouse Cluster**
   - Deployed on Kubernetes (AWS EKS)
   - Central query engine for both options

5. **Dashboard Web Application**
   - React + ECharts frontend
   - Queries ClickHouse for metrics visualization
   - Deployed on Kubernetes (AWS EKS)

6. **Cloud Object Storage**
   - AWS S3 (initial deployment)
   - Stores raw JSON files (from OTEL Collector)
   - Stores processed Parquet files (Hive partitions)
   - Can be replaced with GCS or Azure Blob

### Option 1 Specific Components

- ClickHouse S3 table engine configuration for Parquet
- External table definitions for runtime S3 queries
- Queries Parquet files with Hive partitions

### Option 2 Specific Components

- Lambda function (or K8s CronJob for cloud-agnostic alternative)
- EventBridge/CloudWatch Events (10-minute trigger)
- Lambda to ClickHouse data ingestion pipeline

## Implementation Phases

### Phase 1: AWS Infrastructure Setup

**Objective**: Prepare AWS environment and IAM configuration

#### Tasks

1. **AWS Account Setup**
   - Create dedicated IAM Administrator user
   - Download and configure Access Key and Secret
   - Install and configure AWS CLI
   - Set up AWS CLI profile

2. **S3 Bucket Creation**
   - Create S3 bucket for OTEL metrics storage
   - Configure bucket policies and permissions
   - Set up lifecycle policies if needed

3. **EKS Cluster Setup**
   - Create VPC and networking components
   - Deploy EKS cluster
   - Configure kubectl access
   - Set up IAM roles for service accounts (IRSA)

### Phase 2: ClickHouse Deployment

**Objective**: Deploy and configure ClickHouse on EKS

#### Tasks

1. **ClickHouse Installation**
   - Deploy ClickHouse operator or helm chart
   - Configure storage class and persistent volumes
   - Set up ClickHouse cluster (single node or multi-node)

2. **Database Schema Design**
   - Design OTEL metrics table schema
   - Create database and tables for Option 2
   - Configure partitioning strategy

3. **S3 Integration (Option 1)**
   - Configure S3 access credentials/IAM roles
   - Create external table definitions using S3 engine
   - Test S3 connectivity and queries

### Phase 3: Data Generation and Conversion Pipeline

**Objective**: Deploy application that generates OTEL metrics and converts to Parquet

#### Tasks

1. **Metrics Generation Application**
   - Develop/configure application generating OTEL metrics
   - Containerize the application
   - Create Kubernetes deployment manifests

2. **OTEL Collector Setup**
   - Configure OTEL collector with file exporter (awss3exporter)
   - Set up S3 destination configuration for JSON format
   - Configure output path structure (raw/YYYY/MM/DD/HH/)
   - Deploy collector to EKS

3. **JSON to Parquet Converter Service (Python/PyArrow)**
   - Develop Python conversion service using PyArrow
   - Implement cloud-agnostic storage interface (s3fs for S3, gcsfs for GCS, adlfs for Azure)
   - Add Hive partition logic (year=YYYY/month=MM/day=DD/hour=HH/)
   - Create Docker image for converter
   - Deploy as Kubernetes CronJob (runs every 5-10 minutes)
   - Configure IAM role for S3 access (IRSA)
   - Add error handling and logging

4. **Testing Data Flow**
   - Verify metrics generation
   - Confirm S3 JSON file uploads to raw/ prefix
   - Validate converter execution and Parquet output
   - Verify Hive partition structure in processed/ prefix
   - Test ClickHouse can read Parquet files from S3

### Phase 4: Lambda Data Ingestion (Option 2)

**Objective**: Implement automated data ingestion from S3 to ClickHouse

#### Tasks

1. **Lambda Function Development**
   - Develop Lambda function in Python
   - Implement Parquet file reading logic from S3 (using PyArrow)
   - Implement ClickHouse insertion logic (clickhouse-driver)
   - Handle Hive partition reading and filtering
   - Add error handling and logging
   - Track processed files to avoid duplicates

2. **Lambda Deployment**
   - Package Lambda function with dependencies
   - Create Lambda execution role with necessary permissions (S3 read, VPC access)
   - Deploy to AWS Lambda
   - Configure VPC access to EKS for ClickHouse connectivity
   - Set memory and timeout appropriately (5-10 minutes)

3. **Scheduling Setup**
   - Create EventBridge rule for 10-minute interval
   - Connect EventBridge to Lambda function
   - Configure retry policy for failures
   - Test scheduled execution and data ingestion

### Phase 5: Dashboard Application

**Objective**: Deploy web application for metrics visualization

#### Tasks

1. **Frontend Development**
   - Set up React application structure
   - Integrate ECharts library
   - Develop visualization components (one simple line chart)
   - Create API client for ClickHouse queries
   - Add toggle to switch between Option 1 and Option 2 data sources

2. **Backend API (Optional)**
   - Create a simple Node.js API service
   - Implement ClickHouse query endpoints
   - Add authentication if required

3. **Containerization and Deployment**
   - Create Dockerfile for dashboard
   - Build and push to container registry (ECR/DockerHub)
   - Create Kubernetes deployment manifests
   - Deploy to EKS
   - Set up ingress/load balancer for external access

### Phase 6: Performance Benchmarking

**Objective**: Execute performance tests and collect metrics

#### Tasks

1. **Test Scenario Design**
   - Define representative query patterns (simple aggregations, complex joins, time-range queries)
   - Create test data volume scenarios (1GB, 10GB, 50GB)
   - Document query complexity variations
   - Prepare benchmark scripts

2. **Option 1 Testing (S3 External Tables)**
   - Execute queries against S3 Parquet files via external tables
   - Measure query response times (p50, p95, p99)
   - Monitor ClickHouse resource utilization (CPU, memory, network I/O)
   - Track S3 data transfer costs
   - Collect detailed metrics and logs

3. **Option 2 Testing (Ingested Data)**
   - Execute same queries against ingested ClickHouse tables
   - Measure query response times (p50, p95, p99)
   - Monitor ClickHouse resource utilization (CPU, memory, disk I/O)
   - Measure data freshness/latency (10-minute ingestion lag)
   - Collect detailed metrics and logs

4. **Data Volume Scalability Testing**
   - Evaluate if Python/PyArrow converter handles data volume adequately
   - If converter struggles (>15 min processing time or OOM errors), migrate to Spark
   - Deploy Spark on Kubernetes if needed
   - Re-test conversion performance

5. **Comparative Analysis**
   - Compare query performance between options
   - Analyze resource consumption differences
   - Evaluate cost implications (compute, storage, data transfer)
   - Document trade-offs (performance vs data freshness vs cost)
   - Create performance comparison charts

### Phase 7: Monitoring and Observability

**Objective**: Set up monitoring for the entire system

#### Tasks

1. **ClickHouse Monitoring**
   - Set up Prometheus + Grafana on Kubernetes
   - Configure ClickHouse metrics export
   - Create performance dashboards (query latency, throughput, resource usage)
   - Monitor system tables for query performance

2. **Application Monitoring**
   - Monitor data generation application (metrics rate)
   - Monitor JSON to Parquet converter (CronJob execution, processing time)
   - Monitor Lambda execution (Option 2) - invocation count, duration, errors
   - Track S3 operations (PUT/GET requests, data transfer)

3. **EKS Cluster Monitoring**
   - Configure cluster-level metrics (Metrics Server)
   - Monitor pod resource utilization
   - Set up logging aggregation (CloudWatch or ELK stack)
   - Create alerting rules for failures

### Phase 8: Documentation and Teardown

**Objective**: Document findings and clean up resources

#### Tasks

1. **Results Documentation**
   - Document performance results with detailed metrics
   - Create comparison charts and graphs
   - Write analysis report comparing both options
   - Document lessons learned and recommendations
   - Include cost analysis breakdown

2. **Infrastructure Teardown**
   - Delete EKS cluster and node groups
   - Remove S3 buckets (ensure data backup if needed)
   - Delete Lambda functions and EventBridge rules
   - Remove IAM roles, policies, and service accounts
   - Delete VPC and networking components
   - Verify all AWS resources are removed (check billing dashboard)

## Technical Specifications

### Data Schema

```sql
-- Option 2: ClickHouse Internal Table (Ingested Data)
CREATE TABLE otel_metrics (
    timestamp DateTime,
    metric_name String,
    metric_value Float64,
    resource_attributes Map(String, String),
    metric_attributes Map(String, String),
    partition_date Date
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(partition_date)
ORDER BY (metric_name, timestamp);

-- Option 1: ClickHouse External Table (S3 Parquet)
CREATE TABLE otel_metrics_s3 (
    timestamp DateTime,
    metric_name String,
    metric_value Float64,
    resource_attributes Map(String, String),
    metric_attributes Map(String, String)
) ENGINE = S3(
    's3://bucket-name/processed/year=*/month=*/day=*/hour=*/*.parquet',
    'Parquet'
);
```

### S3 Storage Structure

```
s3://bucket-name/
├── raw/                          # JSON files from OTEL Collector
│   └── 2025/
│       └── 11/
│           └── 11/
│               └── 14/
│                   └── metrics.json
└── processed/                    # Parquet files with Hive partitions
    ├── year=2025/
    │   └── month=11/
    │       └── day=11/
    │           └── hour=14/
    │               └── metrics.parquet
```

### Python/PyArrow Converter Example

```python
import pyarrow as pa
import pyarrow.parquet as pq
import s3fs
import json

def convert_json_to_parquet(input_path, output_path):
    """Convert JSON to Parquet with Hive partitioning"""
    # Cloud-agnostic filesystem (s3fs, gcsfs, adlfs)
    fs = s3fs.S3FileSystem()

    # Read JSON files
    with fs.open(input_path) as f:
        data = json.load(f)

    # Convert to Arrow Table
    table = pa.Table.from_pylist(data)

    # Write with Hive partitioning
    pq.write_to_dataset(
        table,
        root_path=output_path,
        partition_cols=['year', 'month', 'day', 'hour'],
        filesystem=fs,
        existing_data_behavior='overwrite_or_ignore'
    )
```

### Query Examples for Testing

1. **Simple Time-Range Aggregation**

   ```sql
   SELECT
       toStartOfHour(timestamp) as hour,
       avg(metric_value) as avg_value
   FROM otel_metrics
   WHERE timestamp >= now() - INTERVAL 24 HOUR
   GROUP BY hour
   ORDER BY hour;
   ```

2. **Metric Filtering with Attributes**

   ```sql
   SELECT
       metric_name,
       avg(metric_value) as avg_value
   FROM otel_metrics
   WHERE resource_attributes['service.name'] = 'api-service'
     AND timestamp >= now() - INTERVAL 1 HOUR
   GROUP BY metric_name;
   ```

3. **Complex Multi-Metric Join**

   ```sql
   SELECT
       a.timestamp,
       a.metric_value as cpu_usage,
       b.metric_value as memory_usage
   FROM otel_metrics a
   JOIN otel_metrics b ON a.timestamp = b.timestamp
   WHERE a.metric_name = 'cpu.usage'
     AND b.metric_name = 'memory.usage'
     AND a.timestamp >= now() - INTERVAL 6 HOUR;
   ```

## Infrastructure as Code Structure

```
project-root/
├── infra/
│   ├── terraform/
│   │   ├── vpc/
│   │   ├── eks/
│   │   ├── s3/
│   │   └── lambda/
│   └── kubernetes/
│       ├── clickhouse/
│       │   ├── deployment.yaml
│       │   └── service.yaml
│       ├── otel-collector/
│       │   ├── configmap.yaml
│       │   └── deployment.yaml
│       ├── parquet-converter/
│       │   ├── cronjob.yaml
│       │   └── service-account.yaml
│       ├── metrics-app/
│       │   └── deployment.yaml
│       └── dashboard/
│           ├── deployment.yaml
│           └── service.yaml
├── src/
│   ├── parquet-converter/
│   │   ├── converter.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── lambda-ingestion/
│   │   ├── handler.py
│   │   └── requirements.txt
│   ├── metrics-generator/
│   │   └── app.py
│   └── dashboard/
│       ├── frontend/
│       └── backend/
└── docs/
    └── architecture-diagrams/
```

## Key Performance Indicators

- **Query response time** (p50, p95, p99) for both options
- **Data freshness** - Real-time (Option 1) vs 10-minute lag (Option 2)
- **Resource utilization** (CPU, Memory, Network I/O, Disk I/O)
- **Conversion performance** - JSON to Parquet processing time
- **Cost per query** - Compute and data transfer costs
- **Storage costs** - Parquet compression vs ClickHouse native storage
- **Data ingestion latency** (Option 2)
- **Scalability** - Performance at different data volumes (1GB, 10GB, 50GB)

## Success Criteria

1. Both options fully functional end-to-end
2. Performance metrics collected for meaningful comparison across multiple query types
3. Dashboard successfully visualizes data from both options
4. JSON to Parquet converter working reliably with cloud-agnostic code
5. Clear documentation of performance characteristics and trade-offs
6. Decision point evaluated: Python/PyArrow vs Spark for conversion
7. Complete cleanup of AWS resources

## Estimated Timeline

- **Phase 1**: 1-2 days (AWS Infrastructure Setup)
- **Phase 2**: 2-3 days (ClickHouse Deployment)
- **Phase 3**: 3-4 days (Data Generation and Conversion Pipeline - includes converter development)
- **Phase 4**: 2-3 days (Lambda Data Ingestion for Option 2)
- **Phase 5**: 3-4 days (Dashboard Application)
- **Phase 6**: 3-4 days (Performance Benchmarking - includes potential Spark migration)
- **Phase 7**: 1-2 days (Monitoring and Observability)
- **Phase 8**: 1 day (Documentation and Teardown)

**Total**: 16-23 days

## Prerequisites

- AWS account with appropriate permissions
- Local development environment with:
  - AWS CLI configured
  - kubectl
  - Docker
  - Terraform or eksctl (for EKS setup)
  - Python 3.9+ (for converter and Lambda development)
  - Node.js 18+ (for dashboard development)
- Basic knowledge of:
  - Kubernetes and container orchestration
  - ClickHouse SQL and architecture
  - AWS services (EKS, S3, Lambda, IAM)
  - OTEL metrics and observability
  - Python data processing (Pandas/PyArrow)

## Cloud Portability Notes

**To migrate from AWS to GCP:**

- Replace S3 with Google Cloud Storage (GCS)
- Replace EKS with GKE
- Replace Lambda with Cloud Functions or Cloud Run Jobs
- Use `gcsfs` instead of `s3fs` in Python converter
- Update IAM roles to GCP Service Accounts

**To migrate from AWS to Azure:**

- Replace S3 with Azure Blob Storage
- Replace EKS with AKS
- Replace Lambda with Azure Functions or Azure Container Apps
- Use `adlfs` instead of `s3fs` in Python converter
- Update IAM roles to Azure Managed Identities

## Risk Considerations

1. **Cost Management**: Monitor AWS costs closely (EKS, S3 storage, S3 data transfer, Lambda)
2. **Network Configuration**: EKS to Lambda connectivity may require VPC configuration
3. **Data Volume**: Python/PyArrow converter may need Spark migration if data exceeds 10-20GB/hour
4. **Performance Variables**: Network latency and S3 throttling may affect results
5. **Time Constraints**: Ensure adequate testing time before teardown
6. **OTEL Collector Limitations**: No native Parquet support requires converter service
7. **ClickHouse S3 Integration**: May have performance overhead with large partition scans

## Architecture Diagrams

### Data Flow Architecture

```
┌─────────────────┐
│  Metrics App    │
│  (OTEL SDK)     │
└────────┬────────┘
         │ OTEL Protocol
         ▼
┌─────────────────┐
│ OTEL Collector  │
│   (on K8s)      │
└────────┬────────┘
         │ JSON Export
         ▼
┌─────────────────────────────┐
│      S3 Bucket (raw/)       │
│    JSON files (raw data)    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Parquet Converter         │
│   (Python/PyArrow)          │
│   K8s CronJob              │
└────────┬────────────────────┘
         │ Parquet files
         ▼
┌─────────────────────────────┐
│   S3 Bucket (processed/)    │
│   Parquet + Hive partitions │
└────────┬────────────────────┘
         │
         ├──────────────────┬─────────────────┐
         │                  │                 │
         ▼                  ▼                 ▼
┌────────────────┐   ┌─────────────┐   ┌─────────────┐
│ Option 1:      │   │ Option 2:   │   │  Dashboard  │
│ ClickHouse     │   │   Lambda    │   │   (React +  │
│ External Table │   │ Ingestion   │   │   ECharts)  │
│ (Query S3)     │   └──────┬──────┘   └──────┬──────┘
└────────┬───────┘          │                 │
         │                  ▼                 │
         │          ┌──────────────┐          │
         │          │ ClickHouse   │          │
         └──────────┤ Internal     ├──────────┘
                    │ Tables       │
                    └──────────────┘
```

### Option 1: Direct S3 Querying

```
┌──────────────┐
│  Dashboard   │
│  (Browser)   │
└──────┬───────┘
       │ HTTP/Query
       ▼
┌──────────────────────┐
│   ClickHouse         │
│   (on K8s)           │
└──────┬───────────────┘
       │ S3 API (Read Parquet)
       ▼
┌──────────────────────┐
│  S3 (processed/)     │
│  Parquet Files       │
└──────────────────────┘

Pros: Real-time data, no ingestion delay
Cons: Higher query latency, S3 data transfer costs
```

### Option 2: Lambda Ingestion

```
┌──────────────┐
│ EventBridge  │
│  (10 min)    │
└──────┬───────┘
       │ Trigger
       ▼
┌──────────────────────┐
│   Lambda Function    │
│   (Read Parquet)     │
└──────┬───────────────┘
       │ Read          │ Write
       ▼               ▼
┌─────────────┐  ┌────────────────┐
│ S3 Bucket   │  │  ClickHouse    │
│(processed/) │  │  Internal      │
└─────────────┘  │  Tables        │
                 └────────┬───────┘
                          │ Query
                          ▼
                 ┌────────────────┐
                 │   Dashboard    │
                 └────────────────┘

Pros: Fast queries, optimized storage
Cons: 10-minute data lag, ingestion cost
```
