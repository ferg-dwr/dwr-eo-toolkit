"""Batch download management for multiple parallel sessions."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .result import DownloadResult
from .session import DownloadSession

logger = logging.getLogger(__name__)


@dataclass
class CheckpointData:
    """Data structure for checkpoint state."""

    id: str
    timestamp: str
    session_stats: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)


class BatchDownloadManager:
    """Manage multiple parallel download sessions."""

    def __init__(
        self, max_concurrent_sessions: int = 3, queue: Optional[Any] = None
    ) -> None:
        """
        Initialize batch manager.

        Args:
            max_concurrent_sessions: Maximum parallel sessions
            queue: Optional priority queue (for Week 2+)
        """
        self.max_concurrent = max_concurrent_sessions
        self.queue = queue
        self.sessions: List[DownloadSession] = []
        self.results: List[DownloadResult] = []
        self.paused = False
        self.checkpoint_dir = Path(".dwr/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def add_session(self, session: DownloadSession, priority: str = "medium") -> None:
        """
        Add a session to the batch.

        Args:
            session: DownloadSession to add
            priority: Priority level (low, medium, high) - for future queue implementation
        """
        self.sessions.append(session)
        logger.debug(f"Added session with priority: {priority}")

    def execute_all(self) -> List[DownloadResult]:
        """
        Execute all sessions in parallel.

        Returns:
            List of DownloadResult objects, one per session
        """
        if not self.sessions:
            logger.warning("No sessions to execute")
            return []

        logger.info(f"Starting execution of {len(self.sessions)} sessions")
        results: List[DownloadResult] = []

        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {
                executor.submit(self._execute_with_checkpoint, session): session
                for session in self.sessions
            }

            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Session execution failed: {e}")
                    # Create error result instead of dict
                    error_result = DownloadResult(total=0)
                    error_result.error_messages["session"] = str(e)
                    results.append(error_result)

        self.results = results
        logger.info(f"Execution complete: {len(results)} session results")
        return results

    def _execute_with_checkpoint(self, session: DownloadSession) -> DownloadResult:
        """
        Execute session and save checkpoint.

        Args:
            session: DownloadSession to execute

        Returns:
            DownloadResult from session execution
        """
        # Generate unique checkpoint ID for this session
        checkpoint_id = f"session_{uuid4()}"

        logger.info(f"Starting session execution with checkpoint: {checkpoint_id}")

        # Run session
        result = session.execute()

        # Save checkpoint after completion
        self.save_checkpoint(checkpoint_id, session, result)

        return result

    def save_checkpoint(
        self,
        checkpoint_id: str,
        session: DownloadSession,
        result: DownloadResult,
    ) -> Path:
        """
        Save session state to checkpoint file.

        Args:
            checkpoint_id: Unique identifier for checkpoint
            session: DownloadSession that was executed
            result: DownloadResult from execution

        Returns:
            Path to checkpoint file
        """
        try:
            checkpoint_data = CheckpointData(
                id=checkpoint_id,
                timestamp=datetime.now().isoformat(),
                session_stats=session.get_statistics().__dict__,
                result={
                    "successful": result.successful,
                    "failed": result.failed,
                    "total": result.total,
                    "error_messages": result.error_messages,
                },
            )

            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            checkpoint_file.write_text(
                json.dumps(checkpoint_data.__dict__, indent=2, default=str)
            )

            logger.debug(f"Checkpoint saved: {checkpoint_file}")
            return checkpoint_file

        except Exception as e:
            logger.error(f"Failed to save checkpoint {checkpoint_id}: {e}")
            raise

    def resume_from_checkpoint(
        self, checkpoint_id: str
    ) -> Optional[List[DownloadResult]]:
        """
        Resume from checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to resume from

        Returns:
            DownloadResult or None if checkpoint not found
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        if not checkpoint_file.exists():
            logger.warning(f"Checkpoint {checkpoint_id} not found at {checkpoint_file}")
            return None

        try:
            # Load checkpoint data
            checkpoint_data = json.loads(checkpoint_file.read_text())
            logger.info(f"Resuming from checkpoint {checkpoint_id}")
            logger.info(f"Previous stats: {checkpoint_data.get('session_stats', {})}")

            # TODO: Implement full session restoration
            # For now, re-run all sessions
            # In future, could restore individual session state
            return self.execute_all()

        except Exception as e:
            logger.error(f"Failed to resume from checkpoint {checkpoint_id}: {e}")
            return None

    def get_progress(self) -> Dict[str, Any]:
        """
        Get overall progress across all sessions.

        Returns:
            Dictionary with progress metrics
        """
        total_files = 0
        completed = 0
        failed = 0

        for session in self.sessions:
            try:
                stats = session.get_statistics()
                total_files += stats.total_files
                completed += stats.files_downloaded
                failed += stats.files_failed
            except Exception as e:
                logger.warning(f"Could not get stats from session: {e}")

        percentage = (completed / total_files * 100) if total_files > 0 else 0

        progress = {
            "total_files": total_files,
            "completed": completed,
            "failed": failed,
            "pending": total_files - completed - failed,
            "percentage": round(percentage, 2),
            "paused": self.paused,
        }

        logger.debug(f"Progress: {progress}")
        return progress

    def pause_all(self) -> None:
        """Pause all sessions."""
        logger.info("Pausing all sessions")
        self.paused = True
        for session in self.sessions:
            if hasattr(session, "pause"):
                session.pause()

    def resume_all(self) -> None:
        """Resume all paused sessions."""
        logger.info("Resuming all sessions")
        self.paused = False
        for session in self.sessions:
            if hasattr(session, "resume"):
                session.resume()

    def cancel_all(self) -> None:
        """Cancel all sessions."""
        logger.info("Cancelling all sessions")
        for session in self.sessions:
            if hasattr(session, "cancel"):
                session.cancel()

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List all available checkpoints.

        Returns:
            List of checkpoint metadata
        """
        checkpoints = []

        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                data = json.loads(checkpoint_file.read_text())
                checkpoints.append(
                    {
                        "id": data.get("id"),
                        "timestamp": data.get("timestamp"),
                        "file": str(checkpoint_file),
                    }
                )
            except Exception as e:
                logger.warning(f"Could not read checkpoint {checkpoint_file}: {e}")

        return sorted(checkpoints, key=lambda x: x["timestamp"], reverse=True)

    def clear_checkpoints(self) -> int:
        """
        Clear all checkpoint files.

        Returns:
            Number of checkpoints deleted
        """
        count = 0
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                checkpoint_file.unlink()
                count += 1
                logger.debug(f"Deleted checkpoint: {checkpoint_file}")
            except Exception as e:
                logger.warning(f"Could not delete checkpoint {checkpoint_file}: {e}")

        logger.info(f"Cleared {count} checkpoints")
        return count

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get detailed statistics across all sessions.

        Returns:
            Dictionary with comprehensive statistics
        """
        total_stats: Dict[str, Any] = {
            "total_sessions": len(self.sessions),
            "completed_sessions": len(self.results),
            "sessions": [],
        }

        for i, session in enumerate(self.sessions):
            try:
                stats = session.get_statistics()
                total_stats["sessions"].append(
                    {
                        "session_id": i,
                        "total_files": stats.total_files,
                        "files_downloaded": stats.files_downloaded,
                        "files_failed": stats.files_failed,
                        "duration": (
                            str(stats.duration) if hasattr(stats, "duration") else None
                        ),
                        "avg_speed_mbps": (
                            stats.avg_speed_mbps
                            if hasattr(stats, "avg_speed_mbps")
                            else None
                        ),
                    }
                )
            except Exception as e:
                logger.warning(f"Could not get stats from session {i}: {e}")

        return total_stats
