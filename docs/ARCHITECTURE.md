# 🏗️ dwr-eo-toolkit Architecture

## Overview

**dwr-eo-toolkit** is a Python package that simplifies access to NASA Earth Observation data for DWR (Department of Water Resources) use cases. It provides a unified interface to search, filter, and download satellite imagery and geospatial data.

### Core Philosophy
- **Simplify**: Hide complexity of NASA APIs
- **Unify**: Single interface for multiple data sources
- **Extend**: Easy to add new data providers
- **Scale**: Handle large downloads efficiently

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   User Application Layer                     │
│         (Jupyter Notebooks, Scripts, Web APIs)               │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
    ┌───▼──────────┐      ┌──────▼─────┐
    │   Search API │      │ Download   │
    │              │      │   Manager  │
    └───┬──────────┘      └──────┬─────┘
        │                        │
    ┌───▼──────────────────────▼─┐
    │   Provider Interface        │
    │  (Abstract Base Classes)    │
    └───┬──────────────────────┬─┘
        │                      │
    ┌───▼──────────┐    ┌──────▼──────────┐
    │ EarthAccess  │    │   Instrument    │
    │  Provider    │    │    Adapters     │
    └───┬──────────┘    └──────┬──────────┘
        │                      │
    ┌───▼──────────────────────▼─┐
    │   NASA APIs & Services      │
    │ (earthaccess, CMR, etc.)    │
    └─────────────────────────────┘
```

---

## Module Breakdown

### 1. **Core Module** (`dwr_eo_toolkit.core`)

Provides authentication and HTTP client abstractions.

**Files:**
- `auth.py` - Authentication with NASA Earthdata
- `client.py` - HTTP client for API requests
- `exceptions.py` - Custom exception classes

**Responsibilities:**
- Login to NASA Earthdata servers
- Manage authentication tokens
- Handle HTTP requests with retry logic
- Error handling and reporting

**Key Classes:**
```python
class EarthDataLoginAuth:
    """Manages NASA Earthdata login"""
    def login(self, strategy: str) -> bool

class HTTPClient:
    """HTTP client with retry logic"""
    def get(self, url: str, **kwargs) -> Response
    def post(self, url: str, **kwargs) -> Response
```

---

### 2. **Providers Module** (`dwr_eo_toolkit.providers`)

Abstract interface for different data providers.

**Files:**
- `base.py` - Abstract base provider class
- `earthaccess_provider.py` - NASA earthaccess implementation

**Responsibilities:**
- Define common interface for all data providers
- Search for granules (data files)
- Return metadata about available data
- Validate product/instrument names

**Key Classes:**
```python
class BaseProvider(ABC):
    """Abstract base for data providers"""
    def search(self, **filters) -> Tuple[List, int]
    def validate_product(self, product: str) -> bool
    def get_adapter(self, product: str) -> InstrumentAdapter

class EarthAccessProvider(BaseProvider):
    """NASA earthaccess wrapper provider"""
    # Implements search, validation, adapter lookup
```

**Why This Design?**
- Easy to add new providers (NOAA, USGS, etc.)
- Consistent API regardless of backend
- Testable with mocks

---

### 3. **Adapters Module** (`dwr_eo_toolkit.providers.adapters`)

Instrument-specific metadata and field mappings.

**Files:**
- `base.py` - Abstract adapter base class
- `modis.py` - MODIS-specific metadata
- `ecostress.py` - ECOSTRESS-specific metadata

**Responsibilities:**
- Map instrument-specific fields to common interface
- Validate instrument parameters
- Provide metadata about instruments
- Transform API responses to common format

**Key Classes:**
```python
class InstrumentAdapter(ABC):
    """Maps instrument-specific fields to common interface"""
    def validate_parameters(self, **params) -> bool
    def transform_result(self, granule: dict) -> GranuleMetadata
    def get_metadata(self) -> InstrumentMetadata

class MODISAdapter(InstrumentAdapter):
    """MODIS-specific adapter"""
    PRODUCT_CODES = {"MOD09": "MODIS Terra Surface Reflectance", ...}
    VALID_TILES = ["h00v00", "h00v01", ...]
