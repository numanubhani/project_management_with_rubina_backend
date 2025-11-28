# FlowSpace Backend API

A complete FastAPI backend for the FlowSpace project management system.

## Features

- 🔐 JWT Authentication
- 👥 User & Workspace Management
- 📁 Project Management (CRUD)
- 💬 Comments System
- 📤 File Upload/Download
- 💰 Payment Tracking
- 📊 Dashboard Statistics
- 🔒 Role-Based Access Control (Admin/Client)

## Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL/SQLite** - Database
- **JWT** - Authentication
- **bcrypt** - Password hashing

## Installation

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run database migrations** (if using Alembic)
   ```bash
   alembic upgrade head
   ```

5. **Run the server**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Variables

```env
DATABASE_URL=postgresql://user:password@localhost:5432/flowspace_db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=50
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login user
- `POST /api/auth/register` - Register workspace and admin

### Users
- `GET /api/users/` - Get all users in workspace
- `POST /api/users/` - Create new user (Admin only)
- `GET /api/users/me` - Get current user
- `PUT /api/users/me` - Update profile

### Projects
- `GET /api/projects/` - Get all projects
- `GET /api/projects/dashboard/stats` - Get dashboard statistics
- `GET /api/projects/{id}` - Get project details
- `POST /api/projects/` - Create project (Client only)
- `PUT /api/projects/{id}/status` - Update project status
- `POST /api/projects/{id}/delivery` - Upload delivery files (Admin)
- `POST /api/projects/{id}/comments` - Add comment
- `POST /api/projects/{id}/updates` - Add project update (Client)
- `PUT /api/projects/{id}/payment/clear` - Mark payment cleared (Client)
- `PUT /api/projects/{id}/payment/approve` - Approve payment (Admin)

### Files
- `GET /api/files/{project_id}/{category}/{filename}` - Download file

### Finance
- `GET /api/finance/history` - Get financial history
- `GET /api/finance/stats` - Get financial statistics

## Database Models

- **User** - Users with roles (Admin/Client)
- **Workspace** - Workspace/organization
- **Project** - Projects with status and payment tracking
- **ProjectFile** - File metadata
- **Comment** - Project comments
- **ProjectUpdate** - Client updates for projects

## Security

- Passwords are hashed using bcrypt
- JWT tokens for authentication
- Role-based access control
- File upload size limits
- CORS protection

## Development

For development with auto-reload:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Production

For production, use a production ASGI server like:
- Gunicorn with Uvicorn workers
- Docker deployment
- Environment-specific configurations

## License

Private project

