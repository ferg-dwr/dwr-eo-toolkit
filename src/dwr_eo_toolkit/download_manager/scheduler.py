from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from apscheduler.schedulers.background import BackgroundScheduler

from .session import DownloadSession


class DownloadScheduler:
    """Schedule downloads for specific times or recurring intervals."""

    def __init__(self) -> None:  # Add return type
        """Initialize the scheduler."""
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.jobs: Dict[str, Any] = {}

    def schedule_once(self, session: DownloadSession, run_at: datetime) -> str:  # Add return type
        """Schedule a one-time download."""
        raise NotImplementedError("Implement in Phase 4")

    def schedule_recurring(self, session: DownloadSession, interval: str) -> str:  # Add return type
        """Schedule recurring downloads (daily, weekly, etc)."""
        raise NotImplementedError("Implement in Phase 4")

    def pause_scheduled(self, job_id: str) -> None:  # Add return type
        """Pause a scheduled job."""
        raise NotImplementedError("Implement in Phase 4")

    def resume_scheduled(self, job_id: str) -> None:  # Add return type
        """Resume a paused job."""
        raise NotImplementedError("Implement in Phase 4")

    def cancel_scheduled(self, job_id: str) -> None:  # Add return type
        """Cancel a scheduled job."""
        raise NotImplementedError("Implement in Phase 4")

    def save_schedule(self, path: Path) -> bool:  # Add return type
        """Save schedule to JSON file."""
        raise NotImplementedError("Implement in Phase 4")

    def load_schedule(self, path: Path) -> bool:  # Add return type
        """Load schedule from JSON file."""
        raise NotImplementedError("Implement in Phase 4")

    def __del__(self):
        """Shutdown scheduler on deletion."""
        if self.scheduler.running:
            self.scheduler.shutdown()
