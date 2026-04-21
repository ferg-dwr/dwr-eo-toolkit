# dwr-eo-toolkit

A Python package for DWR employees to programmatically query and download NASA satellite imagery at scale.

Query ECOSTRESS thermal data, MODIS reflectance, and other Earth observation datasets from the comfort of your Python scripts.

## Status

🚀 **Phase 3A-3B Complete** - Batch operations and scheduling ready
- [x] Secure authentication (NASA Earthdata Login) - Phase 1 ✅
- [x] Authenticated HTTP client with retry logic - Phase 1 ✅
- [x] EarthAccess integration - Phase 2A ✅
- [x] Full test suite (197 tests, 100% passing) - Phase 2B ✅
- [x] Provider abstraction layer - Phase 2A ✅
- [x] Query filters and composable API - Phase 2B ✅
- [x] Batch download manager with parallel execution - Phase 3A ✅
- [x] Download scheduler (one-time & recurring) - Phase 3B ✅
- [x] Session persistence and checkpointing - Phase 3A ✅
- [ ] FastAPI REST API server (Phase 4)
- [ ] WebSocket real-time progress streaming (Phase 4)
- [ ] Click-based CLI (Phase 4)
- [ ] PostgreSQL integration (Phase 4)

---

## Quick Start

### Installation

```bash
# Clone the repo
git clone https://github.com/ferg-dwr/dwr-eo-toolkit.git
cd dwr-eo-toolkit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e ".[dev]"
```

### Authentication

