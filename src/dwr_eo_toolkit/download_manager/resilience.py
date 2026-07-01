"""
Resilience - Retry and resume strategies for download operations.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class RetryStrategy(Enum):
    """Retry strategies for failed downloads."""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    """Maximum number of retry attempts."""

    initial_delay: float = 1.0
    """Initial delay in seconds before first retry."""

    max_delay: float = 60.0
    """Maximum delay in seconds between retries."""

    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    """Retry strategy to use."""

    backoff_multiplier: float = 2.0
    """Multiplier for exponential backoff (default: double each time)."""

    retryable_exceptions: tuple = (
        ConnectionError,
        TimeoutError,
        IOError,
    )
    """Exceptions that should trigger a retry."""


class ExponentialBackoffRetry:
    """Retry with exponential backoff strategy."""

    def __init__(self, config: RetryConfig):
        """Initialize retry strategy.

        Args:
            config: RetryConfig instance
        """
        self.config = config
        self.attempt = 0
        self.last_exception: Optional[Exception] = None

    def get_delay(self) -> float:
        """Calculate delay for next attempt.

        Returns:
            Delay in seconds
        """
        if self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.initial_delay * (
                self.config.backoff_multiplier**self.attempt
            )
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.config.initial_delay * (self.attempt + 1)
        else:  # FIXED_DELAY
            delay = self.config.initial_delay

        return min(delay, self.config.max_delay)

    def should_retry(self, exception: Exception) -> bool:
        """Determine if exception should trigger retry.

        Args:
            exception: Exception that occurred

        Returns:
            True if should retry, False otherwise
        """
        self.last_exception = exception

        if self.attempt >= self.config.max_attempts:
            return False

        return isinstance(exception, self.config.retryable_exceptions)

    def execute(self, func: Callable, *args, **kwargs) -> tuple:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tuple of (success: bool, result: any, error: Optional[Exception])
        """
        self.attempt = 0

        while self.attempt <= self.config.max_attempts:
            try:
                result = func(*args, **kwargs)
                return (True, result, None)
            except Exception as e:
                if not self.should_retry(e):
                    return (False, None, e)

                delay = self.get_delay()
                self.attempt += 1

                if self.attempt <= self.config.max_attempts:
                    time.sleep(delay)

        return (False, None, self.last_exception)


class ResumeConfig:
    """Configuration for resume behavior."""

    def __init__(
        self,
        enable_resume: bool = True,
        metadata_suffix: str = ".metadata",
        persist_metadata: bool = True,
    ):
        """Initialize resume configuration.

        Args:
            enable_resume: Whether to enable resume capability
            metadata_suffix: Suffix for metadata files
            persist_metadata: Whether to save metadata to disk
        """
        self.enable_resume = enable_resume
        self.metadata_suffix = metadata_suffix
        self.persist_metadata = persist_metadata


class ResilienceManager:
    """Manage retry and resume operations."""

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        resume_config: Optional[ResumeConfig] = None,
    ):
        """Initialize resilience manager.

        Args:
            retry_config: Configuration for retries
            resume_config: Configuration for resume
        """
        self.retry_config = retry_config or RetryConfig()
        self.resume_config = resume_config or ResumeConfig()
        self.retry = ExponentialBackoffRetry(self.retry_config)

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> tuple:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Tuple of (success: bool, result: any, error: Optional[Exception])
        """
        return self.retry.execute(func, *args, **kwargs)

    def should_resume(self, task) -> bool:
        """Check if task should be resumed.

        Args:
            task: DownloadTask instance

        Returns:
            True if task should be resumed, False otherwise
        """
        if not self.resume_config.enable_resume:
            return False

        if not task.output_path.exists():
            return False

        # Check if partial download
        if task.size and task.output_path.stat().st_size < task.size:
            return True

        return False
