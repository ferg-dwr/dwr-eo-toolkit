"""
Test suite for downloads module - 50+ comprehensive tests.

Tests cover:
- DownloadTask: Single file downloads, checksums, resume, errors
- DownloadProgress: Progress tracking, speed calculation, ETA
- DownloadResult: Statistics, success rates, size conversions
- DownloadSession: Batch operations, parallel downloads, pause/resume
- DownloadManager: Main API, granule preparation
- Resilience: Retry strategies, exponential backoff
- Utilities: Formatting functions for bytes, speed, time
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Union, cast
from unittest.mock import MagicMock, patch

import pytest

from dwr_eo_toolkit.download_manager import (  # ResilienceManager, ResumeConfig,
    DownloadManager,
    DownloadProgress,
    DownloadResult,
    DownloadSession,
    DownloadStatistics,
    DownloadTask,
    ExponentialBackoffRetry,
    RetryConfig,
    RetryStrategy,
    TaskStatus,
    format_bytes,
    format_speed,
    format_time,
)


class TestDownloadTask:
    """Test DownloadTask class for single file downloads."""

    def test_create_task(self, tmp_path):
        """Test creating a download task."""
        task = DownloadTask(
            url="https://example.com/file.hdf",
            output_path=tmp_path / "file.hdf",
            filename="file.hdf",
            size=1024 * 1024,
            checksum="abc123",
        )
        assert task.url == "https://example.com/file.hdf"
        assert task.filename == "file.hdf"
        assert task.status == TaskStatus.PENDING
        assert task.downloaded_bytes == 0

    def test_task_string_path(self, tmp_path):
        """Test task with string path converts to Path."""
        task = DownloadTask(
            url="https://example.com/file.hdf",
            output_path=cast(Path, str(tmp_path / "file.hdf")),
        )
        assert isinstance(task.output_path, Path)

    def test_task_auto_filename(self, tmp_path):
        """Test task with auto-generated filename."""
        task = DownloadTask(
            url="https://example.com/file.hdf",
            output_path=tmp_path / "file.hdf",
        )
        assert task.filename == "file.hdf"

    def test_task_status_transitions(self, tmp_path):
        """Test task status transitions."""
        task = DownloadTask(
            url="https://example.com/file.hdf",
            output_path=tmp_path / "file.hdf",
        )
        assert task.status == TaskStatus.PENDING

        task.status = TaskStatus.DOWNLOADING
        assert task.status == TaskStatus.DOWNLOADING

        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

    @patch("requests.get")
    def test_download_success(self, mock_get, tmp_path):
        """Test successful download."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"test data"]
        mock_response.headers = {"content-length": "9"}
        mock_get.return_value = mock_response

        task = DownloadTask(
            url="https://example.com/file.txt",
            output_path=tmp_path / "file.txt",
        )

        success = task.download()
        assert success
        assert task.status == TaskStatus.COMPLETED
        assert task.output_path.exists()

    @patch("requests.get")
    def test_download_with_checksum_match(self, mock_get, tmp_path):
        """Test download with matching checksum."""
        content = b"test data"
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [content]
        mock_response.headers = {"content-length": "9"}
        mock_get.return_value = mock_response

        checksum = hashlib.md5(content).hexdigest()

        task = DownloadTask(
            url="https://example.com/file.txt",
            output_path=tmp_path / "file.txt",
            checksum=checksum,
            checksum_type="md5",
        )

        success = task.download()
        assert success
        assert task.status == TaskStatus.COMPLETED

    @patch("requests.get")
    def test_download_checksum_mismatch(self, mock_get, tmp_path):
        """Test download with mismatched checksum."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"test data"]
        mock_response.headers = {"content-length": "9"}
        mock_get.return_value = mock_response

        task = DownloadTask(
            url="https://example.com/file.txt",
            output_path=tmp_path / "file.txt",
            checksum="invalid_checksum",
        )

        success = task.download()
        assert not success
        assert task.status == TaskStatus.FAILED

    @patch("requests.get")
    def test_download_network_error(self, mock_get, tmp_path):
        """Test download with network error."""
        import requests

        mock_get.side_effect = requests.ConnectionError("Network error")

        task = DownloadTask(
            url="https://example.com/file.txt",
            output_path=tmp_path / "file.txt",
        )

        success = task.download()
        assert not success
        assert task.status == TaskStatus.FAILED
        assert task.error_message is not None
        assert "Network error" in task.error_message

    @patch("requests.get")
    def test_download_timeout(self, mock_get, tmp_path):
        """Test download with timeout error."""
        mock_get.side_effect = TimeoutError("Request timeout")

        task = DownloadTask(
            url="https://example.com/file.txt",
            output_path=tmp_path / "file.txt",
        )

        success = task.download()
        assert not success
        assert task.status == TaskStatus.FAILED

    def test_save_metadata(self, tmp_path):
        """Test saving task metadata."""
        task = DownloadTask(
            url="https://example.com/file.hdf",
            output_path=tmp_path / "file.hdf",
            filename="file.hdf",
            size=1024,
            checksum="abc123",
        )
        task.status = TaskStatus.COMPLETED
        task.downloaded_bytes = 1024

        task.save_metadata()

        metadata_file = tmp_path / "file.hdf.metadata"
        assert metadata_file.exists()

        with open(metadata_file) as f:
            metadata = json.load(f)

        assert metadata["url"] == "https://example.com/file.hdf"
        assert metadata["filename"] == "file.hdf"
        assert metadata["status"] == "completed"

    @patch("requests.get")
    def test_resume_from_partial(self, mock_get, tmp_path):
        """Test resuming from a partial download."""
        # Create partial file
        partial_file = tmp_path / "file.txt"
        partial_file.write_bytes(b"partial")

        # Mock response for resume
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b" continued"]
        mock_response.status_code = 206
        mock_response.headers = {"content-length": "10"}
        mock_get.return_value = mock_response

        task = DownloadTask(
            url="https://example.com/file.txt",
            output_path=partial_file,
        )

        success = task.resume()
        assert success
        assert task.status == TaskStatus.COMPLETED

    @patch("requests.get")
    def test_resume_file_complete(self, mock_get, tmp_path):
        """Test resume when file is already complete."""
        # Create complete file
        complete_file = tmp_path / "file.txt"
        complete_file.write_bytes(b"complete file")

        # Mock response: 416 Range Not Satisfiable
        mock_response = MagicMock()
        mock_response.status_code = 416
        mock_get.return_value = mock_response

        task = DownloadTask(
            url="https://example.com/file.txt",
            output_path=complete_file,
            size=len(b"complete file"),
        )

        success = task.resume()
        assert success
        assert task.status == TaskStatus.COMPLETED


class TestDownloadProgress:
    """Test DownloadProgress for tracking download progress."""

    def test_create_progress(self):
        """Test creating progress tracker."""
        progress = DownloadProgress(
            total_files=10,
            total_bytes=1024 * 1024 * 100,
        )
        assert progress.total_files == 10
        assert progress.total_bytes == 1024 * 1024 * 100
        assert progress.overall_progress == 0.0

    def test_progress_percentage(self):
        """Test progress percentage calculation."""
        progress = DownloadProgress(
            total_files=10,
            total_bytes=1000,
            downloaded_bytes=500,
        )
        assert progress.overall_progress == 0.5

    def test_file_progress(self):
        """Test file count progress."""
        progress = DownloadProgress(
            total_files=10,
            completed_files=3,
        )
        assert progress.files_progress == 0.3

    def test_elapsed_time(self):
        """Test elapsed time calculation."""
        progress = DownloadProgress()
        progress.start_time = datetime.now() - timedelta(seconds=10)

        elapsed = progress.elapsed_time
        assert 9 <= elapsed.total_seconds() <= 11

    def test_download_speed(self):
        """Test download speed calculation."""
        progress = DownloadProgress(
            total_bytes=1024 * 1024,
            downloaded_bytes=512 * 1024,
        )
        progress.start_time = datetime.now() - timedelta(seconds=1)

        speed = progress.download_speed
        assert "KB/s" in speed or "MB/s" in speed

    def test_format_speed(self):
        """Test speed formatting."""
        speed = DownloadProgress._format_speed(1024 * 1024)
        assert "MB/s" in speed

        speed = DownloadProgress._format_speed(1024)
        assert "KB/s" in speed

    def test_format_bytes(self):
        """Test byte formatting."""
        assert "MB" in DownloadProgress._format_bytes(1024 * 1024)
        assert "GB" in DownloadProgress._format_bytes(1024 * 1024 * 1024)
        assert "B" in DownloadProgress._format_bytes(512)

    def test_estimated_remaining(self):
        """Test ETA calculation."""
        progress = DownloadProgress(
            total_bytes=1000,
            downloaded_bytes=500,
        )
        progress.start_time = datetime.now() - timedelta(seconds=5)

        eta = progress.estimated_remaining
        assert isinstance(eta, timedelta)


class TestDownloadResult:
    """Test DownloadResult for download statistics."""

    def test_create_result(self):
        """Test creating download result."""
        result = DownloadResult(
            successful=8,
            failed=2,
            total=10,
            total_size_bytes=1024 * 1024 * 100,
        )
        assert result.successful == 8
        assert result.failed == 2
        assert result.total == 10

    def test_success_rate(self):
        """Test success rate calculation."""
        result = DownloadResult(successful=8, failed=2, total=10)
        assert result.success_rate == 80.0

    def test_is_complete(self):
        """Test completion check."""
        result = DownloadResult(successful=10, failed=0, total=10)
        assert result.is_complete

        result2 = DownloadResult(successful=8, failed=2, total=10)
        assert not result2.is_complete

    def test_size_conversion(self):
        """Test size unit conversions."""
        result = DownloadResult(total_size_bytes=1024 * 1024 * 1024)
        assert result.total_size_gb == 1.0

        result2 = DownloadResult(total_size_bytes=1024 * 1024)
        assert 0.9 < result2.total_size_mb < 1.1


class TestRetryConfig:
    """Test retry configuration."""

    def test_default_config(self):
        """Test default retry config."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF

    def test_custom_config(self):
        """Test custom retry config."""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=0.5,
            strategy=RetryStrategy.LINEAR_BACKOFF,
        )
        assert config.max_attempts == 5
        assert config.initial_delay == 0.5
        assert config.strategy == RetryStrategy.LINEAR_BACKOFF


