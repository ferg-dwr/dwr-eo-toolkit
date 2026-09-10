"""
API Routes — REST endpoints for downloads, batches, scheduled jobs, and search.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..database.models import BatchOperation, DownloadSession, ScheduledJob
from ..filters.spatial import BoundingBox
from ..providers import EarthAccessProvider
from .schemas import BatchCreate, DownloadCreate, JobCreate

# ==============================================================================
# Pydantic Models for Search & Download Endpoints
# ==============================================================================


class GranuleQueryRequest(BaseModel):
    """Fields shared by every endpoint that resolves a product + bbox + date range.

    Search and download differ in what they do with the granules, not in how
    the query is described, so the validation lives here once. Coordinate
    checking delegates to filters.spatial.BoundingBox rather than restating
    the rules -- that class already knows latitude is +/-90, not +/-180, and
    that an inverted box is an error rather than an empty result.
    """

    product: str = Field(..., description="Product name (e.g., 'ECOSTRESS', 'MODIS')")
    min_lon: float = Field(..., description="Min longitude")
    min_lat: float = Field(..., description="Min latitude")
    max_lon: float = Field(..., description="Max longitude")
    max_lat: float = Field(..., description="Max latitude")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")

    @field_validator("product")
    @classmethod
    def validate_product(cls, v):
        valid_products = ["ECOSTRESS", "MODIS"]
        if v.upper() not in valid_products:
            raise ValueError(f"Product must be one of {valid_products}")
        return v.upper()

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in format YYYY-MM-DD")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v, info):
        if "start_date" in info.data:
            start = datetime.strptime(info.data["start_date"], "%Y-%m-%d")
            end = datetime.strptime(v, "%Y-%m-%d")
            if end < start:
                raise ValueError("end_date must be >= start_date")
        return v

    @model_validator(mode="after")
    def validate_bbox(self):
        """Reject out-of-range and inverted boxes at the door.

        A transposed bbox is not a validation error to CMR -- it just returns
        no granules, which is indistinguishable from a genuinely empty result
        and miserable to debug from a notebook.
        """
        BoundingBox(self.min_lon, self.min_lat, self.max_lon, self.max_lat).validate()
        return self

    def get_bbox(self) -> tuple[float, float, float, float]:
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)


class SearchRequest(GranuleQueryRequest):
    """Request model for search endpoint"""

    max_results: int = Field(100, description="Max granules to return", ge=1, le=2000)


class SearchResponse(BaseModel):
    """Response model for search endpoint"""

    success: bool
    message: str
    total: int = Field(0, description="Total granules found")
    returned: int = Field(0, description="Granules returned in this response")
    granules: list[dict] = Field(default_factory=list)
    request_summary: dict = Field(default_factory=dict)


class DownloadStartRequest(GranuleQueryRequest):
    """Request to search for granules and download them."""

    max_results: int = Field(10, description="Max granules to download", ge=1, le=100)
    output_dir: str = Field("./downloads", description="Output directory for files")
    max_workers: int = Field(3, description="Parallel download workers", ge=1, le=10)


class DownloadStartResponse(BaseModel):
    """Response when download finishes"""

    success: bool
    message: str
    download_session_id: str
    status: str = Field(..., description="Final status (completed/failed/partial)")
    product: str
    granules_found: int
    files_downloaded: int
    files_failed: int
    output_dir: str
    downloaded_files: list[str] = Field(default_factory=list)
    tracking_url: str


# ==============================================================================
# Routers & Provider
# ==============================================================================

downloads_router = APIRouter(prefix="/api/v1/downloads", tags=["downloads"])
batches_router = APIRouter(prefix="/api/v1/batches", tags=["batches"])
jobs_router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

_provider = None


def get_provider() -> EarthAccessProvider:
    """Get or create provider instance"""
    global _provider
    if _provider is None:
        _provider = EarthAccessProvider()
    return _provider


# ---------------------------------------------------------------------------
# Search Endpoint
# ---------------------------------------------------------------------------


@downloads_router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search for imagery granules",
    description="""
    Search for NASA Earth observation granules by product, location, and date range.

    Returns metadata about available granules that match the search criteria.
    """,
)
async def search_imagery(
    request: SearchRequest,
    provider: EarthAccessProvider = Depends(get_provider),
) -> SearchResponse:
    """Search for imagery granules."""
    try:
        print(f"🔍 Search request: {request.product}")
        print(f"   Bbox: {request.get_bbox()}")
        print(f"   Dates: {request.start_date} to {request.end_date}")

        granules, total = provider.search(
            product=request.product,
            bounding_box=request.get_bbox(),
            start_date=request.start_date,
            end_date=request.end_date,
            max_results=request.max_results,
        )

        print(f"   ✅ Found {total} granules (returning {len(granules)})")

        return SearchResponse(
            success=True,
            message=f"Found {total} granules matching criteria",
            total=total,
            returned=len(granules),
            granules=[{"id": str(g), "title": str(g), "raw": str(g)} for g in granules],
            request_summary={
                "product": request.product,
                "bbox": request.get_bbox(),
                "start_date": request.start_date,
                "end_date": request.end_date,
            },
        )

    except ValueError as e:
        print(f"❌ Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        print(f"❌ Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ---------------------------------------------------------------------------
# Download Endpoint — SYNCHRONOUS download wired in
# ---------------------------------------------------------------------------


@downloads_router.post(
    "/start",
    status_code=200,
    response_model=DownloadStartResponse,
    summary="Search and download granules",
    description="""
    Search for granules and download them to the specified directory.

    This endpoint:
    1. Searches NASA Earthdata for granules matching your criteria
    2. Creates a DownloadSession record in the database
    3. Downloads files to the specified output directory
    4. Updates session status and returns final results

    Note: This is a synchronous endpoint — the request will block until
    downloads complete. For large downloads, this may take a while.
    """,
)
async def start_download(
    request: DownloadStartRequest,
    db: Session = Depends(get_db),
    provider: EarthAccessProvider = Depends(get_provider),
) -> DownloadStartResponse:
    """Search for granules and download them."""
    session = None

    try:
        # ---- Step 1: Search ----
        print(f"📥 Starting download: {request.product}")
        print(f"   Output: {request.output_dir}")
        print("   🔍 Searching for granules...")

        granules, total = provider.search(
            product=request.product,
            bounding_box=(
                request.min_lon,
                request.min_lat,
                request.max_lon,
                request.max_lat,
            ),
            start_date=request.start_date,
            end_date=request.end_date,
            max_results=request.max_results,
        )

        if not granules:
            raise ValueError("No granules found matching search criteria")

        print(f"   ✅ Found {len(granules)} granules")

        # ---- Step 2: Create DB record ----
        session = DownloadSession(
            status="downloading",
            total_files=len(granules),
            state={
                "product": request.product,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "bbox": [
                    request.min_lon,
                    request.min_lat,
                    request.max_lon,
                    request.max_lat,
                ],
                "output_dir": request.output_dir,
                "granule_count": len(granules),
            },
        )
        session.started_at = datetime.utcnow()  # type: ignore[assignment]
        db.add(session)
        db.commit()
        db.refresh(session)

        download_id = session.session_id
        print(f"   💾 Created download session: {download_id}")

        # ---- Step 3: Ensure output dir exists ----
        output_path = Path(request.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"   📁 Output dir ready: {output_path.resolve()}")

        # ---- Step 4: Download ----
        print(f"   ⬇️  Downloading {len(granules)} granules...")
        try:
            files = provider.download(
                granules,
                str(output_path),
                max_workers=request.max_workers,
                show_progress=False,  # Don't spam logs
            )

            # ---- Step 5: Update DB record on success ----
            files_downloaded = len(files)
            files_failed = len(granules) - files_downloaded

            session.completed_files = files_downloaded  # type: ignore[assignment]
            session.failed_files = files_failed  # type: ignore[assignment]
            session.status = "completed" if files_failed == 0 else "partial"  # type: ignore[assignment]
            session.completed_at = datetime.utcnow()  # type: ignore[assignment]
            db.commit()

            print(f"   ✅ Downloaded {files_downloaded}/{len(granules)} files")

            return DownloadStartResponse(
                success=True,
                message=f"Downloaded {files_downloaded} of {len(granules)} files",
                download_session_id=download_id,
                status=session.status,  # type: ignore[arg-type]
                product=request.product,
                granules_found=len(granules),
                files_downloaded=files_downloaded,
                files_failed=files_failed,
                output_dir=str(output_path.resolve()),
                downloaded_files=[str(f) for f in files],
                tracking_url=f"/api/v1/downloads/{download_id}",
            )

        except Exception as download_err:
            # ---- Mark session failed ----
            print(f"   ❌ Download failed: {download_err}")
            if session is not None:
                session.status = "failed"  # type: ignore[assignment]
                session.completed_at = datetime.utcnow()  # type: ignore[assignment]
                db.commit()
            raise

    except ValueError as e:
        print(f"❌ Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        print(f"❌ Download start failed: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


# ---------------------------------------------------------------------------
# Downloads — list, get, update, delete
# ---------------------------------------------------------------------------


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
    """Register a download session without running it.

    Cheap and side-effect free: no CMR query, no files. Use POST
    /api/v1/downloads/start to actually fetch granules.
    """
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


# ---------------------------------------------------------------------------
# Batches
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session_to_dict(s: DownloadSession) -> dict[str, Any]:
    state: dict[str, Any] = cast(dict[str, Any], s.state) or {}
    return {
        "id": s.session_id,
        "status": s.status,
        "product": state.get("product", ""),
        "output_dir": state.get("output_dir", ""),
        "total_files": s.total_files,
        "completed_files": s.completed_files,
        "failed_files": s.failed_files,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }


def _batch_to_dict(b: BatchOperation) -> dict[str, Any]:
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


def _job_to_dict(j: ScheduledJob) -> dict[str, Any]:
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
