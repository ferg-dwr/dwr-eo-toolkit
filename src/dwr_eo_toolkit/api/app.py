"""
FastAPI REST API Application

This is the main FastAPI application for the DWR EO Toolkit.
Provides REST endpoints for downloads, batch operations, and scheduled jobs.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime, timezone

# Import routers
from .routes import downloads_router, batches_router, jobs_router
from .websocket import ws_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Application Startup/Shutdown
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle (startup and shutdown).
    """
    # Startup
    logger.info("Starting DWR EO Toolkit API")
    logger.info(f"Environment: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info(f"Database: {os.getenv('POSTGRES_DB', 'dwr_eo_toolkit_dev')}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down DWR EO Toolkit API")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="DWR EO Toolkit API",
    description="REST API for downloading and processing Earth observation data",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Register API Routers
# ============================================================================

app.include_router(downloads_router)
app.include_router(batches_router)
app.include_router(jobs_router)
app.include_router(ws_router)

# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint. Returns API status and database connectivity.
    """
    return {
        "status": "healthy",
        "service": "dwr-eo-toolkit",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected"
    }


@app.get("/status")
async def status():
    """
    Detailed status endpoint with API and database information.
    """
    return {
        "api": {
            "status": "running",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "database": {
            "status": "connected",
            "type": "postgresql",
            "version": "15-alpine",
        },
        "environment": {
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "debug": os.getenv("DEBUG", "False") == "True",
        }
    }


# ============================================================================
# API v1 Routes (Placeholder)
# ============================================================================

@app.get("/api/v1/downloads")
async def list_downloads():
    """
    List all downloads for the authenticated user.
    
    **Phase 4 TODO:** Implement with database queries
    """
    return {
        "downloads": [],
        "count": 0,
        "message": "Downloads endpoint - Phase 4 implementation in progress"
    }


@app.post("/api/v1/downloads")
async def create_download():
    """
    Create a new download session.
    
    **Phase 4 TODO:** Implement with request validation and database storage
    """
    return {
        "id": "placeholder-id",
        "status": "created",
        "message": "Download creation - Phase 4 implementation in progress"
    }


@app.get("/api/v1/downloads/{download_id}")
async def get_download(download_id: str):
    """
    Get details of a specific download.
    
    **Phase 4 TODO:** Implement with database queries
    """
    return {
        "id": download_id,
        "status": "placeholder",
        "message": "Download details - Phase 4 implementation in progress"
    }


@app.get("/api/v1/batches")
async def list_batches():
    """
    List all batch operations for the authenticated user.
    
    **Phase 4 TODO:** Implement with database queries
    """
    return {
        "batches": [],
        "count": 0,
        "message": "Batches endpoint - Phase 4 implementation in progress"
    }


@app.post("/api/v1/batches")
async def create_batch():
    """
    Create a new batch operation.
    
    **Phase 4 TODO:** Implement with request validation and database storage
    """
    return {
        "id": "placeholder-id",
        "status": "created",
        "message": "Batch creation - Phase 4 implementation in progress"
    }


@app.get("/api/v1/jobs")
async def list_jobs():
    """
    List all scheduled jobs for the authenticated user.
    
    **Phase 4 TODO:** Implement with database queries
    """
    return {
        "jobs": [],
        "count": 0,
        "message": "Jobs endpoint - Phase 4 implementation in progress"
    }


@app.post("/api/v1/jobs/schedule")
async def schedule_job():
    """
    Schedule a new download job.
    
    **Phase 4 TODO:** Implement with request validation and database storage
    """
    return {
        "id": "placeholder-id",
        "scheduled": True,
        "message": "Job scheduling - Phase 4 implementation in progress"
    }


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """
    Root endpoint with API documentation links.
    """
    return {
        "service": "DWR EO Toolkit API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "downloads": "/api/v1/downloads",
            "batches": "/api/v1/batches",
            "jobs": "/api/v1/jobs",
        }
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Main Entry Point (for local development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )