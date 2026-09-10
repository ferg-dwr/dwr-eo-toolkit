# Phase 4 TBD
"""
Phase 4: Pydantic Schemas

Defines request/response schemas for API validation and documentation.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DownloadStatus(str, Enum):
    """Status of a download task."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class BatchStatus(str, Enum):
    """Status of a batch operation."""

    CREATED = "created"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(str, Enum):
    """Status of a scheduled job."""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


class DownloadCreate(BaseModel):
    """
    Schema for creating a new download.

    **Phase 4 TODO:**
    - Add geometry field (GeoJSON)
    - Add product selection
    - Add date range
    - Add output format options
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "product": "MODIS",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            }
        }
    )

    product: str = Field(..., description="Product name (e.g., MODIS, ECOSTRESS)")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")


class DownloadResponse(BaseModel):
    """
    Schema for download response.

    **Phase 4 TODO:**
    - Add all database fields
    - Add computed fields (progress %)
    - Add nested task information
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "downloading",
                "product": "MODIS",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:35:00Z",
            }
        },
    )

    id: str = Field(..., description="Unique download ID")
    status: DownloadStatus
    product: str
    created_at: datetime
    updated_at: datetime


class DownloadListResponse(BaseModel):
    """Response for listing downloads."""

    downloads: List[DownloadResponse]
    count: int
    total: Optional[int] = None  # For pagination


class BatchCreate(BaseModel):
    """
    Schema for creating a batch operation.

    **Phase 4 TODO:**
    - Add multiple downloads/tasks
    - Add batch-level options
    - Add priority/scheduling
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "January 2024 MODIS Downloads",
                "description": "Monthly MODIS collection for Q1 analysis",
            }
        }
    )

    name: str = Field(..., description="Batch operation name")
    downloads: Optional[List[DownloadCreate]] = None
    description: Optional[str] = None


class BatchResponse(BaseModel):
    """Schema for batch operation response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: BatchStatus
    progress: int = Field(..., ge=0, le=100, description="Progress 0-100")
    task_count: int
    completed_count: int
    failed_count: int
    created_at: datetime
    updated_at: datetime


class BatchListResponse(BaseModel):
    """Response for listing batches."""

    batches: List[BatchResponse]
    count: int


class ScheduleType(str, Enum):
    """Type of schedule."""

    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class JobCreate(BaseModel):
    """
    Schema for scheduling a job.

    **Phase 4 TODO:**
    - Add cron expression support
    - Add timezone handling
    - Add job parameters
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Weekly MODIS Download",
                "product": "MODIS",
                "schedule_type": "weekly",
                "start_date": "2024-01-01",
            }
        }
    )

    name: str = Field(..., description="Job name")
    product: str = Field(..., description="Product to download")
    schedule_type: ScheduleType
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = None


class JobResponse(BaseModel):
    """Schema for scheduled job response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    product: str
    schedule_type: ScheduleType
    status: JobStatus
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    """Response for listing jobs."""

    jobs: List[JobResponse]
    count: int


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    error: str
    status_code: int
    timestamp: datetime
    detail: Optional[str] = None


class ValidationError(BaseModel):
    """Schema for validation errors."""

    loc: List[str]
    msg: str
    type: str


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    service: str
    timestamp: datetime
    database: str


class StatusResponse(BaseModel):
    """Schema for detailed status response."""

    api: dict
    database: dict
    environment: dict


__all__ = [
    # Enums
    "DownloadStatus",
    "BatchStatus",
    "JobStatus",
    "ScheduleType",
    # Download schemas
    "DownloadCreate",
    "DownloadResponse",
    "DownloadListResponse",
    # Batch schemas
    "BatchCreate",
    "BatchResponse",
    "BatchListResponse",
    # Job schemas
    "JobCreate",
    "JobResponse",
    "JobListResponse",
    # Error schemas
    "ErrorResponse",
    "ValidationError",
    # Health schemas
    "HealthResponse",
    "StatusResponse",
]
