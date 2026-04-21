#!/usr/bin/env python3
"""
Simple Phase 3 Example: BatchDownloadManager

Just straight through - no functions, just imports and comments.
Read line by line like a Jupyter notebook.
"""

from dwr_eo_toolkit.download_manager import (
    BatchDownloadManager,
    DownloadSession,
    DownloadTask,
)
from pathlib import Path

# Create downloads directory
Path("./downloads").mkdir(exist_ok=True)

# ============================================================================
# Example 1: Create a BatchDownloadManager
# ============================================================================

print("\n" + "="*80)
print("Example 1: Basic Batch Operations")
print("="*80)

# Create a batch manager that can run up to 3 sessions at the same time
manager = BatchDownloadManager(max_concurrent_sessions=3)
print(f"✓ Created BatchDownloadManager with max 3 concurrent sessions")

# ============================================================================
# Example 2: Create download sessions and add them to the manager
# ============================================================================

print("\n" + "="*80)
print("Example 2: Adding Sessions to Batch")
print("="*80)

# Create first session - ECOSTRESS data
session1 = DownloadSession()
task1 = DownloadTask(
    url="https://example.com/ecostress/file1.tif",
    output_path=Path("./downloads/ecostress_file1.tif"),
)
task2 = DownloadTask(
    url="https://example.com/ecostress/file2.tif",
    output_path=Path("./downloads/ecostress_file2.tif"),
)
session1.add_task(task1)
session1.add_task(task2)
manager.add_session(session1, priority="high")
print(f"Added session 1 (2 ECOSTRESS files, high priority)")

# Create second session - MODIS data
session2 = DownloadSession()
task3 = DownloadTask(
    url="https://example.com/modis/file1.tif",
    output_path=Path("./downloads/modis_file1.tif"),
)
session2.add_task(task3)
manager.add_session(session2, priority="medium")
print(f"Added session 2 (1 MODIS file, medium priority)")

# Create third session - VIIRS data
session3 = DownloadSession()
task4 = DownloadTask(
    url="https://example.com/viirs/file1.tif",
    output_path=Path("./downloads/viirs_file1.tif"),
)
task5 = DownloadTask(
    url="https://example.com/viirs/file2.tif",
    output_path=Path("./downloads/viirs_file2.tif"),
)
session3.add_task(task4)
session3.add_task(task5)
manager.add_session(session3, priority="low")
print(f"Added session 3 (2 VIIRS files, low priority)")

# ============================================================================
# Example 3: Check progress before execution
# ============================================================================

print("\n" + "="*80)
print("Example 3: Check Progress")
print("="*80)

progress = manager.get_progress()
print(f"Before execution:")
print(f"  Total files: {progress['total_files']}")
print(f"  Completed: {progress['completed']}")
print(f"  Failed: {progress['failed']}")
print(f"  Pending: {progress['pending']}")

# ============================================================================
# Example 4: Execute all sessions in parallel
# ============================================================================

print("\n" + "="*80)
print("Example 4: Execute All Sessions in Parallel")
print("="*80)

print("Starting parallel execution of 3 sessions...")
results = manager.execute_all()
print(f"Execution complete")

# ============================================================================
# Example 5: Check progress after execution
# ============================================================================

print("\n" + "="*80)
print("Example 5: Progress After Execution")
print("="*80)

progress = manager.get_progress()
print(f"After execution:")
print(f"  Total files: {progress['total_files']}")
print(f"  Completed: {progress['completed']}")
print(f"  Failed: {progress['failed']}")
success_rate = progress['completed'] / max(progress['total_files'], 1) * 100
print(f"  Success rate: {success_rate:.1f}%")

# ============================================================================
# Example 6: Get detailed statistics
# ============================================================================

# print("\n" + "="*80)
# print("Example 6: Detailed Statistics")
# print("="*80)

# stats = manager.get_statistics()
# print(f"Overall Statistics:")
# print(f"  Total sessions: {stats['total_sessions']}")
# print(f"  Sessions breakdown:")

# for session_stat in stats['sessions']:
#     print(f"\n  Session {session_stat['session_id'][:8]}:")
#     print(f"    Files downloaded: {session_stat['files_downloaded']}")
#     print(f"    Files failed: {session_stat['files_failed']}")
#     print(f"    Success rate: {session_stat.get('success_rate', 'N/A')}")
#     print(f"    Avg speed: {session_stat.get('avg_speed_mbps', 'N/A')} MB/s")

# # ============================================================================
# # Example 7: Save checkpoint (for recovery later)
# # ============================================================================

# print("\n" + "="*80)
# print("Example 7: Checkpoint for Disaster Recovery")
# print("="*80)

# checkpoint_path = manager.save_checkpoint("my_batch_backup")
# print(f"✓ Saved checkpoint: {checkpoint_path}")
# print(f"This checkpoint can be used to resume if something fails")

# # ============================================================================
# # Example 8: List all available checkpoints
# # ============================================================================

# print("\n" + "="*80)
# print("Example 8: List Checkpoints")
# print("="*80)

# checkpoints = manager.list_checkpoints()
# print(f"Available checkpoints: {len(checkpoints)}")
# for cp in checkpoints:
#     print(f"  - {cp}")

# # ============================================================================
# # Example 9: Pause and resume operations
# # ============================================================================

# print("\n" + "="*80)
# print("Example 9: Pause/Resume/Cancel Operations")
# print("="*80)

# # In a real scenario, you could pause ongoing downloads
# # manager.pause_all()
# # print(f"✓ Paused all sessions")

# # Then resume them later
# # manager.resume_all()
# # print(f"✓ Resumed all sessions")

# # Or cancel them
# # manager.cancel_all()
# # print(f"✓ Cancelled all sessions")

# print("(Demonstrated with comments - these would work on active downloads)")

# print("\n" + "="*80)
# print("Done! BatchDownloadManager Example Complete")
# print("="*80)