Get credentials from [NASA Earthdata Login](https://urs.earthdata.nasa.gov/):

#### Option 1: Pre-Generated Token (Recommended)
```bash
# Generate at: https://urs.earthdata.nasa.gov/user_settings/generate_token
export EARTHDATA_TOKEN=your_60day_token_here
```

#### Option 2: Environment Variables
```bash
export EARTHDATA_USERNAME=your_username
export EARTHDATA_PASSWORD=your_password
```

#### Option 3: .netrc File (Unix/Linux/Mac)
```bash
# ~/.netrc
machine urs.earthdata.nasa.gov
login your_username
password your_password
```

### Basic Usage

```python
from dwr_eo_toolkit.providers import EarthAccessProvider

# Create provider (automatically authenticates)
provider = EarthAccessProvider()

# Search for ECOSTRESS thermal data
results, total = provider.search(
    product="ECOSTRESS",
    bounding_box=(-122.82, 36.78, -120.94, 38.25),  # California
    start_date="2020-01-01",
    end_date="2026-04-13",
)

print(f"Found {total} granules")
for granule in results[:5]:
    print(f"  {granule}")
```

**With Batch Manager (Phase 3):**

```python
from dwr_eo_toolkit.download_manager import (
    BatchDownloadManager, 
    DownloadSession
)

# Create batch manager for parallel downloads
manager = BatchDownloadManager(max_concurrent_sessions=3)

# Create independent download sessions
session1 = DownloadSession()
session1.add_task(task1)
session1.add_task(task2)
manager.add_session(session1, priority="high")

session2 = DownloadSession()
session2.add_task(task3)
manager.add_session(session2, priority="medium")

# Execute all in parallel with checkpointing
results = manager.execute_all()

# Check progress
progress = manager.get_progress()
print(f"{progress['completed']}/{progress['total_files']} completed")

# Save checkpoint for recovery
manager.save_checkpoint("backup_1")

# Resume later from checkpoint
results = manager.resume_from_checkpoint("backup_1")
```

**With Scheduler (Phase 3):**

```python
from dwr_eo_toolkit.download_manager import DownloadScheduler
from datetime import datetime, timedelta

scheduler = DownloadScheduler()

# Schedule one-time download
job_id = scheduler.schedule_once(
    session,
    run_at=datetime.now() + timedelta(hours=2)
)

# Schedule recurring (every Monday at 2 AM)
recurring_id = scheduler.schedule_recurring(
    session,
    cron="0 2 * * MON"
)

# Control jobs
scheduler.pause_scheduled(job_id)
scheduler.resume_scheduled(job_id)
scheduler.cancel_scheduled(job_id)
```

**With Composable Filters:**

```python
from dwr_eo_toolkit.filters import Query, BoundingBox, DateRange

# Build query fluently
query = (
    Query()
    .with_product("ECOSTRESS")
    .with_spatial_bounds(BoundingBox(-122.82, 36.78, -120.94, 38.25))
    .with_date_range(DateRange("2020-01-01", "2026-04-13"))
)

# Execute on provider
results, total = query.execute(provider)
```

---

## What's New in Phase 3

### BatchDownloadManager ⭐

Manage multiple download sessions in parallel with automatic checkpointing:

- **Parallel execution** - Run multiple sessions concurrently
- **Progress tracking** - Real-time progress across all sessions
- **Checkpointing** - Save state and resume from failures
- **Priority support** - High/medium/low priority sessions
- **Pause/resume/cancel** - Full control over batch operations
- **Statistics** - Detailed metrics per session

### DownloadScheduler ⭐

Schedule downloads for specific times or recurring intervals:

- **One-time scheduling** - Schedule downloads at future times
- **Recurring scheduling** - Cron expression support (daily, weekly, monthly)
- **Job management** - Pause, resume, cancel scheduled jobs
- **APScheduler backend** - Robust scheduling engine
- **List active jobs** - View all scheduled and running jobs

### Session Persistence ⭐

Save and restore download sessions:

```python
# Save session state
session.save_state("my_session.json")

# Later, restore and resume
restored = DownloadSession.load_state("my_session.json")
results = restored.execute()
```

### Enhanced Statistics

Track detailed download metrics:

```python
stats = session.get_statistics()
print(f"Files downloaded: {stats.files_downloaded}")
print(f"Files failed: {stats.files_failed}")
print(f"Success rate: {stats.success_rate:.1%}")
print(f"Avg speed: {stats.avg_speed_mbps:.2f} MB/s")
print(f"Total bytes: {stats.total_bytes_downloaded}")
```

---

## Architecture

### Current (Phase 3B)

```
Your Script
    ↓
Batch Operations (Phase 3A) + Scheduler (Phase 3B) ✅
├─ BatchDownloadManager
├─ DownloadScheduler
└─ Session Persistence
    ↓
Download Sessions
├─ Parallel execution
├─ Progress tracking
├─ Checksum validation
└─ Resume capability
    ↓
Provider Abstraction + Adapters (Phase 2) ✅
├─ EarthAccessProvider
├─ Instrument adapters (ECOSTRESS, MODIS)
└─ Query filters (spatial, temporal, product-specific)
    ↓
NASA Earth Observation APIs
```

---

## Project Statistics

| Metric | Value |
|--------|-------|
| Total Tests | 197 ✅ |
| New Tests (Phase 3) | 34 ✅ |
| Test Coverage | 87% (Phase 3 modules) ✅ |
| Type Coverage | 0 mypy errors ✅ |
| Lint Coverage | 0 ruff errors ✅ |
| Python Versions | 3.9, 3.10, 3.11, 3.12 ✅ |
| CI/CD | GitHub Actions ✅ |

---

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src/dwr_eo_toolkit --cov-report=html

# Check Phase 3 module coverage
python scripts/check_coverage.py

# Specific test file
pytest tests/test_batch_manager.py -v    # Batch manager tests
pytest tests/test_scheduler.py -v        # Scheduler tests
pytest tests/test_downloads.py -v        # Download tests
```

### Type Checking & Linting

```bash
# Type checking
mypy src/dwr_eo_toolkit

# Linting
ruff check src tests

# Format check
ruff format --check src tests
```

### Project Structure

```
dwr-eo-toolkit/
├── .github/
│   └── workflows/tests.yml          # GitHub Actions CI/CD
├── .gitignore
├── pyproject.toml                    # Package config
├── README.md                         # This file
├── scripts/
│   └── check_coverage.py             # Coverage validation (Phase 3)
├── src/
│   └── dwr_eo_toolkit/
│       ├── __init__.py
│       ├── core/                     # Authentication & HTTP
│       │   ├── auth.py
│       │   ├── client.py
│       │   └── exceptions.py
│       ├── providers/                # EarthAccess integration
│       │   ├── base.py
│       │   ├── earthaccess_provider.py
│       │   └── adapters/
│       │       ├── ecostress.py
│       │       └── modis.py
│       ├── filters/                  # Query filters
│       │   ├── base.py
│       │   ├── spatial.py
│       │   ├── temporal.py
│       │   ├── product.py
│       │   └── query.py
│       ├── download_manager/         # Phase 3 ✅
│       │   ├── batch_manager.py      # Parallel batch execution
│       │   ├── scheduler.py          # Scheduled downloads
│       │   ├── session.py            # Download sessions
│       │   ├── task.py               # Individual download tasks
│       │   ├── progress.py           # Progress tracking
│       │   ├── result.py             # Download results
│       │   ├── queue.py              # Priority queue
│       │   ├── resilience.py         # Retry logic
│       │   ├── manager.py            # Base manager
│       │   └── utils.py              # Utilities
│       ├── api/                      # Phase 4 (TBD)
│       │   └── __init__.py
│       ├── cli/                      # Phase 4 (TBD)
│       │   └── __init__.py
│       ├── monitoring/               # Phase 4 (TBD)
│       │   ├── health.py
│       │   ├── logger.py
│       │   └── metrics.py
│       └── database/                 # Phase 4 (TBD)
│           └── __init__.py
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_client.py
│   ├── test_providers.py
│   ├── test_filters.py
│   ├── test_downloads.py
│   ├── test_batch_manager.py         # Phase 3 ✅
│   ├── test_scheduler.py             # Phase 3 ✅
│   └── test_batch_downloads.py
├── examples/
│   ├── search_and_download.py
│   ├── batch_downloads.py            # Phase 3 ✅
│   └── scheduled_downloads.py        # Phase 3 ✅
└── docs/
    ├── index.md
    ├── authentication.md
    └── examples.md
```

---

## Roadmap

### Phase 1-2B ✅ (Complete)
- [x] Secure authentication
- [x] EarthAccess integration
- [x] Composable query filters
- [x] Provider abstraction layer

### Phase 3A-3B ✅ (Complete)
- [x] Batch download manager
- [x] Download scheduler
- [x] Session persistence
- [x] 34 comprehensive tests
- [x] 87% code coverage

### Phase 4 (In Development - Starting Now)
- [ ] FastAPI REST API server (4A)
- [ ] WebSocket progress streaming (4B)
- [ ] Structured logging & metrics (4B)
- [ ] Click-based CLI (4C)
- [ ] PostgreSQL integration (4C)
- [ ] Kubernetes manifests (4C)
- [ ] API documentation (4D)
- [ ] Deployment guide (4D)

### Phase 5 (Future)
- [ ] External model pipeline integration
- [ ] Message queue orchestration
- [ ] Horizontal pod autoscaling
- [ ] Advanced monitoring

---

## Getting Ready for Phase 4

Phase 4 will add the REST API server, monitoring, and CLI.

To prepare:

```bash
# 1. Install Phase 4 dependencies
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary click python-dotenv

# 2. Install PostgreSQL locally
# macOS: brew install postgresql@15
# Ubuntu: sudo apt-get install postgresql postgresql-contrib
# Windows: Download from https://www.postgresql.org/download/windows/

# 3. Create development database
createdb dwr_eo_toolkit_dev

# 4. Verify everything
python -c "
import fastapi; print(f'✅ FastAPI {fastapi.__version__}')
import sqlalchemy; print(f'✅ SQLAlchemy {sqlalchemy.__version__}')
import click; print(f'✅ Click {click.__version__}')
"
```

### Coming in Phase 4

**REST API Endpoints:**
```
POST   /downloads/start              # Start new download session
GET    /downloads/{session_id}       # Get session status
GET    /downloads/{session_id}/stats # Get detailed statistics
POST   /downloads/{session_id}/pause # Pause session
DELETE /downloads/{session_id}       # Cancel session

WebSocket /ws/progress/{session_id}  # Real-time progress
```

**CLI Commands:**
```bash
dwr download <url> <path>            # Download file
dwr session <session_id>             # Show status
dwr stats <session_id>               # Show statistics
dwr schedule once --time <time>      # Schedule one-time
dwr batch <batch_file>               # Run batch from JSON
```

---

## References

- [NASA Earthdata Login](https://urs.earthdata.nasa.gov/)
- [EarthAccess Documentation](https://nsidc.org/earthaccess/)
- [ECOSTRESS Data](https://lpdaac.usgs.gov/products/eco_l2t_lste/)
- [MODIS Data](https://lpdaac.usgs.gov/products/mod09ga/)
- [FastAPI (Phase 4)](https://fastapi.tiangolo.com/)
- [SQLAlchemy (Phase 4)](https://docs.sqlalchemy.org/)

---

## Support

For issues, questions, or feature requests:
- 📧 Open an issue on GitHub
- 📚 Check the docs
- 🔍 Search closed issues for similar problems

---

**Built with ❤️ for water resource monitoring and Earth observation.**