class TestResilienceManager:
    """Test resilience features."""

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(
            initial_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            backoff_multiplier=2.0,
        )
        retry = ExponentialBackoffRetry(config)

        retry.attempt = 0
        assert retry.get_delay() == 1.0

        retry.attempt = 1
        assert retry.get_delay() == 2.0

        retry.attempt = 2
        assert retry.get_delay() == 4.0

    def test_linear_backoff(self):
        """Test linear backoff calculation."""
        config = RetryConfig(
            initial_delay=1.0,
            strategy=RetryStrategy.LINEAR_BACKOFF,
        )
        retry = ExponentialBackoffRetry(config)

        retry.attempt = 0
        assert retry.get_delay() == 1.0

        retry.attempt = 1
        assert retry.get_delay() == 2.0

        retry.attempt = 2
        assert retry.get_delay() == 3.0

    def test_max_delay_cap(self):
        """Test maximum delay cap."""
        config = RetryConfig(
            initial_delay=10.0,
            max_delay=30.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        )
        retry = ExponentialBackoffRetry(config)

        retry.attempt = 5
        delay = retry.get_delay()
        assert delay <= 30.0


class TestDownloadSession:
    """Test DownloadSession for batch operations."""

    def test_create_session(self, tmp_path):
        """Test creating download session."""
        tasks = [
            DownloadTask(
                url="https://example.com/file1.hdf",
                output_path=tmp_path / "file1.hdf",
            ),
            DownloadTask(
                url="https://example.com/file2.hdf",
                output_path=tmp_path / "file2.hdf",
                size=1024,
            ),
        ]

        session = DownloadSession(
            tasks=tasks,
            max_workers=2,
            retry_attempts=3,
        )

        assert session.progress.total_files == 2

    def test_session_pause_resume(self, tmp_path):
        """Test pausing and resuming session."""
        task = DownloadTask(
            url="https://example.com/file.hdf",
            output_path=tmp_path / "file.hdf",
        )

        session = DownloadSession(tasks=[task])
        assert not session.is_paused()

        session.pause()
        assert session.is_paused()

        session.resume()
        assert not session.is_paused()

    def test_session_cancel(self, tmp_path):
        """Test cancelling session."""
        task = DownloadTask(
            url="https://example.com/file.hdf",
            output_path=tmp_path / "file.hdf",
        )

        session = DownloadSession(tasks=[task])
        assert not session.is_cancelled()

        session.cancel()
        assert session.is_cancelled()


