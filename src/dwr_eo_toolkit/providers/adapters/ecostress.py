"""
Adapter for ECOSTRESS thermal imagery products.

Provides metadata and constants for ECOSTRESS product handling.
"""

from typing import Any

from dwr_eo_toolkit.providers.adapters.base import InstrumentAdapter, InstrumentMetadata


class ECOSTRESSAdapter(InstrumentAdapter):
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
        "ECO_L2T_LSTE",  # Level 2 Land Surface Temperature & Emissivity
        "ECO_L2T_QC",  # Quality assessment
        "ECO_L2T_RQC",  # Radiometric QC
        "ECO_L2T_RTC",  # Radiometric Terrain Correction
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

    # Declare long_name attribute for type checking
    long_name: str

    def __init__(self) -> None:
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
                    "title": "ECOSTRESS L2T LSTE Product Page",
                },
                {
                    "url": "https://cmr.earthdata.nasa.gov/search/site/collections.json?keyword=ECOSTRESS",
                    "type": "cmr",
                    "title": "ECOSTRESS in CMR",
                },
            ],
        )

    def post_process_granules(self, granules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Post-process ECOSTRESS granules.

        Adds ECOSTRESS-specific metadata to granules.
        """
        for granule in granules:
            umm = granule.get("umm", {})
            if "RelatedUrls" in umm:
                for url in umm["RelatedUrls"]:
                    if "LST" in url.get("Description", ""):
                        url["Type"] = "ECOSTRESS_LSTE"

        return granules
