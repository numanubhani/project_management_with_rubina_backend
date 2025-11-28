"""
Vercel serverless function handler for FastAPI application.
This file is required for Vercel to properly route requests to the FastAPI app.

The handler wraps the FastAPI ASGI application using Mangum, which converts
AWS Lambda/API Gateway events to ASGI-compatible requests.
"""
import sys
import os
import traceback
import logging
from pathlib import Path

# Configure logging to show in Vercel function logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    handler = Mangum(
        app, 
        lifespan="off", 
        log_level="info"  # Changed to info to see more details in Vercel logs
    )
    
    logger.info("FastAPI application and Mangum handler initialized successfully")
    
except Exception as e:
    # If import fails, create a simple error handler that logs the issue
    error_detail = traceback.format_exc()
    logger.error(f"Failed to initialize application:\n{error_detail}")
    
    import json
    
    def handler(event, context):
        """Error handler when application fails to initialize"""
        logger.error(f"Handler called but app initialization failed. Event: {event}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Failed to initialize application",
                "detail": str(e),
                "message": "Check Vercel function logs for full traceback"
            })
        }
    
    logger.error("Using fallback error handler due to initialization failure")

