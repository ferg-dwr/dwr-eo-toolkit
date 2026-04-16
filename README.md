# dwr-eo-toolkit

A Python package for DWR employees to programmatically query and download NASA satellite imagery at scale.

Query ECOSTRESS thermal data, MODIS reflectance, and other Earth observation datasets from the comfort of your Python scripts.

## Status

🚀 **Phase 2B Complete** - Provider abstraction and filter layer ready
- [x] Secure authentication (NASA Earthdata Login)
- [x] Authenticated HTTP client with retry logic
- [x] EarthAccess integration
- [x] Full test suite (100+ tests, 100% passing)
- [x] Provider abstraction layer (Phase 2A ✅)
- [x] Query filters and composable API (Phase 2B ✅)
- [ ] Batch download manager (Phase 3)
- [ ] High-level query API (Phase 4)

---

## Quick Start

### Installation

```bash
# Clone the repo
git clone https://github.com/your-org/dwr-eo-toolkit.git
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

# Download granules
files = provider.download(results[:10], "./data")
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

## Architecture

### Current (Phase 2B)

```
┌─────────────────────────────────────────┐
│   Your Script                           │
└────────────┬────────────────────────────┘
             │
┌────────────▼──────────────────────────┐
│ High-Level Provider API               │
│ ├─ EarthAccessProvider                │
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
│ HTTPClient                            │ ← Authenticated requests + retries
│ ├─ Token caching (1 hour)             │
│ ├─ Exponential backoff                │
│ ├─ Rate limit handling (429)          │
│ └─ Error handling                     │
└────────────┬──────────────────────────┘
             │
     ┌───────▼──────────┐
     │ NASA EarthAccess │
     │ & Earthdata APIs │
     └───────────────────┘
```

### Instrument Adapters

Metadata and product-specific constants are provided via instrument adapters:
```
providers/
├── base.py                  # BaseProvider abstract class
├── earthaccess_provider.py  # EarthAccessProvider implementation
├── adapters/
│   ├── base.py              # InstrumentAdapter abstract base
│   ├── ecostress.py         # ECOSTRESS metadata & constants
│   └── modis.py             # MODIS metadata & constants
└── __init__.py
```

### Full Vision (Phases 3-4)

```
Your Script
    ↓
High-Level Query API (Phase 4)
    ↓
Provider Abstraction + Adapters (Phase 2C ✅)
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

### Current
- **ECOSTRESS** - Thermal imagery for water resource monitoring ⭐
- **MODIS** (Terra/Aqua)
- **VIIRS** (S-NPP, NOAA-20)
- **Landsat** (8, 9)
- Any dataset available via NASA Earthdata

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

### Data Access
- ✅ Granule search via EarthAccess
- ✅ Collection search
- ✅ Pagination support
- ✅ Metadata extraction
- ✅ Request ID tracking

### Error Handling
- ✅ Specific exceptions (`AuthenticationError`, `RateLimitError`, `APIError`)
- ✅ Graceful degradation
- ✅ Detailed error messages

### Testing
- ✅ 100+ comprehensive unit tests
- ✅ 90%+ code coverage
- ✅ GitHub Actions CI/CD
- ✅ Multi-version testing (Python 3.11, 3.12)

---

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_providers.py -v   # Provider tests
pytest tests/test_filters.py -v     # Filter tests
pytest tests/test_auth.py -v        # Auth tests
pytest tests/test_client.py -v      # Client tests

# With coverage report
pytest tests/ --cov=src/dwr_eo_toolkit --cov-report=html
open htmlcov/index.html
```

### Project Structure

```
dwr-eo-toolkit/
├── .github/
│   └── workflows/tests.yml          # GitHub Actions CI/CD
├── .gitignore                        # Git ignore rules
├── pyproject.toml                    # Package config
├── README.md                         # This file
├── src/
│   └── dwr_eo_toolkit/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── auth.py               # Authentication
│       │   ├── client.py             # HTTP client
│       │   └── exceptions.py         # Custom exceptions
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py               # BaseProvider abstract class
│       │   ├── earthaccess_provider.py  # EarthAccessProvider
│       │   └── adapters/             # Instrument adapters
│       │       ├── base.py           # InstrumentAdapter base
│       │       ├── ecostress.py      # ECOSTRESS adapter
│       │       └── modis.py          # MODIS adapter
│       ├── filters/
│       │   ├── __init__.py
│       │   ├── base.py               # BaseFilter abstract class
│       │   ├── spatial.py            # Bounding box, polygon filters
│       │   ├── temporal.py           # Date range filters
│       │   ├── product.py            # Product-specific filters
│       │   └── query.py              # Query builder
│       ├── downloads/
│       │   ├── __init__.py
│       │   ├── manager.py            # Download manager
│       │   ├── session.py            # Download session
│       │   └── progress.py           # Progress tracking
│       └── __init__.py
├── tests/
│   ├── conftest.py                   # Shared fixtures
│   ├── test_auth.py                  # Auth tests
│   ├── test_client.py                # Client tests
│   ├── test_providers.py             # Provider tests
│   ├── test_filters.py               # Filter tests
│   └── test_downloads.py             # Download tests
├── examples/
│   ├── search_and_download.py
│   ├── example_full_workflow.py
│   └── testing_query.py
├── docs/
│   ├── authentication.md
│   ├── examples.md
│   └── index.md
└── LICENSE
```

---

## Use Cases

### Water Resource Monitoring (DWR)

Query thermal imagery to monitor:
- Water surface temperatures
- Agricultural irrigation
- Reservoir levels
- Groundwater indicators
- Climate change impacts

```python
# Example: Monitor California Central Valley
provider = EarthAccessProvider()

