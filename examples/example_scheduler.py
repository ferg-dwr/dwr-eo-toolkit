#!/usr/bin/env python3
"""
Simple Phase 3 Example: DownloadScheduler

Just straight through - no functions, just imports and comments.
Read line by line like a Jupyter notebook.
"""

from datetime import datetime, timedelta
from pathlib import Path

from dwr_eo_toolkit.download_manager import (
    DownloadScheduler,
    DownloadSession,
    DownloadTask,
)

# Create downloads directory
Path("./downloads").mkdir(exist_ok=True)

# ============================================================================
# Example 1: Create a DownloadScheduler
# ============================================================================

print("\n" + "=" * 80)
print("Example 1: Create a Scheduler")
print("=" * 80)

# Create a scheduler to manage scheduled downloads
scheduler = DownloadScheduler()
print("✓ Created DownloadScheduler")

# ============================================================================
# Example 2: Schedule a one-time download
# ============================================================================

print("\n" + "=" * 80)
print("Example 2: One-Time Download (in 2 hours)")
print("=" * 80)

# Create a download session
session_onetime = DownloadSession()
task_onetime = DownloadTask(
    url="https://example.com/thermal_data.tif",
    output_path=Path("./downloads/thermal_data.tif"),
)
session_onetime.add_task(task_onetime)

# Schedule it for 2 hours from now
run_time = datetime.now() + timedelta(hours=2)
job_id_onetime = scheduler.schedule_once(session_onetime, run_at=run_time)
print("✓ Scheduled one-time download")
print(f"  Job ID: {job_id_onetime}")
print(f"  Will run at: {run_time}")

# ============================================================================
# Example 3: Schedule a daily download at 6 AM
# ============================================================================

print("\n" + "=" * 80)
print("Example 3: Daily Download at 6 AM")
print("=" * 80)

# Create session for daily downloads
session_daily = DownloadSession()
task_daily = DownloadTask(
    url="https://example.com/daily_modis.tif",
    output_path=Path("./downloads/daily_modis.tif"),
)
session_daily.add_task(task_daily)

# Schedule it to run every day at 6 AM (cron: 0 6 * * *)
job_id_daily = scheduler.schedule_recurring(
    session_daily,
    cron="0 6 * * *",
)
print("Scheduled daily download")
print(f"  Job ID: {job_id_daily}")
print("  Cron: 0 6 * * * (every day at 6 AM)")

# ============================================================================
# Example 4: Schedule a weekly download on Monday at 10 AM
# ============================================================================

print("\n" + "=" * 80)
print("Example 4: Weekly Download (Mondays at 10 AM)")
print("=" * 80)

# Create session for weekly downloads
session_weekly = DownloadSession()
task_weekly = DownloadTask(
    url="https://example.com/weekly_summary.tif",
    output_path=Path("./downloads/weekly_summary.tif"),
)
session_weekly.add_task(task_weekly)

# Schedule it to run every Monday at 10 AM (cron: 0 10 * * MON)
job_id_weekly = scheduler.schedule_recurring(
    session_weekly,
    cron="0 10 * * MON",
)
print("Scheduled weekly download")
print(f"  Job ID: {job_id_weekly}")
print("  Cron: 0 10 * * MON (every Monday at 10 AM)")

# ============================================================================
# Example 5: Schedule a monthly download on the 1st
# ============================================================================

print("\n" + "=" * 80)
print("Example 5: Monthly Download (1st of month at midnight)")
print("=" * 80)

# Create session for monthly downloads
session_monthly = DownloadSession()
task_monthly = DownloadTask(
    url="https://example.com/monthly_report.tif",
    output_path=Path("./downloads/monthly_report.tif"),
)
session_monthly.add_task(task_monthly)

# Schedule it to run on the 1st of every month at midnight (cron: 0 0 1 * *)
job_id_monthly = scheduler.schedule_recurring(
    session_monthly,
    cron="0 0 1 * *",
)
print("✓ Scheduled monthly download")
print(f"  Job ID: {job_id_monthly}")
print("  Cron: 0 0 1 * * (1st of each month at midnight)")

# ============================================================================
# Example 6: List all scheduled jobs
# ============================================================================

print("\n" + "=" * 80)
print("Example 6: List All Scheduled Jobs")
print("=" * 80)

all_jobs = scheduler.list_jobs()
print(f"Total scheduled jobs: {len(all_jobs)}")
print()

for job_id, job_info in all_jobs.items():
    print(f"Job ID: {job_id}")
    print(f"  Type: {job_info.get('type', 'unknown')}")
    print(f"  Status: {job_info.get('status', 'unknown')}")
    if job_info.get("next_run_time"):
        print(f"  Next run: {job_info['next_run_time']}")
    if job_info.get("cron"):
        print(f"  Cron: {job_info['cron']}")
    print()

# ============================================================================
# Example 7: Pause a job
# ============================================================================

print("\n" + "=" * 80)
print("Example 7: Pause a Job")
print("=" * 80)

paused = scheduler.pause_scheduled(job_id_daily)
if paused:
    print(f"Paused job {job_id_daily[:8]}...")
else:
    print(f"Could not pause job {job_id_daily[:8]}...")

# ============================================================================
# Example 8: Resume a paused job
# ============================================================================

print("\n" + "=" * 80)
print("Example 8: Resume a Paused Job")
print("=" * 80)

resumed = scheduler.resume_scheduled(job_id_daily)
if resumed:
    print(f"Resumed job {job_id_daily[:8]}...")
else:
    print(f"Could not resume job {job_id_daily[:8]}...")

# ============================================================================
# Example 9: Cancel a job
# ============================================================================

print("\n" + "=" * 80)
print("Example 9: Cancel a Job")
print("=" * 80)

cancelled = scheduler.cancel_scheduled(job_id_onetime)
if cancelled:
    print(f"Cancelled one-time job {job_id_onetime[:8]}...")
else:
    print(f"Could not cancel job {job_id_onetime[:8]}...")

# ============================================================================
# Example 10: Cron Expression Reference
# ============================================================================

print("\n" + "=" * 80)
print("Example 10: Cron Expression Reference")
print("=" * 80)

print("Cron Format: MM HH DD MM DOW")
print("  MM  = Minute (0-59)")
print("  HH  = Hour (0-23, 24-hour format)")
print("  DD  = Day of month (1-31)")
print("  MM  = Month (1-12)")
print("  DOW = Day of week (0-6, where 0=Sunday or use MON-SUN)")
print()

print("Common Examples:")
print("  0 * * * *        = Every hour at minute 0")
print("  0 0 * * *        = Every day at midnight")
print("  0 6 * * *        = Every day at 6 AM")
print("  0 10 * * MON     = Every Monday at 10 AM")
print("  0 0 1 * *        = 1st of every month at midnight")
print("  0 9 * * MON-FRI  = Weekdays at 9 AM")
print("  0 0 * * 0        = Every Sunday at midnight")
print("  30 14 * * *      = Every day at 2:30 PM")

print("\n" + "=" * 80)
print("Done! DownloadScheduler Example Complete")
print("=" * 80)
