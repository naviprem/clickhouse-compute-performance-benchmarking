const express = require('express');
const cors = require('cors');
const { createClient } = require('@clickhouse/client');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// ClickHouse client configuration
const clickhouseClient = createClient({
  host: process.env.CLICKHOUSE_HOST || 'http://clickhouse-option1:8123',
  username: process.env.CLICKHOUSE_USER || 'default',
  password: process.env.CLICKHOUSE_PASSWORD || '',
  database: process.env.CLICKHOUSE_DATABASE || 'metrics_s3',
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Metrics query endpoint - Option 1 (S3)
app.post('/api/metrics/option1', async (req, res) => {
  try {
    const { metricName, startTime, endTime } = req.body;

    const query = `
      SELECT
        toStartOfMinute(timestamp) as time,
        avg(metric_value) as avg_value,
        min(metric_value) as min_value,
        max(metric_value) as max_value
      FROM otel_metrics_s3
      WHERE metric_name = {metricName: String}
        AND timestamp >= {startTime: DateTime}
        AND timestamp <= {endTime: DateTime}
      GROUP BY time
      ORDER BY time
    `;

    const resultSet = await clickhouseClient.query({
      query,
      query_params: {
        metricName,
        startTime,
        endTime,
      },
      format: 'JSONEachRow',
    });

    const data = await resultSet.json();

    res.json({
      source: 'option1',
      metric: metricName,
      data,
      count: data.length,
    });
  } catch (error) {
    console.error('Option 1 query error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Metrics query endpoint - Option 2 (Ingested)
app.post('/api/metrics/option2', async (req, res) => {
  try {
    const { metricName, startTime, endTime } = req.body;

    const query = `
      SELECT
        toStartOfMinute(timestamp) as time,
        avg(metric_value) as avg_value,
        min(metric_value) as min_value,
        max(metric_value) as max_value
      FROM otel_metrics
      WHERE metric_name = {metricName: String}
        AND timestamp >= {startTime: DateTime}
        AND timestamp <= {endTime: DateTime}
      GROUP BY time
      ORDER BY time
    `;

    const resultSet = await clickhouseClient.query({
      query,
      query_params: {
        metricName,
        startTime,
        endTime,
      },
      format: 'JSONEachRow',
    });

    const data = await resultSet.json();

    res.json({
      source: 'option2',
      metric: metricName,
      data,
      count: data.length,
    });
  } catch (error) {
    console.error('Option 2 query error:', error);
    res.status(500).json({ error: error.message });
  }
});

// List available metrics
app.get('/api/metrics/list', async (req, res) => {
  try {
    const query = `
      SELECT DISTINCT metric_name
      FROM otel_metrics_s3
      LIMIT 100
    `;

    const resultSet = await clickhouseClient.query({
      query,
      format: 'JSONEachRow',
    });

    const metrics = await resultSet.json();

    res.json({ metrics: metrics.map(m => m.metric_name) });
  } catch (error) {
    console.error('List metrics error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Performance comparison endpoint
app.post('/api/metrics/compare', async (req, res) => {
  try {
    const { metricName, startTime, endTime } = req.body;

    // Query both options and measure performance
    const option1Start = Date.now();
    const option1Query = `
      SELECT count() as total
      FROM otel_metrics_s3
      WHERE metric_name = {metricName: String}
        AND timestamp >= {startTime: DateTime}
        AND timestamp <= {endTime: DateTime}
    `;
    const option1Result = await clickhouseClient.query({
      query: option1Query,
      query_params: { metricName, startTime, endTime },
      format: 'JSONEachRow',
    });
    const option1Data = await option1Result.json();
    const option1Duration = Date.now() - option1Start;

    const option2Start = Date.now();
    const option2Query = `
      SELECT count() as total
      FROM otel_metrics
      WHERE metric_name = {metricName: String}
        AND timestamp >= {startTime: DateTime}
        AND timestamp <= {endTime: DateTime}
    `;
    const option2Result = await clickhouseClient.query({
      query: option2Query,
      query_params: { metricName, startTime, endTime },
      format: 'JSONEachRow',
    });
    const option2Data = await option2Result.json();
    const option2Duration = Date.now() - option2Start;

    res.json({
      option1: {
        duration_ms: option1Duration,
        count: option1Data[0]?.total || 0,
      },
      option2: {
        duration_ms: option2Duration,
        count: option2Data[0]?.total || 0,
      },
      winner: option1Duration < option2Duration ? 'option1' : 'option2',
    });
  } catch (error) {
    console.error('Compare metrics error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`Dashboard API server running on port ${PORT}`);
  console.log(`ClickHouse host: ${process.env.CLICKHOUSE_HOST}`);
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, closing ClickHouse client...');
  await clickhouseClient.close();
  process.exit(0);
});