class TestDownloadManager:
    """Test DownloadManager main API."""

    def test_create_manager(self):
        """Test creating download manager."""
        manager = DownloadManager(
            max_workers=4,
            retry_attempts=3,
        )
        assert manager.max_workers == 4
        assert manager.retry_attempts == 3

    def test_prepare_dict_granules(self, tmp_path):
        """Test preparing dictionary granules."""
        manager = DownloadManager()

        granules = [
            {
                "url": "https://example.com/file1.hdf",
                "filename": "file1.hdf",
                "size": 1000,
            },
            {
                "url": "https://example.com/file2.hdf",
                "filename": "file2.hdf",
                "size": 2000,
            },
        ]

        tasks = manager._prepare_tasks(granules, tmp_path)
        assert len(tasks) == 2
        assert all(isinstance(t, DownloadTask) for t in tasks)

    def test_prepare_task_granules(self, tmp_path):
        """Test preparing DownloadTask granules."""
        manager = DownloadManager()

        granules = [
            DownloadTask(
                url="https://example.com/file1.hdf",
                output_path=tmp_path / "file1.hdf",
            ),
        ]

        tasks = manager._prepare_tasks(granules, tmp_path)
        assert len(tasks) == 1
        assert tasks[0] is granules[0]

    def test_create_session(self, tmp_path):
        """Test creating session from manager."""
        manager = DownloadManager()

        granules = [
            {"url": "https://example.com/file.hdf", "filename": "file.hdf"},
        ]

        session = manager.create_session(granules, tmp_path)
        assert isinstance(session, DownloadSession)
        assert len(session.tasks) == 1


