# Vercel Deployment Guide - FUNCTION_INVOCATION_FAILED Fix

## Summary of Changes

This guide explains the fixes applied to resolve the `FUNCTION_INVOCATION_FAILED` error on Vercel and how to avoid similar issues in the future.

## Files Modified/Created

1. **`api/index.py`** (NEW) - Vercel serverless function handler
2. **`vercel.json`** (NEW) - Vercel configuration file
3. **`app/main.py`** (MODIFIED) - Removed eager database initialization
4. **`app/database.py`** (MODIFIED) - Added serverless-friendly connection pooling
5. **`app/config.py`** (MODIFIED) - Added serverless environment detection
6. **`requirements.txt`** (MODIFIED) - Added `mangum` dependency

## Critical Issues Fixed

### 1. Missing Serverless Handler
**Problem:** FastAPI apps need a special handler wrapper for Vercel's serverless environment.

**Fix:** Created `api/index.py` with Mangum adapter that converts AWS Lambda events to ASGI requests.

### 2. Database Initialization on Import
**Problem:** `Base.metadata.create_all()` was running at module import time, causing:
- Slow cold starts
- Potential timeout errors
- Connection issues in serverless environments

**Fix:** Removed eager initialization. Use Alembic migrations instead for production.

### 3. SQLite in Serverless
**Problem:** SQLite uses local filesystem which is read-only in serverless environments.

**Fix:** 
- Added detection for serverless environments
- Skip SQLite table creation on Vercel
- **Recommendation:** Use PostgreSQL (via Vercel Postgres, Neon, Supabase, etc.)

### 4. File System Operations
**Problem:** Creating directories at startup fails in read-only serverless filesystems.

**Fix:** Only create directories when not in serverless environment. For production, use cloud storage (S3, Vercel Blob, etc.).

## Deployment Checklist

### Required Environment Variables

Set these in your Vercel project settings:

```bash
# Database (REQUIRED - use PostgreSQL, not SQLite)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Security (REQUIRED)
SECRET_KEY=your-very-secure-random-secret-key-here

# CORS (REQUIRED)
CORS_ORIGINS=https://your-frontend-domain.vercel.app

# Optional
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
MAX_FILE_SIZE_MB=50
```

### Database Setup

1. **Create PostgreSQL database:**
   - Vercel Postgres (recommended, easiest integration)
   - Neon.tech (free tier available)
   - Supabase (free tier available)
   - Railway, Render, or other providers

2. **Run migrations:**
   ```bash
   # Before deploying, run migrations locally with production DATABASE_URL
   alembic upgrade head
   ```

### File Storage Setup

For file uploads, you need cloud storage. Options:
- **Vercel Blob Storage** (easiest with Vercel)
- **AWS S3**
- **Cloudinary**
- **Supabase Storage**

Update your file upload logic to use these services instead of local filesystem.

## Testing Locally

To test the serverless handler locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Test the handler
python -m pytest tests/  # if you have tests

# Test with Vercel CLI (optional)
npm i -g vercel
vercel dev
```

## Monitoring

After deployment, monitor:
1. **Vercel Dashboard** → Functions → Check logs for errors
2. **Function execution time** - should be < 10s for most requests
3. **Cold start frequency** - first request after inactivity
4. **Database connection errors** - check connection pool settings

## Common Pitfalls to Avoid

1. ❌ **Don't use SQLite in production serverless**
2. ❌ **Don't create files/directories on filesystem**
3. ❌ **Don't run heavy initialization at import time**
4. ❌ **Don't forget to set all required environment variables**
5. ❌ **Don't use synchronous blocking operations**

## Next Steps

1. Set up PostgreSQL database
2. Configure environment variables in Vercel
3. Set up cloud file storage
4. Deploy and test
5. Monitor logs for any remaining issues

