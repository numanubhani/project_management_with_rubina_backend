from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.config import settings
from app.routers import auth, users, projects, files, finance, workspaces
import os
import logging
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO if os.getenv("VERCEL") else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FlowSpace API",
    description="Project Management System Backend API",
    version="1.0.0"
)

# Database initialization is handled lazily on first request
# This prevents errors during cold starts in serverless environments
# Tables should be created via migrations (Alembic) or managed externally
# DO NOT create tables automatically in serverless - use migrations instead

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for debugging in serverless environments"""
    start_time = datetime.now()
    path = request.url.path
    method = request.method
    
    try:
        response = await call_next(request)
        process_time = (datetime.now() - start_time).total_seconds()
        
        # Log request details (useful for Vercel function logs)
        logger.info(
            f"{method} {path} - Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        
        return response
    except Exception as e:
        process_time = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"{method} {path} - ERROR: {str(e)} - Time: {process_time:.3f}s\n"
            f"Traceback: {traceback.format_exc()}"
        )
        raise

# Global exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with proper JSON responses"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "path": request.url.path,
            "method": request.method
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to prevent 500 errors from crashing"""
    error_detail = str(exc)
    error_traceback = traceback.format_exc()
    
    # Log the full error with traceback (visible in Vercel function logs)
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}:\n"
        f"{error_traceback}"
    )
    
    # Return a proper error response instead of crashing
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "path": request.url.path,
            "method": request.method,
            "error": error_detail if not os.getenv("VERCEL") else "Check server logs"
        }
    )

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(files.router)
app.include_router(finance.router)
app.include_router(workspaces.router)


@app.get("/")
async def root():
    return {
        "message": "FlowSpace API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/favicon.ico")
async def favicon():
    """Handle favicon requests to prevent 500 errors"""
    # Return 204 No Content instead of 404 to prevent browser retries
    return Response(status_code=204)

