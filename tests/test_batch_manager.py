"""Tests for BatchDownloadManager."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dwr_eo_toolkit.download_manager.batch_manager import BatchDownloadManager
from dwr_eo_toolkit.download_manager.result import DownloadResult
from dwr_eo_toolkit.download_manager.session import DownloadSession


@pytest.fixture
def batch_manager(tmp_path: Path) -> BatchDownloadManager:
    """Create batch manager with temp checkpoint dir."""
    manager = BatchDownloadManager(max_concurrent_sessions=2)
    manager.checkpoint_dir = tmp_path / "checkpoints"
    manager.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    return manager


@pytest.fixture
def mock_session() -> MagicMock:
    """Create mock DownloadSession."""
    session = MagicMock(spec=DownloadSession)

    # Mock get_statistics()
    mock_stats = MagicMock()
    mock_stats.total_files = 10
    mock_stats.files_downloaded = 8
    mock_stats.files_failed = 2
    session.get_statistics.return_value = mock_stats

    # Mock execute()
    result = DownloadResult(total=10)
    result.successful = 8
    result.failed = 2
    session.execute.return_value = result

    return session


class TestBatchManagerBasics:
    """Test basic batch manager functionality."""

    def test_batch_manager_init(self) -> None:
        """Test batch manager initialization."""
        manager = BatchDownloadManager(max_concurrent_sessions=3)
        assert manager.max_concurrent == 3
        assert len(manager.sessions) == 0
        assert manager.paused is False

    def test_batch_manager_add_session(self, batch_manager: BatchDownloadManager) -> None:
        """Add single session."""
        session = MagicMock(spec=DownloadSession)
        batch_manager.add_session(session)
        assert len(batch_manager.sessions) == 1

    def test_batch_manager_add_multiple_sessions(self, batch_manager: BatchDownloadManager) -> None:
        """Add multiple sessions."""
        session1 = MagicMock(spec=DownloadSession)
        session2 = MagicMock(spec=DownloadSession)
        session3 = MagicMock(spec=DownloadSession)

        batch_manager.add_session(session1, priority="high")
        batch_manager.add_session(session2, priority="medium")
        batch_manager.add_session(session3, priority="low")

        assert len(batch_manager.sessions) == 3


class TestBatchManagerExecution:
    """Test batch execution."""

    def test_batch_manager_execute_empty(self, batch_manager: BatchDownloadManager) -> None:
        """Execute with no sessions."""
        results = batch_manager.execute_all()
        assert results == []

    def test_batch_manager_execute_single_session(
        self, batch_manager: BatchDownloadManager, mock_session: MagicMock
    ) -> None:
        """Execute single session."""
        batch_manager.add_session(mock_session)
        results = batch_manager.execute_all()

        assert len(results) == 1
        assert isinstance(results[0], DownloadResult)
        assert results[0].successful == 8
        assert results[0].failed == 2

    def test_batch_manager_execute_multiple_sessions(
        self, batch_manager: BatchDownloadManager
    ) -> None:
        """Execute multiple sessions in parallel."""
        mock_session1 = MagicMock(spec=DownloadSession)
        result1 = DownloadResult(total=5)
        result1.successful = 5
        mock_session1.execute.return_value = result1
        mock_session1.get_statistics.return_value = MagicMock(
            total_files=5, files_downloaded=5, files_failed=0
        )

        mock_session2 = MagicMock(spec=DownloadSession)
        result2 = DownloadResult(total=3)
        result2.successful = 3
        mock_session2.execute.return_value = result2
        mock_session2.get_statistics.return_value = MagicMock(
            total_files=3, files_downloaded=3, files_failed=0
        )

        batch_manager.add_session(mock_session1)
        batch_manager.add_session(mock_session2)

        results = batch_manager.execute_all()
        assert len(results) == 2
        assert all(isinstance(r, DownloadResult) for r in results)

    def test_batch_manager_execute_with_error(self, batch_manager: BatchDownloadManager) -> None:
        """Execute with session that raises error."""
        mock_session = MagicMock(spec=DownloadSession)
        mock_session.execute.side_effect = RuntimeError("Download failed")

        batch_manager.add_session(mock_session)
        results = batch_manager.execute_all()

        assert len(results) == 1
        assert results[0].total == 0
        assert "Download failed" in results[0].error_messages["session"]


class TestBatchManagerCheckpoints:
    """Test checkpoint functionality."""

    def test_batch_manager_save_checkpoint(
        self, batch_manager: BatchDownloadManager, mock_session: MagicMock
    ) -> None:
        """Save checkpoint during execution."""
        result = DownloadResult(total=10)
        result.successful = 8
        result.failed = 2

        checkpoint_file = batch_manager.save_checkpoint("test_checkpoint", mock_session, result)

        assert checkpoint_file.exists()
        assert checkpoint_file.name == "test_checkpoint.json"

        # Verify checkpoint content
        checkpoint_data = json.loads(checkpoint_file.read_text())
        assert checkpoint_data["id"] == "test_checkpoint"
        assert "timestamp" in checkpoint_data
        assert checkpoint_data["result"]["successful"] == 8
        assert checkpoint_data["result"]["failed"] == 2

    def test_batch_manager_list_checkpoints(
        self, batch_manager: BatchDownloadManager, mock_session: MagicMock
    ) -> None:
        """List available checkpoints."""
        result = DownloadResult(total=10)

        # Create multiple checkpoints
        batch_manager.save_checkpoint("checkpoint1", mock_session, result)
        batch_manager.save_checkpoint("checkpoint2", mock_session, result)

        checkpoints = batch_manager.list_checkpoints()

        assert len(checkpoints) == 2
        assert checkpoints[0]["id"] in ["checkpoint1", "checkpoint2"]
        assert "timestamp" in checkpoints[0]
        assert "file" in checkpoints[0]

    def test_batch_manager_resume_from_checkpoint_not_found(
        self, batch_manager: BatchDownloadManager
    ) -> None:
        """Resume from non-existent checkpoint."""
        result = batch_manager.resume_from_checkpoint("nonexistent")
        assert result is None

    def test_batch_manager_resume_from_checkpoint(
        self, batch_manager: BatchDownloadManager, mock_session: MagicMock
    ) -> None:
        """Resume from checkpoint."""
        # Create and save a checkpoint
        result = DownloadResult(total=10)
        result.successful = 5
        batch_manager.save_checkpoint("test_checkpoint", mock_session, result)

        # Resume from checkpoint
        batch_manager.add_session(mock_session)
        resumed = batch_manager.resume_from_checkpoint("test_checkpoint")

        assert resumed is not None
        assert isinstance(resumed, list)

    def test_batch_manager_clear_checkpoints(
        self, batch_manager: BatchDownloadManager, mock_session: MagicMock
    ) -> None:
        """Clear all checkpoints."""
        result = DownloadResult(total=10)

        # Create multiple checkpoints
        batch_manager.save_checkpoint("checkpoint1", mock_session, result)
        batch_manager.save_checkpoint("checkpoint2", mock_session, result)

        count = batch_manager.clear_checkpoints()

        assert count == 2
        assert len(batch_manager.list_checkpoints()) == 0


class TestBatchManagerControl:
    """Test pause/resume/cancel functionality."""

    def test_batch_manager_pause_all(self, batch_manager: BatchDownloadManager) -> None:
        """Pause all sessions."""
        mock_session = MagicMock(spec=DownloadSession)
        batch_manager.add_session(mock_session)

        batch_manager.pause_all()

        assert batch_manager.paused is True
        mock_session.pause.assert_called_once()

    def test_batch_manager_resume_all(self, batch_manager: BatchDownloadManager) -> None:
        """Resume all sessions."""
        mock_session = MagicMock(spec=DownloadSession)
        batch_manager.add_session(mock_session)

        batch_manager.pause_all()
        assert batch_manager.paused is True

        batch_manager.resume_all()
        assert batch_manager.paused is False
        mock_session.resume.assert_called_once()

    def test_batch_manager_cancel_all(self, batch_manager: BatchDownloadManager) -> None:
        """Cancel all sessions."""
        mock_session = MagicMock(spec=DownloadSession)
        batch_manager.add_session(mock_session)

        batch_manager.cancel_all()

        mock_session.cancel.assert_called_once()


class TestBatchManagerProgress:
    """Test progress tracking."""

    def test_batch_manager_get_progress_empty(self, batch_manager: BatchDownloadManager) -> None:
        """Get progress with no sessions."""
        progress = batch_manager.get_progress()

        assert progress["total_files"] == 0
        assert progress["completed"] == 0
        assert progress["failed"] == 0
        assert progress["percentage"] == 0.0

    def test_batch_manager_get_progress_single_session(
        self, batch_manager: BatchDownloadManager, mock_session: MagicMock
    ) -> None:
        """Get progress with single session."""
        batch_manager.add_session(mock_session)
        progress = batch_manager.get_progress()

        assert progress["total_files"] == 10
        assert progress["completed"] == 8
        assert progress["failed"] == 2
        assert progress["pending"] == 0
        assert progress["percentage"] == 80.0

    def test_batch_manager_get_progress_multiple_sessions(
        self, batch_manager: BatchDownloadManager
    ) -> None:
        """Get progress with multiple sessions."""
        mock_session1 = MagicMock(spec=DownloadSession)
        mock_session1.get_statistics.return_value = MagicMock(
            total_files=10, files_downloaded=8, files_failed=2
        )

        mock_session2 = MagicMock(spec=DownloadSession)
        mock_session2.get_statistics.return_value = MagicMock(
            total_files=5, files_downloaded=5, files_failed=0
        )

        batch_manager.add_session(mock_session1)
        batch_manager.add_session(mock_session2)

        progress = batch_manager.get_progress()

        assert progress["total_files"] == 15
        assert progress["completed"] == 13
        assert progress["failed"] == 2
        assert progress["pending"] == 0
        assert progress["percentage"] == pytest.approx(86.67, 0.01)


class TestBatchManagerStatistics:
    """Test statistics gathering."""

    def test_batch_manager_get_statistics_empty(self, batch_manager: BatchDownloadManager) -> None:
        """Get statistics with no sessions."""
        stats = batch_manager.get_statistics()

        assert stats["total_sessions"] == 0
        assert stats["completed_sessions"] == 0
        assert stats["sessions"] == []

    def test_batch_manager_get_statistics_single_session(
        self, batch_manager: BatchDownloadManager, mock_session: MagicMock
    ) -> None:
        """Get statistics with single session."""
        batch_manager.add_session(mock_session)
        stats = batch_manager.get_statistics()

        assert stats["total_sessions"] == 1
        assert len(stats["sessions"]) == 1
        assert stats["sessions"][0]["session_id"] == 0
        assert stats["sessions"][0]["total_files"] == 10
        assert stats["sessions"][0]["files_downloaded"] == 8
        assert stats["sessions"][0]["files_failed"] == 2

    def test_batch_manager_get_statistics_multiple_sessions(
        self, batch_manager: BatchDownloadManager
    ) -> None:
        """Get statistics with multiple sessions."""
        mock_session1 = MagicMock(spec=DownloadSession)
        mock_session1.get_statistics.return_value = MagicMock(
            total_files=10, files_downloaded=8, files_failed=2
        )

        mock_session2 = MagicMock(spec=DownloadSession)
        mock_session2.get_statistics.return_value = MagicMock(
            total_files=5, files_downloaded=5, files_failed=0
        )

        batch_manager.add_session(mock_session1)
        batch_manager.add_session(mock_session2)

        stats = batch_manager.get_statistics()

        assert stats["total_sessions"] == 2
        assert len(stats["sessions"]) == 2
        assert stats["sessions"][0]["session_id"] == 0
        assert stats["sessions"][1]["session_id"] == 1