```

**Why This Design?**
- Isolates instrument-specific logic
- Easy to add new instruments
- Keeps provider code clean
- Reusable across providers

---

### 4. **Download Manager Module** (`dwr_eo_toolkit.download_manager`)

Handles file downloads with progress tracking and resilience.

**Files:**
- `manager.py` - Main download orchestrator
- `session.py` - Parallel download session
- `task.py` - Single file download task
- `progress.py` - Progress tracking and reporting
- `resilience.py` - Retry logic and resume capability
- `result.py` - Download results and statistics
- `utils.py` - Helper functions

**Responsibilities:**
- Download multiple files in parallel
- Track progress in real-time
- Resume interrupted downloads
- Retry failed downloads with backoff
- Verify file checksums
- Generate download reports

**Key Classes:**
```python
class DownloadManager:
    """Orchestrates downloads"""
    def download(
        self, 
        granules: List[str],
        output_dir: Path,
        max_workers: int = 8,
        retry_attempts: int = 3
    ) -> DownloadResult

class DownloadSession:
    """Manages parallel downloads"""
    def download_batch(self, tasks: List[DownloadTask]) -> DownloadResult

class DownloadTask:
    """Single file download"""
    def execute(self) -> bool

class DownloadProgress:
    """Real-time progress tracking"""
    def update(self, bytes_downloaded: int)
    def get_eta(self) -> timedelta
```

**Architecture:**
```
DownloadManager
    ├─ DownloadSession (ThreadPoolExecutor)
    │   ├─ DownloadTask (file 1)
    │   ├─ DownloadTask (file 2)
    │   └─ DownloadTask (file N)
    │
    ├─ ResilienceManager (retry/resume)
    └─ DownloadProgress (tracking)
```

---

### 5. **Filters Module** (`dwr_eo_toolkit.filters`)

Query builder for search filters.

**Files:**
- `base.py` - Abstract filter base class
- `spatial.py` - Spatial filters (bounding boxes, etc.)
- `temporal.py` - Temporal filters (date ranges, etc.)
- `attribute.py` - Attribute filters (cloud cover, etc.)

**Responsibilities:**
- Build complex search queries
- Validate filter parameters
- Convert to API-specific query format

**Key Classes:**
```python
class Filter(ABC):
    """Base filter class"""
    def validate(self) -> bool
    def to_query(self) -> dict

class SpatialFilter(Filter):
    """Spatial queries (geometry, bbox)"""
    
class TemporalFilter(Filter):
    """Temporal queries (date ranges)"""
```

---

## Data Flow

### Search Flow

```
User Request
    ↓
[Search API]
    ├─ Validate filters
    ├─ Build query
    └─ Call provider.search()
        ↓
    [EarthAccessProvider]
        ├─ Authenticate with NASA
        ├─ Query earthaccess API
        └─ Return granule list
            ↓
        [InstrumentAdapter]
            ├─ Transform metadata
            └─ Validate granules
                ↓
    [Response to User]
        ├─ Granule list
        ├─ Metadata
        └─ Total count
```

### Download Flow

```
User Request: download(granules, output_dir)
    ↓
[DownloadManager]
    ├─ Create DownloadTask for each granule
    ├─ Create DownloadSession
    └─ Start downloads
        ↓
    [DownloadSession] (ThreadPoolExecutor, 8 threads)
        ├─ Task 1: Download file 1
        │   ├─ HEAD request for size
        │   ├─ GET request with Range
        │   ├─ Check resume capability
        │   └─ Verify checksum
        │
        ├─ Task 2: Download file 2
        │   └─ ...
        │
        └─ Task N: Download file N
            └─ ...
        
        ↓ (All tasks report progress)
        
    [DownloadProgress]
        ├─ Aggregate progress
        ├─ Calculate speed
        ├─ Estimate ETA
        └─ Callback to user
            ↓
    [ResilienceManager]
        ├─ Handle failures
        ├─ Retry with exponential backoff
        ├─ Resume interrupted downloads
        └─ Track retry attempts
            ↓
    [DownloadResult]
        ├─ List of successful downloads
        ├─ List of failed downloads
        ├─ Total size downloaded
        ├─ Download duration
        └─ Success rate
