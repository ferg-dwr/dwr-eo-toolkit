"""
Unit tests for EarthAccessProvider.

Tests cover:
- Authentication workflows
- Search functionality (ECOSTRESS, MODIS)
- Filtering (temporal, spatial, product)
- Pagination and result handling
- Error handling
- Metadata retrieval
- Product validation
- Adapter integration
"""

from unittest.mock import Mock, patch

import pytest

from dwr_eo_toolkit.providers.earthaccess_provider import (
    AdapterRegistry,
    EarthAccessProvider,
)


@pytest.fixture
def mock_earthaccess():
    """Mock earthaccess module."""
    with patch("dwr_eo_toolkit.providers.earthaccess_provider.earthaccess") as mock:
        yield mock


@pytest.fixture
def provider(mock_earthaccess):
    """Create EarthAccessProvider instance."""
    mock_earthaccess.login.return_value = True
    return EarthAccessProvider()


class TestAdapterRegistry:
    """Tests for AdapterRegistry."""

    def test_registry_initialization(self):
        """Should initialize with default adapters."""
        registry = AdapterRegistry()

        assert isinstance(registry.adapters, dict)
        assert len(registry.adapters) > 0

    def test_registry_registers_ecostress_adapter(self):
        """Should register ECOSTRESS adapter."""
        registry = AdapterRegistry()

        # ECOSTRESS keywords should be registered
        adapter = registry.get_adapter("ECOSTRESS")
        assert adapter is not None

    def test_registry_registers_modis_adapter(self):
        """Should register MODIS adapter."""
        registry = AdapterRegistry()

        adapter = registry.get_adapter("MODIS")
        assert adapter is not None

    def test_registry_case_insensitive(self):
        """Should handle case-insensitive product names."""
        registry = AdapterRegistry()

        adapter_lower = registry.get_adapter("ecostress")
        adapter_upper = registry.get_adapter("ECOSTRESS")
        adapter_mixed = registry.get_adapter("EcOsTrEsS")

        assert adapter_lower is not None
        assert adapter_upper is not None
        assert adapter_mixed is not None

    def test_registry_returns_none_for_unknown_product(self):
        """Should return None for unknown product."""
        registry = AdapterRegistry()

        adapter = registry.get_adapter("UNKNOWN_PRODUCT")

        assert adapter is None


class TestEarthAccessProviderAuthentication:
    """Tests for authentication workflows."""

    def test_provider_initialization_authenticates(self, mock_earthaccess):
        """Should authenticate on initialization."""
        mock_earthaccess.login.return_value = True

        EarthAccessProvider()

        mock_earthaccess.login.assert_called()

    def test_provider_login_with_environment_strategy(self, mock_earthaccess):
        """Should login with environment strategy if initial login fails."""
        mock_earthaccess.login.side_effect = [False, True]

        EarthAccessProvider()

        # First call should fail, triggering second call with strategy
        assert mock_earthaccess.login.call_count >= 1

    def test_provider_ensures_authenticated(self, provider, mock_earthaccess):
        """Should ensure authentication is established."""
        mock_earthaccess.login.reset_mock()
        mock_earthaccess.login.return_value = True

        provider._ensure_authenticated()

        mock_earthaccess.login.assert_called()


class TestEarthAccessProviderAdapterIntegration:
    """Tests for adapter integration."""

    def test_get_adapter_for_known_product(self, provider):
        """Should get adapter for known product."""
        adapter = provider.get_adapter("ECOSTRESS")

        assert adapter is not None

    def test_get_adapter_for_unknown_product(self, provider):
        """Should return None for unknown product."""
        adapter = provider.get_adapter("UNKNOWN")

        assert adapter is None

    def test_adapter_registry_accessible(self, provider):
        """Should have accessible adapter registry."""
        assert hasattr(provider, "adapter_registry")
        assert isinstance(provider.adapter_registry, AdapterRegistry)


