"""
Adapter for MODIS products.

Provides metadata and constants for MODIS product handling.

Note: Phase 2C implementation details can be added as needed.
"""

from typing import Any, Dict, Tuple

from nasa_eo_data.providers.adapters.base import (InstrumentAdapter,
                                                  InstrumentMetadata)


class MODISAdapter(InstrumentAdapter):
    """
    Adapter for MODIS products (stub for Phase 2C).

    MODIS (Moderate Resolution Imaging Spectroradiometer)

    Key characteristics:
    - 250m-1km spatial resolution (varies by band)
    - 1-2 day temporal resolution
    - Visible/infrared bands
    - Multiple products: vegetation, thermal, aerosol, etc.
    - Data available from 2000 onwards (Terra), 2002 onwards (Aqua)

    Note: Full implementation in Phase 2C
    """

    MODIS_SHORT_NAMES = [
        "MOD09GA",  # MODIS/Terra Surface Reflectance Daily
        "MYD09GA",  # MODIS/Aqua Surface Reflectance Daily
        "MOD11A1",  # MODIS/Terra Land Surface Temperature Daily
        "MYD11A1",  # MODIS/Aqua Land Surface Temperature Daily
        # More products...
    ]

    KEYWORDS = [
        "modis",
        "terra",
        "aqua",
        "reflectance",
        "surface temperature",
    ]

    SPATIAL_RESOLUTION = "250m-1km"
    TEMPORAL_RESOLUTION = "1-2 days"
    DATA_FORMAT = "HDF4"
    PROVIDER = "LPDAAC"
    PROCESSING_LEVEL = "3"

    START_DATE = "2000-02-24"  # Terra launch
    END_DATE = None  # Ongoing

    def __init__(self):
        """Initialize MODIS adapter (stub)."""
        super().__init__()
        self.long_name = "Moderate Resolution Imaging Spectroradiometer"

    def get_keywords(self) -> list[str]:
        """Get keywords that match MODIS."""
        return self.KEYWORDS

    def get_short_names(self) -> list[str]:
        """Get MODIS product short names."""
        return self.MODIS_SHORT_NAMES

    def get_metadata(self) -> InstrumentMetadata:
        """Get MODIS metadata (stub)."""
        return InstrumentMetadata(
            short_name="MOD09GA",
            long_name=self.long_name,
            description=(
                "MODIS/Terra Surface Reflectance Daily product. "
                "Provides surface reflectance at 250m-1km resolution. "
                "Phase 2C: Full metadata implementation pending."
            ),
            provider=self.PROVIDER,
            processing_level=self.PROCESSING_LEVEL,
            temporal_resolution=self.TEMPORAL_RESOLUTION,
            spatial_resolution=self.SPATIAL_RESOLUTION,
            data_format=self.DATA_FORMAT,
            doi="10.5067/MODIS/MOD09GA.006",
            keywords=self.KEYWORDS,
            related_urls=[
                {
                    "url": "https://lpdaac.usgs.gov/products/mod09ga/",
                    "type": "landing page",
                    "title": "MODIS MOD09GA Product Page",
                },
            ],
        )
