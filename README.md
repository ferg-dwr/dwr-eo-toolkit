# dwr-eo-toolkit

A Python package for DWR employees to programmatically query and download NASA satellite imagery at scale.

Query ECOSTRESS thermal data, MODIS reflectance, and other Earth observation datasets from the comfort of your Python scripts — or via the REST API.

---

## Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (for REST API)
- NASA Earthdata Login account ([sign up here](https://urs.earthdata.nasa.gov/))

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

Get credentials from [NASA Earthdata Login](https://urs.earthdata.nasa.gov/). Pick one method:

**Option 1: Pre-generated token (recommended)**
```bash
# Generate at: https://urs.earthdata.nasa.gov/users/[user]/user_tokens
export EARTHDATA_TOKEN=your_60day_token_here
```

**Option 2: Username/password environment variables**
```bash
export EARTHDATA_USERNAME=your_username
export EARTHDATA_PASSWORD=your_password
```

**Option 3: `.netrc` file (Unix/Linux/Mac)**
```bash
# ~/.netrc
machine urs.earthdata.nasa.gov
login your_username
password your_password
```

---

## Usage

### As a Python Package

```python
from dwr_eo_toolkit.providers import EarthAccessProvider

# Create provider (automatically authenticates)
provider = EarthAccessProvider()

# Search for ECOSTRESS thermal data over California
results, total = provider.search(
    product="ECOSTRESS",
    bounding_box=(-122.82, 36.78, -120.94, 38.25),
    start_date="2024-01-01",
    end_date="2024-12-31",
)

print(f"Found {total} granules")

# Download the first 5
files = provider.download(results[:5], "./downloads")
```

### Composable Query Filters

```python
from dwr_eo_toolkit.filters import Query, BoundingBox, DateRange

query = (
    Query()
    .with_product("ECOSTRESS")
    .with_spatial_bounds(BoundingBox(-122.82, 36.78, -120.94, 38.25))
    .with_date_range(DateRange("2024-01-01", "2024-12-31"))
)

results, total = query.execute(provider)
```

### Parallel Batch Downloads

```python
from dwr_eo_toolkit.download_manager import BatchDownloadManager, DownloadSession

manager = BatchDownloadManager(max_concurrent_sessions=3)

session = DownloadSession()
# ... add tasks ...
manager.add_session(session, priority="high")

results = manager.execute_all()

# Progress tracking
progress = manager.get_progress()
print(f"{progress['completed']}/{progress['total_files']} completed")

# Save and resume from checkpoint
manager.save_checkpoint("backup_1")
results = manager.resume_from_checkpoint("backup_1")
```

### Scheduled Downloads

```python
from dwr_eo_toolkit.download_manager import DownloadScheduler
from datetime import datetime, timedelta

scheduler = DownloadScheduler()

# One-time
job_id = scheduler.schedule_once(session, run_at=datetime.now() + timedelta(hours=2))

# Recurring (every Monday at 2 AM)
recurring_id = scheduler.schedule_recurring(session, cron="0 2 * * MON")
```

---

## Running the REST API

The toolkit ships with a FastAPI server that exposes search, download, batch, and scheduling operations over HTTP.

### Launch

```bash
# 1. Copy environment template
cp .env.example .env
# Edit .env with your values (EARTHDATA_TOKEN, etc.)

# 2. Start services (API + PostgreSQL)
docker compose up --build

# 3. Run database migrations (in another terminal)
docker compose exec dwr-eo-toolkit alembic upgrade head

# 4. Verify it's running
curl http://localhost:8000/health
```

The API is now available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health check:** http://localhost:8000/health

### Example: Search via REST API

```bash
curl -X POST http://localhost:8000/api/v1/downloads/search \
  -H "Content-Type: application/json" \
  -d '{
    "product": "ECOSTRESS",
    "min_lon": -122.82,
    "min_lat": 36.78,
    "max_lon": -120.94,
    "max_lat": 38.25,
    "start_date": "2024-12-29",
    "end_date": "2024-12-31",
    "max_results": 10
  }'
```

### Example: Start a Download

```bash
curl -X POST http://localhost:8000/api/v1/downloads/start \
  -H "Content-Type: application/json" \
  -d '{
    "product": "ECOSTRESS",
    "min_lon": -122.82,
    "min_lat": 36.78,
    "max_lon": -120.94,
    "max_lat": 38.25,
    "start_date": "2024-12-29",
    "end_date": "2024-12-31",
    "max_results": 5,
    "output_dir": "./downloads/my_session"
  }'
```

### API Endpoints

```
GET    /                              # Root
GET    /health                        # Health check
GET    /status                        # Detailed status
GET    /docs                          # Swagger UI
GET    /redoc                         # ReDoc

POST   /api/v1/downloads/search       # Search for granules
GET    /api/v1/downloads              # List download sessions
POST   /api/v1/downloads              # Register a download session (no I/O)
POST   /api/v1/downloads/start        # Search + download synchronously
GET    /api/v1/downloads/{id}         # Get download details
PATCH  /api/v1/downloads/{id}         # Update download
DELETE /api/v1/downloads/{id}         # Cancel download

GET    /api/v1/batches                # List batch operations
POST   /api/v1/batches                # Create batch
GET    /api/v1/batches/{id}           # Get batch details
PATCH  /api/v1/batches/{id}           # Update batch
DELETE /api/v1/batches/{id}           # Cancel batch

GET    /api/v1/jobs                   # List scheduled jobs
POST   /api/v1/jobs/schedule          # Schedule a job
GET    /api/v1/jobs/{id}              # Get job details
PATCH  /api/v1/jobs/{id}              # Update job
DELETE /api/v1/jobs/{id}              # Cancel job
```

---

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/dwr_eo_toolkit --cov-report=html

# Specific module
pytest tests/test_batch_manager.py -v
```

### Type Checking & Linting

```bash
mypy src/dwr_eo_toolkit          # Type check
ruff check src tests             # Lint
ruff format --check src tests    # Format check
```

### Useful Docker Commands

```bash
# View logs
docker compose logs -f dwr-eo-toolkit
docker compose logs -f postgres

# Run commands in container
docker compose exec dwr-eo-toolkit bash
docker compose exec dwr-eo-toolkit pytest -v
docker compose exec dwr-eo-toolkit alembic current

# Database access
docker compose exec postgres psql -U postgres -d dwr_eo_toolkit_dev

# Stop and clean up
docker compose down              # Stop containers
docker compose down -v           # Stop + remove volumes
```

---

## Project Structure

```
dwr-eo-toolkit/
├── alembic/                          # Database migrations
├── src/
│   └── dwr_eo_toolkit/
│       ├── core/                     # Authentication & HTTP
│       ├── providers/                # EarthAccess integration + adapters
│       ├── filters/                  # Composable query filters
│       ├── download_manager/         # Batch downloads, scheduler, sessions
│       ├── api/                      # FastAPI app, routes, schemas
│       ├── database/                 # SQLAlchemy ORM + connection
│       ├── cli/                      # CLI (planned)
│       └── monitoring/               # Health, logging, metrics
├── tests/
├── examples/
│   ├── example_earthdata_query.py
│   ├── example_earthdata_batchdownload.py
│   └── ...
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## References

- [NASA Earthdata Login](https://urs.earthdata.nasa.gov/)
- [EarthAccess Documentation](https://nsidc.org/earthaccess/)
- [ECOSTRESS Data](https://lpdaac.usgs.gov/products/eco_l2t_lste/)
- [MODIS Data](https://lpdaac.usgs.gov/products/mod09ga/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)

---

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check the docs in `/docs`
- For Docker issues, verify your `.env` file is configured correctly

---

**Built with ❤️ for water resource monitoring and Earth observation.**
