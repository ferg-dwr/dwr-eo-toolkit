"""
API Routes — REST endpoints for downloads, batches, scheduled jobs, and search.
"""

from datetime import datetime
from typing import Any, Dict, List, Tuple, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..database.models import BatchOperation, DownloadSession, ScheduledJob
from ..providers import EarthAccessProvider
from .schemas import BatchCreate, DownloadCreate, JobCreate


class SearchRequest(BaseModel):
    """Request model for search endpoint"""

    product: str = Field(..., description="Product name (e.g., 'ECOSTRESS', 'MODIS')")
    min_lon: float = Field(..., description="Min longitude")
    min_lat: float = Field(..., description="Min latitude")
    max_lon: float = Field(..., description="Max longitude")
    max_lat: float = Field(..., description="Max latitude")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    max_results: int = Field(100, description="Max granules to return", ge=1, le=2000)

    @field_validator("product")
    @classmethod
    def validate_product(cls, v):
        """Validate product is supported"""
        valid_products = ["ECOSTRESS", "MODIS"]
        if v.upper() not in valid_products:
            raise ValueError(f"Product must be one of {valid_products}")
        return v.upper()

    @field_validator("min_lon", "min_lat", "max_lon", "max_lat")
    @classmethod
    def validate_coords(cls, v):
        """Validate coordinates are reasonable"""
        if not -180 <= v <= 180:
            raise ValueError("Coordinate must be between -180 and 180")
        return v

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v):
        """Validate date format"""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in format YYYY-MM-DD")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v, info):
        """Ensure end_date >= start_date"""
        if "start_date" in info.data:
            start = datetime.strptime(info.data["start_date"], "%Y-%m-%d")
            end = datetime.strptime(v, "%Y-%m-%d")
            if end < start:
                raise ValueError("end_date must be >= start_date")
        return v

    def get_bbox(self) -> Tuple[float, float, float, float]:
        """Get bounding box as tuple"""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)


class SearchResponse(BaseModel):
    """Response model for search endpoint"""

    success: bool
    message: str
    total: int = Field(0, description="Total granules found")
    returned: int = Field(0, description="Granules returned in this response")
    granules: List[dict] = Field(default_factory=list, description="Granule data")
    request_summary: dict = Field(default_factory=dict, description="Echo of request params")


downloads_router = APIRouter(prefix="/api/v1/downloads", tags=["downloads"])
batches_router = APIRouter(prefix="/api/v1/batches", tags=["batches"])
jobs_router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

# Initialize provider (once at startup)
_provider = None


def get_provider() -> EarthAccessProvider:
    """Get or create provider instance"""
    global _provider
    if _provider is None:
        _provider = EarthAccessProvider()
    return _provider


