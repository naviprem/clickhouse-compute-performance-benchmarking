import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetchMetricsOption1 = async (metricName, startTime, endTime) => {
  const response = await apiClient.post('/api/metrics/option1', {
    metricName,
    startTime,
    endTime,
  });
  return response.data;
};

export const fetchMetricsOption2 = async (metricName, startTime, endTime) => {
  const response = await apiClient.post('/api/metrics/option2', {
    metricName,
    startTime,
    endTime,
  });
  return response.data;
};

export const listMetrics = async () => {
  const response = await apiClient.get('/api/metrics/list');
  return response.data.metrics;
};

export const comparePerformance = async (metricName, startTime, endTime) => {
  const response = await apiClient.post('/api/metrics/compare', {
    metricName,
    startTime,
    endTime,
  });
  return response.data;
};

export default apiClient;