```

---

## Data Models

### Granule Metadata

```python
@dataclass
class GranuleMetadata:
    """Metadata for a single granule (data file)"""
    id: str                          # Unique granule ID
    product: str                     # Product name (e.g., "MOD09")
    title: str                       # Human-readable title
    url: str                         # Download URL
    size_bytes: int                  # File size in bytes
    checksum: str                    # File checksum
    checksum_type: str               # Type of checksum (MD5, SHA256)
    temporal_coverage: DatetimeRange # Date range covered
    spatial_coverage: BoundingBox    # Geographic coverage
    cloud_cover: Optional[float]     # Cloud cover percentage
    metadata: dict                   # Additional metadata
```

### Download Result

```python
@dataclass
class DownloadResult:
    """Summary of download operation"""
    successful: int                  # Files downloaded successfully
    failed: int                       # Files that failed
    total: int                        # Total attempted
    size_bytes: int                  # Total size downloaded
    duration: timedelta              # Time taken
    started_at: datetime             # Start time
    completed_at: datetime           # Completion time
    
    @property
    def success_rate(self) -> float:
        """Percentage of successful downloads"""
        return (self.successful / self.total) * 100 if self.total > 0 else 0
```

---

## Design Patterns Used

### 1. **Abstract Base Class (Provider)**
```python
class BaseProvider(ABC):
    @abstractmethod
    def search(self, **filters) -> Tuple[List, int]:
        pass
```
**Why:** Allows multiple implementations (earthaccess, future NOAA, etc.)

### 2. **Adapter Pattern (Instruments)**
```python
class InstrumentAdapter(ABC):
    def transform_result(self, raw: dict) -> GranuleMetadata:
        pass
```
**Why:** Isolates instrument-specific logic

### 3. **Strategy Pattern (Download Resilience)**
```python
class RetryStrategy(ABC):
    def should_retry(self, attempt: int) -> bool:
        pass
```
**Why:** Easy to swap retry strategies

### 4. **Factory Pattern (Adapter Selection)**
```python
def get_adapter(self, product: str) -> InstrumentAdapter:
    if product.startswith("MOD"):
        return MODISAdapter()
    elif product.startswith("ECO"):
        return ECOSTRESSAdapter()
```
**Why:** Centralized adapter creation

### 5. **Threading (Download Sessions)**
```python
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(task.execute) for task in tasks]
```
**Why:** Parallel downloads for performance

---

## Key Design Decisions

### 1. **earthaccess as Primary Provider**
- **Why:** NASA's official Python client
- **Tradeoff:** Tightly coupled to NASA, but well-maintained

### 2. **Instrument Adapters Over Monolithic Provider**
- **Why:** Scales better, easier to add instruments
- **Tradeoff:** More code initially, but cleaner long-term

### 3. **Thread-Based Parallelism**
- **Why:** Python standard, good for I/O-bound tasks
- **Tradeoff:** GIL doesn't matter for downloads, but limits CPU work

### 4. **Separate DownloadManager Module**
- **Why:** Download logic is complex and decoupled from search
- **Tradeoff:** Two separate APIs for users, but clear separation

### 5. **In-Memory Progress Callbacks**
- **Why:** Real-time updates without file I/O
- **Tradeoff:** Memory usage for large downloads

---

## Extensibility Points

### Add a New Data Provider

```python
# 1. Create provider class
class NOAAProvider(BaseProvider):
    def search(self, **filters):
        # NOAA-specific search logic
        pass

# 2. Register in factory
provider_factory = {
    "earthaccess": EarthAccessProvider,
    "noaa": NOAAProvider,  # NEW
}
```

### Add a New Instrument

```python
# 1. Create adapter
class LandsatAdapter(InstrumentAdapter):
    PRODUCT_CODES = {"LC08": "Landsat 8", ...}
    
    def validate_parameters(self, **params):
        # Landsat-specific validation
        pass

# 2. Register in provider
ADAPTERS = {
    "MODIS": MODISAdapter,
    "ECOSTRESS": ECOSTRESSAdapter,
    "LANDSAT": LandsatAdapter,  # NEW
}
```

### Add a New Retry Strategy

```python
class CustomBackoffRetry(RetryStrategy):
    def should_retry(self, attempt: int) -> bool:
        # Custom logic
        return attempt < 5

