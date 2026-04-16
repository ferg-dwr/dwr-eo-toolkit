"""
Utility functions for downloads module.
"""

import json
from pathlib import Path
from typing import List


def format_bytes(num_bytes: float) -> str:
    """Format bytes as human-readable string.

    Args:
        num_bytes: Number of bytes

    Returns:
        Formatted string like "256.5 MB"
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def format_speed(bytes_per_second: float) -> str:
    """Format bytes per second as human-readable speed.

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


def format_time(seconds: float) -> str:
    """Format seconds as human-readable time duration.

    Args:
        seconds: Number of seconds

    Returns:
        Formatted string like "2h 30m 45s"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def organize_by_date(output_dir: Path, date_format: str = "%Y/%m/%d") -> None:
    """Organize downloaded files by date.

    Args:
        output_dir: Directory containing downloaded files
        date_format: Date format for organization (default: YYYY/MM/DD)
    """
    # This is a placeholder for file organization logic
    # Can be extended to parse filenames and organize by date
    pass


def load_metadata(metadata_path: Path) -> dict:
    """Load metadata from .metadata file.

    Args:
        metadata_path: Path to .metadata file

    Returns:
        Dictionary of metadata
    """
    if not metadata_path.exists():
        return {}

    try:
        with open(metadata_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_metadata(metadata_path: Path, metadata: dict) -> None:
    """Save metadata to .metadata file.

    Args:
        metadata_path: Path to .metadata file
        metadata: Dictionary of metadata to save
    """
    try:
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
    except Exception:
        pass


def get_partial_files(output_dir: Path) -> List[Path]:
    """Find partial (incomplete) downloads in directory.

    Args:
        output_dir: Directory to search

    Returns:
        List of partial file paths
    """
    partial_files = []

    for metadata_file in output_dir.glob("*.metadata"):
        metadata = load_metadata(metadata_file)
        data_file = metadata_file.with_suffix("")

        if data_file.exists():
            # Check if file is partial
            if metadata.get("status") in ["downloading", "paused"]:
                partial_files.append(data_file)
            elif "downloaded_bytes" in metadata:
                size = metadata.get("size")
                if size and metadata["downloaded_bytes"] < size:
                    partial_files.append(data_file)

    return partial_files


def cleanup_failed(output_dir: Path) -> int:
    """Clean up failed downloads.

    Removes partially downloaded files and their metadata.

    Args:
        output_dir: Directory to clean

    Returns:
        Number of files cleaned up
    """
    count = 0

    for metadata_file in output_dir.glob("*.metadata"):
        metadata = load_metadata(metadata_file)

        if metadata.get("status") == "failed":
            data_file = metadata_file.with_suffix("")

            # Remove both metadata and data file
            if data_file.exists():
                data_file.unlink()
                count += 1

            metadata_file.unlink()

    return count
