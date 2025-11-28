# Debugging Vercel Function Errors - Complete Guide

## Understanding the Favicon.ico 500 Error

The `/favicon.ico` 500 error you're seeing is a symptom, not the root cause. Here's what's happening:

1. **Browser automatically requests favicon** - Every browser automatically requests `/favicon.ico` when loading a page
2. **No route handler** - Your FastAPI app didn't have a handler for this route
3. **Error cascades** - This caused an unhandled exception, returning 500 instead of proper 404

## What I Fixed

### 1. Added Favicon Handler
```python
@app.get("/favicon.ico")
async def favicon():
    """Handle favicon requests to prevent 500 errors"""
    return Response(status_code=204)  # No Content - browser stops retrying
```

### 2. Added Global Exception Handlers
- Catches all unhandled exceptions
- Returns proper JSON error responses instead of crashing
- Logs full stack traces to Vercel function logs

### 3. Added Request Logging Middleware
- Logs every request with method, path, status, and execution time
- Visible in Vercel function logs for debugging

### 4. Improved Handler Error Reporting
- Better error messages in `api/index.py`
- Logs initialization failures with full tracebacks

## How to Debug Using Vercel Function Logs

### Step 1: Access Function Logs

1. Go to **Vercel Dashboard** → Your Project
2. Click on **Functions** tab (top navigation)
3. You'll see a list of all serverless functions
4. Click on the function name (usually shows as your route path)
5. You'll see **real-time logs** as requests come in

### Step 2: Reproduce the Error

1. Open your deployed site
2. Open browser DevTools (F12) → Network tab
3. Navigate to the page or trigger the error
4. Watch the Network tab for failed requests
5. Go back to Vercel Functions tab - you should see new log entries

### Step 3: Read the Logs

The logs now show:
```
INFO - GET /favicon.ico - Status: 204 - Time: 0.023s
INFO - GET /api/workspaces/me - Status: 200 - Time: 0.145s
ERROR - GET /some/path - ERROR: Connection timeout - Time: 2.500s
Traceback: [full stack trace]
```

### What to Look For:

#### ✅ **Good Logs:**
```
INFO - GET /api/workspaces/me - Status: 200 - Time: 0.145s
```
- Status 200/201/204 = Success
- Short execution time = Good performance

#### ⚠️ **Warning Logs:**
```
WARNING - Validation error on POST /api/projects/: [error details]
```
- Validation errors (422) = Client sent bad data
- Not a server issue, but useful for debugging

#### ❌ **Error Logs:**
```
ERROR - GET /api/something - ERROR: Database connection failed
Traceback:
  File "app/database.py", line 23...
  ...
```
- Status 500 = Server error
- Full traceback shows exactly where it failed

### Step 4: Set Up Log Drains (Optional)

For persistent logging and better tracking:

1. Go to **Vercel Dashboard** → Your Project → Settings
2. Click **Log Drains**
3. Add a log drain service:
   - **Datadog** (free tier available)
   - **Logtail** (free tier)
   - **Axiom** (free tier)
   - Or use webhook URL

This lets you:
- Search historical logs
- Set up alerts
- Track error frequency
- Analyze patterns

## Common Error Patterns in Logs

### Pattern 1: Import Errors
```
ERROR - Failed to initialize application:
ModuleNotFoundError: No module named 'mangum'
```
**Fix:** Check `requirements.txt` includes all dependencies

### Pattern 2: Database Connection Errors
```
ERROR - GET /api/workspaces/me - ERROR: Connection refused
```
**Fix:** Check `DATABASE_URL` environment variable is set correctly

### Pattern 3: Authentication Errors
```
ERROR - GET /api/projects/ - ERROR: Invalid token
```
**Fix:** Check token generation and validation logic

### Pattern 4: Timeout Errors
```
ERROR - GET /api/export - ERROR: Function execution timeout
```
**Fix:** Optimize the endpoint or use background jobs for long operations

### Pattern 5: Missing Environment Variables
```
ERROR - KeyError: 'DATABASE_URL'
```
**Fix:** Set all required environment variables in Vercel project settings

## Debugging Workflow

### 1. **Reproduce Locally First**
```bash
# Install Vercel CLI
npm i -g vercel

# Run locally with Vercel
cd your-backend-directory
vercel dev
```

This simulates the Vercel environment locally and shows logs in your terminal.

### 2. **Add Temporary Debug Logging**
```python
# In your route handler
import logging
logger = logging.getLogger(__name__)

@router.get("/api/workspaces/me")
async def get_workspace(...):
    logger.info("Starting workspace fetch")
    logger.debug(f"User ID: {current_user.id}")
    # ... your code ...
    logger.info("Workspace fetch completed")
    return workspace
```

### 3. **Check Environment Variables**
```python
# Temporary debug route (remove after debugging)
@app.get("/debug/env")
async def debug_env():
    return {
        "has_database_url": bool(os.getenv("DATABASE_URL")),
        "has_secret_key": bool(os.getenv("SECRET_KEY")),
        "vercel_env": os.getenv("VERCEL"),
        # Don't return actual values for security!
    }
```

### 4. **Test Database Connection**
```python
# Temporary debug route
@app.get("/debug/db")
async def debug_db():
    try:
        from app.database import engine
        with engine.connect() as conn:
            return {"status": "connected", "engine": str(engine)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
```

## Error Response Format

All errors now return consistent JSON:

```json
{
  "detail": "Error message here",
  "path": "/api/workspaces/me",
  "method": "GET",
  "error": "Connection timeout"
}
```

This makes it easier to:
- Debug from client side
- Track errors in monitoring tools
- Provide better user feedback

## Testing the Fixes

After deploying, test these scenarios:

1. **Favicon Request:**
   ```bash
   curl -I https://your-app.vercel.app/favicon.ico
   # Should return: 204 No Content (not 500)
   ```

2. **Invalid Route:**
   ```bash
   curl https://your-app.vercel.app/nonexistent
   # Should return: 404 with JSON error (not 500)
   ```

3. **Health Check:**
   ```bash
   curl https://your-app.vercel.app/health
   # Should return: {"status": "healthy"}
   ```

## Next Steps

1. ✅ Deploy the updated code
2. ✅ Check Vercel Functions tab for logs
3. ✅ Monitor for any remaining 500 errors
4. ✅ Set up log drains for production monitoring
5. ✅ Remove any temporary debug routes before production

## Additional Resources

- [Vercel Function Logs Documentation](https://vercel.com/docs/concepts/functions/serverless-functions/logs)
- [FastAPI Error Handling](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- [Mangum Documentation](https://mangum.io/)