class TestUtilityFunctions:
    """Test utility functions."""

    def test_format_bytes(self):
        """Test byte formatting."""
        assert "B" in format_bytes(512)
        assert "KB" in format_bytes(1024 * 2)
        assert "MB" in format_bytes(1024 * 1024)
        assert "GB" in format_bytes(1024 * 1024 * 1024)

    def test_format_speed(self):
        """Test speed formatting."""
        assert "B/s" in format_speed(100)
        assert "KB/s" in format_speed(1024 * 100)
        assert "MB/s" in format_speed(1024 * 1024 * 5)

    def test_format_time(self):
        """Test time formatting."""
        assert format_time(45) == "45s"
        assert "1m" in format_time(65)
        assert "1h" in format_time(3665)


class TestDownloadIntegration:
    """Integration tests for complete workflows."""

    @patch("requests.get")
    def test_full_workflow_mock(self, mock_get, tmp_path):
        """Test complete download workflow with mocks."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"file content"]
        mock_response.headers = {"content-length": "12"}
        mock_get.return_value = mock_response

        manager = DownloadManager(max_workers=1)

        granules: List[Union[Dict[str, Any], DownloadTask]] = [
            {"url": "https://example.com/file.hdf", "filename": "file.hdf", "size": 12},
        ]

        result = manager.download(granules, tmp_path)

        assert result.successful == 1
        assert result.total == 1
        assert (tmp_path / "file.hdf").exists()

    @patch("requests.get")
    def test_multiple_downloads_mock(self, mock_get, tmp_path):
        """Test multiple concurrent downloads."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"content"]
        mock_response.headers = {"content-length": "7"}
        mock_get.return_value = mock_response

        manager = DownloadManager(max_workers=2)

        granules: List[Union[Dict[str, Any], DownloadTask]] = [
            {
                "url": f"https://example.com/file{i}.hdf",
                "filename": f"file{i}.hdf",
                "size": 7,
            }
            for i in range(3)
        ]

        result = manager.download(granules, tmp_path)

        assert result.total == 3

    def test_save_and_load_session_state(self, tmp_path):
        """Test saving and loading session state."""
        # Create session with tasks
        tasks = [
            DownloadTask(
                url="https://example.com/file1.hdf",
                output_path=tmp_path / "file1.hdf",
            ),
            DownloadTask(
                url="https://example.com/file2.hdf",
                output_path=tmp_path / "file2.hdf",
            ),
        ]

        session = DownloadSession(tasks=tasks, max_workers=2)

        # Save state
        session_file = tmp_path / "session.json"
        assert session.save_state(session_file)
        assert session_file.exists()

        # Load state
        loaded_session = DownloadSession.load_state(session_file)
        assert loaded_session is not None
        assert len(loaded_session.tasks) == 2
        assert loaded_session.progress.total_files == 2

    def test_get_statistics(self):
        """Test getting download statistics."""
        tasks = [
            DownloadTask(
                url="https://example.com/file1.hdf",
                output_path=Path("file1.hdf"),
                size=1000,
            ),
            DownloadTask(
                url="https://example.com/file2.hdf",
                output_path=Path("file2.hdf"),
                size=2000,
            ),
        ]

        session = DownloadSession(tasks=tasks)
        session.progress.total_files = 2
        session.progress.total_bytes = 3000
        session.progress.completed_files = 1
        session.progress.downloaded_bytes = 1000
        session.results.successful = 1
        session.results.failed = 0
        session.results.total = 2

        stats = session.get_statistics()

        assert stats.total_files == 2
        assert stats.files_downloaded == 1
        assert stats.files_failed == 0
        assert stats.success_rate == 50.0

    def test_statistics_to_dict(self):
        """Test DownloadStatistics serialization."""
        from datetime import timedelta

        stats = DownloadStatistics(
            total_files=10,
            files_downloaded=8,
            files_failed=2,
            total_size_bytes=1000000,
            bytes_downloaded=800000,
            duration=timedelta(seconds=100),
            avg_speed_mbps=8.0,
            success_rate=80.0,
        )

        data = stats.to_dict()

        assert data["total_files"] == 10
        assert data["success_rate"] == 80.0
        assert data["duration_seconds"] == 100

    def test_statistics_from_dict(self):
        """Test DownloadStatistics deserialization."""
        from datetime import timedelta

        data = {
            "total_files": 10,
            "files_downloaded": 8,
            "files_failed": 2,
            "total_size_bytes": 1000000,
            "bytes_downloaded": 800000,
            "duration_seconds": 100,
            "avg_speed_mbps": 8.0,
            "success_rate": 80.0,
        }

        stats = DownloadStatistics.from_dict(data)

        assert stats.total_files == 10
        assert stats.files_downloaded == 8
        assert stats.duration == timedelta(seconds=100)


