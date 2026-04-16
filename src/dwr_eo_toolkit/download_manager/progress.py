"""
DownloadProgress - Real-time progress tracking for downloads.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


@dataclass
class DownloadProgress:
    """Track download progress in real-time."""

    total_files: int = 0
    """Total number of files to download."""

    completed_files: int = 0
    """Number of files successfully downloaded."""

    failed_files: int = 0
    """Number of files that failed to download."""

    total_bytes: int = 0
    """Total size in bytes of all files."""

    downloaded_bytes: int = 0
    """Total bytes downloaded so far."""

    current_file: str = ""
    """Name of file currently being downloaded."""

    current_file_progress: float = 0.0
    """Progress of current file as float 0-1."""

    start_time: datetime = field(default_factory=datetime.now)
    """When the download session started."""

    @property
    def overall_progress(self) -> float:
        """Get overall progress as float 0-1.

        Returns:
            Progress from 0.0 to 1.0. Returns 0 if total_bytes is 0.
        """
        if self.total_bytes == 0:
            return 0.0
        return min(1.0, self.downloaded_bytes / self.total_bytes)

    @property
    def files_progress(self) -> float:
        """Get progress by file count as float 0-1.

        Returns:
            Progress from 0.0 to 1.0. Returns 0 if total_files is 0.
        """
        if self.total_files == 0:
            return 0.0
        return min(1.0, self.completed_files / self.total_files)

    @property
    def elapsed_time(self) -> timedelta:
        """Get time elapsed since start.

        Returns:
            timedelta object representing elapsed time.
        """
        return datetime.now() - self.start_time

    @property
    def download_speed(self) -> str:
        """Get average download speed as human-readable string.

        Returns:
            Speed string like "2.5 MB/s" or "150 KB/s".
        """
        elapsed_seconds = self.elapsed_time.total_seconds()
        if elapsed_seconds == 0:
            return "0 B/s"

        bytes_per_second = self.downloaded_bytes / elapsed_seconds
        return self._format_speed(bytes_per_second)

    @property
    def estimated_remaining(self) -> timedelta:
        """Estimate time remaining for download.

        Returns:
            timedelta object. Returns 0 if speed is 0 or all done.
        """
        elapsed_seconds = self.elapsed_time.total_seconds()
        if elapsed_seconds == 0 or self.downloaded_bytes == 0:
            return timedelta(seconds=0)

        bytes_per_second = self.downloaded_bytes / elapsed_seconds
        if bytes_per_second == 0:
            return timedelta(seconds=0)

        remaining_bytes = self.total_bytes - self.downloaded_bytes
        remaining_seconds = remaining_bytes / bytes_per_second
        return timedelta(seconds=max(0, remaining_seconds))

    @property
    def current_file_speed(self) -> str:
        """Get current file download speed.

        Returns:
            Speed string like "1.5 MB/s".
        """
        elapsed_seconds = self.elapsed_time.total_seconds()
        if elapsed_seconds < 0.1:  # Avoid division issues
            return "0 B/s"

        file_downloaded = int(self.downloaded_bytes * self.current_file_progress)
        bytes_per_second = (
            file_downloaded / elapsed_seconds if elapsed_seconds > 0 else 0
        )
        return self._format_speed(bytes_per_second)

    @staticmethod
    def _format_speed(bytes_per_second: float) -> str:
        """Format bytes per second as human-readable string.

        Args:
            bytes_per_second: Speed in bytes/second

        Returns:
            Formatted string like "2.5 MB/s"
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_per_second < 1024.0:
                return f"{bytes_per_second:.1f} {unit}/s"
            bytes_per_second /= 1024.0
        return f"{bytes_per_second:.1f} TB/s"

    @staticmethod
    def _format_bytes(num_bytes: float) -> str:
        """Format bytes as human-readable string.
        Args:
            num_bytes: Number of bytes

        Returns:
            Formatted string like "256.5 MB"
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if num_bytes < 1024.0:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} TB"

    def __str__(self) -> str:
        """User-friendly string representation."""
        return (
            f"DownloadProgress("
            f"files={self.completed_files}/{self.total_files}, "
            f"bytes={self._format_bytes(self.downloaded_bytes)}/{self._format_bytes(self.total_bytes)}, "
            f"speed={self.download_speed}, "
            f"eta={self.estimated_remaining})"
        )


@dataclass
class DownloadStatistics:
    """Download session statistics."""

    total_files: int
    """Total number of files to download."""

    files_downloaded: int
    """Number of files successfully downloaded."""

    files_failed: int
    """Number of files that failed to download."""

    total_size_bytes: int
    """Total size of all files in bytes."""

    bytes_downloaded: int
    """Total bytes downloaded so far."""

    duration: timedelta
    """Time taken for download session."""

    avg_speed_mbps: float
    """Average download speed in MB/s."""

    success_rate: float
    """Success rate as percentage (0-100)."""

    most_common_errors: Optional[List[str]] = None
    """Most common errors encountered."""

    def __post_init__(self):
        """Initialize after creation."""
        if self.most_common_errors is None:
            self.most_common_errors = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary for JSON serialization."""
        return {
            "total_files": self.total_files,
            "files_downloaded": self.files_downloaded,
            "files_failed": self.files_failed,
            "total_size_bytes": self.total_size_bytes,
            "bytes_downloaded": self.bytes_downloaded,
            "duration_seconds": self.duration.total_seconds(),
            "avg_speed_mbps": round(self.avg_speed_mbps, 2),
            "success_rate": round(self.success_rate, 2),
            "most_common_errors": self.most_common_errors,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadStatistics":
        """Create DownloadStatistics from dictionary."""
        return cls(
            total_files=data["total_files"],
            files_downloaded=data["files_downloaded"],
            files_failed=data["files_failed"],
            total_size_bytes=data["total_size_bytes"],
            bytes_downloaded=data["bytes_downloaded"],
            duration=timedelta(seconds=data["duration_seconds"]),
            avg_speed_mbps=data["avg_speed_mbps"],
            success_rate=data["success_rate"],
            most_common_errors=data.get("most_common_errors", []),
        )

    def __str__(self) -> str:
        """User-friendly string representation."""
        return (
            f"DownloadStatistics("
            f"files={self.files_downloaded}/{self.total_files}, "
            f"speed={self.avg_speed_mbps:.1f} MB/s, "
            f"success={self.success_rate:.1f}%)"
        )
