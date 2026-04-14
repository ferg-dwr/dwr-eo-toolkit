"""
ECOSTRESS adapter for CMR provider.

Handles ECOSTRESS thermal imagery product details, metadata, and filtering.
"""

from typing import Dict, Any, Tuple
from datetime import datetime, timedelta

from nasa_eo_data.providers.cmr_adapters.base import CMRAdapter, InstrumentMetadata


class ECOSTRESSAdapter(CMRAdapter):
    """
    Adapter for ECOSTRESS thermal imagery products.
    
    ECOSTRESS (ECOsystem Spaceborne Thermal Radiometer Experiment on Space Station)
    measures thermal radiance from the International Space Station.
    
    Key characteristics:
    - ~70m spatial resolution
    - ~8 day temporal resolution
    - Thermal infrared (TIR) band
    - Land surface temperature & emissivity products
    - Data available from 2018 onwards
    """

    # ECOSTRESS short names
    ECOSTRESS_SHORT_NAMES = [
        "ECO_L2T_LSTE",      # Level 2 Land Surface Temperature & Emissivity
        "ECO_L2T_QC",        # Quality assessment
        "ECO_L2T_RQC",       # Radiometric QC
        "ECO_L2T_RTC",       # Radiometric Terrain Correction
    ]

    # Keywords that identify this instrument
    KEYWORDS = [
        "ecostress",
        "eco",
        "thermal",
        "tir",
        "lste",
        "land surface temperature",
        "emissivity",
    ]

    # Constants
    SPATIAL_RESOLUTION = "70m"
    TEMPORAL_RESOLUTION = "8 days"
    DATA_FORMAT = "NetCDF4"
    PROVIDER = "LP_DAAC"
    PROCESSING_LEVEL = "2"

    # ECOSTRESS data availability
    START_DATE = "2018-06-20"  # Mission start
    END_DATE = None  # Ongoing

    def __init__(self):
        """Initialize ECOSTRESS adapter."""
        super().__init__()
        self.long_name = "ECOsystem Spaceborne Thermal Radiometer Experiment on Space Station"

    def get_keywords(self) -> list[str]:
        """Get keywords that match ECOSTRESS."""
        return self.KEYWORDS

    def get_short_names(self) -> list[str]:
        """Get ECOSTRESS product short names."""
        return self.ECOSTRESS_SHORT_NAMES

    def get_metadata(self) -> InstrumentMetadata:
        """Get ECOSTRESS metadata."""
        return InstrumentMetadata(
            short_name="ECO_L2T_LSTE",
            long_name=self.long_name,
            description=(
                "ECOSTRESS Level 2 Land Surface Temperature and Emissivity (LSTE) product. "
                "Provides 70m resolution thermal imagery from the ISS. "
                "Used for water resource monitoring, agriculture, and climate research."
            ),
            provider=self.PROVIDER,
            processing_level=self.PROCESSING_LEVEL,
            temporal_resolution=self.TEMPORAL_RESOLUTION,
            spatial_resolution=self.SPATIAL_RESOLUTION,
            data_format=self.DATA_FORMAT,
            doi="10.5067/ECOSTRESS/ECO_L2T_LSTE.006",
            keywords=self.KEYWORDS,
            related_urls=[
                {
                    "url": "https://lpdaac.usgs.gov/products/eco_l2t_lste/",
                    "type": "landing page",
                    "title": "ECOSTRESS L2T LSTE Product Page"
                },
                {
                    "url": "https://cmr.earthdata.nasa.gov/search/site/collections.json?keyword=ECOSTRESS",
                    "type": "cmr",
                    "title": "ECOSTRESS in CMR"
                },
            ],
        )

    def process_search_params(self, **kwargs) -> Dict[str, Any]:
        """
        Process ECOSTRESS-specific search parameters.
        
        ECOSTRESS supports:
        - Basic spatial/temporal filters
        
        Does NOT support:
        - Cloud cover filtering (not available in CMR)
        - Quality flags (use QC product instead)
        """
        params = {}

        # Validate cloud cover parameter
        if "cloud_cover" in kwargs:
            cloud_cover = kwargs["cloud_cover"]
            if not (0 <= cloud_cover <= 100):
                raise ValueError("cloud_cover must be 0-100")
            # Note: ECOSTRESS doesn't support cloud cover filtering in CMR
            # Use post-processing if needed
        
        # Validate quality flags
        if "quality_flags" in kwargs:
            raise ValueError(
                "ECOSTRESS doesn't support quality flag filtering in CMR. "
                "Use the ECO_L2T_QC product instead."
            )

        return params

    def supports_cloud_cover(self) -> bool:
        """ECOSTRESS doesn't support cloud cover filtering in CMR."""
        return False

    def supports_quality_flags(self) -> bool:
        """Quality flags available via separate QC product."""
        return False

    def get_default_spatial_resolution(self) -> str:
        """ECOSTRESS spatial resolution: 70m."""
        return self.SPATIAL_RESOLUTION

    def get_default_temporal_resolution(self) -> str:
        """ECOSTRESS temporal resolution: 8 days."""
        return self.TEMPORAL_RESOLUTION

    def get_recommended_date_range(self) -> Tuple[str, str]:
        """
        Get recommended date range for ECOSTRESS.
        
        Returns:
            (start_date, end_date) as ISO strings
        """
        # Recommend last 2 years by default
        end_date = datetime.now().isoformat()[:10] + "T00:00:00Z"
        start_date = (datetime.now() - timedelta(days=730)).isoformat()[:10] + "T00:00:00Z"
        return (start_date, end_date)

    def validate_temporal_range(self, start_date: str, end_date: str) -> bool:
        """
        Validate ECOSTRESS temporal range.
        
        ECOSTRESS data available from 2018-06-20 onwards.
        """
        from datetime import timezone
        
        mission_start = datetime.fromisoformat(self.START_DATE.replace("Z", "+00:00"))
        
        if start_date:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            # Ensure both are offset-aware for comparison
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if mission_start.tzinfo is None:
                mission_start = mission_start.replace(tzinfo=timezone.utc)
            
            if start < mission_start:
                raise ValueError(
                    f"ECOSTRESS data not available before {self.START_DATE}. "
                    f"Requested: {start_date}"
                )
        
        return True

    def validate_spatial_bounds(
        self, 
        min_lon: float, 
        min_lat: float, 
        max_lon: float, 
        max_lat: float
    ) -> bool:
        """ECOSTRESS covers global land areas (global extent)."""
        return True

    def post_process_granules(
        self, 
        granules: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """
        Post-process ECOSTRESS granules.
        
        Adds ECOSTRESS-specific metadata to granules.
        """
        for granule in granules:
            # Extract ECOSTRESS-specific fields
            umm = granule.get("umm", {})
            
            # Add instrument-specific metadata
            if "RelatedUrls" in umm:
                for url in umm["RelatedUrls"]:
                    if "LST" in url.get("Description", ""):
                        url["Type"] = "ECOSTRESS_LSTE"
        
        return granules