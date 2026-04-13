"""
Pytest configuration and shared fixtures.

This file is automatically loaded by pytest and provides:
- Shared fixtures for auth and clients
- Pytest plugins and configuration
- Mock helpers
"""

import pytest
import logging
from unittest.mock import Mock

from nasa_eo_data.core.auth import EarthDataLoginAuth
from nasa_eo_data.core.client import HTTPClient, CMRClient


@pytest.fixture
def caplog_debug(caplog):
    """Fixture to capture DEBUG level logs."""
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def mock_auth():
    """
    Provide a mock EarthDataLoginAuth for tests.
    
    Returns a Mock with:
    - get_bearer_token() returning a test token
    - Other methods callable but not configured
    """
    auth = Mock(spec=EarthDataLoginAuth)
    auth.get_bearer_token.return_value = "test_bearer_token_12345"
    return auth


@pytest.fixture
def http_client(mock_auth):
    """
    Provide a real HTTPClient with mock auth.
    
    Use this when you want to test HTTPClient methods
    but don't want to deal with actual authentication.
    """
    return HTTPClient(
        auth_handler=mock_auth,
        base_url="https://api.example.com",
        client_id="test-client",
        timeout=10,
    )


@pytest.fixture
def cmr_client(mock_auth):
    """
    Provide a real CMRClient with mock auth.
    
    Use this when testing CMR-specific functionality
    like pagination and metadata extraction.
    """
    return CMRClient(
        auth_handler=mock_auth,
        client_id="test-cmr-client",
    )


@pytest.fixture
def sample_cmr_granule():
    """
    Provide a sample CMR granule for testing.
    
    This represents a typical granule returned by CMR API.
    """
    return {
        "concept_id": "G1234567890-LPDAAC_ECS",
        "native_id": "MODIS_TERRA_L2.A2023001.h00v08.061.2023002120530",
        "umm": {
            "RelatedUrls": [
                {
                    "URL": "https://e4ftl01.cr.usgs.gov/MODIS_TERRA_L2/MODIST_L2.061/2023.01.01/MOD35_L2.A2023001.h00v08.061.2023002120530.hdf",
                    "Type": "GET DATA",
                    "Subtype": "OPENDAP",
                },
                {
                    "URL": "https://search.earthdata.nasa.gov/search/granules/collection-details?p=C1234567890-LPDAAC_ECS&g=G1234567890-LPDAAC_ECS",
                    "Type": "VIEW RELATED INFORMATION",
                    "Subtype": "USER GUIDES",
                }
            ],
            "TemporalExtent": {
                "RangeDateTime": {
                    "BeginningDateTime": "2023-01-01T00:00:00Z",
                    "EndingDateTime": "2023-01-01T04:00:00Z",
                }
            },
            "SpatialExtent": {
                "HorizontalSpatialDomain": {
                    "Geometry": {
                        "BoundingRectangles": [
                            {
                                "WestBoundingCoordinate": -180,
                                "EastBoundingCoordinate": -120,
                                "NorthBoundingCoordinate": 45,
                                "SouthBoundingCoordinate": 0,
                            }
                        ]
                    }
                }
            },
        },
    }


@pytest.fixture
def sample_cmr_collection():
    """
    Provide a sample CMR collection for testing.
    
    This represents a typical collection returned by CMR API.
    """
    return {
        "concept_id": "C1234567890-LPDAAC_ECS",
        "native_id": "MODIS_TERRA_L2",
        "umm": {
            "ShortName": "MODIS_TERRA_L2",
            "Version": "6.1",
            "LongName": "MODIS/Terra Level 2 Cloud Top Properties 5-Min L2 Swath 1km",
            "Abstract": "The MODIS Terra Level 2 Cloud Top Properties dataset...",
            "TemporalExtents": [
                {
                    "RangeDateTime": {
                        "BeginningDateTime": "2000-02-24T00:00:00Z",
                    }
                }
            ],
            "SpatialExtent": {
                "SpatialRepresentation": "CARTESIAN",
                "BoundingRectangles": [
                    {
                        "WestBoundingCoordinate": -180,
                        "EastBoundingCoordinate": 180,
                        "NorthBoundingCoordinate": 90,
                        "SouthBoundingCoordinate": -90,
                    }
                ],
            },
            "RelatedUrls": [
                {
                    "URL": "https://lpdaac.usgs.gov/products/mod35_l2v061/",
                    "Type": "HOMEPAGE",
                }
            ],
        },
    }


@pytest.fixture
def mock_response_success():
    """
    Provide a successful HTTP response mock.
    
    Useful for testing success paths without mocking requests.Session.request.
    """
    from unittest.mock import Mock
    response = Mock()
    response.status_code = 200
    response.headers = {
        "Content-Type": "application/json",
        "CMR-Request-Id": "test-request-123",
    }
    response.text = '{"data": "test"}'
    response.json.return_value = {"data": "test"}
    return response


@pytest.fixture
def mock_response_rate_limit():
    """
    Provide a rate-limited HTTP response mock (429).
    
    Useful for testing rate limit handling without mocking requests.
    """
    from unittest.mock import Mock
    response = Mock()
    response.status_code = 429
    response.headers = {"Retry-After": "60"}
    response.text = "Too Many Requests"
    return response


@pytest.fixture
def mock_response_auth_error():
    """
    Provide an authentication error HTTP response mock (401).
    
    Useful for testing auth error handling.
    """
    from unittest.mock import Mock
    response = Mock()
    response.status_code = 401
    response.headers = {"Content-Type": "application/json"}
    response.text = "Unauthorized: Invalid token"
    return response


# Pytest configuration
def pytest_configure(config):
    """
    Configure pytest with custom markers and settings.
    """
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test (requires API access)"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "auth: mark test as related to authentication"
    )
    config.addinivalue_line(
        "markers",
        "client: mark test as related to HTTP client"
    )
    config.addinivalue_line(
        "markers",
        "cmr: mark test as related to CMR client"
    )


# Markers for organizing tests
pytestmark = []


# Logging configuration for tests
logging.basicConfig(
    level=logging.WARNING,
    format="%(name)s - %(levelname)s - %(message)s",
)
