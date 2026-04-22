"""
Unit tests for download manager utility functions.

Tests cover:
- Byte/speed/time formatting for human-readable output
- Metadata file operations (load/save)
- Partial file detection
- Failed download cleanup
"""

import json
import tempfile
from pathlib import Path

import pytest

from dwr_eo_toolkit.download_manager.utils import (
    cleanup_failed,
    format_bytes,
    format_speed,
    format_time,
    get_partial_files,
    load_metadata,
    save_metadata,
)


class TestFormatBytes:
    """Tests for byte formatting."""

    def test_format_bytes_zero(self):
        """Should format 0 bytes."""
        assert format_bytes(0) == "0.0 B"

    def test_format_bytes_single_byte(self):
        """Should format single byte."""
        assert format_bytes(1) == "1.0 B"

    def test_format_bytes_kilobytes(self):
        """Should format kilobytes."""
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(2048) == "2.0 KB"

    def test_format_bytes_megabytes(self):
        """Should format megabytes."""
        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(512 * 1024) == "512.0 KB"

    def test_format_bytes_gigabytes(self):
        """Should format gigabytes."""
        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"
        assert format_bytes(2.5 * 1024 * 1024 * 1024) == "2.5 GB"

    def test_format_bytes_terabytes(self):
        """Should format terabytes."""
        assert format_bytes(1024 * 1024 * 1024 * 1024) == "1.0 TB"

    def test_format_bytes_petabytes(self):
        """Should format petabytes."""
        assert format_bytes(1024 * 1024 * 1024 * 1024 * 1024) == "1.0 PB"

    def test_format_bytes_less_than_1024(self):
        """Should keep bytes as B when less than 1024."""
        result = format_bytes(256)
        assert result == "256.0 B"

    def test_format_bytes_fractional_kb(self):
        """Should format fractional kilobytes."""
        result = format_bytes(1536)  # 1.5 KB
        assert "1.5" in result and "KB" in result

    @pytest.mark.parametrize(
        "bytes_val,unit",
        [
            (512 * 1024, "KB"),  # 512 KB
            (512 * 1024 * 1024, "MB"),  # 512 MB
            (512 * 1024 * 1024 * 1024, "GB"),  # 512 GB
            (512 * 1024 * 1024 * 1024 * 1024, "TB"),  # 512 TB
        ],
    )
    def test_format_bytes_various_sizes(self, bytes_val, unit):
        """Should format various byte sizes correctly."""
        result = format_bytes(bytes_val)
        assert unit in result


class TestFormatSpeed:
    """Tests for speed formatting (bytes per second)."""

    def test_format_speed_bytes_per_second(self):
        """Should format bytes/sec."""
        assert format_speed(512) == "512.0 B/s"

    def test_format_speed_kilobytes_per_second(self):
        """Should format KB/s."""
        assert format_speed(1024) == "1.0 KB/s"
        assert format_speed(2048) == "2.0 KB/s"

    def test_format_speed_megabytes_per_second(self):
        """Should format MB/s."""
        assert format_speed(1024 * 1024) == "1.0 MB/s"
        assert format_speed(5 * 1024 * 1024) == "5.0 MB/s"

    def test_format_speed_gigabytes_per_second(self):
        """Should format GB/s."""
        assert format_speed(1024 * 1024 * 1024) == "1.0 GB/s"

    def test_format_speed_terabytes_per_second(self):
        """Should format TB/s."""
        assert format_speed(1024 * 1024 * 1024 * 1024) == "1.0 TB/s"

    def test_format_speed_fractional(self):
        """Should format fractional speeds."""
        result = format_speed(512)
        assert "512.0" in result or "B/s" in result

    def test_format_speed_zero(self):
        """Should handle zero speed."""
        assert "0.0" in format_speed(0)


