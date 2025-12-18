/**
 * Frontend API Configuration
 * Copy this to your frontend project and customize as needed
 */

// API Configuration
export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000/api',
  TIMEOUT: 10000,
};

// Axios Setup Example
import axios from 'axios';

const apiClient = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor - Add token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor - Handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear auth and redirect
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;

// Example API Functions
export const authAPI = {
  register: (data) => apiClient.post('/auth/register', data),
  login: (data) => apiClient.post('/auth/login', data),
};

export const userAPI = {
  getCurrent: () => apiClient.get('/users/me'),
  updateProfile: (data) => apiClient.put('/users/me/update', data),
  getAll: () => apiClient.get('/users/'),
  create: (data) => apiClient.post('/users/create', data),
};

export const projectAPI = {
  getAll: () => apiClient.get('/projects/'),
  getById: (id) => apiClient.get(`/projects/${id}`),
  create: (formData) => apiClient.post('/projects/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  updateStatus: (id, status) => 
    apiClient.put(`/projects/${id}/status`, { status }),
  uploadDelivery: (id, formData) => 
    apiClient.post(`/projects/${id}/delivery`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  addComment: (id, text) => 
    apiClient.post(`/projects/${id}/comments`, { text }),
  addUpdate: (id, formData) => 
    apiClient.post(`/projects/${id}/updates`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getStats: () => apiClient.get('/projects/dashboard/stats'),
  markPaymentCleared: (id) => 
    apiClient.put(`/projects/${id}/payment/clear`),
  approvePayment: (id) => 
    apiClient.put(`/projects/${id}/payment/approve`),
};

export const workspaceAPI = {
  getCurrent: () => apiClient.get('/workspaces/me'),
  update: (data) => apiClient.put('/workspaces/me/update', data),
  getStats: () => apiClient.get('/workspaces/me/stats'),
  export: () => apiClient.get('/workspaces/me/export'),
};

export const financeAPI = {
  getHistory: () => apiClient.get('/finance/history'),
  getStats: () => apiClient.get('/finance/stats'),
};

// File download helper
export const downloadFile = (projectId, category, filename) => {
  const token = localStorage.getItem('access_token');
  const url = `${API_CONFIG.BASE_URL}/files/${projectId}/${category}/${filename}`;
  
  return fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
    .then((response) => response.blob())
    .then((blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    });
};