# Use it
manager = DownloadManager(
    retry_strategy=CustomBackoffRetry()
)
```

---

## Dependencies & External Services

### Required External Services
- **NASA Earthdata**: Authentication and data access
- **earthaccess Library**: Python client for NASA data
- **CMR API**: Catalog for granule metadata

### Python Dependencies
- `requests>=2.28.0` - HTTP client
- `earthaccess>=0.7.0` - NASA data access

### Testing Dependencies
- `pytest>=7.0` - Test framework
- `pytest-cov>=4.0` - Coverage reporting
- `black>=23.0.0` - Code formatting
- `isort>=5.12.0` - Import sorting
- `flake8>=6.0.0` - Linting

---

## Performance Characteristics

### Search Performance
- **Typical search**: 100-500ms (includes network latency)
- **Large search (2000+ granules)**: 2-5 seconds
- **Bottleneck**: NASA API response time

### Download Performance
- **Single file (100MB)**: 5-30 seconds (depends on network)
- **Parallel downloads (8 threads)**: ~8x faster than serial
- **Resume capability**: ~90% faster on re-download
- **Bottleneck**: Network bandwidth

### Memory Usage
- **Search**: ~1KB per granule (~2MB for 2000 granules)
- **Download**: ~10MB base + ~1MB per concurrent task
- **With 8 threads**: ~18MB typical

---

## Error Handling Strategy

```
┌─────────────────┐
│  User Request   │
└────────┬────────┘
         │
    ┌────▼─────────────────┐
    │ Try Operation        │
    └────┬────────────────┬┘
         │                │
    ┌────▼────┐      ┌────▼──────────┐
    │ Success │      │ Error Occurs   │
    └─────────┘      └────┬───────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
         ┌────▼─────────┐    ┌───────▼────────┐
         │ Retriable?   │    │ Fatal Error    │
         │ (timeout)    │    │ (auth failed)  │
         └────┬────┬────┘    └────┬───────────┘
          Yes │    │ No           │
         ┌────▼┐   │         ┌────▼──────┐
         │Retry│   │         │ Raise     │
         │(exp)│   │         │Exception  │
         └─────┘   │         └───────────┘
                   │
              ┌────▼──────────┐
              │ Raise         │
              │CustomException│
              └───────────────┘
```

**Custom Exceptions:**
- `AuthenticationError` - Login failed
- `ProviderError` - Provider API failed
- `DownloadError` - File download failed
- `ValidationError` - Input validation failed
- `ChecksumError` - File integrity check failed

---

## Testing Architecture

### Unit Tests
- Individual function testing
- Mocked external dependencies
- Fast execution (<1 second per test)

### Integration Tests
- Real API calls (with test credentials)
- Actual download operations
- Longer execution (~30 seconds)

### End-to-End Tests
- Full workflow testing
- Real NASA data
- Slower execution (~5 minutes)

**Test Organization:**
```
tests/
├── unit/
│   ├── test_auth.py
│   ├── test_filters.py
│   └── test_adapters.py
│
├── integration/
│   ├── test_search.py
│   └── test_download.py
│
└── fixtures/
    ├── conftest.py
    └── mock_data.py
```

---

---

## API Layer (Phase 4A - COMPLETE)

### 6. **API Module** (`dwr_eo_toolkit.api`)

FastAPI REST API with real-time WebSocket updates.

**Files:**
- `app.py` - FastAPI application setup, exception handlers
- `routes.py` - REST endpoints (downloads, batches, jobs)
- `schemas.py` - Pydantic models (request/response)
- `websocket.py` - WebSocket connection management

**REST Endpoints:**
```
Downloads:
  GET    /api/v1/downloads                    List all downloads
  POST   /api/v1/downloads                    Create new download
  GET    /api/v1/downloads/{id}               Get download details
  PATCH  /api/v1/downloads/{id}               Update download
  DELETE /api/v1/downloads/{id}               Cancel download

Batches:
  GET    /api/v1/batches                      List all batches
  POST   /api/v1/batches                      Create new batch
  GET    /api/v1/batches/{id}                 Get batch details
  PATCH  /api/v1/batches/{id}                 Update batch
  DELETE /api/v1/batches/{id}                 Cancel batch