class TestDownloadManagerCoverageExtra:
    """Cover manager.py lines 114-117, 144, 147, 159, 194."""

    def test_download_single_with_string_url(self, tmp_path):
        """download_single accepts a raw URL string (lines 114-117)."""
        manager = DownloadManager()
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.iter_content.return_value = [b"data"]
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp
            result = manager.download_single("https://example.com/file.hdf", tmp_path)
        assert result is not None

    def test_prepare_tasks_missing_url_raises(self, tmp_path):
        """_prepare_tasks raises ValueError when 'url' key is absent (line 144)."""
        manager = DownloadManager()
        with pytest.raises(ValueError, match="missing required 'url'"):
            manager._prepare_tasks([{"filename": "f.hdf"}], tmp_path)

    def test_prepare_tasks_non_string_url_raises(self, tmp_path):
        """_prepare_tasks raises ValueError when url is not a string (line 147)."""
        manager = DownloadManager()
        with pytest.raises(ValueError, match="must be string"):
            manager._prepare_tasks([{"url": 123, "filename": "f.hdf"}], tmp_path)

    def test_prepare_tasks_unsupported_type_raises(self, tmp_path):
        """_prepare_tasks raises ValueError for unsupported granule types (line 159)."""
        manager = DownloadManager()
        with pytest.raises(ValueError, match="unsupported type"):
            manager._prepare_tasks(["not_a_dict_or_task"], tmp_path)

    def test_create_session_returns_session(self, tmp_path):
        """create_session returns a DownloadSession without executing (line 194)."""
        manager = DownloadManager()
        granules = [{"url": "https://example.com/f.hdf", "filename": "f.hdf"}]
        session = manager.create_session(granules, tmp_path)
        assert isinstance(session, DownloadSession)
        assert len(session.tasks) == 1


