# Render Deployment Guide

## Environment Variables Required

Set these in your Render dashboard:

### Required Variables

```env
SECRET_KEY=your-very-secure-random-secret-key-here-min-50-chars
DEBUG=False
ALLOWED_HOSTS=project-management-with-rubina-backend.onrender.com
DATABASE_URL=postgresql://user:password@host:port/dbname
CORS_ORIGINS=https://your-frontend-domain.vercel.app,https://your-frontend-domain.netlify.app
```

### Optional Variables

```env
ACCESS_TOKEN_EXPIRE_MINUTES=1440
UPLOAD_DIR=/tmp/uploads
MAX_FILE_SIZE_MB=50
```

## Build & Start Commands

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
python manage.py migrate && gunicorn flowspace.wsgi:application
```

Or if using Render's automatic detection:
```bash
gunicorn flowspace.wsgi:application
```

## Install Gunicorn

Add to `requirements.txt`:
```
gunicorn>=21.2.0
```

## Database Setup

1. Create PostgreSQL database in Render
2. Copy the Internal Database URL
3. Set as `DATABASE_URL` environment variable
4. Run migrations on first deploy (included in start command)

## Static Files (if needed)

Add to `requirements.txt`:
```
whitenoise>=6.6.0
```

Update `settings.py`:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this
    # ... rest of middleware
]

STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

## Troubleshooting 500 Errors

### Check Render Logs

1. Go to Render Dashboard
2. Click on your service
3. Go to "Logs" tab
4. Look for error messages

### Common Issues

1. **Missing SECRET_KEY**
   - Set a strong random secret key
   - Generate: `python -c "import secrets; print(secrets.token_urlsafe(50))"`

2. **Database Connection**
   - Verify DATABASE_URL is correct
   - Check database is accessible
   - Ensure migrations ran

3. **Missing Environment Variables**
   - Check all required variables are set
   - Verify CORS_ORIGINS includes your frontend URL

4. **Import Errors**
   - Check all packages in requirements.txt are installed
   - Verify Python version matches

## Testing After Deployment

1. Health check: `https://your-app.onrender.com/health/`
2. API root: `https://your-app.onrender.com/`
3. Swagger: `https://your-app.onrender.com/api/docs/`

## Update Frontend API URL

Change your frontend API base URL to:
```javascript
const API_BASE_URL = 'https://project-management-with-rubina-backend.onrender.com/api';
```