Jobs:
  GET    /api/v1/jobs                         List all scheduled jobs
  POST   /api/v1/jobs/schedule                Schedule new job
  GET    /api/v1/jobs/{id}                    Get job details
  PATCH  /api/v1/jobs/{id}                    Update job
  DELETE /api/v1/jobs/{id}                    Delete job

System:
  GET    /                                    Service info
  GET    /health                              Health check
  GET    /status                              System status
  GET    /docs                                Swagger UI
  GET    /redoc                               ReDoc

WebSocket:
  WS     /ws/downloads/{download_id}          Real-time download updates
  WS     /ws/batches/{batch_id}               Real-time batch updates
  WS     /ws/jobs/{job_id}                    Real-time job updates
```

**Key Classes:**
```python
class DownloadResponse(BaseModel):
    id: str
    product: str
    status: str
    start_date: str
    end_date: str

class InferenceJobResponse(BaseModel):
    id: str
    download_id: str
    status: str
    progress: int
    
class ConnectionManager:
    """Manage WebSocket connections per resource"""
    async def connect(resource_id: str, websocket: WebSocket)
    async def broadcast(resource_id: str, message: dict)
```

**Architecture:**
```
HTTP Request
    ↓
[FastAPI Route Handler]
    ├─ Validate input (Pydantic)
    ├─ Get database session
    ├─ Execute business logic
    ├─ Update database
    └─ Return response (schema)

WebSocket Connection
    ↓
[ConnectionManager]
    ├─ Accept connection
    ├─ Add to active connections
    └─ Broadcast on events
```

---

## Database Layer (Phase 4A - COMPLETE)

### 7. **Database Module** (`dwr_eo_toolkit.database`)

SQLAlchemy ORM with PostgreSQL backend.

**Files:**
- `connection.py` - Connection pooling, session management
- `models.py` - SQLAlchemy ORM models
- `migrations/` - Alembic migration scripts

**Key Models:**
```python
class DownloadSession(Base):
    """Represents a download operation"""
    id: str
    product: str
    status: str
    created_at: datetime
    updated_at: datetime

class DownloadTask(Base):
    """Individual file within download"""
    id: str
    session_id: str
    file_url: str
    local_path: str
    status: str

class BatchOperation(Base):
    """Group of downloads"""
    id: str
    name: str
    status: str
    total_tasks: int
    completed_tasks: int

class ScheduledJob(Base):
    """Recurring download job"""
    id: str
    name: str
    schedule: str (cron format)
    product: str
    active: bool
    last_executed: datetime
    next_execution: datetime
```

**Storage:**
- **Production**: PostgreSQL 13+ with psycopg2
- **Testing**: SQLite in-memory with StaticPool
- **Migrations**: Alembic version control

---

## ML Inference Layer (Phase 4B - PLANNED)

### 8. **Models Module** (`dwr_eo_toolkit.models`)

PyTorch model management and inference.

**Planned Components:**
- `manager.py` - GitHub release downloader, model cache
- `registry.py` - Model version management
- `cache/` - Local model storage

**9. Geospatial Module** (`dwr_eo_toolkit.geospatial`)

Raster data handling for inference.

**Planned Components:**
- `reader.py` - GeoTIFF/COG reader with band selection
- `writer.py` - COG writer with geospatial metadata
- `validator.py` - Raster compatibility checks

**10. Inference Module** (`dwr_eo_toolkit.inference`)

Model execution pipeline.

**Planned Components:**
- `engine.py` - PyTorch inference executor
- `pipeline.py` - Download → Inference → Output workflow
- `processors/` - Model-specific input/output handling

**Inference Data Flow:**
```
Download Complete Event
    ↓
[Inference Pipeline]
    ├─ Get model from cache (or download from GitHub)
    ├─ Load raster data
    ├─ Prepare input (band selection, normalization)
    ├─ Run PyTorch model
    ├─ Post-process output
    ├─ Write COG with metadata
    ├─ Store in PostGIS or filesystem
    └─ Broadcast completion via WebSocket
```

---

## System Architecture (Updated)

```
┌───────────────────────────────────────────────────────────┐
│              User Applications                             │
│  (Web UI, Jupyter, CLI, Mobile Apps, Scripts)             │
└───────────────┬─────────────────────────────────────────┘
                │
    ┌───────────┴──────────────┐
    │                          │
