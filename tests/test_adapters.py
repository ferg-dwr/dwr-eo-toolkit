"""
Unit tests for instrument adapters (ECOSTRESS and MODIS).

Tests cover:
- Adapter initialization
- Keyword matching
- Short name retrieval
- Metadata retrieval
- Granule post-processing
"""

import pytest

from dwr_eo_toolkit.providers.adapters.base import InstrumentAdapter, InstrumentMetadata
from dwr_eo_toolkit.providers.adapters.ecostress import ECOSTRESSAdapter
from dwr_eo_toolkit.providers.adapters.modis import MODISAdapter


class TestECOSTRESSAdapter:
    """Tests for ECOSTRESS instrument adapter."""

    @pytest.fixture
    def adapter(self):
        """Create ECOSTRESS adapter instance."""
        return ECOSTRESSAdapter()

    def test_adapter_initialization(self, adapter):
        """Should initialize properly."""
        assert adapter is not None
        assert isinstance(adapter, InstrumentAdapter)
        assert (
            adapter.long_name
            == "ECOsystem Spaceborne Thermal Radiometer Experiment on Space Station"
        )

    def test_get_keywords(self, adapter):
        """Should return ECOSTRESS keywords."""
        keywords = adapter.get_keywords()

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "ecostress" in keywords
        assert "thermal" in keywords
        assert "lste" in keywords

    def test_get_keywords_all_lowercase(self, adapter):
        """Keywords should be usable for case-insensitive matching."""
        keywords = adapter.get_keywords()

        for keyword in keywords:
            assert keyword == keyword.lower()

    def test_get_short_names(self, adapter):
        """Should return ECOSTRESS short names."""
        short_names = adapter.get_short_names()

        assert isinstance(short_names, list)
        assert len(short_names) > 0
        assert "ECO_L2T_LSTE" in short_names

    def test_short_names_are_valid(self, adapter):
        """Short names should start with ECO."""
        short_names = adapter.get_short_names()

        for name in short_names:
            assert name.startswith("ECO_")

    def test_get_metadata(self, adapter):
        """Should return complete metadata."""
        metadata = adapter.get_metadata()

        assert isinstance(metadata, InstrumentMetadata)
        assert metadata.short_name == "ECO_L2T_LSTE"
        assert metadata.long_name is not None
        assert metadata.description is not None
        assert metadata.provider == "LP_DAAC"

    def test_metadata_has_required_fields(self, adapter):
        """Metadata should have all required fields."""
        metadata = adapter.get_metadata()

        required_fields = [
            "short_name",
            "long_name",
            "description",
            "provider",
            "processing_level",
            "temporal_resolution",
            "spatial_resolution",
            "data_format",
            "doi",
            "keywords",
            "related_urls",
        ]

        for field in required_fields:
            assert hasattr(metadata, field)
            assert getattr(metadata, field) is not None

    def test_metadata_processing_level(self, adapter):
        """ECOSTRESS should be Level 2."""
        metadata = adapter.get_metadata()

        assert metadata.processing_level == "2"

    def test_metadata_spatial_resolution(self, adapter):
        """ECOSTRESS should be 70m."""
        metadata = adapter.get_metadata()

        assert "70" in metadata.spatial_resolution or metadata.spatial_resolution == "70m"

    def test_metadata_temporal_resolution(self, adapter):
        """ECOSTRESS should be 8 days."""
        metadata = adapter.get_metadata()

        assert "8" in metadata.temporal_resolution

    def test_metadata_doi_present(self, adapter):
        """ECOSTRESS should have a DOI."""
        metadata = adapter.get_metadata()

        assert metadata.doi is not None
        assert "10.5067" in metadata.doi

    def test_metadata_related_urls(self, adapter):
        """Metadata should include related URLs."""
        metadata = adapter.get_metadata()

        assert isinstance(metadata.related_urls, list)
        assert len(metadata.related_urls) > 0

        # Check URL structure
        for url_info in metadata.related_urls:
            assert "url" in url_info
            assert "type" in url_info

    def test_post_process_granules_empty(self, adapter):
        """Should handle empty granule list."""
        result = adapter.post_process_granules([])

        assert result == []

    def test_post_process_granules_with_data(self, adapter):
        """Should process granules with UMM metadata."""
        granules = [
            {
                "umm": {
                    "RelatedUrls": [
                        {
                            "URL": "https://example.com/file.nc",
                            "Description": "LST data",
                        }
                    ]
                }
            }
        ]

        result = adapter.post_process_granules(granules)

        assert len(result) == 1
        assert "umm" in result[0]

    def test_post_process_granules_without_related_urls(self, adapter):
        """Should handle granules without RelatedUrls."""
        granules = [{"umm": {}}]

        result = adapter.post_process_granules(granules)

        assert len(result) == 1

    def test_post_process_granules_multiple(self, adapter):
        """Should process multiple granules."""
        granules = [
            {"umm": {"RelatedUrls": [{"URL": "file1.nc", "Description": "LST data"}]}},
            {"umm": {"RelatedUrls": [{"URL": "file2.nc", "Description": "LST data"}]}},
        ]

        result = adapter.post_process_granules(granules)

        assert len(result) == 2

    def test_constants_defined(self, adapter):
        """Should have class constants defined."""
        assert hasattr(adapter, "SPATIAL_RESOLUTION")
        assert hasattr(adapter, "TEMPORAL_RESOLUTION")
        assert hasattr(adapter, "DATA_FORMAT")
        assert hasattr(adapter, "PROVIDER")
        assert hasattr(adapter, "PROCESSING_LEVEL")