results, total = provider.search(
    product="ECOSTRESS",
    bounding_box=(-121.0, 35.5, -119.0, 37.5),
    start_date="2024-01-01",
    end_date="2024-12-31",
)

print(f"Found {total} thermal imagery granules for monitoring region")

# Get product metadata
metadata = provider.get_metadata("ECOSTRESS")
print(f"Resolution: {metadata['spatial_resolution']}")
print(f"Temporal frequency: {metadata['temporal_resolution']}")
```

### Climate Research

Track changes in snow cover, vegetation, albedo, etc. across multiple sensors.

### Agriculture

Monitor crop health, irrigation patterns, and drought conditions.

### Disaster Response

Rapid assessment of floods, wildfires, and other emergencies.

---

## API Documentation

### EarthAccessProvider

```python
from dwr_eo_toolkit.providers import EarthAccessProvider

# Initialize provider (auto-authenticates)
provider = EarthAccessProvider()

# Search for granules
results, total = provider.search(
    product="ECOSTRESS",  # Product keyword
    bounding_box=(-122.82, 36.78, -120.94, 38.25),
    start_date="2020-01-01",
    end_date="2026-04-13",
)

print(f"Found {total} granules")

# Get product metadata
metadata = provider.get_metadata("ECOSTRESS")
print(metadata)  # Short name, description, provider, etc.

# Download granules
files = provider.download(results, "./data", max_workers=4)
```

### Composable Query Filters

```python
from dwr_eo_toolkit.filters import Query
from dwr_eo_toolkit.filters import BoundingBox, DateRange

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

### Authentication

```python
from dwr_eo_toolkit.core.auth import EarthDataLoginAuth

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
from dwr_eo_toolkit.core.client import HTTPClient

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
with HTTPClient(auth_handler=auth, base_url="https://api.example.com") as client:
    response = client.get("endpoint")
# Session automatically closed
```

---

## Troubleshooting

### Authentication Failures

```python
# Check which credential source is being used
from dwr_eo_toolkit.core.auth import EarthDataLoginAuth

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

### Search Not Returning Results

1. Verify dataset name with the NASA Earthdata search
2. Check temporal format: `YYYY-MM-DD`
3. Verify bounding box: `[min_lon, min_lat, max_lon, max_lat]`

---

## Performance Tips

1. **Use reasonable page sizes** - Reduces API calls
2. **Set max_results limit** - Avoid fetching millions of granules
3. **Cache results** - Save JSON locally if re-querying
4. **Use temporal filters** - Narrow date ranges when possible
5. **Parallelize downloads** - Use `max_workers` parameter

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
- [EarthAccess Documentation](https://nsidc.org/earthaccess/)
- [ECOSTRESS Data](https://lpdaac.usgs.gov/products/eco_l2t_lste/)
- [MODIS Data](https://lpdaac.usgs.gov/products/mod09ga/)
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
- [x] Provider abstraction layer
- [x] EarthAccess integration
- [x] Composable query filters (spatial, temporal, product-specific)
- [x] Query builder with fluent API
- [x] 100+ comprehensive tests (100% passing)
- [x] Full documentation
- [x] Instrument metadata adapters

### Phase 3 (Next)
- [ ] Batch download manager with progress tracking
- [ ] Parallel download support
- [ ] Resume capability for interrupted downloads
- [ ] Checksum validation

### Phase 4 (Future)
- [ ] High-level query API (`EarthObservationDataAccess`)
- [ ] Simple one-liner queries
- [ ] Automatic format conversions
- [ ] Integration tests with real NASA APIs

---

## Authentication

### Getting Your NASA Earthdata Token

1. Create account at: https://urs.earthdata.nasa.gov
2. Go to: Settings → Applications → Authorized Apps
3. Create new token
4. Set environment variable:
```bash
   export EARTHDATA_TOKEN="your_token_here"
```

### For Docker Users

1. Create Docker Hub account: https://hub.docker.com
2. Go to: Settings → Security → Access Tokens
3. Create new token (read & write)
4. Set environment variable:
```bash
   export DOCKER_PASSWORD="your_token"
```

### Running the Code

```bash
# Set your tokens
export EARTHDATA_TOKEN="your_earthdata_token"

# Run code
python examples/download_imagery.py
```

**Note:** You must create your own tokens. We do not share ours.


## Citation

If you use this project in your research, please cite both this package and earthaccess:

```bibtex
@software{dwr_eo_toolkit,
  title={dwr-eo-toolkit: NASA Earth Observation Data Access for Python},
  author={Romero Galvan, Fernando Emiliano},
  year={2026},
  url={https://github.com/yourusername/dwr-eo-toolkit},
  doi={0000-0003-0664-8169},
  orcid={YOUR-ORCID-HERE},
  note={Wrapper around NASA's earthaccess library}
}

@software{earthaccess,
  title={earthaccess: Simplifying NASA Earth Observational Data Discovery and Access},
  author={NASA NSIDC DAAC and Contributors},
  year={2023},
  url={https://github.com/nsidc/earthaccess},
  doi={10.5281/zenodo.8368432}
}
```

## Acknowledgments
This project is built on NASA's excellent [earthaccess](https://github.com/nsidc/earthaccess) library.

---

**Built with ❤️ for water resource monitoring and Earth observation.**