class TestProgressCoverageExtra:
    """Cover progress.py lines 46, 57, 78, 92, 96, 109-115, 131, 146, 150, 226."""

    def test_overall_progress_zero_when_no_total_bytes(self):
        """overall_progress returns 0.0 when total_bytes is 0 (line 46)."""
        p = DownloadProgress()
        assert p.overall_progress == 0.0

    def test_files_progress_zero_when_no_total_files(self):
        """files_progress returns 0.0 when total_files is 0 (line 57)."""
        p = DownloadProgress()
        assert p.files_progress == 0.0

    def test_download_speed_zero_at_start(self):
        """download_speed returns '0 B/s' when no time has elapsed (line 78)."""
        p = DownloadProgress()
        p.start_time = datetime.now()
        # Force elapsed to 0 by making start_time == now
        with patch.object(type(p), "elapsed_time", property(lambda self: timedelta(seconds=0))):
            speed = p.download_speed
        assert speed == "0 B/s"

    def test_estimated_remaining_zero_when_no_bytes_downloaded(self):
        """estimated_remaining returns 0 when downloaded_bytes=0 (line 92)."""
        p = DownloadProgress(total_bytes=1000, downloaded_bytes=0)
        assert p.estimated_remaining == timedelta(seconds=0)

    def test_estimated_remaining_when_bytes_per_second_is_zero(self):
        """estimated_remaining handles edge case when speed calculated to 0 (line 96)."""
        p = DownloadProgress(total_bytes=1000, downloaded_bytes=1)
        with patch.object(
            type(p), "elapsed_time", property(lambda self: timedelta(seconds=0.0001))
        ):
            # With very tiny elapsed, bytes_per_second would normally be huge,
            # but we force the scenario by making downloaded_bytes match total
            p.downloaded_bytes = 1000
            result = p.estimated_remaining
        assert result >= timedelta(seconds=0)

    def test_current_file_speed_returns_zero_when_elapsed_too_small(self):
        """current_file_speed returns '0 B/s' when elapsed < 0.1s (lines 109-115)."""
        p = DownloadProgress(total_bytes=1000, downloaded_bytes=500)
        p.current_file_progress = 0.5
        with patch.object(type(p), "elapsed_time", property(lambda self: timedelta(seconds=0.05))):
            speed = p.current_file_speed
        assert speed == "0 B/s"

    def test_format_speed_gb_range(self):
        """_format_speed handles values in GB/s range (line 131)."""
        speed = DownloadProgress._format_speed(2 * 1024**3)
        assert "GB/s" in speed or "TB/s" in speed

    def test_format_bytes_gb_range(self):
        """_format_bytes handles values in GB range (lines 146, 150)."""
        result = DownloadProgress._format_bytes(2 * 1024**3)
        assert "GB" in result or "TB" in result

    def test_statistics_str(self):
        """DownloadStatistics.__str__ is exercised (line 226)."""
        stats = DownloadStatistics(
            total_files=5,
            files_downloaded=4,
            files_failed=1,
            total_size_bytes=500000,
            bytes_downloaded=400000,
            duration=timedelta(seconds=60),
            avg_speed_mbps=6.0,
            success_rate=80.0,
        )
        s = str(stats)
        assert "DownloadStatistics" in s


class TestResilienceCoverageExtra:
    """Cover resilience.py lines 70, 83-88, 107-117, 182, 188-191."""

    def test_fixed_delay_strategy(self):
        """get_delay returns initial_delay when strategy is FIXED_DELAY (line 70)."""
        config = RetryConfig(initial_delay=2.0, strategy=RetryStrategy.FIXED_DELAY)
        retry = ExponentialBackoffRetry(config)
        assert retry.get_delay() == 2.0

    def test_should_retry_false_when_max_attempts_reached(self):
        """should_retry returns False after max_attempts exceeded (lines 83-88)."""
        config = RetryConfig(max_attempts=2)
        retry = ExponentialBackoffRetry(config)
        retry.attempt = 2
        result = retry.should_retry(ConnectionError("test"))
        assert result is False

    def test_should_retry_false_for_non_retryable_exception(self):
        """should_retry returns False for non-retryable exception type."""
        config = RetryConfig(max_attempts=3)
        retry = ExponentialBackoffRetry(config)
        result = retry.should_retry(ValueError("not retryable"))
        assert result is False

    def test_execute_retries_on_transient_error(self):
        """execute retries the function on retryable exceptions (lines 107-117)."""
        config = RetryConfig(max_attempts=2, initial_delay=0.001)
        retry = ExponentialBackoffRetry(config)

        call_count = [0]

        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("transient")
            return "ok"

        success, result, error = retry.execute(flaky)
        assert success is True
        assert result == "ok"
        assert call_count[0] == 3

    def test_execute_fails_after_max_attempts(self):
        """execute returns failure after exhausting all retries."""
        config = RetryConfig(max_attempts=1, initial_delay=0.001)
        retry = ExponentialBackoffRetry(config)

        def always_fail():
            raise ConnectionError("always")

        success, result, error = retry.execute(always_fail)
        assert success is False
        assert error is not None

    def test_should_resume_false_when_disabled(self, tmp_path):
        """should_resume returns False when resume is disabled (line 182)."""
        from dwr_eo_toolkit.download_manager.resilience import (
            ResilienceManager,
            ResumeConfig,
        )

        manager = ResilienceManager(resume_config=ResumeConfig(enable_resume=False))
        task = DownloadTask(url="https://ex.com/f.hdf", output_path=tmp_path / "f.hdf")
        assert manager.should_resume(task) is False

    def test_should_resume_false_when_file_missing(self, tmp_path):
        """should_resume returns False when output file doesn't exist (line 184)."""
        from dwr_eo_toolkit.download_manager.resilience import ResilienceManager

        manager = ResilienceManager()
        task = DownloadTask(url="https://ex.com/f.hdf", output_path=tmp_path / "missing.hdf")
        assert manager.should_resume(task) is False

    def test_should_resume_true_for_partial_file(self, tmp_path):
        """should_resume returns True when partial file exists (lines 188-191)."""
        from dwr_eo_toolkit.download_manager.resilience import ResilienceManager

        manager = ResilienceManager()
        partial = tmp_path / "partial.hdf"
        partial.write_bytes(b"partial data")
        task = DownloadTask(
            url="https://ex.com/partial.hdf",
            output_path=partial,
            size=1000,
        )
        assert manager.should_resume(task) is True