class TestMODISAdapter:
    """Tests for MODIS instrument adapter."""

    @pytest.fixture
    def adapter(self):
        """Create MODIS adapter instance."""
        return MODISAdapter()

    def test_adapter_initialization(self, adapter):
        """Should initialize properly."""
        assert adapter is not None
        assert isinstance(adapter, InstrumentAdapter)
        assert "Moderate Resolution Imaging" in adapter.long_name

    def test_get_keywords(self, adapter):
        """Should return MODIS keywords."""
        keywords = adapter.get_keywords()

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert "modis" in keywords
        assert "terra" in keywords or "aqua" in keywords

    def test_get_short_names(self, adapter):
        """Should return MODIS short names."""
        short_names = adapter.get_short_names()

        assert isinstance(short_names, list)
        assert len(short_names) > 0
        # Should have both Terra (MOD) and Aqua (MYD) products
        assert any(name.startswith("MOD") for name in short_names)
        assert any(name.startswith("MYD") for name in short_names)

    def test_get_metadata(self, adapter):
        """Should return metadata."""
        metadata = adapter.get_metadata()

        assert isinstance(metadata, InstrumentMetadata)
        assert metadata.short_name is not None
        assert metadata.long_name is not None
        assert metadata.provider == "LPDAAC"

    def test_metadata_has_required_fields(self, adapter):
        """Metadata should have all required fields."""
        metadata = adapter.get_metadata()

        required_fields = [
            "short_name",
            "long_name",
            "description",
            "provider",
            "processing_level",
            "temporal_resolution",
            "spatial_resolution",
            "data_format",
            "doi",
            "keywords",
            "related_urls",
        ]

        for field in required_fields:
            assert hasattr(metadata, field)
            assert getattr(metadata, field) is not None

    def test_metadata_processing_level(self, adapter):
        """MODIS should be Level 3."""
        metadata = adapter.get_metadata()

        assert metadata.processing_level == "3"

    def test_metadata_spatial_resolution(self, adapter):
        """MODIS should have variable spatial resolution."""
        metadata = adapter.get_metadata()

        assert "250" in metadata.spatial_resolution or "km" in metadata.spatial_resolution

    def test_metadata_temporal_resolution(self, adapter):
        """MODIS should be 1-2 days."""
        metadata = adapter.get_metadata()

        assert "1" in metadata.temporal_resolution or "2" in metadata.temporal_resolution

    def test_metadata_doi_present(self, adapter):
        """MODIS should have a DOI."""
        metadata = adapter.get_metadata()

        assert metadata.doi is not None
        assert "10.5067" in metadata.doi

    def test_metadata_related_urls(self, adapter):
        """Metadata should include related URLs."""
        metadata = adapter.get_metadata()

        assert isinstance(metadata.related_urls, list)
        assert len(metadata.related_urls) > 0

    def test_constants_defined(self, adapter):
        """Should have class constants defined."""
        assert hasattr(adapter, "SPATIAL_RESOLUTION")
        assert hasattr(adapter, "TEMPORAL_RESOLUTION")
        assert hasattr(adapter, "DATA_FORMAT")
        assert hasattr(adapter, "PROVIDER")
        assert hasattr(adapter, "PROCESSING_LEVEL")

    def test_data_availability(self, adapter):
        """Should have data availability dates."""
        assert hasattr(adapter, "START_DATE")
        assert adapter.START_DATE is not None
        assert "2000" in adapter.START_DATE


