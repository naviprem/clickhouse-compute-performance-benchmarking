#!/usr/bin/env python3
"""
Convert OTEL JSON metrics from S3 to Parquet with Hive partitioning.
Moves processed files to archive to prevent duplicates.
"""

import json
import os
import boto3
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from collections import defaultdict

# Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "clickhouse-demo-metrics-np-2025")
RAW_PREFIX = os.getenv("RAW_PREFIX", "raw")
PROCESSED_PREFIX = os.getenv("PROCESSED_PREFIX", "processed")
ARCHIVE_PREFIX = os.getenv("ARCHIVE_PREFIX", "archive")
LOOKBACK_HOURS = float(os.getenv("LOOKBACK_HOURS", "0.2"))  # 12 minutes default

s3_client = boto3.client('s3')

def list_raw_files(bucket, prefix, lookback_hours):
    """List JSON files from S3 raw prefix within lookback window."""
    now = datetime.utcnow()
    start_time = now - timedelta(hours=lookback_hours)

    files = []
    try:
        paginator = s3_client.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                if obj['Key'].endswith('.json'):
                    # Check if file is within lookback window
                    if obj['LastModified'].replace(tzinfo=None) >= start_time:
                        files.append(obj['Key'])
    except Exception as e:
        print(f"Error listing files: {e}")

    return files

def parse_otel_metrics(otel_data):
    """Parse OTEL Protocol format to flat metric records."""
    records = []

    # Handle OTEL Protocol format: resourceMetrics -> scopeMetrics -> metrics
    resource_metrics_list = otel_data.get('resourceMetrics', [])

    for resource_metrics in resource_metrics_list:
        # Extract resource attributes
        resource_attrs = {}
        resource = resource_metrics.get('resource', {})
        for attr in resource.get('attributes', []):
            key = attr.get('key', '')
            value_obj = attr.get('value', {})
            # Extract value from nested structure
            if 'stringValue' in value_obj:
                resource_attrs[key] = str(value_obj['stringValue'])
            elif 'intValue' in value_obj:
                resource_attrs[key] = str(value_obj['intValue'])
            elif 'doubleValue' in value_obj:
                resource_attrs[key] = str(value_obj['doubleValue'])

        # Iterate through scope metrics
        for scope_metrics in resource_metrics.get('scopeMetrics', []):
            # Iterate through metrics
            for metric in scope_metrics.get('metrics', []):
                metric_name = metric.get('name', 'unknown')
                metric_description = metric.get('description', '')
                metric_unit = metric.get('unit', '')

                # Handle different metric types: gauge, sum, histogram
                data_points = []
                metric_type = 'unknown'

                # Gauge metrics
                if 'gauge' in metric:
                    data_points = metric['gauge'].get('dataPoints', [])
                    metric_type = 'gauge'

                # Sum metrics (counters)
                elif 'sum' in metric:
                    data_points = metric['sum'].get('dataPoints', [])
                    metric_type = 'sum'

                # Histogram metrics
                elif 'histogram' in metric:
                    data_points = metric['histogram'].get('dataPoints', [])
                    metric_type = 'histogram'

                # Process each data point
                for dp in data_points:
                    # Extract timestamp (nanoseconds to seconds)
                    time_unix_nano = dp.get('timeUnixNano', 0)
                    # Convert to int if it's a string
                    if isinstance(time_unix_nano, str):
                        time_unix_nano = int(time_unix_nano)
                    timestamp = datetime.utcfromtimestamp(time_unix_nano / 1e9)

                    # Extract value based on type
                    value = None
                    if 'asDouble' in dp:
                        value = dp['asDouble']
                    elif 'asInt' in dp:
                        value = float(dp['asInt'])
                    elif 'sum' in dp:  # For histograms
                        value = dp['sum']
                    elif 'count' in dp:  # Alternative for histograms
                        value = float(dp['count'])

                    if value is not None:
                        # Extract data point attributes
                        dp_attrs = {}
                        for attr in dp.get('attributes', []):
                            key = attr.get('key', '')
                            value_obj = attr.get('value', {})
                            if 'stringValue' in value_obj:
                                dp_attrs[key] = str(value_obj['stringValue'])
                            elif 'intValue' in value_obj:
                                dp_attrs[key] = str(value_obj['intValue'])
                            elif 'doubleValue' in value_obj:
                                dp_attrs[key] = str(value_obj['doubleValue'])

                        # Create flattened record
                        record = {
                            'timestamp': timestamp,
                            'metric_name': metric_name,
                            'metric_value': value,
                            'metric_type': metric_type,
                            'metric_unit': metric_unit,
                            'metric_description': metric_description,
                            'resource_attributes': resource_attrs,
                            'metric_attributes': dp_attrs,
                            'year': timestamp.year,
                            'month': timestamp.month,
                            'day': timestamp.day,
                            'hour': timestamp.hour,
                        }

                        records.append(record)

    return records

