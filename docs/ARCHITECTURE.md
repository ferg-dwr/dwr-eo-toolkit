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

## Future Architecture Considerations

### Phase 4: Web API Layer
```
FastAPI Application
    ├─ /search - Query API
    ├─ /download - Download API
    ├─ /status - Download status
    └─ /results - Download results
```

### Phase 5: Asynchronous Downloads
```
Celery Task Queue
    ├─ Search tasks
    ├─ Download tasks
    └─ Post-processing tasks
```

### Phase 6: Database Integration
```
PostgreSQL
    ├─ Granule metadata cache
    ├─ Download history
    └─ User preferences
```

---

## Summary

**dwr-eo-toolkit** follows a **layered architecture**:

1. **Presentation Layer**: User API (search, download)
2. **Provider Layer**: Abstract data source interface
3. **Adapter Layer**: Instrument-specific logic
4. **Service Layer**: Download management, filtering
5. **Core Layer**: Authentication, HTTP, exceptions
6. **External Layer**: NASA APIs, earthaccess

---

Generated: 2026-04-16