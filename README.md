# FlowSpace API - Django Backend

Project Management System Backend API built with Django REST Framework.

## Features

- ✅ JWT Authentication
- ✅ Workspace Management
- ✅ Project Management
- ✅ File Upload/Download
- ✅ Comments & Updates
- ✅ Finance Tracking
- ✅ Swagger/OpenAPI Documentation

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///./db.sqlite3
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
ACCESS_TOKEN_EXPIRE_MINUTES=1440
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=50
```

### 3. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 5. Run Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

## API Documentation

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **Schema**: http://localhost:8000/api/schema/

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register workspace

### Users
- `GET /api/users/` - Get all users
- `POST /api/users/create` - Create user (Admin only)
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

### Workspaces
- `GET /api/workspaces/me` - Get current workspace
- `PUT /api/workspaces/me/update` - Update workspace
- `GET /api/workspaces/me/stats` - Get stats

### Files
- `GET /api/files/{project_id}/{category}/{filename}` - Download file

### Finance
- `GET /api/finance/history` - Get finance history
- `GET /api/finance/stats` - Get finance stats

## Frontend Connection

The backend is configured to accept requests from:
- `http://localhost:3000` (React default)
- `http://localhost:5173` (Vite default)

Update `CORS_ORIGINS` in `.env` to add your frontend URL.

## Authentication

All endpoints (except login/register) require JWT authentication.

Include the token in the Authorization header:
```
Authorization: Bearer <your-access-token>
```

## Database

By default, uses SQLite. For production, use PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

## Deployment

For production deployment:

1. Set `DEBUG=False`
2. Set a strong `SECRET_KEY`
3. Configure proper `CORS_ORIGINS`
4. Use PostgreSQL database
5. Set up static file serving
6. Configure proper security settings
