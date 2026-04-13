"""
Unit tests for provider classes.

Tests cover:
- CMRProvider search functionality
- Metadata retrieval
- Parameter validation
- Error handling
- Date/temporal handling
- Bounding box validation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from nasa_eo_data.providers import BaseProvider, CMRProvider
from nasa_eo_data.core.auth import EarthDataLoginAuth


class TestBaseProvider:
    """Tests for BaseProvider abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Should not be able to instantiate BaseProvider directly."""
        with pytest.raises(TypeError):
            BaseProvider()

    def test_requires_search_implementation(self):
        """Subclass must implement search method."""

        class IncompleteProvider(BaseProvider):
            def get_metadata(self, product):
                pass

            def validate_product(self, product):
                pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_requires_all_abstract_methods(self):
        """Subclass must implement all abstract methods."""

        class AlmostProvider(BaseProvider):
            def search(self, product, **kwargs):
                pass

        with pytest.raises(TypeError):
            AlmostProvider()


class TestCMRProvider:
    """Tests for CMRProvider implementation."""

    @pytest.fixture
    def mock_auth(self):
        """Mock authentication handler."""
        return Mock(spec=EarthDataLoginAuth)

    @pytest.fixture
    def provider(self, mock_auth):
        """CMRProvider instance with mocked auth."""
        with patch("nasa_eo_data.providers.cmr_provider.CMRClient"):
            return CMRProvider(mock_auth)

    def test_initialization(self, mock_auth):
        """Should initialize with auth handler."""
        with patch("nasa_eo_data.providers.cmr_provider.CMRClient"):
            provider = CMRProvider(mock_auth)
            assert provider.auth == mock_auth
            assert provider._product_cache == {}

    # ==================== Search Tests ====================

    def test_search_basic(self, provider):
        """Should search with product name only."""
        mock_results = [{"umm": {"GranuleUR": "granule1"}}]
        provider.cmr_client.search.return_value = (mock_results, 1)

        results, total = provider.search(product="ECOSTRESS_L2_LSTE")

        assert results == mock_results
        assert total == 1
        provider.cmr_client.search.assert_called_once()

    def test_search_with_bounding_box(self, provider):
        """Should search with spatial constraints."""
        mock_results = []
        provider.cmr_client.search.return_value = (mock_results, 0)

        provider.search(
            product="ECOSTRESS_L2_LSTE",
            bounding_box=(-120, 30, -100, 40),
        )

        call_args = provider.cmr_client.search.call_args
        params = call_args[1]["params"]
        assert "bounding_box" in params
        assert params["bounding_box"] == "-120,30,-100,40"

    def test_search_with_date_range(self, provider):
        """Should search with temporal constraints."""
        mock_results = []
        provider.cmr_client.search.return_value = (mock_results, 0)

        provider.search(
            product="ECOSTRESS_L2_LSTE",
            start_date="2023-01-01",
            end_date="2023-12-31",
        )

        call_args = provider.cmr_client.search.call_args
        params = call_args[1]["params"]
        assert "temporal" in params
        assert "2023-01-01T00:00:00Z" in params["temporal"]
        assert "2023-12-31T00:00:00Z" in params["temporal"]

    def test_search_with_iso_dates(self, provider):
        """Should handle ISO format dates."""
        mock_results = []
        provider.cmr_client.search.return_value = (mock_results, 0)

        provider.search(
            product="ECOSTRESS_L2_LSTE",
            start_date="2023-01-01T12:30:45Z",
            end_date="2023-12-31T23:59:59Z",
        )

        call_args = provider.cmr_client.search.call_args
        params = call_args[1]["params"]
        assert "2023-01-01T12:30:45Z" in params["temporal"]
        assert "2023-12-31T23:59:59Z" in params["temporal"]

    def test_search_with_all_parameters(self, provider):
        """Should search with all parameters."""
        mock_results = [{"umm": {}}]
        provider.cmr_client.search.return_value = (mock_results, 1)

        results, total = provider.search(
            product="ECOSTRESS_L2_LSTE",
            bounding_box=(-120, 30, -100, 40),
            start_date="2023-01-01",
            end_date="2023-12-31",
            page_size=2000,
            max_results=10000,
        )

        assert len(results) == 1
        assert total == 1

    def test_search_with_cloud_cover(self, provider):
        """Should filter by cloud cover."""
        mock_results = []
        provider.cmr_client.search.return_value = (mock_results, 0)

        provider.search(
            product="MODIS_TERRA_L2",
            cloud_cover=10,
        )

        call_args = provider.cmr_client.search.call_args
        params = call_args[1]["params"]
        assert "attribute[]" in params

    def test_search_invalid_cloud_cover(self, provider):
        """Should reject invalid cloud cover values."""
        with pytest.raises(ValueError, match="cloud_cover must be 0-100"):
            provider.search(product="MODIS_TERRA_L2", cloud_cover=150)

        with pytest.raises(ValueError, match="cloud_cover must be 0-100"):
            provider.search(product="MODIS_TERRA_L2", cloud_cover=-10)

    # ==================== Bounding Box Validation ====================

    def test_validate_bounding_box_valid(self, provider):
        """Should accept valid bounding boxes."""
        # Should not raise
        provider._validate_bounding_box(-120, 30, -100, 40)
        provider._validate_bounding_box(-180, -90, 180, 90)
        provider._validate_bounding_box(0, 0, 10, 10)

    def test_validate_bounding_box_invalid_longitude(self, provider):
        """Should reject invalid longitude."""
        with pytest.raises(ValueError, match="Longitude must be"):
            provider._validate_bounding_box(-200, 30, -100, 40)

        with pytest.raises(ValueError, match="Longitude must be"):
            provider._validate_bounding_box(-120, 30, 200, 40)

    def test_validate_bounding_box_invalid_latitude(self, provider):
        """Should reject invalid latitude."""
        with pytest.raises(ValueError, match="Latitude must be"):
            provider._validate_bounding_box(-120, -100, -100, 40)

        with pytest.raises(ValueError, match="Latitude must be"):
            provider._validate_bounding_box(-120, 30, -100, 100)

    def test_validate_bounding_box_inverted(self, provider):
        """Should reject inverted bounding boxes."""
        with pytest.raises(ValueError, match="min_lon must be less than max_lon"):
            provider._validate_bounding_box(100, 30, -100, 40)

        with pytest.raises(ValueError, match="min_lat must be less than max_lat"):
            provider._validate_bounding_box(-120, 40, -100, 30)

    # ==================== Date Handling ====================

    def test_normalize_date_yyyy_mm_dd(self, provider):
        """Should convert YYYY-MM-DD to ISO."""
        result = provider._normalize_date("2023-01-15")
        assert result == "2023-01-15T00:00:00Z"

    def test_normalize_date_iso_with_z(self, provider):
        """Should accept ISO format with Z."""
        iso_date = "2023-01-15T12:30:45Z"
        result = provider._normalize_date(iso_date)
        assert result == iso_date

    def test_normalize_date_iso_without_z(self, provider):
        """Should add Z to ISO format if missing."""
        result = provider._normalize_date("2023-01-15T12:30:45")
        assert result == "2023-01-15T12:30:45Z"

    def test_normalize_date_invalid(self, provider):
        """Should reject invalid date formats."""
        with pytest.raises(ValueError, match="Date format not recognized"):
            provider._normalize_date("01/15/2023")

        with pytest.raises(ValueError, match="Date format not recognized"):
            provider._normalize_date("2023-13-01")

    def test_build_temporal_range_both_dates(self, provider):
        """Should build temporal range with both dates."""
        result = provider._build_temporal_range("2023-01-01", "2023-12-31")
        assert "2023-01-01T00:00:00Z" in result
        assert "2023-12-31T00:00:00Z" in result

    def test_build_temporal_range_start_only(self, provider):
        """Should build temporal range with start date only."""
        result = provider._build_temporal_range("2023-01-01", None)
        assert "2023-01-01T00:00:00Z" in result

    def test_build_temporal_range_end_only(self, provider):
        """Should build temporal range with end date only."""
        result = provider._build_temporal_range(None, "2023-12-31")
        assert "2023-12-31T00:00:00Z" in result

    def test_build_temporal_range_neither(self, provider):
        """Should return None with no dates."""
        result = provider._build_temporal_range(None, None)
        assert result is None

    # ==================== Metadata Tests ====================

    def test_get_metadata_success(self, provider):
        """Should retrieve collection metadata."""
        mock_collection = {
            "umm": {
                "ShortName": "ECOSTRESS_L2_LSTE",
                "LongName": "ECOSTRESS Level 2 Land Surface Temperature...",
                "Summary": "Thermal infrared radiances in at-sensor brightness...",
                "Provider": {"ShortName": "LP_DAAC"},
                "ProcessingLevel": {"Id": "2"},
                "DOI": {"DOI": "10.5067/EXAMPLE"},
            }
        }
        provider.cmr_client.search.return_value = ([mock_collection], 1)

        metadata = provider.get_metadata("ECOSTRESS_L2_LSTE")

        assert metadata["short_name"] == "ECOSTRESS_L2_LSTE"
        assert "Thermal infrared" in metadata["description"]
        assert metadata["provider"] == "LP_DAAC"
        assert "10.5067/EXAMPLE" in metadata["doi"]

    def test_get_metadata_not_found(self, provider):
        """Should raise error if product not found."""
        provider.cmr_client.search.return_value = ([], 0)

        with pytest.raises(ValueError, match="not found in CMR"):
            provider.get_metadata("NONEXISTENT_PRODUCT")

    def test_get_metadata_caching(self, provider):
        """Should cache metadata after first retrieval."""
        mock_collection = {
            "umm": {
                "ShortName": "ECOSTRESS_L2_LSTE",
                "LongName": "Test product",
                "Summary": "Test summary",
            }
        }
        provider.cmr_client.search.return_value = ([mock_collection], 1)

        # First call
        metadata1 = provider.get_metadata("ECOSTRESS_L2_LSTE")

        # Second call should use cache
        metadata2 = provider.get_metadata("ECOSTRESS_L2_LSTE")

        assert metadata1 == metadata2
        # Should only call CMR once
        assert provider.cmr_client.search.call_count == 1

    # ==================== Validation Tests ====================

    def test_validate_product_exists(self, provider):
        """Should return True for existing product."""
        mock_collection = {
            "umm": {"ShortName": "ECOSTRESS_L2_LSTE", "LongName": "Test"}
        }
        provider.cmr_client.search.return_value = ([mock_collection], 1)

        result = provider.validate_product("ECOSTRESS_L2_LSTE")
        assert result is True

    def test_validate_product_not_exists(self, provider):
        """Should return False for non-existent product."""
        provider.cmr_client.search.return_value = ([], 0)

        result = provider.validate_product("NONEXISTENT")
        assert result is False

    # ==================== Integration-like Tests ====================

    def test_search_returns_tuple(self, provider):
        """Should return (results, total) tuple."""
        mock_results = [{"id": "granule1"}, {"id": "granule2"}]
        provider.cmr_client.search.return_value = (mock_results, 100)

        results, total = provider.search(product="ECOSTRESS_L2_LSTE")

        assert isinstance(results, list)
        assert isinstance(total, int)
        assert len(results) == 2
        assert total == 100

    def test_search_with_max_results(self, provider):
        """Should respect max_results parameter."""
        provider.cmr_client.search.return_value = ([], 0)

        provider.search(
            product="ECOSTRESS_L2_LSTE",
            max_results=5000,
        )

        call_args = provider.cmr_client.search.call_args
        assert call_args[1]["max_results"] == 5000

    def test_build_search_params_includes_product(self, provider):
        """Should always include product in params."""
        params = provider._build_search_params(product="ECOSTRESS_L2_LSTE")
        assert params["short_name"] == "ECOSTRESS_L2_LSTE"

    def test_build_search_params_minimal(self, provider):
        """Should handle minimal parameters."""
        params = provider._build_search_params(product="ECOSTRESS_L2_LSTE")
        assert "short_name" in params
        assert "bounding_box" not in params
        assert "temporal" not in params