"""
DownloadResult - Encapsulates results from download operations.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class DownloadResult:
    """Encapsulates results from a download operation."""

    successful: int = 0
    """Number of successfully downloaded files."""

    failed: int = 0
    """Number of failed downloads."""

    total: int = 0
    """Total number of files requested."""

    total_size_bytes: int = 0
    """Total size of all downloaded files in bytes."""

    failed_tasks: List = field(default_factory=list)
    """List of failed DownloadTask objects."""

    error_messages: Dict[str, str] = field(default_factory=dict)
    """Mapping of URL to error message for failed downloads."""

    @property
    def total_size_gb(self) -> float:
        """Convert total size to gigabytes.

        Returns:
            Total size in GB, rounded to 2 decimal places.
        """
        return round(self.total_size_bytes / (1024**3), 2)

    @property
    def total_size_mb(self) -> float:
        """Convert total size to megabytes.

        Returns:
            Total size in MB, rounded to 2 decimal places.
        """
        return round(self.total_size_bytes / (1024**2), 2)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage.

        Returns:
            Success rate from 0-100. Returns 0 if total is 0.
        """
        if self.total == 0:
            return 0.0
        return round((self.successful / self.total) * 100, 2)

    @property
    def is_complete(self) -> bool:
        """Check if all downloads were successful.

        Returns:
            True if all downloads succeeded, False otherwise.
        """
        return self.failed == 0 and self.total > 0

    def __str__(self) -> str:
        """User-friendly string representation."""
        return f"DownloadResult(successful={
            self.successful}, failed={
            self.failed}, " f"total={
            self.total}, size={
            self.total_size_gb}GB, " f"success_rate={
            self.success_rate}%)"