@downloads_router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search for imagery granules",
    description="""
    Search for NASA Earth observation granules by product, location, and date range.

    Returns metadata about available granules that match the search criteria.
    """,
)
async def search_imagery(request: SearchRequest) -> SearchResponse:
    """
    Search for imagery granules.

    Args:
        request: Search parameters (product, bbox, dates, etc.)

    Returns:
        SearchResponse with matching granules

    Raises:
        HTTPException: If search fails
    """
    try:
        provider = get_provider()

        # Log the request
        print(f"🔍 Search request: {request.product}")
        print(f"   Bbox: {request.get_bbox()}")
        print(f"   Dates: {request.start_date} to {request.end_date}")

        # Execute search
        granules, total = provider.search(
            product=request.product,
            bounding_box=request.get_bbox(),
            start_date=request.start_date,
            end_date=request.end_date,
            max_results=request.max_results,
        )

        print(f"   ✅ Found {total} granules (returning {len(granules)})")

        # Build response
        return SearchResponse(
            success=True,
            message=f"Found {total} granules matching criteria",
            total=total,
            returned=len(granules),
            granules=[
                {
                    "id": str(g),
                    "title": str(g),
                    "raw": str(g),
                }
                for g in granules
            ],
            request_summary={
                "product": request.product,
                "bbox": request.get_bbox(),
                "start_date": request.start_date,
                "end_date": request.end_date,
            },
        )

    except ValueError as e:
        # Validation error
        print(f"❌ Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:
        # Search failed
        print(f"❌ Search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )


@downloads_router.get("")
async def list_downloads(db: Session = Depends(get_db)):
    """List all download sessions."""
    sessions = db.query(DownloadSession).all()
    return {
        "downloads": [_session_to_dict(s) for s in sessions],
        "count": len(sessions),
    }


@downloads_router.post("", status_code=201)
async def create_download(payload: DownloadCreate, db: Session = Depends(get_db)):
    """Create a new download session."""
    session = DownloadSession(
        status="pending",
        state={
            "product": payload.product,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
        },
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_to_dict(session)


@downloads_router.get("/{download_id}")
async def get_download(download_id: str, db: Session = Depends(get_db)):
    """Get details of a specific download session."""
    session = db.query(DownloadSession).filter(DownloadSession.session_id == download_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Download '{download_id}' not found")
    return _session_to_dict(session)


@downloads_router.patch("/{download_id}")
async def update_download(download_id: str, db: Session = Depends(get_db)):
    """Update a download (pause, resume, cancel)."""
    session = db.query(DownloadSession).filter(DownloadSession.session_id == download_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Download '{download_id}' not found")
    db.commit()
    return _session_to_dict(session)


@downloads_router.delete("/{download_id}", status_code=204)
async def cancel_download(download_id: str, db: Session = Depends(get_db)):
    """Cancel a download session."""
    session = db.query(DownloadSession).filter(DownloadSession.session_id == download_id).first()
    if not session:
        raise HTTPException(status_code=404, detail=f"Download '{download_id}' not found")
    session.status = "cancelled"  # type: ignore[assignment]
    db.commit()


@batches_router.get("")
async def list_batches(db: Session = Depends(get_db)):
    """List all batch operations."""
    batches = db.query(BatchOperation).all()
    return {
        "batches": [_batch_to_dict(b) for b in batches],
        "count": len(batches),
    }


@batches_router.post("", status_code=201)
async def create_batch(payload: BatchCreate, db: Session = Depends(get_db)):
    """Create a new batch operation."""
    batch = BatchOperation(
        name=payload.name,
        description=payload.description,
        status="queued",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return _batch_to_dict(batch)


@batches_router.get("/{batch_id}")
async def get_batch(batch_id: str, db: Session = Depends(get_db)):
    """Get details of a specific batch."""
    batch = db.query(BatchOperation).filter(BatchOperation.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")
    return _batch_to_dict(batch)


@batches_router.patch("/{batch_id}")
async def update_batch(batch_id: str, db: Session = Depends(get_db)):
    """Update batch (pause, resume, retry)."""
    batch = db.query(BatchOperation).filter(BatchOperation.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")
    db.commit()
    return _batch_to_dict(batch)


@batches_router.delete("/{batch_id}", status_code=204)
async def cancel_batch(batch_id: str, db: Session = Depends(get_db)):
    """Cancel entire batch operation."""
    batch = db.query(BatchOperation).filter(BatchOperation.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")
    batch.status = "cancelled"  # type: ignore[assignment]
    db.commit()


@jobs_router.get("")
async def list_jobs(db: Session = Depends(get_db)):
    """List all scheduled jobs."""
    jobs = db.query(ScheduledJob).all()
    return {
        "jobs": [_job_to_dict(j) for j in jobs],
        "count": len(jobs),
    }


@jobs_router.post("/schedule", status_code=201)
async def schedule_job(payload: JobCreate, db: Session = Depends(get_db)):
    """Schedule a new download job."""
    job = ScheduledJob(
        name=payload.name,
        job_type="recurring" if payload.schedule_type.value != "once" else "one_time",
        status="pending",
        session_config={
            "product": payload.product,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "schedule_type": payload.schedule_type.value,
        },
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_to_dict(job)


@jobs_router.get("/{job_id}")
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get details of a specific scheduled job."""
    job = db.query(ScheduledJob).filter(ScheduledJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return _job_to_dict(job)


@jobs_router.patch("/{job_id}")
async def update_job(job_id: str, db: Session = Depends(get_db)):
    """Update a scheduled job (reschedule, enable, disable)."""
    job = db.query(ScheduledJob).filter(ScheduledJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    db.commit()
    return _job_to_dict(job)


@jobs_router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Delete/cancel a scheduled job."""
    job = db.query(ScheduledJob).filter(ScheduledJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    job.status = "cancelled"  # type: ignore[assignment]
    db.commit()


def _session_to_dict(s: DownloadSession) -> Dict[str, Any]:
    state: Dict[str, Any] = cast(Dict[str, Any], s.state) or {}
    return {
        "id": s.session_id,
        "status": s.status,
        "product": state.get("product", ""),
        "total_files": s.total_files,
        "completed_files": s.completed_files,
        "failed_files": s.failed_files,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _batch_to_dict(b: BatchOperation) -> Dict[str, Any]:
    return {
        "id": b.batch_id,
        "name": b.name,
        "description": b.description,
        "status": b.status,
        "total_sessions": b.total_sessions,
        "completed_sessions": b.completed_sessions,
        "failed_sessions": b.failed_sessions,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }


def _job_to_dict(j: ScheduledJob) -> Dict[str, Any]:
    return {
        "id": j.job_id,
        "name": j.name,
        "job_type": j.job_type,
        "status": j.status,
        "is_active": j.is_active,
        "next_run_time": j.next_run_time.isoformat() if j.next_run_time else None,
        "last_run_time": j.last_run_time.isoformat() if j.last_run_time else None,
        "created_at": j.created_at.isoformat() if j.created_at else None,
        "updated_at": j.updated_at.isoformat() if j.updated_at else None,
    }


__all__ = ["downloads_router", "batches_router", "jobs_router"]
