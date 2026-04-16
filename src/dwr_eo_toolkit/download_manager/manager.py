"""
DownloadManager - Main interface for downloading granules.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from .progress import DownloadProgress
from .result import DownloadResult
from .session import DownloadSession
from .task import DownloadTask


class DownloadManager:
    """Main interface for managing downloads.

    Supports:
    - Single and batch downloads
    - Parallel downloads with configurable workers
    - Progress tracking with callbacks
    - Automatic retry with exponential backoff
    - Resume capability for interrupted downloads
    - File verification with checksums
    """

    def __init__(
        self,
        max_workers: int = 4,
        retry_attempts: int = 3,
        timeout_seconds: int = 300,
        verify_checksum: bool = True,
        enable_resume: bool = True,
    ):
        """Initialize DownloadManager.

        Args:
            max_workers: Number of concurrent downloads (default: 4)
            retry_attempts: Number of times to retry failed downloads (default: 3)
            timeout_seconds: Timeout per download in seconds (default: 300)
            verify_checksum: Whether to verify checksums (default: True)
            enable_resume: Whether to resume interrupted downloads (default: True)
        """
        self.max_workers = max_workers
        self.retry_attempts = retry_attempts
        self.timeout_seconds = timeout_seconds
        self.verify_checksum = verify_checksum
        self.enable_resume = enable_resume

    def download(
        self,
        granules: List[Union[Dict[str, Any], DownloadTask]],
        output_dir: Union[str, Path],
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> DownloadResult:
        """Download multiple granules.

        Args:
            granules: List of granule dictionaries or DownloadTask objects
                     Dictionaries should have: 'url', 'filename', 'size', 'checksum'
            output_dir: Directory to save files to
            progress_callback: Optional callback for progress updates

        Returns:
            DownloadResult with summary of download operation

        Example:
            >>> manager = DownloadManager(max_workers=4)
            >>> granules = [
            ...     {'url': 'https://...', 'filename': 'file1.hdf', 'size': 1000},
            ...     {'url': 'https://...', 'filename': 'file2.hdf', 'size': 2000},
            ... ]
            >>> results = manager.download(granules, '/data/ecostress')
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Convert granules to DownloadTask objects
        tasks = self._prepare_tasks(granules, output_dir)

        # Create and execute session
        session = DownloadSession(
            tasks=tasks,
            max_workers=self.max_workers,
            retry_attempts=self.retry_attempts,
            timeout_seconds=self.timeout_seconds,
            verify_checksum=self.verify_checksum,
            enable_resume=self.enable_resume,
            progress_callback=progress_callback,
        )

        return session.download_all()

    def download_single(
        self,
        granule: Union[Dict[str, Any], str],
        output_dir: Union[str, Path],
        filename: Optional[str] = None,
    ) -> DownloadResult:
        """Download a single granule.

        Args:
            granule: Granule dictionary or URL string
            output_dir: Directory to save file to
            filename: Optional filename (extracted from URL if not provided)

        Returns:
            DownloadResult with download status

        Example:
            >>> manager = DownloadManager()
            >>> granule = {'url': 'https://...', 'filename': 'file.hdf', 'size': 1000}
            >>> result = manager.download_single(granule, '/data')
        """
        if isinstance(granule, str):
            granule = {"url": granule, "filename": filename or Path(granule).name}

        return self.download([granule], output_dir)

    def _prepare_tasks(
        self,
        granules: Sequence[Union[Dict[str, Any], DownloadTask]],
        output_dir: Path,
    ) -> List[DownloadTask]:
        """Convert granules to DownloadTask objects.

        Args:
            granules: List of granules (dict or DownloadTask)
            output_dir: Directory for output files

        Returns:
            List of DownloadTask objects

        Raises:
            ValueError: If required fields are missing
        """
        tasks = []

        for i, granule in enumerate(granules):
            if isinstance(granule, DownloadTask):
                tasks.append(granule)
            elif isinstance(granule, dict):
                url = granule.get("url")  # Validate required fields
                if not url:
                    raise ValueError(f"Granule {i} missing required 'url' field")

                if not isinstance(url, str):
                    raise ValueError(
                        f"Granule {i} 'url' must be string, got {type(url)}"
                    )

                task = DownloadTask(
                    url=url,
                    output_path=output_dir / granule.get("filename", Path(url).name),
                    filename=granule.get("filename", Path(url).name),
                    size=granule.get("size"),
                    checksum=granule.get("checksum"),
                    checksum_type=granule.get("checksum_type", "md5"),
                )
                tasks.append(task)
            else:
                raise ValueError(f"Granule {i}: unsupported type {
                    type(granule)}")

        return tasks

    def create_session(
        self,
        granules: Union[List[Dict[str, Any]], List],
        output_dir: Union[str, Path],
    ) -> DownloadSession:
        """Create a DownloadSession without executing downloads.

        Useful for advanced use cases where you want more control over
        the download process.

        Args:
            granules: List of granules
            output_dir: Directory to save files to

        Returns:
            DownloadSession object (not started)
        """
        output_dir = Path(output_dir)
        tasks = self._prepare_tasks(granules, output_dir)

        return DownloadSession(
            tasks=tasks,
            max_workers=self.max_workers,
            retry_attempts=self.retry_attempts,
            timeout_seconds=self.timeout_seconds,
            verify_checksum=self.verify_checksum,
            enable_resume=self.enable_resume,
        )

    def __str__(self) -> str:
        """User-friendly string representation."""
        return (
            f"DownloadManager("
            f"workers={self.max_workers}, "
            f"retry={self.retry_attempts}, "
            f"timeout={self.timeout_seconds}s, "
            f"checksum={self.verify_checksum}, "
            f"resume={self.enable_resume})"
        )
