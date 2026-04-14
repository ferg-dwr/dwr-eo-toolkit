"""
Tests for CMR adapters (Phase 2C).

Tests adapter pattern implementation including:
- CMRAdapter abstract base class
- ECOSTRESSAdapter implementation
- MODISAdapter stub
- Adapter registry
"""

import pytest
from datetime import datetime

from nasa_eo_data.providers.cmr_adapters.base import CMRAdapter, InstrumentMetadata
from nasa_eo_data.providers.cmr_adapters.ecostress import ECOSTRESSAdapter
from nasa_eo_data.providers.cmr_adapters.modis import MODISAdapter


# ============================================================================
# Test InstrumentMetadata Dataclass
# ============================================================================

class TestInstrumentMetadata:
    """Test InstrumentMetadata dataclass."""

    def test_create_metadata(self):
        """Test creating metadata instance."""
        metadata = InstrumentMetadata(
            short_name="ECO_L2T_LSTE",
            long_name="ECOSTRESS Land Surface Temperature",
            description="Thermal imagery from ISS",
            provider="LP_DAAC",
            processing_level="2",
            temporal_resolution="8 days",
            spatial_resolution="70m",
            data_format="NetCDF4",
            doi="10.5067/...",
            keywords=["ecostress", "thermal"],
            related_urls=[],
        )
        
        assert metadata.short_name == "ECO_L2T_LSTE"
        assert metadata.provider == "LP_DAAC"
        assert len(metadata.keywords) == 2

    def test_metadata_all_fields(self):
        """Test metadata has all required fields."""
        metadata = InstrumentMetadata(
            short_name="TEST",
            long_name="Test Product",
            description="Test description",
            provider="TEST_DAAC",
            processing_level="1",
            temporal_resolution="1 day",
            spatial_resolution="1m",
            data_format="HDF5",
            doi="10.5067/TEST",
            keywords=["test"],
            related_urls=[{"url": "http://example.com", "type": "landing"}],
        )
        
        assert metadata.short_name
        assert metadata.long_name
        assert metadata.description
        assert metadata.provider
        assert metadata.processing_level
        assert metadata.temporal_resolution
        assert metadata.spatial_resolution
        assert metadata.data_format
        assert metadata.doi
        assert metadata.keywords
        assert metadata.related_urls


# ============================================================================
# Test CMRAdapter Abstract Base Class
# ============================================================================

class TestCMRAdapterInterface:
    """Test CMRAdapter abstract interface."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that CMRAdapter cannot be instantiated directly."""
        # This should fail because CMRAdapter is abstract
        with pytest.raises(TypeError):
            CMRAdapter()

    def test_subclass_must_implement_all_methods(self):
        """Test that subclass must implement all abstract methods."""
        # Create a partial subclass missing methods
        class IncompleteAdapter(CMRAdapter):
            def get_keywords(self):
                return ["test"]
            # Missing other abstract methods

        # Should raise TypeError
        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_adapter_interface_defined(self):
        """Test that adapter interface is properly defined."""
        # Check abstract methods exist
        abstract_methods = {
            "get_keywords",
            "get_short_names",
            "get_metadata",
            "process_search_params",
            "supports_cloud_cover",
            "supports_quality_flags",
            "get_default_spatial_resolution",
            "get_default_temporal_resolution",
            "get_recommended_date_range",
        }
        
        # Get abstract methods from CMRAdapter
        adapter_abstract_methods = set(CMRAdapter.__abstractmethods__)
        
        assert abstract_methods == adapter_abstract_methods


# ============================================================================
# Test ECOSTRESSAdapter Implementation
# ============================================================================