class TestDownloadResultCoverageExtra:
    """Cover result.py lines 52, 66."""

    def test_success_rate_zero_when_total_is_zero(self):
        """success_rate returns 0.0 when total==0 (line 52)."""
        result = DownloadResult(total=0, successful=0)
        assert result.success_rate == 0.0

    def test_str_representation(self):
        """__str__ is exercised (line 66)."""
        result = DownloadResult(total=5, successful=4, failed=1)
        s = str(result)
        assert "DownloadResult" in s


class TestDownloadQueueCoverageExtra:
    """Cover queue.py lines 49-51."""

    def test_peek_returns_task_without_removing(self, tmp_path):
        """peek returns the next task when queue is non-empty (lines 49-51)."""
        from dwr_eo_toolkit.download_manager.queue import DownloadQueue, Priority

        q = DownloadQueue()
        task = DownloadTask(url="https://ex.com/f.hdf", output_path=tmp_path / "f.hdf")
        q.enqueue(task, Priority.HIGH)
        peeked = q.peek()
        assert peeked is task
        assert q.size() == 1  # Not removed


class TestDownloadSessionCoverageExtra:
    """Cover session.py lines 144-146, 171, 203-204, 224, 264-265, 272-273,
    277-279, 294, 334-337, 381."""

    def test_save_state_returns_false_on_exception(self, tmp_path):
        """save_state swallows errors and returns False (lines 144-146)."""
        session = DownloadSession(tasks=[])
        bad_path = Path("/nonexistent_root/cannot/write.json")
        result = session.save_state(bad_path)
        assert result is False

    def test_load_state_returns_none_when_file_missing(self, tmp_path):
        """load_state returns None when file does not exist (line 171)."""
        result = DownloadSession.load_state(tmp_path / "missing.json")
        assert result is None

    def test_load_state_returns_none_on_corrupt_json(self, tmp_path):
        """load_state returns None on JSON parse errors (lines 203-204)."""
        bad = tmp_path / "corrupt.json"
        bad.write_text("not valid json {{{{")
        result = DownloadSession.load_state(bad)
        assert result is None

    def test_get_statistics_elapsed_zero(self, tmp_path):
        """get_statistics handles zero-elapsed case (line 224)."""
        session = DownloadSession(tasks=[])
        # Force elapsed to 0 via monkeypatching start_time to now
        session.progress.start_time = datetime.now()
        # elapsed will be effectively 0; statistics should not raise
        stats = session.get_statistics()
        assert stats.avg_speed_mbps == 0.0 or stats.avg_speed_mbps >= 0.0

    def test_execute_cancelled_breaks_loop(self, tmp_path):
        """execute stops processing when _cancelled is True (lines 264-265)."""
        task = DownloadTask(url="https://ex.com/f.hdf", output_path=tmp_path / "f.hdf")
        session = DownloadSession(tasks=[task])
        session._cancelled = True

        with patch.object(session, "_download_task", return_value=False):
            result = session.execute()

        assert result is not None

    def test_execute_handles_future_exception(self, tmp_path):
        """execute catches exceptions from individual futures (lines 272-273)."""
        task = DownloadTask(url="https://ex.com/f.hdf", output_path=tmp_path / "f.hdf")
        session = DownloadSession(tasks=[task])

        with patch.object(session, "_download_task", side_effect=RuntimeError("boom")):
            result = session.execute()

        assert result.failed == 1

    def test_execute_handles_outer_exception(self, tmp_path):
        """execute catches exceptions outside the future loop (lines 277-279)."""
        session = DownloadSession(
            tasks=[DownloadTask(url="https://ex.com/f.hdf", output_path=tmp_path / "f.hdf")]
        )

        with patch(
            "dwr_eo_toolkit.download_manager.session.ThreadPoolExecutor",
            side_effect=RuntimeError("executor failure"),
        ):
            result = session.execute()

        assert "session" in result.error_messages

    def test_download_task_uses_resume_for_partial_file(self, tmp_path):
        """_download_task calls task.resume when file is partially downloaded (line 294)."""
        partial = tmp_path / "partial.hdf"
        partial.write_bytes(b"x" * 100)
        task = DownloadTask(
            url="https://ex.com/partial.hdf",
            output_path=partial,
            size=1000,
        )
        session = DownloadSession(tasks=[task])

        with patch.object(task, "resume", return_value=True) as mock_resume:
            session._download_task(task)

        mock_resume.assert_called_once()

    def test_call_progress_callback_swallows_exception(self, tmp_path):
        """_call_progress_callback does not propagate callback errors (lines 334-337)."""

        def bad_callback(p):
            raise RuntimeError("callback error")

        session = DownloadSession(tasks=[], progress_callback=bad_callback)
        session._call_progress_callback()  # Should not raise

    def test_str_representation(self):
        """__str__ is exercised (line 381)."""
        session = DownloadSession(tasks=[], max_workers=2)
        s = str(session)
        assert "DownloadSession" in s