def download_and_parse_json(bucket, key):
    """Download JSON file from S3 and parse OTEL Protocol format metrics."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')

        records = []
        for line in content.strip().split('\n'):
            if not line:
                continue
            try:
                otel_data = json.loads(line)
                # Parse OTEL Protocol format
                parsed_metrics = parse_otel_metrics(otel_data)
                records.extend(parsed_metrics)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line in {key}: {e}")
                continue
            except Exception as e:
                print(f"Warning: Failed to parse OTEL data: {e}")
                continue

        return records
    except Exception as e:
        print(f"Error downloading {key}: {e}")
        return []

def convert_to_parquet_records(json_metrics):
    """Convert parsed metrics to Parquet-compatible records (already parsed by download_and_parse_json)."""
    # Records are already in the correct format from parse_otel_metrics
    return json_metrics

def write_parquet_to_s3(records, bucket, prefix):
    """Write records to S3 as Parquet with Hive partitioning."""
    if not records:
        print("No records to write")
        return 0

    # Group records by partition
    partitions = defaultdict(list)
    for record in records:
        partition_key = (record['year'], record['month'], record['day'], record['hour'])
        partitions[partition_key].append(record)

    total_written = 0

    for (year, month, day, hour), partition_records in partitions.items():
        # Create DataFrame
        df = pd.DataFrame(partition_records)

        # Define schema
        schema = pa.schema([
            pa.field('timestamp', pa.timestamp('us')),
            pa.field('metric_name', pa.string()),
            pa.field('metric_value', pa.float64()),
            pa.field('metric_type', pa.string()),
            pa.field('metric_unit', pa.string()),
            pa.field('metric_description', pa.string()),
            pa.field('resource_attributes', pa.map_(pa.string(), pa.string())),
            pa.field('metric_attributes', pa.map_(pa.string(), pa.string())),
            pa.field('year', pa.uint16()),
            pa.field('month', pa.uint8()),
            pa.field('day', pa.uint8()),
            pa.field('hour', pa.uint8()),
        ])

        # Convert to Arrow table
        table = pa.Table.from_pandas(df, schema=schema)

        # Write to local file first
        local_path = f"/tmp/part-{year}-{month:02d}-{day:02d}-{hour:02d}.parquet"
        pq.write_table(table, local_path, compression='snappy')

        # Upload to S3 with Hive partitioning
        timestamp_suffix = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        s3_key = f"{prefix}/year={year}/month={month}/day={day}/hour={hour}/part-{timestamp_suffix}.parquet"

        try:
            s3_client.upload_file(local_path, bucket, s3_key)
            print(f"✓ Uploaded {len(partition_records)} records to s3://{bucket}/{s3_key}")
            total_written += len(partition_records)

            # Cleanup local file
            os.remove(local_path)
        except Exception as e:
            print(f"✗ Failed to upload {s3_key}: {e}")

    return total_written

def move_to_archive(bucket, source_key, archive_prefix):
    """Move processed file to archive to prevent reprocessing."""
    # Create archive key preserving directory structure
    archive_key = source_key.replace(RAW_PREFIX, archive_prefix, 1)

    try:
        # Copy to archive
        s3_client.copy_object(
            Bucket=bucket,
            CopySource={'Bucket': bucket, 'Key': source_key},
            Key=archive_key
        )

        # Delete from raw
        s3_client.delete_object(Bucket=bucket, Key=source_key)

        return True
    except Exception as e:
        print(f"✗ Failed to archive {source_key}: {e}")
        return False

def main():
    print(f"Starting Parquet converter")
    print(f"S3 Bucket: {S3_BUCKET}")
    print(f"Raw prefix: {RAW_PREFIX}")
    print(f"Processed prefix: {PROCESSED_PREFIX}")
    print(f"Archive prefix: {ARCHIVE_PREFIX}")
    print(f"Lookback: {LOOKBACK_HOURS} hours ({LOOKBACK_HOURS * 60} minutes)")
    print()

    # List raw JSON files
    print("Listing raw files...")
    raw_files = list_raw_files(S3_BUCKET, RAW_PREFIX, LOOKBACK_HOURS)
    print(f"Found {len(raw_files)} files to process")

    if not raw_files:
        print("No files to process")
        return

    # Download and parse all files
    all_records = []
    processed_files = []

    for file_key in raw_files:
        print(f"Processing {file_key}...", end=" ")
        json_metrics = download_and_parse_json(S3_BUCKET, file_key)

        if json_metrics:
            records = convert_to_parquet_records(json_metrics)
            all_records.extend(records)
            processed_files.append(file_key)
            print(f"✓ {len(records)} records")
        else:
            print("✗ No records")

    print()
    print(f"Total records: {len(all_records)}")

    if not all_records:
        print("No records to convert")
        return

    # Write to Parquet
    print("Writing Parquet files to S3...")
    total_written = write_parquet_to_s3(all_records, S3_BUCKET, PROCESSED_PREFIX)

    print()
    print(f"✓ Conversion complete: {total_written} records written")

    # Move processed files to archive
    print()
    print("Moving processed files to archive...")
    archived_count = 0

    for file_key in processed_files:
        print(f"Archiving {file_key}...", end=" ")
        if move_to_archive(S3_BUCKET, file_key, ARCHIVE_PREFIX):
            print("✓")
            archived_count += 1
        else:
            print("✗")

    print()
    print(f"✓ Archived {archived_count}/{len(processed_files)} files")
    print()
    print("Summary:")
    print(f"  - Files processed: {len(processed_files)}")
    print(f"  - Records converted: {total_written}")
    print(f"  - Files archived: {archived_count}")

if __name__ == "__main__":
    main()
