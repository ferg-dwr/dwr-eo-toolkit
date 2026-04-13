# nasa-eo-data

A Python package for DWR employees to programmatically query and download NASA satellite imagery at scale.

Query ECOSTRESS thermal data, MODIS reflectance, and other Earth observation datasets from the comfort of your Python scripts.

## Status

🚀 **Phase 1 Core Foundation Complete** - Authentication and HTTP client ready
- [x] Secure authentication (NASA Earthdata Login)
- [x] Authenticated HTTP client with retry logic
- [x] CMR API integration
- [x] Full test suite (62 tests, 92%+ coverage)
- [ ] Provider abstraction layer (WIP Phase 2A)
- [ ] Query filters and composable API (Phase 2B)
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
from nasa_eo_data.core.client import CMRClient

# Authenticate
auth = EarthDataLoginAuth()

# Create CMR client
client = CMRClient(auth_handler=auth)

# Search for granules
results, total = client.search(
    "search/granules",
    {
        "short_name": "MODIS_TERRA_L2",
        "bounding_box": "-120,30,-100,40",  # [min_lon, min_lat, max_lon, max_lat]
        "temporal": ["2023-01-01T00:00:00Z", "2023-12-31T23:59:59Z"],
        "page_size": 2000,
    },
    max_results=10000,
)

print(f"Found {total} granules")
for granule in results:
    print(f"  {granule['umm']['RelatedUrls']}")
```

---

## Architecture

### Current (Phase 1)

```
┌─────────────────────────────────────────┐
│   Your Script                           │
└────────────┬────────────────────────────┘
             │
┌────────────▼──────────────────────────┐
│ EarthDataLoginAuth                     │ ← Handles all credential sources
│ ├─ TokenProvider (env var)             │
│ ├─ EnvironmentProvider (username/pwd)  │
│ └─ NetrcProvider (.netrc file)         │
└────────────┬──────────────────────────┘
             │
┌────────────▼──────────────────────────┐
│ HTTPClient / CMRClient                 │ ← Authenticated requests + retries
│ ├─ Token caching (1 hour)              │
│ ├─ Exponential backoff                 │
│ ├─ Rate limit handling (429)           │
│ └─ Error handling                      │
└────────────┬──────────────────────────┘
             │
     ┌───────▼────────┐
     │  NASA Earthdata│
     │  CMR API       │
     └────────────────┘
```

### Future (Phases 2-4)

```
Your Script
    ↓
High-Level Query API (Phase 4)
    ↓
Provider Abstraction (Phase 2A)
├─ CMRProvider
├─ LPDaacProvider  
└─ NsidcProvider
    ↓
Composable Filters (Phase 2B)
├─ Spatial (bounding box, polygon, point+radius)
├─ Temporal (date range)
├─ Product-specific
└─ Cloud cover, quality flags
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

### Phase 1 (Current)
- Any dataset queryable via CMR API
- Example: MODIS, VIIRS, Landsat, etc.

### Phase 2 (Coming Soon)
- **ECOSTRESS** - Thermal imagery for water resource monitoring ⭐
- MODIS (Terra/Aqua)
- VIIRS (S-NPP, NOAA-20)
- Landsat (8, 9)

### Planned
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
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_auth.py -v

# With coverage report
pytest tests/ --cov=src/nasa_eo_data --cov-report=html
open htmlcov/index.html
```

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
│       └── core/
│           ├── __init__.py
│           ├── auth.py               # Authentication
│           └── client.py             # HTTP & CMR clients
├── tests/
│   ├── conftest.py                   # Shared fixtures
│   ├── test_auth.py                  # Auth tests (20+)
│   └── test_client.py                # Client tests (40+)
├── examples/
│   └── auth_and_client.py            # Usage examples
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

## Use Cases

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

### Authentication

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

### Phase 2 (Next 2-3 weeks)
- [ ] Provider abstraction layer (CMRProvider, LPDaacProvider, etc.)
- [ ] Composable query filters (spatial, temporal, product-specific)
- [ ] ECOSTRESS-specific metadata and constants

### Phase 3 (Weeks 4-5)
- [ ] Batch download manager with progress tracking
- [ ] Parallel download support
- [ ] Resume capability for interrupted downloads
- [ ] Checksum validation

### Phase 4 (Week 6)
- [ ] High-level query API (`EarthObservationDataAccess`)
- [ ] Simple one-liner queries
- [ ] Automatic format conversions
- [ ] Integration tests with real NASA APIs

See [FEATURE_ROADMAP.md](./FEATURE_ROADMAP.md) for detailed plans.

---

## Citation

If you use this package in research, please cite:

```bibtex
@software{nasa_eo_data,
  title={nasa-eo-data: NASA Earth Observation Data Access for Python},
  author={Your Name},
  year={2024},
  url={https://github.com/your-org/nasa-eo-data}
}
```

---

**Built with ❤️ for water resource monitoring and Earth observation.**