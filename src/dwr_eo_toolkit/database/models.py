"""SQLAlchemy models for the DWR EO Toolkit."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class DownloadSession(Base):
    """Model for download sessions persisted to PostgreSQL."""

    __tablename__ = "download_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))

    # Session state and metadata
    state = Column(JSON, default={})  # Stores DownloadSession state
    status = Column(String, default="pending")  # pending, in_progress, completed, failed

    # File counts
    total_files = Column(Integer, default=0)
    completed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    tasks = relationship("DownloadTask", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return (
            f"<DownloadSession(id={self.id}, session_id={self.session_id}, status={self.status})>"
        )


class DownloadTask(Base):
    """Model for individual download tasks within a session."""

    __tablename__ = "download_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("download_sessions.session_id"))

    # Task details
    url = Column(String, index=True)
    destination = Column(String)
    file_name = Column(String)

    # Status and progress
    status = Column(String, default="pending")  # pending, downloading, completed, failed
    progress = Column(Float, default=0.0)  # 0-100%

    # File information
    file_size = Column(Integer, nullable=True)  # bytes
    downloaded_size = Column(Integer, default=0)  # bytes

    # Error tracking
    error_message = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    session = relationship("DownloadSession", back_populates="tasks")

    def __repr__(self):
        return f"<DownloadTask(id={self.id}, task_id={self.task_id}, status={self.status})>"


class BatchOperation(Base):
    """Model for batch download operations."""

    __tablename__ = "batch_operations"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))

    # Batch metadata
    name = Column(String)
    description = Column(String, nullable=True)

    # Status
    status = Column(String, default="queued")  # queued, running, completed, failed

    # Session tracking
    session_ids = Column(JSON, default=[])  # List of session IDs in this batch
    total_sessions = Column(Integer, default=0)
    completed_sessions = Column(Integer, default=0)
    failed_sessions = Column(Integer, default=0)

    # Configuration
    max_concurrent = Column(Integer, default=3)
    config = Column(JSON, default={})  # Any additional configuration

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<BatchOperation(id={self.id}, batch_id={self.batch_id}, status={self.status})>"


class ScheduledJob(Base):
    """Model for scheduled download jobs (APScheduler integration)."""

    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))

    # Job details
    name = Column(String, index=True)
    job_type = Column(String)  # 'one_time' or 'recurring'
    cron_expression = Column(String, nullable=True)  # For recurring jobs

    # Status
    status = Column(String, default="pending")  # pending, active, paused, completed, failed
    is_active = Column(Boolean, default=True)

    # Schedule information
    next_run_time = Column(DateTime, nullable=True, index=True)
    last_run_time = Column(DateTime, nullable=True)

    # Session to run
    session_config = Column(JSON)  # Serialized DownloadSession config

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ScheduledJob(id={self.id}, job_id={self.job_id}, status={self.status})>"


class DownloadResult(Base):
    """Model for storing download results and metadata."""

    __tablename__ = "download_results"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("download_tasks.task_id"))

    # Download result information
    success = Column(Boolean, default=False)
    file_path = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)  # bytes

    # Checksums and verification
    checksum_md5 = Column(String, nullable=True)
    checksum_sha256 = Column(String, nullable=True)
    verified = Column(Boolean, default=False)

    # Metadata
    http_status = Column(Integer, nullable=True)
    download_time = Column(Float, nullable=True)  # seconds
    speed = Column(Float, nullable=True)  # MB/s

    # Error information
    error_type = Column(String, nullable=True)
    error_message = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<DownloadResult(id={self.id}, result_id={self.result_id}, success={self.success})>"
