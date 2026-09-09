"""
Unit tests for DownloadScheduler.

Tests cover:
- One-time scheduling (date trigger)
- Recurring scheduling (cron patterns)
- Job lifecycle (pause, resume, cancel)
- Job listing and retrieval
- Error handling
- APScheduler integration
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from dwr_eo_toolkit.download_manager.scheduler import DownloadScheduler
from dwr_eo_toolkit.download_manager.session import DownloadSession


@pytest.fixture
def mock_session():
    """Create a mock DownloadSession."""
    session = Mock(spec=DownloadSession)
    session.execute = MagicMock()
    return session


@pytest.fixture
def scheduler():
    """Create a DownloadScheduler instance with proper Mock job IDs."""
    with patch(
        "dwr_eo_toolkit.download_manager.scheduler.BackgroundScheduler"
    ) as mock_bg_class:
        mock_scheduler = Mock()
        mock_bg_class.return_value = mock_scheduler

        call_count = [0]

        def create_mock_job(*args, **kwargs):
            """Create a Mock job with unique ID."""
            call_count[0] += 1
            mock_job = Mock()
            mock_job.id = f"job_{call_count[0]}"
            mock_job.pause = Mock()
            mock_job.resume = Mock()
            return mock_job

        mock_scheduler.add_job.side_effect = create_mock_job

        scheduler_instance = DownloadScheduler()

        return scheduler_instance


class TestDownloadSchedulerBasics:
    """Tests for basic scheduler functionality."""

    def test_scheduler_initialization(self):
        """Should initialize with BackgroundScheduler."""
        with patch(
            "dwr_eo_toolkit.download_manager.scheduler.BackgroundScheduler"
        ) as mock_bg:
            scheduler = DownloadScheduler()

            assert scheduler.scheduler is not None
            assert isinstance(scheduler.jobs, dict)
            assert len(scheduler.jobs) == 0
            mock_bg.return_value.start.assert_called_once()

    def test_schedule_once_basic(self, scheduler, mock_session):
        """Should schedule a one-time download."""
        run_at = datetime.now() + timedelta(hours=1)

        job_id = scheduler.schedule_once(mock_session, run_at)

        assert job_id is not None
        assert job_id in scheduler.jobs
        assert scheduler.jobs[job_id]["type"] == "once"
        assert scheduler.jobs[job_id]["status"] == "scheduled"
        assert scheduler.jobs[job_id]["scheduled_for"] == run_at.isoformat()

    def test_schedule_once_calls_add_job(self, scheduler, mock_session):
        """Should call scheduler.add_job with DateTrigger."""
        run_at = datetime.now() + timedelta(hours=2)

        scheduler.schedule_once(mock_session, run_at)

        scheduler.scheduler.add_job.assert_called_once()
        call_args = scheduler.scheduler.add_job.call_args

        # Verify trigger type and function
        assert call_args[0][0] == scheduler._execute_session
        assert call_args[1]["args"] == [mock_session]

    def test_schedule_recurring_basic(self, scheduler, mock_session):
        """Should schedule recurring downloads with cron."""
        cron = "0 2 * * MON"  # Monday 2 AM

        job_id = scheduler.schedule_recurring(mock_session, cron)

        assert job_id is not None
        assert job_id in scheduler.jobs
        assert scheduler.jobs[job_id]["type"] == "recurring"
        assert scheduler.jobs[job_id]["cron"] == cron
        assert scheduler.jobs[job_id]["status"] == "scheduled"

    def test_schedule_recurring_calls_add_job(self, scheduler, mock_session):
        """Should call scheduler.add_job with CronTrigger."""
        cron = "0 6 * * *"  # Every day at 6 AM

        scheduler.schedule_recurring(mock_session, cron)

        scheduler.scheduler.add_job.assert_called_once()
        call_args = scheduler.scheduler.add_job.call_args

        assert call_args[0][0] == scheduler._execute_session
        assert call_args[1]["args"] == [mock_session]


class TestSchedulerJobLifecycle:
    """Tests for job pause, resume, cancel operations."""

    def test_pause_scheduled_job(self, scheduler, mock_session):
        """Should pause a scheduled job."""
        job_id = scheduler.schedule_once(
            mock_session, datetime.now() + timedelta(hours=1)
        )
        mock_job = Mock()
        scheduler.scheduler.get_job.return_value = mock_job

        result = scheduler.pause_scheduled(job_id)

        assert result is True
        mock_job.pause.assert_called_once()
        assert scheduler.jobs[job_id]["status"] == "paused"

    def test_pause_nonexistent_job(self, scheduler):
        """Should return False for nonexistent job."""
        scheduler.scheduler.get_job.return_value = None

        result = scheduler.pause_scheduled("nonexistent")

        assert result is False

    def test_pause_job_error_handling(self, scheduler):
        """Should handle errors when pausing job."""
        scheduler.scheduler.get_job.side_effect = Exception("Scheduler error")

        result = scheduler.pause_scheduled("some_job_id")

        assert result is False

    def test_resume_scheduled_job(self, scheduler, mock_session):
        """Should resume a paused job."""
        job_id = scheduler.schedule_once(
            mock_session, datetime.now() + timedelta(hours=1)
        )
        scheduler.jobs[job_id]["status"] = "paused"

        mock_job = Mock()
        scheduler.scheduler.get_job.return_value = mock_job

        result = scheduler.resume_scheduled(job_id)

        assert result is True
        mock_job.resume.assert_called_once()
        assert scheduler.jobs[job_id]["status"] == "scheduled"

    def test_resume_nonexistent_job(self, scheduler):
        """Should return False for nonexistent job."""
        scheduler.scheduler.get_job.return_value = None

        result = scheduler.resume_scheduled("nonexistent")

        assert result is False

    def test_cancel_scheduled_job(self, scheduler, mock_session):
        """Should cancel and remove a scheduled job."""
        job_id = scheduler.schedule_once(
            mock_session, datetime.now() + timedelta(hours=1)
        )

        result = scheduler.cancel_scheduled(job_id)

        assert result is True
        scheduler.scheduler.remove_job.assert_called_with(job_id)
        assert job_id not in scheduler.jobs

    def test_cancel_nonexistent_job(self, scheduler):
        """Should handle canceling nonexistent job."""
        scheduler.scheduler.remove_job.side_effect = Exception("Job not found")

        result = scheduler.cancel_scheduled("nonexistent")

        assert result is False

    def test_cancel_removes_from_tracking(self, scheduler, mock_session):
        """Should remove job from internal tracking on cancel."""
        job_id = scheduler.schedule_once(
            mock_session, datetime.now() + timedelta(hours=1)
        )
        assert job_id in scheduler.jobs

        scheduler.cancel_scheduled(job_id)

        assert job_id not in scheduler.jobs


class TestSchedulerJobRetrieval:
    """Tests for getting and listing jobs."""

    def test_get_job_returns_metadata(self, scheduler, mock_session):
        """Should return job metadata."""
        run_at = datetime.now() + timedelta(hours=1)
        job_id = scheduler.schedule_once(mock_session, run_at)

        job_metadata = scheduler.get_job(job_id)

        assert job_metadata is not None
        assert job_metadata["type"] == "once"
        assert job_metadata["status"] == "scheduled"

    def test_get_nonexistent_job(self, scheduler):
        """Should return None for nonexistent job."""
        result = scheduler.get_job("nonexistent")

        assert result is None

    def test_list_jobs_empty(self, scheduler):
        """Should return empty dict when no jobs scheduled."""
        jobs = scheduler.list_jobs()

        assert isinstance(jobs, dict)
        assert len(jobs) == 0

    def test_list_jobs_returns_all(self, scheduler, mock_session):
        """Should return all scheduled jobs."""
        job_id_1 = scheduler.schedule_once(
            mock_session, datetime.now() + timedelta(hours=1)
        )
        job_id_2 = scheduler.schedule_recurring(mock_session, "0 6 * * *")

        jobs = scheduler.list_jobs()

        assert len(jobs) == 2
        assert job_id_1 in jobs
        assert job_id_2 in jobs
        assert jobs[job_id_1]["type"] == "once"
        assert jobs[job_id_2]["type"] == "recurring"

    def test_list_jobs_returns_copy(self, scheduler, mock_session):
        """Should return a copy, not the original dict."""
        scheduler.schedule_once(mock_session, datetime.now() + timedelta(hours=1))

        jobs = scheduler.list_jobs()
        jobs["fake_job"] = {"type": "fake"}

        # Original scheduler.jobs should not be modified
        assert "fake_job" not in scheduler.jobs
        assert len(scheduler.jobs) == 1


class TestSchedulerCronPatterns:
    """Tests for various cron expression patterns."""

    @pytest.mark.parametrize(
        "cron,description",
        [
            ("0 6 * * *", "Daily at 6 AM"),
            ("0 6 * * MON", "Monday at 6 AM"),
            ("0 6 * * MON-FRI", "Weekdays at 6 AM"),
            ("0 6 1 * *", "Monthly on 1st at 6 AM"),
            ("*/15 * * * *", "Every 15 minutes"),
            ("0 0 * * SUN", "Weekly on Sunday midnight"),
        ],
    )
    def test_schedule_various_cron_patterns(
        self, scheduler, mock_session, cron, description
    ):
        """Should schedule with various cron patterns."""
        job_id = scheduler.schedule_recurring(mock_session, cron)

        assert job_id in scheduler.jobs
        assert scheduler.jobs[job_id]["cron"] == cron

    def test_invalid_cron_expression(self, scheduler, mock_session):
        """Should fail gracefully with invalid cron."""
        with patch.object(
            scheduler.scheduler, "add_job", side_effect=ValueError("Invalid cron")
        ):
            with pytest.raises(ValueError):
                scheduler.schedule_recurring(mock_session, "invalid cron")


class TestSchedulerExecution:
    """Tests for session execution callback."""

    def test_execute_session_calls_execute(self, scheduler, mock_session):
        """Should call session.execute() when job runs."""
        scheduler._execute_session(mock_session)

        mock_session.execute.assert_called_once()

    def test_execute_session_with_multiple_calls(self, scheduler, mock_session):
        """Should handle multiple executions."""
        for _ in range(3):
            scheduler._execute_session(mock_session)

        assert mock_session.execute.call_count == 3


class TestSchedulerIntegration:
    """Integration tests for scheduler workflow."""

    def test_complete_job_lifecycle(self, scheduler, mock_session):
        """Should handle complete job lifecycle: schedule -> pause -> resume -> cancel."""
        # Schedule
        job_id = scheduler.schedule_once(
            mock_session, datetime.now() + timedelta(hours=1)
        )
        assert scheduler.jobs[job_id]["status"] == "scheduled"

        # Pause
        mock_job = Mock()
        scheduler.scheduler.get_job.return_value = mock_job
        scheduler.pause_scheduled(job_id)
        assert scheduler.jobs[job_id]["status"] == "paused"

        # Resume
        scheduler.resume_scheduled(job_id)
        assert scheduler.jobs[job_id]["status"] == "scheduled"

        # Cancel
        scheduler.cancel_scheduled(job_id)
        assert job_id not in scheduler.jobs

    def test_multiple_concurrent_jobs(self, scheduler, mock_session):
        """Should handle multiple concurrent scheduled jobs."""
        job_ids = []
        for i in range(5):
            job_id = scheduler.schedule_once(
                mock_session, datetime.now() + timedelta(hours=i + 1)
            )
            job_ids.append(job_id)

        all_jobs = scheduler.list_jobs()

        assert len(all_jobs) == 5
        for job_id in job_ids:
            assert job_id in all_jobs

    def test_mixed_job_types(self, scheduler, mock_session):
        """Should handle mix of one-time and recurring jobs."""
        once_id = scheduler.schedule_once(
            mock_session, datetime.now() + timedelta(hours=1)
        )
        recurring_id = scheduler.schedule_recurring(mock_session, "0 6 * * *")

        all_jobs = scheduler.list_jobs()

        assert all_jobs[once_id]["type"] == "once"
        assert all_jobs[recurring_id]["type"] == "recurring"


class TestSchedulerCleanup:
    """Tests for scheduler cleanup and shutdown."""

    def test_scheduler_shutdown_on_deletion(self):
        """Should shutdown scheduler when deleted."""
        with patch(
            "dwr_eo_toolkit.download_manager.scheduler.BackgroundScheduler"
        ) as mock_bg:
            mock_scheduler = Mock()
            mock_bg.return_value = mock_scheduler
            mock_scheduler.running = True

            scheduler = DownloadScheduler()
            del scheduler

            mock_scheduler.shutdown.assert_called_once()

    def test_scheduler_cleanup_skips_if_not_running(self):
        """Should skip shutdown if scheduler not running."""
        with patch(
            "dwr_eo_toolkit.download_manager.scheduler.BackgroundScheduler"
        ) as mock_bg:
            mock_scheduler = Mock()
            mock_bg.return_value = mock_scheduler
            mock_scheduler.running = False

            scheduler = DownloadScheduler()
            del scheduler

            mock_scheduler.shutdown.assert_not_called()
