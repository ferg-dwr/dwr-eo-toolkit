# nasa-eo-data

A Python package for DWR employees to programmatically query and download NASA satellite imagery at scale.

Query ECOSTRESS thermal data, MODIS reflectance, and other Earth observation datasets from the comfort of your Python scripts.

## Status

🚀 **Phase 2B Complete** - Provider abstraction and filter layer ready
- [x] Secure authentication (NASA Earthdata Login)
- [x] Authenticated HTTP client with retry logic
- [x] CMR API integration
- [x] Full test suite (156 tests, 100% passing)
- [x] Provider abstraction layer (Phase 2A ✅)
- [x] Query filters and composable API (Phase 2B ✅)
- [ ] Batch download manager (Phase 3)
- [ ] High-level query API (Phase 4)

---

## Quick Start

### Installation

```bash
# Clone the repo
git clone https://github.com/your-org/nasa-eo-data.git
cd nasa-eo-data

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
from nasa_eo_data.core.auth import EarthDataLoginAuth
from nasa_eo_data.providers import CMRProvider

# Authenticate
auth = EarthDataLoginAuth()

# Create provider
provider = CMRProvider(auth)

# Search for ECOSTRESS thermal data
results, total = provider.search(
    product="ECOSTRESS",
    bounding_box=(-122.82, 36.78, -120.94, 38.25),  # California
    start_date="2020-01-01",
    end_date="2026-04-13",
)

print(f"Found {total} granules")
for granule in results[:5]:
    print(f"  {granule['umm']['GranuleUR']}")
```

**With Composable Filters:**

```python
from nasa_eo_data.filters import Query, BoundingBox, DateRange

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

## Architecture

### Current (Phase 2B)

```
┌─────────────────────────────────────────┐
│   Your Script                           │
└────────────┬────────────────────────────┘
             │
┌────────────▼──────────────────────────┐
│ High-Level Provider API (Phase 2B)    │
│ ├─ CMRProvider (search & metadata)    │
│ └─ BaseProvider (abstract interface)  │
└────────────┬──────────────────────────┘
             │
┌────────────▼──────────────────────────┐
│ Composable Query Filters (Phase 2B)   │
│ ├─ Spatial (bounding box, polygon)    │
│ ├─ Temporal (date ranges)             │
│ ├─ Product-specific (cloud cover)     │
│ └─ Query builder (fluent API)         │
└────────────┬──────────────────────────┘
             │
┌────────────▼──────────────────────────┐
│ EarthDataLoginAuth                    │ ← Handles all credential sources
│ ├─ TokenProvider (env var)            │
│ ├─ EnvironmentProvider (username/pwd) │
│ └─ NetrcProvider (.netrc file)        │
└────────────┬──────────────────────────┘
             │
┌────────────▼──────────────────────────┐
│ HTTPClient / CMRClient                │ ← Authenticated requests + retries
│ ├─ Token caching (1 hour)             │
│ ├─ Exponential backoff                │
│ ├─ Rate limit handling (429)          │
│ └─ Error handling                     │
└────────────┬──────────────────────────┘
             │
     ┌───────▼────────┐
     │  NASA Earthdata│
     │  CMR API       │
     └────────────────┘
```

### Future (Phase 2C)

Adapter pattern for instrument-specific logic:
```
providers/
├── cmr_provider.py          # Generic CMR interface
└── cmr_adapters/
    ├── base.py              # Abstract adapter
    ├── ecostress.py         # ECOSTRESS-specific logic
    ├── modis.py             # MODIS-specific logic
    └── landsat.py           # Landsat-specific logic
```

### Full Vision (Phases 3-4)

```
Your Script
    ↓
High-Level Query API (Phase 4)
    ↓
Provider Abstraction + Adapters (Phase 2C)
    ↓
Composable Filters (Phase 2B) ✅
    ↓
Download Manager (Phase 3)
├─ Parallel downloads
├─ Progress tracking
├─ Resume capability
└─ Checksum validation
    ↓
