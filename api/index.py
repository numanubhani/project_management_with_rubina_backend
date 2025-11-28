"""
Vercel serverless function handler for FastAPI application.
This file is required for Vercel to properly route requests to the FastAPI app.

The handler wraps the FastAPI ASGI application using Mangum, which converts
AWS Lambda/API Gateway events to ASGI-compatible requests.
"""
import sys
import os
from pathlib import Path

# Ensure the parent directory is in Python path for imports
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Set Vercel environment variable for config detection
os.environ["VERCEL"] = "1"

try:
    from mangum import Mangum
    from app.main import app
    
    # Create ASGI adapter for Vercel
    # lifespan="off" disables FastAPI lifespan events which can cause issues in serverless
    handler = Mangum(app, lifespan="off", log_level="warning")
except Exception as e:
    # If import fails, create a simple error handler
    import json
    
    def handler(event, context):
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Failed to initialize application",
                "detail": str(e)
            })
        }

