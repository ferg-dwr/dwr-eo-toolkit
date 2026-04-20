"""Download scheduling management."""

import logging
from datetime import datetime
from typing import Dict, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from .session import DownloadSession

logger = logging.getLogger(__name__)


class DownloadScheduler:
    """Schedule downloads at specific times or intervals."""

    def __init__(self) -> None:
        """Initialize scheduler."""
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.jobs: Dict[str, dict] = {}

    def schedule_once(self, session: DownloadSession, run_at: datetime) -> str:
        """Schedule a one-time download.

        Args:
            session: DownloadSession to execute
            run_at: When to run (datetime object)

        Returns:
            Job ID
        """
        job = self.scheduler.add_job(
            self._execute_session,
            trigger=DateTrigger(run_date=run_at),
            args=[session],
        )

        job_id = str(job.id)
        self.jobs[job_id] = {
            "type": "once",
            "scheduled_for": run_at.isoformat(),
            "status": "scheduled",
        }

        logger.info(f"Scheduled one-time download for {run_at} (job_id={job_id})")
        return job_id

    def schedule_recurring(self, session: DownloadSession, cron: str) -> str:
        """Schedule recurring downloads.

        Args:
            session: DownloadSession to execute
            cron: Cron expression (e.g., "0 2 * * MON" = Monday 2 AM)

        Returns:
            Job ID
        """
        job = self.scheduler.add_job(
            self._execute_session,
            trigger=CronTrigger.from_crontab(cron),
            args=[session],
        )

        job_id = str(job.id)
        self.jobs[job_id] = {
            "type": "recurring",
            "cron": cron,
            "status": "scheduled",
        }

        logger.info(f"Scheduled recurring download: {cron} (job_id={job_id})")
        return job_id

    def pause_scheduled(self, job_id: str) -> bool:
        """Pause a scheduled job.

        Args:
            job_id: Job to pause

        Returns:
            True if successful
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.pause()
                self.jobs[job_id]["status"] = "paused"
                logger.info(f"Paused job {job_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")
        return False

    def resume_scheduled(self, job_id: str) -> bool:
        """Resume a paused job.

        Args:
            job_id: Job to resume

        Returns:
            True if successful
        """
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.resume()
                self.jobs[job_id]["status"] = "scheduled"
                logger.info(f"Resumed job {job_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
        return False

    def cancel_scheduled(self, job_id: str) -> bool:
        """Cancel a scheduled job.

        Args:
            job_id: Job to cancel

        Returns:
            True if successful
        """
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.jobs:
                del self.jobs[job_id]
            logger.info(f"Cancelled job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
        return False

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job details.

        Args:
            job_id: Job ID

        Returns:
            Job metadata or None
        """
        return self.jobs.get(job_id)

    def list_jobs(self) -> Dict[str, dict]:
        """List all scheduled jobs.

        Returns:
            Dictionary of all jobs
        """
        return self.jobs.copy()

    def _execute_session(self, session: DownloadSession) -> None:
        """Execute a download session.

        Args:
            session: DownloadSession to run
        """
        logger.info("Executing scheduled download session")
        session.execute()

    def __del__(self):
        """Cleanup scheduler on deletion."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
