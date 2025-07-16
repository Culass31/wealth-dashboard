import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY;
const DEFAULT_USER_ID = import.meta.env.VITE_DEFAULT_USER_ID;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
});

// Add a request interceptor to include the user_id in params for GET requests
api.interceptors.request.use(
  (config) => {
    if (config.method === 'get') {
      config.params = { ...config.params, user_id: DEFAULT_USER_ID };
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const getGlobalKpis = () => api.get('/api/v1/kpis/global');
export const getPlatformKpis = (platformName) => api.get(`/api/v1/kpis/platform/${platformName}`);
export const getInvestments = (filters) => api.get('/api/v1/investments', { params: filters });
export const getCashFlows = (filters) => api.get('/api/v1/cashflows', { params: filters });
export const getChartsData = () => api.get('/api/v1/charts');

export default api;