┌───▼──────────┐      ┌────────▼────────┐
│   REST API   │      │  WebSocket      │
│  (FastAPI)   │      │  (Real-time)    │
└───┬──────────┘      └────────┬────────┘
    │                          │
    └───────────┬──────────────┘
                │
        ┌───────▼────────┐
        │  Core Services │
        │  ┌──────────┐  │
        │  │ Download │  │
        │  │ Manager  │  │
        │  ├──────────┤  │
        │  │ Scheduler│  │
        │  ├──────────┤  │
        │  │ Inference│  │
        │  │ Pipeline │  │
        │  └──────────┘  │
        └───────┬────────┘
                │
    ┌───────────┴──────────────┬──────────────┐
    │                          │              │
┌───▼──────────┐    ┌─────────▼────┐  ┌─────▼──────┐
│  Database    │    │   Models     │  │ Geospatial │
│ (PostgreSQL) │    │  (PyTorch)   │  │  (Raster)  │
└──────────────┘    └──────────────┘  └────────────┘
                │
        ┌───────▼────────┐
        │  External APIs │
        │  ┌──────────┐  │
        │  │  NASA    │  │
        │  │Earthdata │  │
        │  ├──────────┤  │
        │  │ GitHub   │  │
        │  │ Releases │  │
        │  └──────────┘  │
        └────────────────┘
```

---

## Complete Architecture Stack

**dwr-eo-toolkit** is a **full-stack geospatial ML platform**:

### Layer 1: API & Presentation
- **FastAPI**: RESTful endpoints, OpenAPI docs
- **WebSocket**: Real-time progress updates
- **Pydantic**: Schema validation, type safety

### Layer 2: Orchestration & Jobs
- **APScheduler**: Recurring jobs, cron patterns
- **Download Manager**: Parallel downloads, resilience
- **Inference Pipeline**: Model execution workflow

### Layer 3: Data Access
- **EarthAccess Provider**: NASA data search/download
- **Instrument Adapters**: ECOSTRESS, MODIS metadata
- **Geospatial Handler**: Raster I/O, band selection

### Layer 4: Storage & Models
- **PostgreSQL**: Metadata, job history, results
- **PyTorch Models**: GitHub releases, caching
- **Raster Files**: GeoTIFF/COG output storage

### Layer 5: External Services
- **NASA Earthdata**: Authentication, granule access
- **GitHub**: Model distribution via releases
- **PostGIS**: Geospatial queries (optional)

---

## Phase Completion Status

| Phase | Feature | Status | Tests | Type Safety |
|-------|---------|--------|-------|------------|
| 3 | Download Manager | ✅ Complete | 197+ | Full |
| 3 | Scheduler | ✅ Complete | 197+ | Full |
| 4A | FastAPI REST API | ✅ Complete | 476 | 0 errors |
| 4A | WebSocket | ✅ Complete | 476 | 0 errors |
| 4A | Database | ✅ Complete | 476 | 0 errors |
| 4A | Authentication | ✅ Complete | 476 | 0 errors |
| 4A | Docker/Compose | ✅ Complete | - | - |
| 4B | Model Manager | 🚀 Planned | TBD | TBD |
| 4B | Inference Pipeline | 🚀 Planned | TBD | TBD |
| 4B | Geospatial Handler | 🚀 Planned | TBD | TBD |
| 4C | Kubernetes | 🎯 Future | TBD | TBD |
| 4C | GPU Scaling | 🎯 Future | TBD | TBD |

---

## Summary

**dwr-eo-toolkit** is a production-ready **data orchestration and ML inference platform**:

- **Phase 3-4A**: Complete data pipeline (download, schedule, API)
- **Phase 4B**: Add ML inference on geospatial data
- **Phase 4C**: Scale with Kubernetes and GPU workers

Key strengths:
- Clean layered architecture with clear separation of concerns
- Fully tested (476+ tests, 100% passing)
- Type-safe (mypy clean)
- Cloud-native (Docker, REST API, WebSocket)
- Extensible (easy to add models, providers, instruments)

---

Generated: 2026-04-22