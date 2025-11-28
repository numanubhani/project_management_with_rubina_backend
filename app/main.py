from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, users, projects, files, finance, workspaces
import os

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

