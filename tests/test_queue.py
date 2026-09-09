from pathlib import Path

from dwr_eo_toolkit.download_manager.queue import DownloadQueue, Priority
from dwr_eo_toolkit.download_manager.task import DownloadTask


class TestDownloadQueue:
    def test_enqueue_dequeue(self):
        """Test basic enqueue/dequeue."""
        queue = DownloadQueue()
        task = DownloadTask(
            url="https://example.com/file.hdf", output_path=Path("file.hdf")
        )

        queue.enqueue(task, Priority.HIGH)
        retrieved = queue.dequeue()

        assert retrieved.url == task.url

    def test_priority_ordering(self):
        """Test HIGH priority tasks come first."""
        queue = DownloadQueue()

        # Add LOW first
        task_low = DownloadTask(
            url="https://example.com/low.hdf", output_path=Path("low.hdf")
        )
        queue.enqueue(task_low, Priority.LOW)

        # Add HIGH second
        task_high = DownloadTask(
            url="https://example.com/high.hdf", output_path=Path("high.hdf")
        )
        queue.enqueue(task_high, Priority.HIGH)

        # HIGH should come out first despite being added second
        first = queue.dequeue()
        assert first.url == task_high.url

        second = queue.dequeue()
        assert second.url == task_low.url

    def test_fifo_same_priority(self):
        """Test FIFO for same priority."""
        queue = DownloadQueue()

        task1 = DownloadTask(url="https://example.com/1.hdf", output_path=Path("1.hdf"))
        task2 = DownloadTask(url="https://example.com/2.hdf", output_path=Path("2.hdf"))

        queue.enqueue(task1, Priority.MEDIUM)
        queue.enqueue(task2, Priority.MEDIUM)

        first = queue.dequeue()
        assert first.url == task1.url

        second = queue.dequeue()
        assert second.url == task2.url

    def test_queue_statistics(self):
        """Test queue stats."""
        queue = DownloadQueue()

        task = DownloadTask(
            url="https://example.com/file.hdf", output_path=Path("file.hdf")
        )
        queue.enqueue(task)

        stats = queue.get_stats()
        assert stats["size"] == 1
        assert stats["total_enqueued"] == 1
        assert stats["pending"] == 1