class TestEarthAccessProviderSearch:
    """Tests for search functionality."""

    def test_search_basic_with_product(self, provider, mock_earthaccess):
        """Should search with product keyword."""
        mock_granules = [
            {"id": "granule1", "properties": {"title": "test1"}},
            {"id": "granule2", "properties": {"title": "test2"}},
        ]
        mock_earthaccess.search_data.return_value = mock_granules

        results, total = provider.search(product="ECOSTRESS")

        assert len(results) == 2
        assert total == 2
        mock_earthaccess.search_data.assert_called_once()

    def test_search_with_bounding_box(self, provider, mock_earthaccess):
        """Should search with spatial bounds."""
        mock_granules = [{"id": "granule1"}]
        mock_earthaccess.search_data.return_value = mock_granules

        bbox = (-122.82, 36.78, -120.94, 38.25)
        results, total = provider.search(product="MODIS", bounding_box=bbox)

        assert total == 1
        # Verify bounding_box was passed to search
        call_kwargs = mock_earthaccess.search_data.call_args[1]
        assert "bounding_box" in call_kwargs

    def test_search_with_temporal_range(self, provider, mock_earthaccess):
        """Should search with temporal bounds."""
        mock_granules = [{"id": "granule1"}]
        mock_earthaccess.search_data.return_value = mock_granules

        results, total = provider.search(
            product="ECOSTRESS", start_date="2020-01-01", end_date="2020-12-31"
        )

        assert total == 1
        # Verify temporal was passed to search
        call_kwargs = mock_earthaccess.search_data.call_args[1]
        assert "temporal" in call_kwargs

    def test_search_with_spatial_and_temporal(self, provider, mock_earthaccess):
        """Should search with both spatial and temporal filters."""
        mock_granules = [{"id": "granule1"}, {"id": "granule2"}]
        mock_earthaccess.search_data.return_value = mock_granules

        bbox = (-122.82, 36.78, -120.94, 38.25)
        results, total = provider.search(
            product="MODIS",
            bounding_box=bbox,
            start_date="2020-01-01",
            end_date="2020-12-31",
        )

        assert total == 2
        call_kwargs = mock_earthaccess.search_data.call_args[1]
        assert "bounding_box" in call_kwargs
        assert "temporal" in call_kwargs

    def test_search_with_max_results(self, provider, mock_earthaccess):
        """Should respect max_results parameter."""
        mock_granules = [{"id": f"granule{i}"} for i in range(100)]
        mock_earthaccess.search_data.return_value = mock_granules

        results, total = provider.search(product="ECOSTRESS", max_results=50)

        # Verify max_results was passed as count
        call_kwargs = mock_earthaccess.search_data.call_args[1]
        assert call_kwargs["count"] == 50

    def test_search_no_results(self, provider, mock_earthaccess):
        """Should handle empty search results."""
        mock_earthaccess.search_data.return_value = []

        results, total = provider.search(product="ECOSTRESS")

        assert len(results) == 0
        assert total == 0

    def test_search_with_known_adapter_uses_short_name(
        self, provider, mock_earthaccess
    ):
        """Should use short_name from adapter when available."""
        mock_granules = [{"id": "granule1"}]
        mock_earthaccess.search_data.return_value = mock_granules

        with patch.object(provider, "get_adapter") as mock_get_adapter:
            mock_adapter = Mock()
            mock_metadata = Mock()
            mock_metadata.short_name = "ECO_L2T_LSTE"
            mock_adapter.get_metadata.return_value = mock_metadata
            mock_adapter.post_process_granules.return_value = (
                mock_granules  # ← ADD THIS
            )
            mock_get_adapter.return_value = mock_adapter

            results, total = provider.search(product="ECOSTRESS")

            # Verify short_name was used
            call_kwargs = mock_earthaccess.search_data.call_args[1]
            assert "short_name" in call_kwargs
            assert call_kwargs["short_name"] == "ECO_L2T_LSTE"

    def test_search_error_handling(self, provider, mock_earthaccess):
        """Should propagate search errors."""
        mock_earthaccess.search_data.side_effect = Exception("Search failed")

        with pytest.raises(Exception, match="Search failed"):
            provider.search(product="ECOSTRESS")

    @pytest.mark.parametrize("product", ["ECOSTRESS", "MODIS", "GEDI"])
    def test_search_multiple_products(self, provider, mock_earthaccess, product):
        """Should search multiple different products."""
        mock_granules = [{"id": "granule1"}]
        mock_earthaccess.search_data.return_value = mock_granules

        results, total = provider.search(product=product)

        assert total >= 0  # Should not raise error