NASA Earth Observation APIs
```

---

## Supported Datasets

### Phase 2B (Current)
- **ECOSTRESS** - Thermal imagery for water resource monitoring ⭐
- **MODIS** (Terra/Aqua)
- **VIIRS** (S-NPP, NOAA-20)
- **Landsat** (8, 9)
- Any dataset queryable via CMR API

### Phase 2C (Coming Soon)
- Instrument-specific metadata and adapters
- Expanded ECOSTRESS functionality
- MODIS product variants

### Planned (Phase 3+)
- Sentinel-1, Sentinel-2
- Planet Labs
- Custom data providers

---

## Features

### Authentication
- ✅ Secure credential management
- ✅ Multiple auth sources (tokens, env vars, .netrc)
- ✅ Automatic token caching (1 hour)
- ✅ Automatic token refresh

### HTTP Client
- ✅ Exponential backoff retry strategy
- ✅ Rate limit handling (HTTP 429)
- ✅ Automatic authentication header injection
- ✅ Request/response logging
- ✅ Timeout management
- ✅ Context manager support

### CMR API
- ✅ Granule search
- ✅ Collection search
- ✅ Pagination (search-after)
- ✅ CMR metadata extraction
- ✅ Request ID tracking

### Error Handling
- ✅ Specific exceptions (`AuthenticationError`, `RateLimitError`, `APIError`)
- ✅ Graceful degradation
- ✅ Detailed error messages

### Testing
- ✅ 62 comprehensive unit tests
- ✅ 92%+ code coverage
- ✅ GitHub Actions CI/CD
- ✅ Multi-version testing (Python 3.11, 3.12)

---

## Development

### Running Tests

```bash
# All tests (156 total)
pytest tests/ -v

# Specific test file
pytest tests/test_providers.py -v   # Provider tests
pytest tests/test_filters.py -v     # Filter tests
pytest tests/test_auth.py -v        # Auth tests
pytest tests/test_client.py -v      # Client tests

# With coverage report
pytest tests/ --cov=src/nasa_eo_data --cov-report=html
open htmlcov/index.html
```

**Current Test Results:**
- ✅ 156 / 156 tests passing (100%)
- ✅ 14 tests fixed in Phase 2B
- ✅ Authentication tests: 14
- ✅ Client tests: 29
- ✅ Provider tests: 32
- ✅ Filter tests: 62
- ✅ Filter composition tests: 5

### Project Structure

```
nasa-eo-data/
├── .github/
│   └── workflows/tests.yml          # GitHub Actions CI/CD
├── .gitignore                        # Git ignore rules
├── pyproject.toml                    # Package config
├── README.md                         # This file
├── src/
│   └── nasa_eo_data/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── auth.py               # Authentication
│       │   └── client.py             # HTTP & CMR clients
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py               # BaseProvider abstract class
│       │   ├── cmr_provider.py       # CMRProvider implementation
│       │   └── cmr_adapters/         # Future: instrument adapters
│       └── filters/
│           ├── __init__.py
│           ├── base.py               # BaseFilter abstract class
│           ├── spatial.py            # Bounding box, polygon filters
│           ├── temporal.py           # Date range filters
│           ├── product.py            # Product-specific filters
│           └── query.py              # Query builder
├── tests/
│   ├── conftest.py                   # Shared fixtures
│   ├── test_auth.py                  # Auth tests (14+)
│   ├── test_client.py                # Client tests (29+)
│   ├── test_providers.py             # Provider tests (32+)
│   └── test_filters.py               # Filter tests (62+)
├── examples/
│   ├── auth_and_client.py            # Phase 1 example
│   └── full_workflow.py              # Phase 2B example (ECOSTRESS)
└── docs/                             # Documentation (future)
```

### Code Standards

- **Language:** Python 3.11+
- **Style:** PEP 8 (enforced via type hints)
- **Testing:** pytest + fixtures
- **Coverage:** Aim for 90%+
- **Type Hints:** Fully typed
- **Documentation:** Docstrings on all public APIs

### Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and add tests
3. Run tests locally: `pytest tests/ -v`
4. Push and create a pull request
5. GitHub Actions will auto-test on Python 3.11+

---

## Phase 2B Highlights

### CMR API Issues Fixed
During Phase 2B implementation, we discovered and fixed several undocumented CMR API behaviors:

1. **Collections endpoint** - Public endpoint that rejects bearer tokens (now uses `requests.get()` without auth)
2. **Granule search parameters** - Requires `short_name` not `keyword`
3. **Pagination** - Uses `page_num` not `search-after` cursor
4. **Response format** - Returns `feed.entry` not `items`
5. **Cloud cover filtering** - Not supported on granules endpoint (workaround provided)

These are now properly handled in `CMRProvider`. See [ISSUE_RESOLUTION_DETAILED.md](./docs/ISSUE_RESOLUTION_DETAILED.md) for technical details.

### Test Suite Completion
- **Before:** 142 passing, 14 failing (91%)
- **After:** 156 passing, 0 failing (100%) ✅
- All failures due to test mocking patterns, now fixed

---

### Water Resource Monitoring (DWR)

Query thermal imagery to monitor:
- Water surface temperatures
- Agricultural irrigation
- Reservoir levels
- Groundwater indicators
- Climate change impacts

```python
# Future example (Phase 4):
eo = EarthObservationDataAccess(auth)
thermal_data = eo.query_ecostress(
    roi="California Central Valley",
    start_date="2024-01-01",
    end_date="2024-12-31",
    product="L2_LSTE",  # Land Surface Temperature & Emissivity
    max_cloud_cover=10,
    output_dir="/data/ecostress/",
)
```

### Climate Research

Track changes in snow cover, vegetation, albedo, etc. across multiple sensors.

### Agriculture

Monitor crop health, irrigation patterns, and drought conditions.

### Disaster Response

Rapid assessment of floods, wildfires, and other emergencies.

---

## API Documentation

### CMRProvider (Phase 2B)

```python
from nasa_eo_data.core.auth import EarthDataLoginAuth
from nasa_eo_data.providers import CMRProvider

