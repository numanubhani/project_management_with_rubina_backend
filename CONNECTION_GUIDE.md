# Backend Connection Guide

## ✅ Backend is Running!

The Django server should now be running on: **http://localhost:8000**

## Quick Test

### 1. Test Health Endpoint
```bash
curl http://localhost:8000/health/
```

Or visit in browser: http://localhost:8000/health/

### 2. Test API Root
```bash
curl http://localhost:8000/
```

### 3. View Swagger Documentation
Visit: **http://localhost:8000/api/docs/**

## Frontend Connection

### Update your frontend API configuration:

```javascript
// Example: src/config/api.js or similar
export const API_BASE_URL = 'http://localhost:8000/api';

// Example: axios setup
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

## Test Registration

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_name": "My Workspace",
    "admin_name": "Admin User",
    "email": "admin@example.com",
    "password": "password123"
  }'
```

## Test Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password123"
  }'
```

## CORS Configuration

The backend is configured to accept requests from:
- ✅ `http://localhost:3000` (React default)
- ✅ `http://localhost:5173` (Vite default)

If your frontend runs on a different port, update `CORS_ORIGINS` in `flowspace/settings.py` or set it in `.env`:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5174
```

## Common Issues

### 1. Port Already in Use
If port 8000 is busy, use a different port:
```bash
python manage.py runserver 8001
```

### 2. Database Not Migrated
Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. CORS Errors
- Check `CORS_ORIGINS` in settings
- Ensure frontend URL is in the allowed list
- Check browser console for specific CORS errors

### 4. Authentication Errors
- Ensure token is included in Authorization header
- Check token expiration (default: 1440 minutes)
- Verify token format: `Bearer <token>`

## Next Steps

1. ✅ Backend is running
2. ✅ Test endpoints using Swagger UI
3. ✅ Update frontend API base URL
4. ✅ Test authentication flow
5. ✅ Connect frontend to backend

## API Endpoints Summary

- **Auth:** `/api/auth/login`, `/api/auth/register`
- **Users:** `/api/users/`, `/api/users/me`
- **Projects:** `/api/projects/`
- **Workspaces:** `/api/workspaces/me`
- **Files:** `/api/files/{project_id}/{category}/{filename}`
- **Finance:** `/api/finance/history`, `/api/finance/stats`

All endpoints (except login/register) require JWT authentication!