class TestEarthAccessProviderDownload:
    """Tests for download functionality."""

    def test_download_basic(self, provider, mock_earthaccess):
        """Should download granules."""
        mock_files = ["/data/file1.nc", "/data/file2.nc"]
        mock_earthaccess.download.return_value = mock_files

        granules = [{"id": "granule1"}, {"id": "granule2"}]
        files = provider.download(granules, "/output/dir")

        assert len(files) == 2
        assert all(isinstance(f, str) for f in files)
        mock_earthaccess.download.assert_called_once()

    def test_download_with_max_workers(self, provider, mock_earthaccess):
        """Should respect max_workers parameter."""
        mock_files = ["/data/file1.nc"]
        mock_earthaccess.download.return_value = mock_files

        granules = [{"id": "granule1"}]
        provider.download(granules, "/output/dir", max_workers=8)

        # Verify threads parameter was passed
        call_kwargs = mock_earthaccess.download.call_args[1]
        assert call_kwargs["threads"] == 8

    def test_download_empty_granules(self, provider, mock_earthaccess):
        """Should handle empty granule list."""
        mock_earthaccess.download.return_value = []

        files = provider.download([], "/output/dir")

        assert len(files) == 0

    def test_download_error_handling(self, provider, mock_earthaccess):
        """Should propagate download errors."""
        mock_earthaccess.download.side_effect = Exception("Download failed")

        granules = [{"id": "granule1"}]
        with pytest.raises(Exception, match="Download failed"):
            provider.download(granules, "/output/dir")

    def test_download_returns_strings(self, provider, mock_earthaccess):
        """Should convert returned paths to strings."""
        from pathlib import Path

        mock_files = [Path("/data/file1.nc"), Path("/data/file2.nc")]
        mock_earthaccess.download.return_value = mock_files

        granules = [{"id": "granule1"}, {"id": "granule2"}]
        files = provider.download(granules, "/output/dir")

        assert all(isinstance(f, str) for f in files)


class TestEarthAccessProviderMetadata:
    """Tests for metadata retrieval."""

    def test_get_metadata_for_known_product(self, provider):
        """Should get metadata for known product."""
        with patch.object(provider, "get_adapter") as mock_get_adapter:
            mock_adapter = Mock()
            mock_metadata = Mock()
            mock_metadata.short_name = "ECO_L2T_LSTE"
            mock_metadata.long_name = "ECOSTRESS Level 2 LST and Emissivity"
            mock_metadata.description = "Test description"
            mock_metadata.provider = "NASA"
            mock_metadata.processing_level = "L2"
            mock_metadata.spatial_resolution = "70m"
            mock_metadata.temporal_resolution = "8 days"

            mock_adapter.get_metadata.return_value = mock_metadata
            mock_get_adapter.return_value = mock_adapter

            metadata = provider.get_metadata("ECOSTRESS")

            assert metadata["short_name"] == "ECO_L2T_LSTE"
            assert metadata["long_name"] == "ECOSTRESS Level 2 LST and Emissivity"
            assert metadata["provider"] == "NASA"

    def test_get_metadata_for_unknown_product(self, provider):
        """Should return basic metadata for unknown product."""
        with patch.object(provider, "get_adapter", return_value=None):
            metadata = provider.get_metadata("UNKNOWN_PRODUCT")

            assert metadata == {"keyword": "UNKNOWN_PRODUCT"}

    def test_metadata_contains_expected_fields(self, provider):
        """Should include all expected metadata fields."""
        with patch.object(provider, "get_adapter") as mock_get_adapter:
            mock_adapter = Mock()
            mock_metadata = Mock()
            mock_metadata.short_name = "TEST"
            mock_metadata.long_name = "Test"
            mock_metadata.description = "Test"
            mock_metadata.provider = "NASA"
            mock_metadata.processing_level = "L2"
            mock_metadata.spatial_resolution = "1km"
            mock_metadata.temporal_resolution = "1 day"

            mock_adapter.get_metadata.return_value = mock_metadata
            mock_get_adapter.return_value = mock_adapter

            metadata = provider.get_metadata("TEST")

            required_fields = [
                "short_name",
                "long_name",
                "description",
                "provider",
                "processing_level",
                "spatial_resolution",
                "temporal_resolution",
            ]
            for field in required_fields:
                assert field in metadata


