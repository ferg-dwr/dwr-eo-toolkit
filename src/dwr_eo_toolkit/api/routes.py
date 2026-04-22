"""
API Routes — REST endpoints for downloads, batches, and scheduled jobs.
"""

from typing import Any, Dict, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..database.models import BatchOperation, DownloadSession, ScheduledJob
from .schemas import BatchCreate, DownloadCreate, JobCreate

downloads_router = APIRouter(prefix="/api/v1/downloads", tags=["downloads"])
batches_router = APIRouter(prefix="/api/v1/batches", tags=["batches"])
jobs_router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


# ---------------------------------------------------------------------------
# Downloads
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