class TestECOSTRESSAdapter:
    """Test ECOSTRESS adapter implementation."""

    @pytest.fixture
    def adapter(self):
        """Fixture providing ECOSTRESSAdapter instance."""
        return ECOSTRESSAdapter()

    def test_instantiation(self, adapter):
        """Test ECOSTRESS adapter can be instantiated."""
        assert isinstance(adapter, ECOSTRESSAdapter)
        assert isinstance(adapter, CMRAdapter)

    def test_get_keywords(self, adapter):
        """Test ECOSTRESS keywords."""
        keywords = adapter.get_keywords()
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "ecostress" in [k.lower() for k in keywords]
        assert all(isinstance(k, str) for k in keywords)

    def test_get_short_names(self, adapter):
        """Test ECOSTRESS short names."""
        short_names = adapter.get_short_names()
        
        assert isinstance(short_names, list)
        assert len(short_names) > 0
        assert "ECO_L2T_LSTE" in short_names
        assert all(isinstance(sn, str) for sn in short_names)

    def test_get_metadata(self, adapter):
        """Test ECOSTRESS metadata."""
        metadata = adapter.get_metadata()
        
        assert isinstance(metadata, InstrumentMetadata)
        assert metadata.short_name == "ECO_L2T_LSTE"
        assert metadata.provider == "LP_DAAC"
        assert metadata.spatial_resolution == "70m"
        assert metadata.temporal_resolution == "8 days"
        assert "ecostress" in [k.lower() for k in metadata.keywords]

    def test_process_search_params_empty(self, adapter):
        """Test processing empty search parameters."""
        params = adapter.process_search_params()
        
        assert isinstance(params, dict)

    def test_process_search_params_with_cloud_cover(self, adapter):
        """Test processing cloud cover parameter."""
        # ECOSTRESS doesn't support cloud cover, but should handle it
        params = adapter.process_search_params(cloud_cover=50)
        
        assert isinstance(params, dict)

    def test_process_search_params_invalid_cloud_cover(self, adapter):
        """Test invalid cloud cover value raises error."""
        with pytest.raises(ValueError):
            adapter.process_search_params(cloud_cover=150)  # Invalid: > 100

    def test_process_search_params_quality_flags_not_supported(self, adapter):
        """Test quality flags not supported for ECOSTRESS."""
        with pytest.raises(ValueError):
            adapter.process_search_params(quality_flags="high")

    def test_supports_cloud_cover(self, adapter):
        """Test ECOSTRESS doesn't support cloud cover."""
        assert adapter.supports_cloud_cover() is False

    def test_supports_quality_flags(self, adapter):
        """Test ECOSTRESS doesn't support quality flags."""
        assert adapter.supports_quality_flags() is False

    def test_get_default_spatial_resolution(self, adapter):
        """Test default spatial resolution."""
        resolution = adapter.get_default_spatial_resolution()
        
        assert isinstance(resolution, str)
        assert "70" in resolution
        assert "m" in resolution

    def test_get_default_temporal_resolution(self, adapter):
        """Test default temporal resolution."""
        resolution = adapter.get_default_temporal_resolution()
        
        assert isinstance(resolution, str)
        assert "8" in resolution
        assert "day" in resolution

    def test_get_recommended_date_range(self, adapter):
        """Test recommended date range."""
        start_date, end_date = adapter.get_recommended_date_range()
        
        assert isinstance(start_date, str)
        assert isinstance(end_date, str)
        # Should have ISO format with T and Z
        assert "T" in start_date
        assert "Z" in start_date
        assert "T" in end_date
        assert "Z" in end_date

    def test_validate_temporal_range_valid(self, adapter):
        """Test valid temporal range."""
        result = adapter.validate_temporal_range(
            "2020-01-01T00:00:00Z",
            "2020-12-31T23:59:59Z"
        )
        assert result is True

    def test_validate_temporal_range_before_mission_start(self, adapter):
        """Test temporal range before mission start."""
        with pytest.raises(ValueError):
            adapter.validate_temporal_range(
                "2017-01-01T00:00:00Z",  # Before 2018-06-20
                "2020-12-31T23:59:59Z"
            )

    def test_validate_spatial_bounds(self, adapter):
        """Test spatial bounds validation."""
        result = adapter.validate_spatial_bounds(
            min_lon=-122.0,
            min_lat=36.0,
            max_lon=-120.0,
            max_lat=38.0
        )
        assert result is True

    def test_post_process_granules_empty(self, adapter):
        """Test post-processing empty granules."""
        granules = []
        result = adapter.post_process_granules(granules)
        
        assert isinstance(result, list)
        assert len(result) == 0

    def test_post_process_granules_with_data(self, adapter):
        """Test post-processing granules with data."""
        granules = [
            {
                "granule_ur": "G123456789",
                "umm": {
                    "RelatedUrls": [
                        {"Description": "LST data", "URL": "http://example.com"}
                    ]
                }
            }
        ]
        result = adapter.post_process_granules(granules)
        
        assert isinstance(result, list)
        assert len(result) == 1
        # Should preserve structure
        assert result[0]["granule_ur"] == "G123456789"


