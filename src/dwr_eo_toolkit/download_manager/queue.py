from dataclasses import dataclass
from enum import Enum
from queue import PriorityQueue
from typing import Optional

from .task import DownloadTask


class Priority(Enum):
    LOW = 3
    MEDIUM = 2
    HIGH = 1


@dataclass
class PrioritizedTask:
    priority: Priority
    task: DownloadTask

    def __lt__(self, other: "PrioritizedTask") -> bool:  # ✅ Add type hints
        return self.priority.value < other.priority.value


class DownloadQueue:
    """Priority-based task queue for downloads."""

    def __init__(self, max_size: Optional[int] = None):
        self.queue: PriorityQueue[PrioritizedTask] = PriorityQueue(
            maxsize=max_size or 0
        )  # ✅ Fixed
        self.total_enqueued = 0
        self.total_dequeued = 0

    def enqueue(
        self, task: DownloadTask, priority: Priority = Priority.MEDIUM
    ) -> None:  # ✅ Add return type
        """Add task to queue with priority."""
        self.total_enqueued += 1
        self.queue.put(PrioritizedTask(priority, task))

    def dequeue(self) -> DownloadTask:
        """Get highest priority task."""
        prioritized = self.queue.get()
        self.total_dequeued += 1
        return prioritized.task

    def peek(self) -> Optional[DownloadTask]:
        """Look at next task without removing."""
        if self.queue.empty():
            return None
        return self.queue.queue[0].task

    def size(self) -> int:
        """Current queue size."""
        return self.queue.qsize()

    def get_stats(self) -> dict:  # ✅ Could be dict[str, int] for better typing
        """Queue statistics."""
        return {
            "size": self.size(),
            "total_enqueued": self.total_enqueued,
            "total_dequeued": self.total_dequeued,
            "pending": self.total_enqueued - self.total_dequeued,
        }
