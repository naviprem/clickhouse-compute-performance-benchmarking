-- Create database for Option 2
CREATE DATABASE IF NOT EXISTS metrics_ingested;

USE metrics_ingested;

-- Create MergeTree table for ingested data
CREATE TABLE IF NOT EXISTS otel_metrics
(
    timestamp DateTime,
    metric_name String,
    metric_value Float64,
    resource_attributes Map(String, String),
    metric_attributes Map(String, String),
    partition_date Date DEFAULT toDate(timestamp)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(partition_date)
ORDER BY (metric_name, timestamp)
SETTINGS index_granularity = 8192;

-- Insert sample test data
INSERT INTO otel_metrics (timestamp, metric_name, metric_value, resource_attributes, metric_attributes)
VALUES
    (now() - INTERVAL 1 HOUR, 'cpu.usage', 45.5, map('service.name', 'api-service', 'host', 'server-1'), map('unit', 'percent')),
    (now() - INTERVAL 2 HOUR, 'cpu.usage', 52.3, map('service.name', 'api-service', 'host', 'server-1'), map('unit', 'percent')),
    (now() - INTERVAL 1 HOUR, 'memory.usage', 1024.0, map('service.name', 'api-service', 'host', 'server-1'), map('unit', 'MB')),
    (now() - INTERVAL 2 HOUR, 'memory.usage', 980.5, map('service.name', 'api-service', 'host', 'server-1'), map('unit', 'MB'));

-- Verify data
SELECT
    metric_name,
    count() as count,
    avg(metric_value) as avg_value
FROM otel_metrics
GROUP BY metric_name;

-- Show tables
SHOW TABLES;
