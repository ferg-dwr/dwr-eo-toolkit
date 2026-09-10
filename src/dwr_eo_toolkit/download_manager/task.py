"""
DownloadTask - Represents a single file download operation.
"""

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import requests


class TaskStatus(Enum):
    """Status of a download task."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class DownloadTask:
    """Represents a single file download task."""

    url: str
    """URL to download from."""
    output_path: Path
    """Path where file will be saved."""
    filename: str = ""
    """Display name of file."""
    size: int | None = None
    """Expected file size in bytes."""
    checksum: str | None = None
    """Expected checksum of file."""
    checksum_type: str = "md5"
    """Type of checksum (md5, sha256, etc)."""
    status: TaskStatus = TaskStatus.PENDING
    """Current status of task."""
    downloaded_bytes: int = 0
    """Bytes downloaded so far."""
    error_message: str | None = None
    """Error message if download failed."""

    def __post_init__(self):
        """Initialize task after creation."""
        if isinstance(self.output_path, str):
            self.output_path = Path(self.output_path)
        if not self.filename:
            self.filename = self.output_path.name

    def download(self, timeout: int = 300, chunk_size: int = 8192) -> bool:
        """Download file from URL.

        Args:
            timeout: Request timeout in seconds
            chunk_size: Size of chunks to download

        Returns:
            True if successful, False otherwise
        """
        try:
            self.status = TaskStatus.DOWNLOADING
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            # Stream download
            response = requests.get(self.url, timeout=timeout, stream=True, allow_redirects=True)
            response.raise_for_status()

            # Download file in chunks
            with open(self.output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        self.downloaded_bytes += len(chunk)

            # Verify if checksum provided
            if self.checksum:
                if not self._verify_checksum():
                    self.status = TaskStatus.FAILED
                    self.error_message = "Checksum mismatch"
                    return False

            self.status = TaskStatus.COMPLETED
            return True

        except requests.exceptions.RequestException as e:
            self.status = TaskStatus.FAILED
            self.error_message = f"Download failed: {str(e)}"
            return False
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error_message = f"Unexpected error: {str(e)}"
            return False

    def resume(self, timeout: int = 300, chunk_size: int = 8192) -> bool:
        """Resume interrupted download using HTTP Range requests.

        Args:
            timeout: Request timeout in seconds
            chunk_size: Size of chunks to download

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.output_path.exists():
                # File doesn't exist, start fresh
                return self.download(timeout, chunk_size)

            # Get current file size
            current_size = self.output_path.stat().st_size

            # Request remaining bytes
            headers = {"Range": f"bytes={current_size}-"}
            response = requests.get(
                self.url,
                headers=headers,
                timeout=timeout,
                stream=True,
                allow_redirects=True,
            )

            # Check if server supports range requests
            if response.status_code == 416:  # Range not satisfiable
                # File is already complete
                self.status = TaskStatus.COMPLETED
                self.downloaded_bytes = current_size
                return True

            if response.status_code not in [200, 206]:
                response.raise_for_status()

            # Append to existing file
            self.status = TaskStatus.DOWNLOADING
            self.downloaded_bytes = current_size

            with open(self.output_path, "ab") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        self.downloaded_bytes += len(chunk)

            # Verify checksum
            if self.checksum:
                if not self._verify_checksum():
                    self.status = TaskStatus.FAILED
                    self.error_message = "Checksum mismatch after resume"
                    return False

            self.status = TaskStatus.COMPLETED
            return True

        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error_message = f"Resume failed: {str(e)}"
            return False

    def _calculate_checksum(self) -> str:
        """Calculate checksum of downloaded file.

        Returns:
            Hexadecimal checksum string
        """
        hasher = hashlib.new(self.checksum_type)

        with open(self.output_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)

        return hasher.hexdigest()

    def _verify_checksum(self) -> bool:
        """Verify downloaded file checksum.

        Returns:
            True if checksum matches or not provided, False if mismatch
        """
        if not self.checksum:
            return True

        calculated = self._calculate_checksum()
        return calculated.lower() == self.checksum.lower()

    def save_metadata(self) -> None:
        """Save task metadata to .metadata file next to downloaded file."""
        metadata_path = self.output_path.with_suffix(self.output_path.suffix + ".metadata")

        metadata = {
            "url": self.url,
            "filename": self.filename,
            "size": self.size,
            "checksum": self.checksum,
            "checksum_type": self.checksum_type,
            "status": self.status.value,
            "downloaded_bytes": self.downloaded_bytes,
        }

        import json

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def __str__(self) -> str:
        """User-friendly string representation."""
        return f"""DownloadTask({self.filename}, status={self.status.value}, progress={
            self.downloaded_bytes
        }/{self.size or "?"})"""
