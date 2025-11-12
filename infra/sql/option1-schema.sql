-- Create database for Option 1
CREATE DATABASE IF NOT EXISTS metrics_s3;

USE metrics_s3;

DROP TABLE IF EXISTS otel_metrics_s3;
-- Create S3 external table
-- Replace 'clickhouse-demo-metrics-np-2025' with your actual bucket name
CREATE TABLE IF NOT EXISTS otel_metrics_s3
(
    timestamp DateTime,
    metric_name String,
    metric_value Float64,
    resource_attributes Map(String, String),
    metric_attributes Map(String, String),
    year UInt16,
    month UInt8,
    day UInt8,
    hour UInt8
)
ENGINE = S3(
    'https://clickhouse-demo-metrics-np-2025.s3.us-east-1.amazonaws.com/processed/year=*/month=*/day=*/hour=*/*.parquet',
    'Parquet'
);

-- Show tables
SHOW TABLES;
