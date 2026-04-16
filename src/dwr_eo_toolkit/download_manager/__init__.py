"""
Downloads Module - Download manager for NASA Earth observation data.

Provides robust download capabilities with:
- Single and batch downloads
- Parallel execution with configurable workers
- Progress tracking and callbacks
- Automatic retry with exponential backoff
- Resume capability for interrupted downloads
- File verification with checksums

Example:
    >>> from dwr_eo_toolkit.downloads import DownloadManager
    >>>
    >>> manager = DownloadManager(max_workers=4)
    >>> granules = [
    ...     {'url': 'https://...', 'filename': 'file1.hdf', 'size': 1000},
    ...     {'url': 'https://...', 'filename': 'file2.hdf', 'size': 2000},
    ... ]
    >>>
    >>> def progress_callback(progress):
    ...     print(f"{progress.overall_progress:.1%} - {progress.download_speed}")
    >>>
    >>> results = manager.download(
    ...     granules,
    ...     output_dir='/data/ecostress',
    ...     progress_callback=progress_callback
    ... )
    >>> print(f"Downloaded: {results.successful}/{results.total}")
"""

from .manager import DownloadManager
from .progress import DownloadProgress, DownloadStatistics
from .resilience import (
    ExponentialBackoffRetry,
    ResilienceManager,
    ResumeConfig,
    RetryConfig,
    RetryStrategy,
)
from .result import DownloadResult
from .session import DownloadSession
from .task import DownloadTask, TaskStatus
from .utils import (
    cleanup_failed,
    format_bytes,
    format_speed,
    format_time,
    get_partial_files,
)

__all__ = [
    # Main API
    "DownloadManager",
    # Session management
    "DownloadSession",
    # Tasks
    "DownloadTask",
    "TaskStatus",
    # Progress
    "DownloadProgress",
    # Statistics
    "DownloadStatistics",
    # Results
    "DownloadResult",
    # Resilience
    "RetryConfig",
    "RetryStrategy",
    "ResumeConfig",
    "ResilienceManager",
    "ExponentialBackoffRetry",
    # Utilities
    "format_bytes",
    "format_speed",
    "format_time",
    "get_partial_files",
    "cleanup_failed",
]

__version__ = "0.3.0"
__doc__ = """DWR Earth Observations Download Modules"""
