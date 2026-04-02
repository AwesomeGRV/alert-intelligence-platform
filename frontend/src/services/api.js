import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Dashboard API
export const fetchDashboardOverview = async () => {
  const response = await api.get('/api/v1/dashboard/overview');
  return response.data;
};

export const fetchAlertTrends = async (hours = 24) => {
  const response = await api.get('/api/v1/dashboard/alerts/trends', {
    params: { hours }
  });
  return response.data;
};

export const fetchIncidentTrends = async (days = 7) => {
  const response = await api.get('/api/v1/dashboard/incidents/trends', {
    params: { days }
  });
  return response.data;
};

export const fetchServiceNoiseScores = async () => {
  const response = await api.get('/api/v1/dashboard/services/noise-score');
  return response.data;
};

export const fetchServicesHealth = async () => {
  const response = await api.get('/api/v1/dashboard/services/health');
  return response.data;
};

export const fetchRealtimeMetrics = async () => {
  const response = await api.get('/api/v1/dashboard/metrics/realtime');
  return response.data;
};

// Alerts API
export const fetchAlerts = async (params = {}) => {
  const response = await api.get('/api/v1/alerts/', { params });
  return response.data;
};

export const fetchAlert = async (alertId) => {
  const response = await api.get(`/api/v1/alerts/${alertId}`);
  return response.data;
};

export const updateAlert = async (alertId, data) => {
  const response = await api.put(`/api/v1/alerts/${alertId}`, data);
  return response.data;
};

export const deleteAlert = async (alertId) => {
  const response = await api.delete(`/api/v1/alerts/${alertId}`);
  return response.data;
};

export const searchAlerts = async (query, size = 50) => {
  const response = await api.get('/api/v1/alerts/search/fulltext', {
    params: { q: query, size }
  });
  return response.data;
};

export const ingestAlert = async (alertData) => {
  const response = await api.post('/api/v1/alerts/ingest', alertData);
  return response.data;
};

// Incidents API
export const fetchIncidents = async (params = {}) => {
  const response = await api.get('/api/v1/incidents/', { params });
  return response.data;
};

export const fetchIncident = async (clusterId) => {
  const response = await api.get(`/api/v1/incidents/${clusterId}`);
  return response.data;
};

export const createIncident = async (incidentData) => {
  const response = await api.post('/api/v1/incidents/', incidentData);
  return response.data;
};

export const updateIncident = async (clusterId, data) => {
  const response = await api.put(`/api/v1/incidents/${clusterId}`, data);
  return response.data;
};

export const resolveIncident = async (clusterId, resolutionData) => {
  const response = await api.post(`/api/v1/incidents/${clusterId}/resolve`, resolutionData);
  return response.data;
};

export const fetchIncidentAlerts = async (clusterId, limit = 100) => {
  const response = await api.get(`/api/v1/incidents/${clusterId}/alerts`, {
    params: { limit }
  });
  return response.data;
};

export const fetchActiveIncidentsSummary = async () => {
  const response = await api.get('/api/v1/incidents/summary/active');
  return response.data;
};

export const searchIncidents = async (query, size = 50) => {
  const response = await api.get('/api/v1/incidents/search/fulltext', {
    params: { q: query, size }
  });
  return response.data;
};

// Services API
export const fetchTopServices = async (metric = 'alerts', limit = 10) => {
  const response = await api.get('/api/v1/dashboard/top/services', {
    params: { metric, limit }
  });
  return response.data;
};

export const fetchSLACompliance = async (days = 30, service = null) => {
  const response = await api.get('/api/v1/dashboard/sla/compliance', {
    params: { days, service }
  });
  return response.data;
};

export const fetchCorrelationInsights = async () => {
  const response = await api.get('/api/v1/dashboard/correlation/insights');
  return response.data;
};

// Utility functions
export const formatTimestamp = (timestamp) => {
  return new Date(timestamp).toLocaleString();
};

export const formatDuration = (minutes) => {
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
};

export const getSeverityColor = (severity) => {
  const colors = {
    critical: 'danger',
    high: 'warning',
    medium: 'primary',
    low: 'success',
    info: 'gray'
  };
  return colors[severity] || 'gray';
};

export const getStatusColor = (status) => {
  const colors = {
    active: 'danger',
    investigating: 'warning',
    identified: 'warning',
    monitoring: 'primary',
    resolved: 'success',
    closed: 'gray'
  };
  return colors[status] || 'gray';
};

export default api;