# Initialize provider
auth = EarthDataLoginAuth()
provider = CMRProvider(auth)

# Search for granules
results, total = provider.search(
    product="ECOSTRESS",  # Product keyword or short_name
    bounding_box=(-122.82, 36.78, -120.94, 38.25),
    start_date="2020-01-01",
    end_date="2026-04-13",
)

print(f"Found {total} granules")
for granule in results:
    print(f"  {granule['umm']['GranuleUR']}")

# Get product metadata
metadata = provider.get_metadata("ECOSTRESS")
print(metadata)  # Short name, description, provider, etc.

# Validate product
is_valid = provider.validate_product("ECOSTRESS")
```

### Composable Query Filters (Phase 2B)

```python
from nasa_eo_data.filters import Query
from nasa_eo_data.filters import BoundingBox, DateRange

# Build query fluently
query = (
    Query()
    .with_product("ECOSTRESS")
    .with_spatial_bounds(BoundingBox(-122.82, 36.78, -120.94, 38.25))
    .with_date_range(DateRange("2020-01-01", "2026-04-13"))
)

# Execute on provider
results, total = query.execute(provider)

# Or add more filters
query.with_cloud_cover(max=20)
results, total = query.execute(provider)
```

### Authentication (Phase 1)

```python
from nasa_eo_data.core.auth import EarthDataLoginAuth

# Initialize (tries token → .netrc → env vars in order)
auth = EarthDataLoginAuth()

# Get bearer token
token = auth.get_bearer_token()

# Setup credentials if needed
auth.setup_environment(username="user", password="pass")
auth.setup_netrc(username="user", password="pass")

# Clear cache
auth.clear_cache()
```

### HTTP Client

```python
from nasa_eo_data.core.client import HTTPClient

client = HTTPClient(
    auth_handler=auth,
    base_url="https://api.example.com",
    timeout=30,
    max_retries=3,
)

# Make requests
response = client.get("endpoint", params={"key": "value"})
response = client.post("endpoint", json={"data": "value"})

# Use as context manager
with HTTPClient(auth_handler=auth) as client:
    response = client.get("endpoint")
# Session automatically closed
```

### CMR Client

```python
from nasa_eo_data.core.client import CMRClient

client = CMRClient(auth_handler=auth)

# Search granules
results, total = client.search(
    "search/granules",
    {
        "short_name": "MODIS_TERRA_L2",
        "bounding_box": "-120,30,-100,40",
        "temporal": ["2023-01-01T00:00:00Z", "2023-12-31T23:59:59Z"],
    },
    page_size=2000,
    max_results=10000,
)