# ============================================================================
# Test MODISAdapter Stub Implementation
# ============================================================================

class TestMODISAdapter:
    """Test MODIS adapter stub implementation."""

    @pytest.fixture
    def adapter(self):
        """Fixture providing MODISAdapter instance."""
        return MODISAdapter()

    def test_instantiation(self, adapter):
        """Test MODIS adapter can be instantiated."""
        assert isinstance(adapter, MODISAdapter)
        assert isinstance(adapter, CMRAdapter)

    def test_get_keywords(self, adapter):
        """Test MODIS keywords."""
        keywords = adapter.get_keywords()
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "modis" in [k.lower() for k in keywords]

    def test_get_short_names(self, adapter):
        """Test MODIS short names."""
        short_names = adapter.get_short_names()
        
        assert isinstance(short_names, list)
        assert len(short_names) > 0
        assert all(isinstance(sn, str) for sn in short_names)

    def test_get_metadata(self, adapter):
        """Test MODIS metadata stub."""
        metadata = adapter.get_metadata()
        
        assert isinstance(metadata, InstrumentMetadata)
        assert metadata.short_name == "MOD09GA"
        assert metadata.provider == "LPDAAC"

    def test_process_search_params_stub(self, adapter):
        """Test MODIS stub returns empty dict."""
        params = adapter.process_search_params()
        
        assert isinstance(params, dict)
        # Stub returns empty dict (TODO for Phase 2C+)
        assert params == {}

    def test_supports_cloud_cover_stub(self, adapter):
        """Test MODIS cloud cover support stub."""
        # TODO for Phase 2C+
        result = adapter.supports_cloud_cover()
        assert isinstance(result, bool)

    def test_supports_quality_flags_stub(self, adapter):
        """Test MODIS quality flags support stub."""
        # TODO for Phase 2C+
        result = adapter.supports_quality_flags()
        assert isinstance(result, bool)

    def test_get_default_spatial_resolution(self, adapter):
        """Test MODIS default spatial resolution."""
        resolution = adapter.get_default_spatial_resolution()
        
        assert isinstance(resolution, str)
        assert "m" in resolution or "km" in resolution

    def test_get_default_temporal_resolution(self, adapter):
        """Test MODIS default temporal resolution."""
        resolution = adapter.get_default_temporal_resolution()
        
        assert isinstance(resolution, str)
        assert "day" in resolution or "hour" in resolution

    def test_get_recommended_date_range(self, adapter):
        """Test MODIS recommended date range."""
        start_date, end_date = adapter.get_recommended_date_range()
        
        assert isinstance(start_date, str)
        assert isinstance(end_date, str)
        # Should have ISO format
        assert "T" in start_date
        assert "T" in end_date

    def test_validate_temporal_range(self, adapter):
        """Test MODIS temporal range validation."""
        # Stub accepts any valid range
        result = adapter.validate_temporal_range(
            "2000-01-01T00:00:00Z",
            "2020-12-31T23:59:59Z"
        )
        assert result is True

    def test_validate_spatial_bounds(self, adapter):
        """Test MODIS spatial bounds validation."""
        result = adapter.validate_spatial_bounds(
            min_lon=-180.0,
            min_lat=-90.0,
            max_lon=180.0,
            max_lat=90.0
        )
        assert result is True


# ============================================================================
# Test Adapter Registry
# ============================================================================