class TestAdapterComparison:
    """Tests comparing ECOSTRESS and MODIS adapters."""

    def test_both_inherit_from_base(self):
        """Both should inherit from InstrumentAdapter."""
        ecostress = ECOSTRESSAdapter()
        modis = MODISAdapter()

        assert isinstance(ecostress, InstrumentAdapter)
        assert isinstance(modis, InstrumentAdapter)

    def test_different_keywords(self):
        """Should have different keywords."""
        ecostress = ECOSTRESSAdapter()
        modis = MODISAdapter()

        ecostress_keywords = set(ecostress.get_keywords())
        modis_keywords = set(modis.get_keywords())

        # Should have mostly different keywords
        assert len(ecostress_keywords & modis_keywords) < len(ecostress_keywords)

    def test_different_short_names(self):
        """Should have different short names."""
        ecostress = ECOSTRESSAdapter()
        modis = MODISAdapter()

        ecostress_names = set(ecostress.get_short_names())
        modis_names = set(modis.get_short_names())

        assert len(ecostress_names & modis_names) == 0

    def test_metadata_structure_consistent(self):
        """Metadata structure should be consistent."""
        ecostress = ECOSTRESSAdapter()
        modis = MODISAdapter()

        ecostress_meta = ecostress.get_metadata()
        modis_meta = modis.get_metadata()

        # Should have same metadata type
        assert type(ecostress_meta) is type(modis_meta)

        # Should have same fields
        assert dir(ecostress_meta) == dir(modis_meta)

    def test_different_providers(self):
        """Should represent different providers."""
        ecostress = ECOSTRESSAdapter()
        modis = MODISAdapter()

        ecostress_meta = ecostress.get_metadata()
        modis_meta = modis.get_metadata()

        assert ecostress_meta.provider != modis_meta.provider


class TestAdapterIntegration:
    """Integration tests for adapters."""

    def test_adapter_retrieval_workflow(self):
        """Test workflow: get keywords → get metadata → get short names."""
        adapter = ECOSTRESSAdapter()

        # Get keywords
        keywords = adapter.get_keywords()
        assert "ecostress" in keywords

        # Get metadata using keyword
        metadata = adapter.get_metadata()
        assert metadata.short_name in adapter.get_short_names()

        # Verify consistency
        assert metadata.provider == "LP_DAAC"

    def test_granule_processing_workflow(self):
        """Test granule processing workflow."""
        adapter = ECOSTRESSAdapter()

        # Create sample granules
        granules = [
            {
                "id": "granule1",
                "umm": {
                    "RelatedUrls": [
                        {
                            "URL": "https://lpdaac.usgs.gov/file1.nc",
                            "Description": "LST data",
                        }
                    ]
                },
            }
        ]

        # Process granules
        result = adapter.post_process_granules(granules)

        # Verify result
        assert len(result) == 1
        assert "umm" in result[0]

    def test_metadata_completeness(self):
        """Verify metadata completeness for both adapters."""
        adapters = [ECOSTRESSAdapter(), MODISAdapter()]

        for adapter in adapters:
            metadata = adapter.get_metadata()

            # Check description length (should be meaningful)
            assert len(metadata.description) > 50

            # Check keywords
            assert len(metadata.keywords) > 0

            # Check related URLs
            assert len(metadata.related_urls) > 0

            # Check all URLs are valid
            for url_info in metadata.related_urls:
                assert url_info["url"].startswith("http")