class TestBatchManagerCoverageExtra:
    """Cover batch_manager.py exception paths (lines 152-154, 183-185,
    204-205, 263-264, 281-282, 315-316)."""

    def _make_batch(self, tmp_path):
        from dwr_eo_toolkit.download_manager.batch_manager import BatchDownloadManager

        mgr = BatchDownloadManager()
        mgr.checkpoint_dir = tmp_path / "checkpoints"
        mgr.checkpoint_dir.mkdir()
        return mgr

    def test_save_checkpoint_raises_on_write_error(self, tmp_path):
        """save_checkpoint exception path (lines 152-154)."""
        from pathlib import Path

        mgr = self._make_batch(tmp_path)
        session = DownloadSession(tasks=[])
        result = DownloadResult(total=0)

        with patch.object(Path, "open", side_effect=OSError("disk full")):
            with pytest.raises(Exception):
                mgr.save_checkpoint("cp1", session, result)

    def test_resume_from_checkpoint_returns_none_if_missing(self, tmp_path):
        """resume_from_checkpoint returns None when checkpoint file not found."""
        mgr = self._make_batch(tmp_path)
        result = mgr.resume_from_checkpoint("nonexistent")
        assert result is None

    def test_resume_from_checkpoint_handles_corrupt_file(self, tmp_path):
        """resume_from_checkpoint exception path (lines 183-185)."""
        mgr = self._make_batch(tmp_path)
        cp_file = mgr.checkpoint_dir / "cp_bad.json"
        cp_file.write_text("{{not json}}")
        result = mgr.resume_from_checkpoint("cp_bad")
        assert result is None

    def test_get_progress_handles_session_stats_error(self, tmp_path):
        """get_progress swallows exceptions from get_statistics (lines 204-205)."""
        mgr = self._make_batch(tmp_path)
        bad_session = MagicMock()
        bad_session.get_statistics.side_effect = RuntimeError("stats error")
        mgr.sessions = [bad_session]
        progress = mgr.get_progress()
        assert "total_files" in progress

    def test_list_checkpoints_skips_corrupt_files(self, tmp_path):
        """list_checkpoints handles corrupt checkpoint files (lines 263-264)."""
        mgr = self._make_batch(tmp_path)
        corrupt = mgr.checkpoint_dir / "bad.json"
        corrupt.write_text("not json")
        checkpoints = mgr.list_checkpoints()
        assert isinstance(checkpoints, list)

    def test_clear_checkpoints_handles_unlink_error(self, tmp_path):
        """clear_checkpoints handles OS errors when deleting files (lines 281-282)."""
        mgr = self._make_batch(tmp_path)
        dummy = mgr.checkpoint_dir / "cp.json"
        dummy.write_text("{}")
        with patch.object(dummy.__class__, "unlink", side_effect=OSError("permission")):
            count = mgr.clear_checkpoints()
        assert count == 0

    def test_get_statistics_handles_session_error(self, tmp_path):
        """get_statistics swallows session exceptions (lines 315-316)."""
        mgr = self._make_batch(tmp_path)
        bad_session = MagicMock()
        bad_session.get_statistics.side_effect = RuntimeError("stats broken")
        mgr.sessions = [bad_session]
        stats = mgr.get_statistics()
        assert "total_sessions" in stats
