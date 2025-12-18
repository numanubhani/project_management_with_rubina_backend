# Frontend Connection Guide

## ✅ Backend is Ready!

**Backend URL:** `http://localhost:8000`  
**API Base URL:** `http://localhost:8000/api`

## Quick Setup

### 1. Update Frontend API Configuration

Create or update your API configuration file:

**For React/Vite (src/config/api.js or src/utils/api.js):**

```javascript
const API_BASE_URL = 'http://localhost:8000/api';

export default API_BASE_URL;
```

### 2. Create API Service (Axios Example)

**src/services/api.js:**

```javascript
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle response errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### 3. Authentication Service

**src/services/auth.js:**

```javascript
import api from './api';

export const authService = {
  // Register workspace
  register: async (workspaceData) => {
    const response = await api.post('/auth/register', workspaceData);
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  // Login
  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }
    return response.data;
  },

  // Logout
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },

  // Get current user
  getCurrentUser: () => {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  },

  // Check if authenticated
  isAuthenticated: () => {
    return !!localStorage.getItem('access_token');
  },
};
```

### 4. Example API Calls

**src/services/projectService.js:**

```javascript
import api from './api';

export const projectService = {
  // Get all projects
  getProjects: () => api.get('/projects/'),

  // Get single project
  getProject: (id) => api.get(`/projects/${id}`),

  // Create project
  createProject: (projectData, files) => {
    const formData = new FormData();
    formData.append('title', projectData.title);
    formData.append('description', projectData.description);
    formData.append('amount', projectData.amount);
    formData.append('deadline', projectData.deadline);
    
    if (files && files.length > 0) {
      files.forEach((file) => {
        formData.append('files', file);
      });
    }

    return api.post('/projects/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // Update project status
  updateStatus: (id, status) => 
    api.put(`/projects/${id}/status`, { status }),

  // Upload delivery
  uploadDelivery: (id, files) => {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    return api.post(`/projects/${id}/delivery`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // Add comment
  addComment: (id, text) => 
    api.post(`/projects/${id}/comments`, { text }),

  // Add update
  addUpdate: (id, text, files) => {
    const formData = new FormData();
    formData.append('text', text);
    if (files && files.length > 0) {
      files.forEach((file) => {
        formData.append('files', file);
      });
    }
    return api.post(`/projects/${id}/updates`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // Get dashboard stats
  getDashboardStats: () => api.get('/projects/dashboard/stats'),
};
```

### 5. Environment Variables (Optional)

Create `.env` file in your frontend root:

```env
VITE_API_BASE_URL=http://localhost:8000/api
# or for Create React App:
# REACT_APP_API_BASE_URL=http://localhost:8000/api
```

Then use in your code:

```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
```

## CORS Configuration

The backend is configured to accept requests from:
- ✅ `http://localhost:3000` (React default)
- ✅ `http://localhost:5173` (Vite default)

If your frontend runs on a different port, update `flowspace/settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://localhost:5174',  # Add your port here
]
```

## Testing the Connection

### 1. Test Registration

```javascript
import { authService } from './services/auth';

const testRegister = async () => {
  try {
    const result = await authService.register({
      workspace_name: 'My Workspace',
      admin_name: 'Admin User',
      email: 'admin@example.com',
      password: 'password123'
    });
    console.log('Registration successful:', result);
  } catch (error) {
    console.error('Registration failed:', error);
  }
};
```

### 2. Test Login

```javascript
const testLogin = async () => {
  try {
    const result = await authService.login('admin@example.com', 'password123');
    console.log('Login successful:', result);
  } catch (error) {
    console.error('Login failed:', error);
  }
};
```

### 3. Test Authenticated Request

```javascript
import api from './services/api';

const testProjects = async () => {
  try {
    const response = await api.get('/projects/');
    console.log('Projects:', response.data);
  } catch (error) {
    console.error('Failed to fetch projects:', error);
  }
};
```

## Common Issues & Solutions

### Issue: CORS Error
**Solution:** 
- Check backend CORS settings in `flowspace/settings.py`
- Ensure frontend URL is in `CORS_ALLOWED_ORIGINS`
- Verify backend is running

### Issue: 401 Unauthorized
**Solution:**
- Check if token is stored: `localStorage.getItem('access_token')`
- Verify token format: `Bearer <token>`
- Token might be expired (default: 1440 minutes)

### Issue: 404 Not Found
**Solution:**
- Verify API endpoint URL is correct
- Check backend is running on port 8000
- Ensure endpoint exists in `api/urls.py`

### Issue: Network Error
**Solution:**
- Verify backend is running: `http://localhost:8000/health/`
- Check firewall settings
- Ensure both frontend and backend are on same network

## API Endpoints Reference

### Authentication
- `POST /api/auth/register` - Register workspace
- `POST /api/auth/login` - Login

### Users
- `GET /api/users/` - Get all users
- `POST /api/users/create` - Create user (Admin)
- `GET /api/users/me` - Get current user
- `PUT /api/users/me/update` - Update profile

### Projects
- `GET /api/projects/` - Get all projects
- `POST /api/projects/` - Create project
- `GET /api/projects/{id}` - Get project
- `PUT /api/projects/{id}/status` - Update status
- `POST /api/projects/{id}/delivery` - Upload delivery
- `POST /api/projects/{id}/comments` - Add comment
- `POST /api/projects/{id}/updates` - Add update
- `GET /api/projects/dashboard/stats` - Get stats

### Workspaces
- `GET /api/workspaces/me` - Get workspace
- `PUT /api/workspaces/me/update` - Update workspace
- `GET /api/workspaces/me/stats` - Get stats

### Files
- `GET /api/files/{project_id}/{category}/{filename}` - Download file

### Finance
- `GET /api/finance/history` - Get history
- `GET /api/finance/stats` - Get stats

## Next Steps

1. ✅ Backend is running
2. ✅ Update frontend API configuration
3. ✅ Create API service files
4. ✅ Test authentication
5. ✅ Test API calls
6. ✅ Connect your components

**Your backend is ready! Just update your frontend API configuration and you're good to go!** 🚀


