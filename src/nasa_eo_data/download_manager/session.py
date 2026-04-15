"""
DownloadSession - Manage multiple downloads with parallel execution.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Callable
import threading

from .task import DownloadTask, TaskStatus
from .progress import DownloadProgress
from .result import DownloadResult
from .resilience import RetryConfig, ResumeConfig, ResilienceManager


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
    
    results: Optional[DownloadResult] = None
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
    
    def download_all(self) -> DownloadResult:
        """Download all tasks with parallel execution.
        
        Returns:
            DownloadResult with summary of download operation.
        """
        self.progress.start_time = __import__('datetime').datetime.now()
        self.results = DownloadResult(total=len(self.tasks))
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_task = {
                    executor.submit(self._download_task, task): task
                    for task in self.tasks
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
            self.results.error_messages['session'] = str(e)
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
        
        # Check if should resume
        if self.resilience.should_resume(task):
            success, _, error = self.resilience.execute_with_retry(
                task.resume,
                timeout=self.timeout_seconds
            )
        else:
            success, _, error = self.resilience.execute_with_retry(
                task.download,
                timeout=self.timeout_seconds
            )
        
        # Update progress
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