# Get metadata
results, metadata = client.get_with_metadata(endpoint, params)
print(metadata["CMR-Hits"])  # Total granules
print(metadata["CMR-Request-Id"])  # For support requests
```

---

## Troubleshooting

### Authentication Failures

```python
# Check which credential source is being used
from nasa_eo_data.core.auth import EarthDataLoginAuth

auth = EarthDataLoginAuth()
try:
    token = auth.get_bearer_token()
    print(f"Got token: {token[:20]}...")
except AuthenticationError as e:
    print(f"Auth failed: {e}")
```

### Rate Limiting

The client automatically handles rate limiting (HTTP 429) with exponential backoff. If you hit hard limits:

```python
# Reduce concurrent requests or add delays
import time
for result in results:
    process(result)
    time.sleep(1)  # 1 second between requests
```

### CMR Search Not Returning Results

1. Verify dataset name: https://cmr.earthdata.nasa.gov/search/site/collections.json?keyword=your-dataset
2. Check temporal format: `YYYY-MM-DDTHH:MM:SSZ`
3. Verify bounding box: `[min_lon, min_lat, max_lon, max_lat]`

---

## Performance Tips

1. **Use page_size=2000** - Reduces API calls
2. **Set max_results limit** - Avoid fetching millions of granules
3. **Cache results** - Save JSON locally if re-querying
4. **Use temporal filters** - Narrow date ranges when possible
5. **Parallelize downloads** - Phase 3 will support this

---

## Security Notes

⚠️ **Never commit credentials to Git:**
- Don't hardcode passwords
- Don't commit `.netrc` files
- Don't commit `.env` files
- Use environment variables or `.netrc` (mode 0600)

✅ **Best practices:**
- Use pre-generated tokens (60-day validity)
- Rotate credentials regularly
- Use `.gitignore` to exclude credential files
- Enable branch protection on GitHub

---

## References

- [NASA Earthdata Login](https://urs.earthdata.nasa.gov/)
- [CMR API Documentation](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)
- [ECOSTRESS Data](https://lpdaac.usgs.gov/products/ecostressL2tir/)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
- [pytest Documentation](https://docs.pytest.org/)

---

## License

[Add your license here - e.g., MIT, Apache 2.0, etc.]

## Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues, questions, or feature requests:
- 📧 Open an issue on GitHub
- 📚 Check the docs
- 🔍 Search closed issues for similar problems

---

## Roadmap

### Phase 2B ✅ (Complete)
- [x] Provider abstraction layer (CMRProvider)
- [x] Composable query filters (spatial, temporal, product-specific)
- [x] Query builder with fluent API
- [x] CMR API integration with proper pagination
- [x] 156 comprehensive tests (100% passing)
- [x] Full documentation

### Phase 2C (Next 1-2 weeks)
- [ ] Adapter pattern for instrument-specific logic
- [ ] ECOSTRESS-specific metadata and constants
- [ ] MODIS product variants
- [ ] Expanded filter support

### Phase 3 (Weeks 3-4)
- [ ] Batch download manager with progress tracking
- [ ] Parallel download support
- [ ] Resume capability for interrupted downloads
- [ ] Checksum validation

### Phase 4 (Week 5)
- [ ] High-level query API (`EarthObservationDataAccess`)
- [ ] Simple one-liner queries
- [ ] Automatic format conversions
- [ ] Integration tests with real NASA APIs

See [PHASE_2B_SUMMARY.md](./docs/PHASE_2B_SUMMARY.md) for Phase 2B completion details (all files in `/docs/` after merge).

**See [FEATURE_ROADMAP.md](./FEATURE_ROADMAP.md) for detailed plans.**

---

## Citation

If you use this package in research, please cite:

```bibtex
@software{nasa_eo_data,
  title={nasa-eo-data: NASA Earth Observation Data Access for Python},
  author={Fernando E. Romero Galvan},
  year={2026},
  url={https://github.com/your-org/nasa-eo-data}
}
```

---

**Built with ❤️ for water resource monitoring and Earth observation.**
