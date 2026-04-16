"""
DownloadSession - Manage multiple downloads with parallel execution.
"""

import json
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from .progress import DownloadProgress, DownloadStatistics
from .resilience import ResilienceManager, ResumeConfig, RetryConfig
from .result import DownloadResult
from .task import DownloadTask, TaskStatus


@dataclass
class DownloadSession:
    """Manage multiple downloads with parallel execution."""

    tasks: List[DownloadTask] = field(default_factory=list)
    """List of DownloadTask objects to execute."""

    max_workers: int = 4
    """Maximum number of concurrent downloads."""

    retry_attempts: int = 3
    """Number of times to retry failed downloads."""

    timeout_seconds: int = 300
    """Timeout for each download in seconds."""

    verify_checksum: bool = True
    """Whether to verify checksums after download."""

    enable_resume: bool = True
    """Whether to resume interrupted downloads."""

    progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    """Callback function for progress updates."""

    progress: DownloadProgress = field(default_factory=DownloadProgress)
    """Current progress tracking."""

    results: DownloadResult = field(default_factory=lambda: DownloadResult(total=0))
    """Results of download session."""

    _paused: bool = field(default=False, init=False)
    """Whether session is paused."""

    _cancelled: bool = field(default=False, init=False)
    """Whether session is cancelled."""

    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    """Lock for thread-safe operations."""

    def __post_init__(self):
        """Initialize session after creation."""
        # Calculate total size
        self.progress.total_files = len(self.tasks)
        self.progress.total_bytes = sum(task.size or 0 for task in self.tasks)

        # Setup resilience
        self.resilience = ResilienceManager(
            retry_config=RetryConfig(max_attempts=self.retry_attempts),
            resume_config=ResumeConfig(enable_resume=self.enable_resume),
        )

    def save_state(self, session_path: Path) -> bool:
        """Save session state to JSON file for recovery.

        Allows resuming interrupted download sessions from where they left off.

        Args:
            session_path: Path where session state will be saved

        Returns:
            True if successful, False otherwise

        Example:
            >>> session = DownloadSession(tasks=[...])
            >>> session.save_state(Path("~/.dwr/sessions/session_123.json"))
        """
        try:
            session_path = Path(session_path)
            session_path.parent.mkdir(parents=True, exist_ok=True)

            state = {
                "metadata": {
                    "saved_at": datetime.now().isoformat(),
                    "total_tasks": len(self.tasks),
                    "completed_tasks": self.progress.completed_files,
                },
                "progress": {
                    "total_files": self.progress.total_files,
                    "completed_files": self.progress.completed_files,
                    "failed_files": self.progress.failed_files,
                    "total_bytes": self.progress.total_bytes,
                    "downloaded_bytes": self.progress.downloaded_bytes,
                    "current_file": self.progress.current_file,
                },
                "results": {
                    "successful": self.results.successful,
                    "failed": self.results.failed,
                    "total": self.results.total,
                    "total_size_bytes": self.results.total_size_bytes,
                },
                "tasks": [
                    {
                        "url": task.url,
                        "filename": task.filename,
                        "status": task.status.value,
                        "downloaded_bytes": task.downloaded_bytes,
                        "error_message": task.error_message,
                    }
                    for task in self.tasks
                ],
            }

            with open(session_path, "w") as f:
                json.dump(state, f, indent=2)

            return True

        except Exception:
            # Log error but don't fail the download
            return False

    @classmethod
    def load_state(cls, session_path: Path) -> Optional["DownloadSession"]:
        """Load session state from JSON file.

        Allows resuming a previous download session from its saved state.

        Args:
            session_path: Path to saved session JSON file

        Returns:
            DownloadSession instance or None if load failed

        Example:
            >>> session = DownloadSession.load_state(
            ...     Path("~/.dwr/sessions/session_123.json")
            ... )
            >>> if session:
            ...     results = session.download_all()
        """
        try:
            session_path = Path(session_path)

            if not session_path.exists():
                return None

            with open(session_path) as f:
                state = json.load(f)

            # Reconstruct tasks from saved state
            tasks = []
            for task_data in state.get("tasks", []):
                task = DownloadTask(
                    url=task_data["url"],
                    output_path=Path(task_data["filename"]).parent
                    / Path(task_data["filename"]).name,
                    filename=task_data["filename"],
                )
                task.status = TaskStatus(task_data["status"])
                task.downloaded_bytes = task_data["downloaded_bytes"]
                task.error_message = task_data.get("error_message")
                tasks.append(task)

            # Create session with recovered tasks
            session = cls(tasks=tasks)

            # Restore progress state
            progress_data = state.get("progress", {})
            session.progress.total_files = progress_data.get("total_files", 0)
            session.progress.completed_files = progress_data.get("completed_files", 0)
            session.progress.failed_files = progress_data.get("failed_files", 0)
            session.progress.total_bytes = progress_data.get("total_bytes", 0)
            session.progress.downloaded_bytes = progress_data.get("downloaded_bytes", 0)

            return session

        except Exception:
            return None

    def get_statistics(self) -> DownloadStatistics:
        """Get download session statistics.

        Returns:
            DownloadStatistics with session metrics

        Example:
            >>> session = DownloadSession(tasks=[...])
            >>> session.download_all()
            >>> stats = session.get_statistics()
            >>> print(f"Speed: {stats.avg_speed_mbps:.1f} MB/s")
        """
        elapsed = self.progress.elapsed_time.total_seconds()

        # Calculate average speed
        if elapsed > 0:
            avg_speed_mbps = self.progress.downloaded_bytes / (1024 * 1024) / elapsed
        else:
            avg_speed_mbps = 0.0

        # Calculate success rate
        total = self.results.total if self.results.total > 0 else 1
        success_rate = (self.results.successful / total) * 100

        # Find most common errors
        error_counts = Counter(self.results.error_messages.values())
        most_common_errors = [error for error, _ in error_counts.most_common(5)]

        return DownloadStatistics(
            total_files=self.progress.total_files,
            files_downloaded=self.results.successful,
            files_failed=self.results.failed,
            total_size_bytes=self.progress.total_bytes,
            bytes_downloaded=self.progress.downloaded_bytes,
            duration=self.progress.elapsed_time,
            avg_speed_mbps=avg_speed_mbps,
            success_rate=success_rate,
            most_common_errors=most_common_errors,
        )

    def download_all(self) -> DownloadResult:
        """Download all tasks with parallel execution.

        Returns:
            DownloadResult with summary of download operation.
        """
        self.progress.start_time = __import__("datetime").datetime.now()
        self.results = DownloadResult(total=len(self.tasks))

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task = {
                    executor.submit(self._download_task, task): task for task in self.tasks
                }

                # Process completed tasks
                for future in as_completed(future_to_task):
                    if self._cancelled:
                        executor.shutdown(wait=False)
                        break

                    task = future_to_task[future]

                    try:
                        success = future.result()
                        self._update_results(task, success)
                    except Exception as e:
                        self._update_results(task, False, str(e))

            return self.results

        except Exception as e:
            self.results.error_messages["session"] = str(e)
            return self.results

    def _download_task(self, task: DownloadTask) -> bool:
        """Download a single task with retry logic.

        Args:
            task: DownloadTask to download

        Returns:
            True if successful, False otherwise
        """
        self.progress.current_file = task.filename
        self._call_progress_callback()

        if self.resilience.should_resume(task):
            success, _, error = self.resilience.execute_with_retry(
                task.resume, timeout=self.timeout_seconds
            )
        else:
            success, _, error = self.resilience.execute_with_retry(
                task.download, timeout=self.timeout_seconds
            )

        with self._lock:
            self.progress.downloaded_bytes += task.downloaded_bytes

        return success

    def _update_results(self, task: DownloadTask, success: bool, error: Optional[str] = None):
        """Update results based on task completion.

        Args:
            task: Completed DownloadTask
            success: Whether task succeeded
            error: Error message if failed
        """
        with self._lock:
            if success and task.status == TaskStatus.COMPLETED:
                self.results.successful += 1
                self.results.total_size_bytes += task.downloaded_bytes
                self.progress.completed_files += 1
            else:
                self.results.failed += 1
                self.results.failed_tasks.append(task)
                self.progress.failed_files += 1

                error_msg = error or task.error_message or "Unknown error"
                self.results.error_messages[task.url] = error_msg
                task.error_message = error_msg

            self._call_progress_callback()

    def _call_progress_callback(self):
        """Call progress callback if provided."""
        if self.progress_callback:
            try:
                self.progress_callback(self.progress)
            except Exception:
                pass  # Don't fail if callback errors

    def pause(self) -> None:
        """Pause the download session.

        Note: Currently paused downloads will complete their current file
        before pausing.
        """
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        """Resume a paused download session."""
        with self._lock:
            self._paused = False

    def cancel(self) -> None:
        """Cancel the download session.

        Note: Currently downloading files will complete before cancellation.
        """
        with self._lock:
            self._cancelled = True

    def is_paused(self) -> bool:
        """Check if session is paused.

        Returns:
            True if paused, False otherwise.
        """
        with self._lock:
            return self._paused

    def is_cancelled(self) -> bool:
        """Check if session is cancelled.

        Returns:
            True if cancelled, False otherwise.
        """
        with self._lock:
            return self._cancelled

    def __str__(self) -> str:
        """User-friendly string representation."""
        return (
            f"DownloadSession("
            f"files={len(self.tasks)}, "
            f"workers={self.max_workers}, "
            f"retry={self.retry_attempts}, "
            f"resume={self.enable_resume})"
        )
