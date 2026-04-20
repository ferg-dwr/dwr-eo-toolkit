from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from dataclasses import dataclass, field
# from pathlib import Path

from .session import DownloadSession
from .progress import DownloadStatistics


class BatchDownloadManager:
    """Manage multiple parallel download sessions."""
    
    def __init__(self, max_concurrent_sessions: int = 3, queue=None):
        """
        Initialize batch manager.
        
        Args:
            max_concurrent_sessions: Maximum parallel sessions
            queue: Optional priority queue (for Week 2+)
        """
        self.max_concurrent = max_concurrent_sessions
        self.queue = queue
        self.sessions: List[DownloadSession] = []
        self.results: List[Dict[str, Any]] = []
        self.paused = False

    def add_session(self, session: DownloadSession, priority: str = "medium") -> None:
        """Add a session to the batch."""
        self.sessions.append(session)

    def execute_all(self) -> List[Dict[str, Any]]:
        """Execute all sessions in parallel."""
        if not self.sessions:
            return []
        
        results = []
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {
                executor.submit(session.execute): session 
                for session in self.sessions
            }
            
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
        
        return results

    def get_progress(self) -> Dict[str, Any]:
        """Get overall progress."""
        total_files = 0
        completed = 0
        
        for session in self.sessions:
            stats = session.get_statistics()
            total_files += stats.total_files
            completed += stats.files_downloaded
        
        return {
            "total_files": total_files,
            "completed": completed,
            "percentage": (completed / total_files * 100) if total_files > 0 else 0,
        }

    def pause_all(self) -> None:
        """Pause all sessions."""
        self.paused = True
        for session in self.sessions:
            if hasattr(session, 'pause'):
                session.pause()

    def resume_all(self) -> None:
        """Resume all sessions."""
        self.paused = False
        for session in self.sessions:
            if hasattr(session, 'resume'):
                session.resume()

    def cancel_all(self) -> None:
        """Cancel all sessions."""
        for session in self.sessions:
            if hasattr(session, 'cancel'):
                session.cancel()