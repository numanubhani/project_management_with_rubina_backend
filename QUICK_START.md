# Quick Start Guide

## Backend Setup (Django)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Start server:**
   ```bash
   python manage.py runserver
   ```

Backend runs on: `http://localhost:8000`

## Frontend Connection

### Update your frontend API base URL:

```javascript
// Example for React/Vite
const API_BASE_URL = 'http://localhost:8000/api';
```

### Authentication:

1. **Register/Login:**
   ```javascript
   // Register
   POST http://localhost:8000/api/auth/register
   Body: {
     "workspace_name": "My Workspace",
     "admin_name": "Admin Name",
     "email": "admin@example.com",
     "password": "password123"
   }

   // Login
   POST http://localhost:8000/api/auth/login
   Body: {
     "email": "admin@example.com",
     "password": "password123"
   }
   ```

2. **Use token in requests:**
   ```javascript
   headers: {
     'Authorization': `Bearer ${access_token}`,
     'Content-Type': 'application/json'
   }
   ```

## API Endpoints

All endpoints are prefixed with `/api/`

- **Auth:** `/api/auth/login`, `/api/auth/register`
- **Users:** `/api/users/`, `/api/users/me`
- **Projects:** `/api/projects/`, `/api/projects/{id}`
- **Workspaces:** `/api/workspaces/me`
- **Files:** `/api/files/{project_id}/{category}/{filename}`
- **Finance:** `/api/finance/history`, `/api/finance/stats`

## Swagger Documentation

Visit: `http://localhost:8000/api/docs/` for interactive API documentation

## CORS Configuration

The backend is configured to accept requests from:
- `http://localhost:3000` (React)
- `http://localhost:5173` (Vite)

To add more origins, update `CORS_ORIGINS` in `.env` or `settings.py`

