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
import subprocess

# ---------------------------------------------------------
# LOGGING SETUP (must be before run_migrations)
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO if os.getenv("VERCEL") else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# RUN ALEMBIC MIGRATIONS AT SERVER STARTUP (Render only)
# ---------------------------------------------------------

def run_migrations():
    """Triggers Alembic migrations safely on container startup."""
    try:
        logger.info("=" * 60)
        logger.info("Starting Alembic database migrations...")
        logger.info("=" * 60)
        
        # Get project root directory (parent of app directory)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logger.info(f"Running migrations from: {project_root}")
        
        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=project_root  # Run from project root where alembic.ini is located
        )

        if result.returncode != 0:
            logger.error("=" * 60)
            logger.error("MIGRATION FAILED!")
            logger.error("=" * 60)
            logger.error(f"Exit code: {result.returncode}")
            logger.error("STDERR:")
            logger.error(result.stderr)
            logger.error("STDOUT:")
            logger.error(result.stdout)
            logger.error("=" * 60)
            # Don't raise exception - let the app start anyway
            # This allows you to fix migration issues without breaking the deployment
        else:
            logger.info("=" * 60)
            logger.info("Migrations applied successfully!")
            logger.info("=" * 60)
            if result.stdout:
                logger.info("Migration output:")
                logger.info(result.stdout)
            logger.info("=" * 60)

    except FileNotFoundError:
        logger.warning("Alembic not found. Make sure 'alembic' is installed and in PATH.")
        logger.warning("Skipping migrations. Tables may need to be created manually.")
    except Exception as e:
        logger.error(f"Unexpected migration error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Don't raise - allow app to start

app = FastAPI(
    title="FlowSpace API",
    description="Project Management System Backend API",
    version="1.0.0"
)

# ---------------------------------------------------------
# STARTUP EVENT → RUN MIGRATIONS (NON-SERVERLESS ONLY)
# ---------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    """
    Run migrations only on platforms like Render.
    Skip on Vercel (serverless) to avoid cold-start crashes.
    """
    if not os.getenv("VERCEL"):
        run_migrations()


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# REQUEST LOGGING MIDDLEWARE
# ---------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    path = request.url.path
    method = request.method

    try:
        response = await call_next(request)
        process_time = (datetime.now() - start_time).total_seconds()

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


# ---------------------------------------------------------
# GLOBAL EXCEPTION HANDLERS
# ---------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
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
    error_detail = str(exc)
    error_traceback = traceback.format_exc()

    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}:\n"
        f"{error_traceback}"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "path": request.url.path,
            "method": request.method,
            "error": error_detail if not os.getenv("VERCEL") else "Check server logs"
        }
    )


# ---------------------------------------------------------
# ROUTERS
# ---------------------------------------------------------

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(files.router)
app.include_router(finance.router)
app.include_router(workspaces.router)


# ---------------------------------------------------------
# ROOT & HEALTH CHECK
# ---------------------------------------------------------

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
    return Response(status_code=204)