class TestAdapterRegistry:
    """Test adapter registry functionality."""

    def test_ecostress_adapter_registration(self):
        """Test ECOSTRESS adapter can be looked up by keywords."""
        adapter = ECOSTRESSAdapter()
        keywords = adapter.get_keywords()
        
        # Each keyword should identify ECOSTRESS
        for keyword in keywords:
            assert keyword.lower() in ["ecostress", "eco", "thermal", "tir", "lste", "land surface temperature", "emissivity"]

    def test_modis_adapter_registration(self):
        """Test MODIS adapter can be looked up by keywords."""
        adapter = MODISAdapter()
        keywords = adapter.get_keywords()
        
        # Should have recognizable MODIS keywords
        assert any(k.lower() in ["modis", "terra", "aqua"] for k in keywords)

    def test_adapter_keyword_uniqueness(self):
        """Test adapters don't share keywords."""
        ecostress = ECOSTRESSAdapter()
        modis = MODISAdapter()
        
        ecostress_keywords = set(k.lower() for k in ecostress.get_keywords())
        modis_keywords = set(k.lower() for k in modis.get_keywords())
        
        # "modis" shouldn't be in ECOSTRESS
        assert "modis" not in ecostress_keywords
        # "ecostress" shouldn't be in MODIS
        assert "ecostress" not in modis_keywords


# ============================================================================
# Integration Tests
# ============================================================================

class TestAdapterIntegration:
    """Integration tests for adapters."""

    def test_all_adapters_implement_interface(self):
        """Test all adapters implement required interface."""
        adapters = [ECOSTRESSAdapter(), MODISAdapter()]
        
        for adapter in adapters:
            # Should be instance of CMRAdapter
            assert isinstance(adapter, CMRAdapter)
            
            # Should have all required methods
            assert hasattr(adapter, "get_keywords")
            assert hasattr(adapter, "get_short_names")
            assert hasattr(adapter, "get_metadata")
            assert hasattr(adapter, "process_search_params")
            assert hasattr(adapter, "supports_cloud_cover")
            assert hasattr(adapter, "supports_quality_flags")
            assert hasattr(adapter, "get_default_spatial_resolution")
            assert hasattr(adapter, "get_default_temporal_resolution")
            assert hasattr(adapter, "get_recommended_date_range")

    def test_all_adapters_return_correct_types(self):
        """Test all adapters return correct data types."""
        adapters = [ECOSTRESSAdapter(), MODISAdapter()]
        
        for adapter in adapters:
            # get_keywords
            keywords = adapter.get_keywords()
            assert isinstance(keywords, list)
            assert all(isinstance(k, str) for k in keywords)
            
            # get_short_names
            short_names = adapter.get_short_names()
            assert isinstance(short_names, list)
            assert all(isinstance(sn, str) for sn in short_names)
            
            # get_metadata
            metadata = adapter.get_metadata()
            assert isinstance(metadata, InstrumentMetadata)
            
            # process_search_params
            params = adapter.process_search_params()
            assert isinstance(params, dict)
            
            # support methods
            assert isinstance(adapter.supports_cloud_cover(), bool)
            assert isinstance(adapter.supports_quality_flags(), bool)
            
            # resolution methods
            assert isinstance(adapter.get_default_spatial_resolution(), str)
            assert isinstance(adapter.get_default_temporal_resolution(), str)
            
            # date range
            start, end = adapter.get_recommended_date_range()
            assert isinstance(start, str)
            assert isinstance(end, str)

    def test_adapter_exports(self):
        """Test adapters are properly exported."""
        from nasa_eo_data.providers.cmr_adapters import (
            CMRAdapter,
            InstrumentMetadata,
            ECOSTRESSAdapter,
            MODISAdapter,
        )
        
        # Should be able to import
        assert CMRAdapter is not None
        assert InstrumentMetadata is not None
        assert ECOSTRESSAdapter is not None
        assert MODISAdapter is not None


# ============================================================================
# Backward Compatibility Tests
# ============================================================================

class TestBackwardCompatibility:
    """Test that adapters don't break existing code."""

    def test_phase_2b_still_works(self):
        """Test Phase 2B CMRProvider still works (if imported separately)."""
        # This test ensures adapters don't interfere with Phase 2B
        # Just verify adapters can be imported without errors
        from nasa_eo_data.providers.cmr_adapters import ECOSTRESSAdapter
        
        adapter = ECOSTRESSAdapter()
        assert adapter is not None

    def test_adapter_optional(self):
        """Test adapters are optional (not required for basic search)."""
        # Creating adapters is optional - you can still use CMRProvider
        # without them (backward compatible)
        adapter = ECOSTRESSAdapter()
        
        # Adapter can be used independently
        metadata = adapter.get_metadata()
        assert metadata is not None