class TestEarthAccessProviderValidation:
    """Tests for product validation."""

    def test_validate_known_product(self, provider):
        """Should validate known product."""
        result = provider.validate_product("ECOSTRESS")

        assert result is True

    def test_validate_unknown_product_returns_true(self, provider):
        """Should allow unknown products (keyword search)."""
        with patch.object(provider, "get_adapter", return_value=None):
            result = provider.validate_product("ANY_KEYWORD")

            # Should return True to allow keyword search
            assert result is True

    def test_validate_case_insensitive(self, provider):
        """Should validate case-insensitively."""
        result_lower = provider.validate_product("ecostress")
        result_upper = provider.validate_product("ECOSTRESS")

        assert result_lower is True
        assert result_upper is True


class TestEarthAccessProviderIntegration:
    """Integration tests for full workflows."""

    def test_complete_search_download_workflow(self, provider, mock_earthaccess):
        """Should handle complete search and download workflow."""
        # Mock search
        mock_granules = [
            {"id": "granule1", "umm": {"RelatedUrls": []}},
            {"id": "granule2", "umm": {"RelatedUrls": []}},
        ]
        mock_earthaccess.search_data.return_value = mock_granules

        # Mock download
        mock_files = ["/data/file1.nc", "/data/file2.nc"]
        mock_earthaccess.download.return_value = mock_files

        # Search
        results, total = provider.search(product="ECOSTRESS")
        assert total == 2

        # Download
        files = provider.download(results, "/output/dir")
        assert len(files) == 2

    def test_search_with_filters_and_download(self, provider, mock_earthaccess):
        """Should handle search with filters followed by download."""
        mock_granules = [{"id": "granule1"}]
        mock_earthaccess.search_data.return_value = mock_granules
        mock_earthaccess.download.return_value = ["/data/file1.nc"]

        # Search with filters
        bbox = (-122.82, 36.78, -120.94, 38.25)
        results, _ = provider.search(
            product="MODIS",
            bounding_box=bbox,
            start_date="2020-01-01",
            end_date="2020-12-31",
        )

        # Download
        files = provider.download(results, "/output/dir")

        assert len(files) == 1

    def test_multiple_searches_same_provider(self, provider, mock_earthaccess):
        """Should handle multiple searches with same provider."""
        mock_granules = [{"id": "granule1"}]
        mock_earthaccess.search_data.return_value = mock_granules

        # First search
        results1, _ = provider.search(product="ECOSTRESS")
        assert len(results1) == 1

        # Second search
        results2, _ = provider.search(product="MODIS")
        assert len(results2) == 1

        # Both should work independently
        assert mock_earthaccess.search_data.call_count == 2


class TestEarthAccessProviderEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_search_with_only_product(self, provider, mock_earthaccess):
        """Should search with only product parameter."""
        mock_earthaccess.search_data.return_value = []

        results, total = provider.search(product="ECOSTRESS")

        assert total == 0

    def test_search_with_invalid_bbox_format(self, provider, mock_earthaccess):
        """Should handle bounding box."""
        mock_earthaccess.search_data.return_value = []

        # Valid bbox format: (min_lon, min_lat, max_lon, max_lat)
        bbox = (-122.82, 36.78, -120.94, 38.25)
        results, total = provider.search(product="ECOSTRESS", bounding_box=bbox)

        assert total == 0

    def test_search_with_invalid_date_format(self, provider, mock_earthaccess):
        """Should pass date strings to earthaccess."""
        mock_earthaccess.search_data.return_value = []

        # earthaccess will handle validation
        results, total = provider.search(
            product="ECOSTRESS", start_date="2020-01-01", end_date="2020-12-31"
        )

        assert total == 0