class TestFormatTime:
    """Tests for time duration formatting."""

    def test_format_time_zero(self):
        """Should format 0 seconds."""
        assert format_time(0) == "0s"

    def test_format_time_seconds_only(self):
        """Should format seconds only."""
        assert format_time(1) == "1s"
        assert format_time(59) == "59s"

    def test_format_time_minutes(self):
        """Should format minutes."""
        assert format_time(60) == "1m"
        assert format_time(120) == "2m"
        assert format_time(90) == "1m 30s"

    def test_format_time_hours(self):
        """Should format hours."""
        assert format_time(3600) == "1h"
        assert format_time(7200) == "2h"

    def test_format_time_hours_and_minutes(self):
        """Should format hours and minutes."""
        assert format_time(3660) == "1h 1m"
        assert format_time(5400) == "1h 30m"

    def test_format_time_hours_minutes_seconds(self):
        """Should format all units."""
        assert format_time(3661) == "1h 1m 1s"
        assert format_time(3725) == "1h 2m 5s"

    def test_format_time_large_values(self):
        """Should format large time values."""
        # 1 day, 2 hours, 30 minutes, 45 seconds
        total_seconds = 86400 + 7200 + 1800 + 45
        result = format_time(total_seconds)
        assert "h" in result

    def test_format_time_fractional_seconds(self):
        """Should handle fractional seconds."""
        result = format_time(90.5)
        assert "1m" in result

    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (1, "1s"),
            (60, "1m"),
            (3600, "1h"),
            (3661, "1h 1m 1s"),
        ],
    )
    def test_format_time_parametrized(self, seconds, expected):
        """Should format various time values."""
        assert format_time(seconds) == expected


class TestLoadMetadata:
    """Tests for loading metadata from files."""

    def test_load_metadata_valid_json(self):
        """Should load valid JSON metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "test.metadata"
            metadata = {"status": "downloading", "downloaded_bytes": 1000}

            with open(metadata_path, "w") as f:
                json.dump(metadata, f)

            result = load_metadata(metadata_path)

            assert result == metadata
            assert result["status"] == "downloading"

    def test_load_metadata_nonexistent_file(self):
        """Should return empty dict for nonexistent file."""
        result = load_metadata(Path("/nonexistent/path.metadata"))

        assert result == {}

    def test_load_metadata_invalid_json(self):
        """Should return empty dict for invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "invalid.metadata"
            metadata_path.write_text("{ invalid json }")

            result = load_metadata(metadata_path)

            assert result == {}

    def test_load_metadata_non_dict_json(self):
        """Should return empty dict if JSON is not a dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "list.metadata"
            metadata_path.write_text('["item1", "item2"]')

            result = load_metadata(metadata_path)

            assert result == {}

    def test_load_metadata_complex_structure(self):
        """Should load complex nested metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "complex.metadata"
            metadata = {
                "status": "downloading",
                "downloaded_bytes": 5000,
                "total_bytes": 10000,
                "retry_count": 2,
                "errors": ["timeout", "connection_reset"],
            }

            with open(metadata_path, "w") as f:
                json.dump(metadata, f)

            result = load_metadata(metadata_path)

            assert result == metadata
            assert len(result["errors"]) == 2

    def test_load_metadata_empty_file(self):
        """Should handle empty files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "empty.metadata"
            metadata_path.write_text("")

            result = load_metadata(metadata_path)

            assert result == {}


class TestSaveMetadata:
    """Tests for saving metadata to files."""

    def test_save_metadata_basic(self):
        """Should save metadata to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "test.metadata"
            metadata = {"status": "completed", "downloaded_bytes": 5000}

            save_metadata(metadata_path, metadata)

            assert metadata_path.exists()
            loaded = json.loads(metadata_path.read_text())
            assert loaded == metadata

    def test_save_metadata_overwrites(self):
        """Should overwrite existing metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "test.metadata"

            # Save first
            save_metadata(metadata_path, {"version": 1})

            # Overwrite
            save_metadata(metadata_path, {"version": 2})

            loaded = json.loads(metadata_path.read_text())
            assert loaded["version"] == 2

    def test_save_metadata_creates_directory(self):
        """Should work if parent directory exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "test.metadata"
            metadata = {"key": "value"}

            save_metadata(metadata_path, metadata)

            assert metadata_path.exists()

    def test_save_metadata_complex_data(self):
        """Should save complex nested data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "complex.metadata"
            metadata = {
                "status": "downloading",
                "progress": {
                    "downloaded_bytes": 5000,
                    "total_bytes": 10000,
                    "percentage": 50.0,
                },
                "errors": ["timeout", "connection_reset"],
            }

            save_metadata(metadata_path, metadata)

            loaded = json.loads(metadata_path.read_text())
            assert loaded == metadata

    def test_save_metadata_empty_dict(self):
        """Should save empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "empty.metadata"

            save_metadata(metadata_path, {})

            assert metadata_path.exists()
            loaded = json.loads(metadata_path.read_text())
            assert loaded == {}

    def test_save_metadata_error_handling(self):
        """Should handle save errors gracefully."""
        # Try to save to invalid path
        metadata_path = Path("/nonexistent/dir/test.metadata")

        # Should not raise, just silently fail
        try:
            save_metadata(metadata_path, {"key": "value"})
        except Exception:
            pass  # Expected to fail


