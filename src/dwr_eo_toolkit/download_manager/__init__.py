"""
Downloads Module - Download manager for NASA Earth observation data.
"""

# Core session management
# Advanced features
from .batch_manager import BatchDownloadManager

# Legacy API (for backward compatibility)
from .manager import DownloadManager

# Progress and results
from .progress import DownloadProgress, DownloadStatistics

# Resilience and retry logic
from .resilience import (
    ExponentialBackoffRetry,
    ResilienceManager,
    ResumeConfig,
    RetryConfig,
    RetryStrategy,
)
from .result import DownloadResult
from .scheduler import DownloadScheduler
from .session import DownloadSession
from .task import DownloadTask, TaskStatus

# Utilities
from .utils import (
    cleanup_failed,
    format_bytes,
    format_speed,
    format_time,
    get_partial_files,
)

__all__ = [
    # Session and tasks
    "DownloadSession",
    "DownloadTask",
    "TaskStatus",
    # Progress and results
    "DownloadProgress",
    "DownloadStatistics",
    "DownloadResult",
    # Resilience
    "RetryConfig",
    "RetryStrategy",
    "ResumeConfig",
    "ResilienceManager",
    "ExponentialBackoffRetry",
    # Advanced features
    "BatchDownloadManager",
    "DownloadScheduler",
    # Utilities
    "format_bytes",
    "format_speed",
    "format_time",
    "get_partial_files",
    "cleanup_failed",
    # Legacy API
    "DownloadManager",
]

__version__ = "0.3.0"
