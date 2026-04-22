"""
FastAPI REST API Application for the DWR EO Toolkit.
Provides REST endpoints for downloads, batch operations, and scheduled jobs.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import batches_router, downloads_router, jobs_router
from .websocket import ws_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DWR EO Toolkit API")
    logger.info(f"Environment: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info(f"Database: {os.getenv('POSTGRES_DB', 'dwr_eo_toolkit_dev')}")
    yield
    logger.info("Shutting down DWR EO Toolkit API")


app = FastAPI(
    title="DWR EO Toolkit API",
    description="REST API for downloading and processing Earth observation data",
    version="1.0.0",
    lifespan=lifespan,
)

_allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(downloads_router)
app.include_router(batches_router)
app.include_router(jobs_router)
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    """Health check endpoint. Returns API status and database connectivity."""
    from ..database.connection import engine

    db_status = "not_configured"
    if engine is not None:
        try:
            from sqlalchemy import text

            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception:
            db_status = "error"

    return {
        "status": "healthy",
        "service": "dwr-eo-toolkit",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
    }


@app.get("/status")
async def status():
    """Detailed status endpoint with API and database information."""
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
        },
    }


@app.get("/")
async def root():
    """Root endpoint with API documentation links."""
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
        },
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
