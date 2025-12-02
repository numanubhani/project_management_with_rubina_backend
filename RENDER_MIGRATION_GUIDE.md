# Render Migration Guide

This guide explains how database migrations run automatically on Render and how to troubleshoot issues.

## ✅ Automatic Migration Setup

Your application is configured to **automatically run migrations** when the server starts on Render. Here's how it works:

### How It Works

1. **Startup Event**: When your FastAPI app starts, it triggers the `startup_event()` function
2. **Migration Check**: The function checks if you're NOT on Vercel (serverless)
3. **Run Migrations**: If on Render, it automatically runs `alembic upgrade head`
4. **Logging**: All migration output is logged to Render's logs

### Files Involved

- **`app/main.py`**: Contains the `run_migrations()` function and `startup_event()` handler
- **`alembic.ini`**: Alembic configuration file
- **`alembic/env.py`**: Environment configuration that reads `DATABASE_URL`
- **`alembic/versions/001_initial_migration.py`**: Initial migration that creates all tables

## 🔧 Render Configuration

### Required Environment Variables

Make sure these are set in your Render dashboard:

```bash
DATABASE_URL=postgresql://user:password@host:port/dbname
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Build Command

Your build command should **NOT** include `alembic upgrade head`. The migrations run automatically at startup.

**Correct Build Command:**
```bash
pip install -r requirements.txt
```

**Wrong Build Command:**
```bash
pip install -r requirements.txt && alembic upgrade head  # ❌ Don't do this
```

### Start Command

Your start command should be:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 📋 Migration Process

When your app starts on Render, you'll see logs like this:

```
============================================================
Starting Alembic database migrations...
============================================================
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial, Initial migration
============================================================
Migrations applied successfully!
============================================================
```

## 🐛 Troubleshooting

### Migration Not Running

**Check 1: Verify DATABASE_URL is set**
- Go to Render Dashboard → Your Service → Environment
- Ensure `DATABASE_URL` is set correctly

**Check 2: Check Render Logs**
- Go to Render Dashboard → Your Service → Logs
- Look for migration messages at startup
- If you see "Alembic not found", ensure `alembic>=1.13.0` is in `requirements.txt`

**Check 3: Verify Alembic Files Exist**
- Ensure `alembic.ini` exists in project root
- Ensure `alembic/env.py` exists
- Ensure `alembic/versions/` directory exists with migration files

### Migration Fails

**Error: "no such table: users"**
- This means migrations haven't run yet
- Check Render logs for migration errors
- Verify `DATABASE_URL` is correct
- Ensure database is accessible from Render

**Error: "alembic: command not found"**
- Ensure `alembic>=1.13.0` is in `requirements.txt`
- Rebuild your service on Render

**Error: "Can't locate revision identified by '001_initial'"**
- The migration file might not be in the repository
- Ensure `alembic/versions/001_initial_migration.py` is committed to git

### Manual Migration (If Needed)

If you need to run migrations manually on Render:

1. **SSH into Render** (if available):
   ```bash
   alembic upgrade head
   ```

2. **Or use Render Shell**:
   - Go to Render Dashboard → Your Service → Shell
   - Run: `alembic upgrade head`

## 📝 Creating New Migrations

When you modify your models, create a new migration:

```bash
# Locally (after activating venv)
alembic revision --autogenerate -m "description of changes"
alembic upgrade head  # Test locally first
```

Then commit the new migration file in `alembic/versions/` to git. It will automatically run on the next Render deployment.

## ✅ Verification

After deployment, verify migrations ran:

1. **Check Render Logs**: Look for "Migrations applied successfully!"
2. **Test API**: Try creating a user or workspace
3. **Check Database**: Connect to your PostgreSQL database and verify tables exist:
   ```sql
   \dt  -- List all tables
   SELECT * FROM users LIMIT 1;
   ```

## 🎯 Summary

- ✅ Migrations run **automatically** on Render startup
- ✅ No need to add `alembic upgrade head` to build/start commands
- ✅ All migration output is logged to Render logs
- ✅ If migration fails, the app still starts (check logs for errors)
- ✅ Ensure `DATABASE_URL` environment variable is set correctly

Your setup is ready! Just deploy to Render and migrations will run automatically. 🚀

