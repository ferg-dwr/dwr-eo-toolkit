"""Database module for DWR EO Toolkit.

Provides SQLAlchemy models, session management, and database initialization.
"""

from .connection import SessionLocal, engine, get_db, init_db
from .models import (
    Base,
    BatchOperation,
    DownloadResult,
    DownloadSession,
    DownloadTask,
    ScheduledJob,
)

__all__ = [
    # Connection
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    # Models
    "Base",
    "DownloadSession",
    "DownloadTask",
    "BatchOperation",
    "ScheduledJob",
    "DownloadResult",
]
