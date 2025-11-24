import React, { useState, useEffect } from 'react';
import {
  Card,
  Select,
  DatePicker,
  Button,
  Switch,
  Space,
  Spin,
  Alert,
  Statistic,
  Row,
  Col
} from 'antd';
import dayjs from 'dayjs';
import MetricsChart from './MetricsChart';
import { fetchMetricsOption1, fetchMetricsOption2, listMetrics, comparePerformance } from '../services/api';

const { RangePicker } = DatePicker;

const Dashboard = () => {
  const [metrics, setMetrics] = useState([]);
  const [selectedMetric, setSelectedMetric] = useState(null);
  const [useOption2, setUseOption2] = useState(false);
  const [dateRange, setDateRange] = useState([
    dayjs().subtract(1, 'hour'),
    dayjs(),
  ]);
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [error, setError] = useState(null);
  const [performanceData, setPerformanceData] = useState(null);

  // Load available metrics on mount
  useEffect(() => {
    const loadMetrics = async () => {
      try {
        const metricsList = await listMetrics();
        setMetrics(metricsList);
        if (metricsList.length > 0) {
          setSelectedMetric(metricsList[0]);
        }
      } catch (err) {
        setError('Failed to load metrics list: ' + err.message);
      }
    };
    loadMetrics();
  }, []);

  const handleFetchMetrics = async () => {
    if (!selectedMetric) {
      setError('Please select a metric');
      return;
    }

    setLoading(true);
    setError(null);
    setChartData(null);

    try {
      const [start, end] = dateRange;
      const startTime = start.format('YYYY-MM-DD HH:mm:ss');
      const endTime = end.format('YYYY-MM-DD HH:mm:ss');

      const fetchFn = useOption2 ? fetchMetricsOption2 : fetchMetricsOption1;
      const result = await fetchFn(selectedMetric, startTime, endTime);

      setChartData(result);
    } catch (err) {
      setError('Failed to fetch metrics: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    if (!selectedMetric) {
      setError('Please select a metric');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const [start, end] = dateRange;
      const startTime = start.format('YYYY-MM-DD HH:mm:ss');
      const endTime = end.format('YYYY-MM-DD HH:mm:ss');

      const result = await comparePerformance(selectedMetric, startTime, endTime);
      setPerformanceData(result);
    } catch (err) {
      setError('Failed to compare performance: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <h1>ClickHouse Performance Dashboard</h1>

      <Card title="Query Controls" style={{ marginBottom: '24px' }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Row gutter={16}>
            <Col span={8}>
              <label>Select Metric:</label>
              <Select
                style={{ width: '100%', marginTop: '8px' }}
                value={selectedMetric}
                onChange={setSelectedMetric}
                options={metrics.map(m => ({ label: m, value: m }))}
                placeholder="Choose a metric"
              />
            </Col>

            <Col span={12}>
              <label>Time Range:</label>
              <RangePicker
                style={{ width: '100%', marginTop: '8px' }}
                showTime
                value={dateRange}
                onChange={setDateRange}
                format="YYYY-MM-DD HH:mm:ss"
              />
            </Col>

            <Col span={4}>
              <label>Data Source:</label>
              <div style={{ marginTop: '8px' }}>
                <Space>
                  <span>Option 1 (S3)</span>
                  <Switch checked={useOption2} onChange={setUseOption2} />
                  <span>Option 2 (Ingested)</span>
                </Space>
              </div>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col>
              <Button type="primary" onClick={handleFetchMetrics} loading={loading}>
                Fetch Metrics
              </Button>
            </Col>
            <Col>
              <Button onClick={handleCompare} loading={loading}>
                Compare Performance
              </Button>
            </Col>
          </Row>
        </Space>
      </Card>

      {error && (
        <Alert
          message="Error"
          description={error}
          type="error"
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: '24px' }}
        />
      )}

      {performanceData && (
        <Card title="Performance Comparison" style={{ marginBottom: '24px' }}>
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title="Option 1 (S3) Query Time"
                value={performanceData.option1.duration_ms}
                suffix="ms"
              />
              <p>Records: {performanceData.option1.count}</p>
            </Col>
            <Col span={8}>
              <Statistic
                title="Option 2 (Ingested) Query Time"
                value={performanceData.option2.duration_ms}
                suffix="ms"
              />
              <p>Records: {performanceData.option2.count}</p>
            </Col>
            <Col span={8}>
              <Statistic
                title="Winner"
                value={performanceData.winner === 'option1' ? 'Option 1' : 'Option 2'}
                valueStyle={{
                  color: performanceData.winner === 'option1' ? '#3f8600' : '#1890ff'
                }}
              />
            </Col>
          </Row>
        </Card>
      )}

      {loading && (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <Spin size="large" tip="Loading metrics..." />
        </div>
      )}

      {chartData && chartData.data && chartData.data.length > 0 && (
        <Card title="Metrics Visualization">
          <MetricsChart
            data={chartData.data}
            metricName={selectedMetric}
            source={chartData.source}
          />
          <p style={{ marginTop: '16px', color: '#666' }}>
            Total data points: {chartData.count}
          </p>
        </Card>
      )}

      {chartData && chartData.data && chartData.data.length === 0 && (
        <Alert
          message="No Data"
          description="No metrics found for the selected time range"
          type="info"
        />
      )}
    </div>
  );
};

export default Dashboard;