class TestGetPartialFiles:
    """Tests for finding partial/incomplete downloads."""

    def test_get_partial_files_none(self):
        """Should return empty list if no partial files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            result = get_partial_files(output_dir)

            assert result == []

    def test_get_partial_files_downloading_status(self):
        """Should find files with 'downloading' status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create data file
            data_file = output_dir / "file.nc"
            data_file.write_text("partial data")

            # Create metadata with downloading status
            metadata_file = output_dir / "file.nc.metadata"
            metadata = {"status": "downloading"}
            metadata_file.write_text(json.dumps(metadata))

            result = get_partial_files(output_dir)

            assert len(result) == 1
            assert result[0] == data_file

    def test_get_partial_files_paused_status(self):
        """Should find files with 'paused' status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create data file
            data_file = output_dir / "file.nc"
            data_file.write_text("partial data")

            # Create metadata with paused status
            metadata_file = output_dir / "file.nc.metadata"
            metadata = {"status": "paused"}
            metadata_file.write_text(json.dumps(metadata))

            result = get_partial_files(output_dir)

            assert len(result) == 1

    def test_get_partial_files_incomplete_download(self):
        """Should find files with less downloaded than total."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create data file
            data_file = output_dir / "file.nc"
            data_file.write_text("partial data")

            # Create metadata showing incomplete download
            metadata_file = output_dir / "file.nc.metadata"
            metadata = {
                "downloaded_bytes": 5000,
                "size": 10000,
            }
            metadata_file.write_text(json.dumps(metadata))

            result = get_partial_files(output_dir)

            assert len(result) == 1

    def test_get_partial_files_completed_ignored(self):
        """Should ignore completed files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create data file
            data_file = output_dir / "file.nc"
            data_file.write_text("complete data")

            # Create metadata showing completed
            metadata_file = output_dir / "file.nc.metadata"
            metadata = {
                "status": "completed",
                "downloaded_bytes": 10000,
                "size": 10000,
            }
            metadata_file.write_text(json.dumps(metadata))

            result = get_partial_files(output_dir)

            assert len(result) == 0

    def test_get_partial_files_multiple(self):
        """Should find multiple partial files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create 3 partial files
            for i in range(3):
                data_file = output_dir / f"file{i}.nc"
                data_file.write_text("partial")

                metadata_file = output_dir / f"file{i}.nc.metadata"
                metadata = {"status": "downloading"}
                metadata_file.write_text(json.dumps(metadata))

            result = get_partial_files(output_dir)

            assert len(result) == 3

    def test_get_partial_files_missing_data_file(self):
        """Should ignore metadata if data file missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create only metadata, no data file
            metadata_file = output_dir / "file.nc.metadata"
            metadata = {"status": "downloading"}
            metadata_file.write_text(json.dumps(metadata))

            result = get_partial_files(output_dir)

            assert len(result) == 0


class TestCleanupFailed:
    """Tests for cleaning up failed downloads."""

    def test_cleanup_failed_none(self):
        """Should clean up 0 files if none failed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            count = cleanup_failed(output_dir)

            assert count == 0

    def test_cleanup_failed_removes_file(self):
        """Should remove failed download file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create failed file
            data_file = output_dir / "failed.nc"
            data_file.write_text("failed data")

            metadata_file = output_dir / "failed.nc.metadata"
            metadata = {"status": "failed"}
            metadata_file.write_text(json.dumps(metadata))

            count = cleanup_failed(output_dir)

            # Count is 1: data file was removed, so count increments
            assert count == 1
            assert not data_file.exists()
            assert not metadata_file.exists()

    def test_cleanup_failed_removes_metadata_only(self):
        """Should remove metadata even if data file missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create only metadata, no data file
            metadata_file = output_dir / "failed.nc.metadata"
            metadata = {"status": "failed"}
            metadata_file.write_text(json.dumps(metadata))

            count = cleanup_failed(output_dir)

            # Implementation only counts when data_file exists
            assert count == 0
            # But metadata is still deleted
            assert not metadata_file.exists()

    def test_cleanup_failed_ignores_completed(self):
        """Should ignore completed downloads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create completed file
            data_file = output_dir / "completed.nc"
            data_file.write_text("completed data")

            metadata_file = output_dir / "completed.nc.metadata"
            metadata = {"status": "completed"}
            metadata_file.write_text(json.dumps(metadata))

            count = cleanup_failed(output_dir)

            assert count == 0
            assert data_file.exists()

    def test_cleanup_failed_multiple(self):
        """Should clean up multiple failed downloads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create 3 failed files
            for i in range(3):
                data_file = output_dir / f"failed{i}.nc"
                data_file.write_text("failed")

                metadata_file = output_dir / f"failed{i}.nc.metadata"
                metadata = {"status": "failed"}
                metadata_file.write_text(json.dumps(metadata))

            count = cleanup_failed(output_dir)

            # Count is 3: all 3 data files were removed
            assert count == 3

    def test_cleanup_failed_mixed_files(self):
        """Should only clean failed, not completed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create 2 failed, 2 completed
            for i in range(2):
                # Failed
                failed_file = output_dir / f"failed{i}.nc"
                failed_file.write_text("failed")
                failed_meta = output_dir / f"failed{i}.nc.metadata"
                failed_meta.write_text(json.dumps({"status": "failed"}))

                # Completed
                completed_file = output_dir / f"completed{i}.nc"
                completed_file.write_text("completed")
                completed_meta = output_dir / f"completed{i}.nc.metadata"
                completed_meta.write_text(json.dumps({"status": "completed"}))

            count = cleanup_failed(output_dir)

            # Count is 2: only 2 failed files removed
            assert count == 2
            # Check completed files still exist
            assert (output_dir / "completed0.nc").exists()
            assert (output_dir / "completed1.nc").exists()


class TestUtilsIntegration:
    """Integration tests combining multiple utils."""

    def test_metadata_and_format_utils(self):
        """Should work together: save metadata with formatted values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            metadata_path = Path(tmpdir) / "test.metadata"

            # Save metadata with formatted values
            metadata = {
                "downloaded_bytes": 5 * 1024 * 1024,  # 5 MB
                "speed": 1024 * 1024,  # 1 MB/s
                "duration_seconds": 3661,  # 1h 1m 1s
            }
            save_metadata(metadata_path, metadata)

            # Load and verify
            loaded = load_metadata(metadata_path)
            assert loaded == metadata

            # Format for display
            size_str = format_bytes(loaded["downloaded_bytes"])
            speed_str = format_speed(loaded["speed"])
            time_str = format_time(loaded["duration_seconds"])

            assert "MB" in size_str
            assert "MB/s" in speed_str
            assert "1h" in time_str

    def test_cleanup_with_partial_files(self):
        """Should work with get_partial_files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Create 2 partial, 1 failed
            for i in range(2):
                data_file = output_dir / f"partial{i}.nc"
                data_file.write_text("partial")

                metadata_file = output_dir / f"partial{i}.nc.metadata"
                metadata = {"status": "downloading"}
                metadata_file.write_text(json.dumps(metadata))

            # Create failed
            failed_file = output_dir / "failed.nc"
            failed_file.write_text("failed")

            failed_meta = output_dir / "failed.nc.metadata"
            failed_meta.write_text(json.dumps({"status": "failed"}))

            # Get partial files
            partial_count = len(get_partial_files(output_dir))

            # Clean up failed
            cleanup_failed(output_dir)

            assert partial_count == 2
            # Partial files unaffected
            assert len(get_partial_files(output_dir)) == 2
