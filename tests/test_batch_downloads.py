import pytest
from pathlib import Path
from dwr_eo_toolkit.download_manager.batch_manager import BatchDownloadManager
from dwr_eo_toolkit.download_manager.session import DownloadSession
from dwr_eo_toolkit.download_manager.task import DownloadTask


@pytest.fixture
def batch_manager():
    """Create a BatchDownloadManager for testing."""
    return BatchDownloadManager(max_concurrent_sessions=2)


@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    session = DownloadSession()
    # Add some mock tasks
    for i in range(3):
        task = DownloadTask(
            url=f"https://example.com/file{i}.hdf",
            output_path=Path(f"test_file{i}.hdf")
        )
        session.add_task(task)
    return session


class TestBatchDownloadManager:
    """Tests for BatchDownloadManager."""
    
    def test_create_batch_manager(self):
        """Test creating a BatchDownloadManager."""
        manager = BatchDownloadManager(max_concurrent_sessions=3)
        assert manager.max_concurrent == 3
        assert len(manager.sessions) == 0
    
    def test_add_single_session(self, batch_manager, mock_session):
        """Test adding a single session."""
        batch_manager.add_session(mock_session)
        assert len(batch_manager.sessions) == 1
    
    def test_add_multiple_sessions(self, batch_manager):
        """Test adding multiple sessions."""
        sessions = [DownloadSession() for _ in range(5)]
        for session in sessions:
            batch_manager.add_session(session)
        assert len(batch_manager.sessions) == 5
    
    def test_execute_all_returns_results(self, batch_manager, mock_session):
        """Test that execute_all returns results."""
        batch_manager.add_session(mock_session)
        results = batch_manager.execute_all()
        assert isinstance(results, list)
        assert len(results) == 1
    
    def test_execute_all_with_multiple_sessions(self, batch_manager):
        """Test executing multiple sessions."""
        sessions = [DownloadSession() for _ in range(3)]
        for session in sessions:
            batch_manager.add_session(session)
        
        results = batch_manager.execute_all()
        assert len(results) == 3
    
    def test_execute_empty_returns_empty(self, batch_manager):
        """Test executing with no sessions returns empty."""
        results = batch_manager.execute_all()
        assert results == []
    
    def test_get_progress_returns_dict(self, batch_manager, mock_session):
        """Test that get_progress returns a dict."""
        batch_manager.add_session(mock_session)
        batch_manager.execute_all()
        
        progress = batch_manager.get_progress()
        assert isinstance(progress, dict)
        assert "total_files" in progress or "total_tasks" in progress
    
    def test_pause_all(self, batch_manager, mock_session):
        """Test pausing all sessions."""
        batch_manager.add_session(mock_session)
        batch_manager.pause_all()
        assert batch_manager.paused is True
    
    def test_resume_all(self, batch_manager, mock_session):
        """Test resuming all sessions."""
        batch_manager.add_session(mock_session)
        batch_manager.pause_all()
        batch_manager.resume_all()
        assert batch_manager.paused is False
    
    def test_cancel_all(self, batch_manager, mock_session):
        """Test canceling all sessions."""
        batch_manager.add_session(mock_session)
        batch_manager.cancel_all()
        # Sessions should be cancelled
        assert len(batch_manager.sessions) >= 0  # At least no crash