"""
Adapter for OPERA Radiometric Terrain Corrected SAR Backscatter from Sentinel-1.

RTC-S1 provides analysis-ready gamma0 backscatter on a fixed 30 m UTM grid.
Calibration, radiometric terrain correction against the Copernicus GLO-30 DEM,
and geocoding are already applied, so surface-water classification can run
directly on the product without SAR preprocessing on the user side.

Chosen over OPERA DSWx-S1 for water mapping at feature scale. DSWx-S1 maps
open inland water bodies larger than 3 hectares and 200 m in width; features
below that -- weir scour ponds, isolated floodplain depressions -- fall under
its minimum mappable unit entirely. RTC-S1 leaves the classification threshold
to the caller, so small features stay recoverable, at the cost of having to
write and validate the classifier.

Burst granularity: unlike the tiled ECOSTRESS L2T products, one RTC-S1 granule
covers a single Sentinel-1 burst. An AOI wider than a burst needs several
granules mosaicked, and burst footprints differ between relative orbits --
group by relative_orbit before treating two dates as comparable.
"""

import re
from typing import Any

from dwr_eo_toolkit.providers.adapters.base import InstrumentAdapter, InstrumentMetadata

# OPERA_L2_RTC-S1_T137-292318-IW1_20230401T140558Z_20230402T014543Z_S1A_30_v1.0
_GRANULE_UR_RE = re.compile(
    r"^OPERA_L2_RTC-S1(?:-STATIC)?_"
    r"(?P<burst_id>T(?P<relative_orbit>\d{3})-\d{6}-IW\d)_"
    r"(?P<acquired>\d{8}T\d{6}Z)_"
    r"(?P<produced>\d{8}T\d{6}Z)_"
    r"(?P<platform>S1[A-D])_"
    r"(?P<posting>\d+)_"
    r"v(?P<version>[\d.]+)$"
)


class OperaRTCS1Adapter(InstrumentAdapter):
    """
    Adapter for OPERA RTC-S1 SAR backscatter products.

    Two collections are covered. OPERA_L2_RTC-S1_V1 holds the per-acquisition
    backscatter; OPERA_L2_RTC-S1-STATIC_V1 holds the static geometry layers
    (local incidence angle, layover/shadow mask) that accompany them. The
    static layers are reachable via the short_name kwarg on search().
    """

    # CMR short names. Verified against NASA Earthdata:
    #   OPERA_L2_RTC-S1_V1         C2777436413-ASF   2016-04-14 to present
    #   OPERA_L2_RTC-S1-STATIC_V1  C2795135174-ASF   2014-04-03 to present
    RTC_S1_SHORT_NAMES = [
        "OPERA_L2_RTC-S1_V1",  # per-acquisition gamma0 backscatter
        "OPERA_L2_RTC-S1-STATIC_V1",  # static geometry layers
    ]

    # Deliberately narrow. The registry is a flat keyword -> adapter dict, so a
    # duplicate silently overwrites and routes searches to the wrong
    # collection. Generic SAR terms ("sar", "sentinel-1") are left unclaimed
    # because OPERA ships several Sentinel-1 products -- CSLC-S1, DSWx-S1,
    # DIST-S1 -- and any of them would have an equal claim.
    KEYWORDS = [
        "rtc-s1",
        "rtc_s1",
        "rtcs1",
        "opera-rtc",
        "opera_rtc",
        "backscatter",
        "gamma0",
    ]

    SPATIAL_RESOLUTION = "30m"
    # Sentinel-1 revisit, not a fixed product cadence. Varies with constellation
    # state and acquisition planning; state it as a range rather than a number.
    TEMPORAL_RESOLUTION = "6-12 days (Sentinel-1 SLC availability)"
    # NASA Earthdata lists HDF5, GeoTIFF, XML for this collection. The raster
    # layers are GeoTIFF; metadata accompanies them in HDF5 and XML.
    DATA_FORMAT = "GeoTIFF (metadata in HDF5, XML)"
    PROVIDER = "ASF_DAAC"
    PROCESSING_LEVEL = "2"
    START_DATE = "2016-04-14"
    END_DATE = None  # Ongoing

    long_name: str

    def __init__(self) -> None:
        """Initialize OPERA RTC-S1 adapter."""
        super().__init__()
        self.long_name = "OPERA Radiometric Terrain Corrected SAR Backscatter from Sentinel-1"

    def get_keywords(self) -> list[str]:
        """Get keywords that match OPERA RTC-S1."""
        return self.KEYWORDS

    def get_short_names(self) -> list[str]:
        """Get OPERA RTC-S1 product short names."""
        return self.RTC_S1_SHORT_NAMES

    def get_metadata(self) -> InstrumentMetadata:
        """Get OPERA RTC-S1 metadata."""
        return InstrumentMetadata(
            short_name="OPERA_L2_RTC-S1_V1",
            long_name=self.long_name,
            description=(
                "OPERA Level 2 Radiometric Terrain Corrected SAR backscatter from "
                "Sentinel-1. Gamma0 normalized with respect to topography, geocoded "
                "to a 30 m UTM grid using the Copernicus GLO-30 DEM. Analysis-ready "
                "input for surface water classification, flood mapping, and change "
                "detection. One granule per Sentinel-1 burst."
            ),
            provider=self.PROVIDER,
            processing_level=self.PROCESSING_LEVEL,
            temporal_resolution=self.TEMPORAL_RESOLUTION,
            spatial_resolution=self.SPATIAL_RESOLUTION,
            data_format=self.DATA_FORMAT,
            doi="10.5067/SNWG/OPERA_L2_RTC-S1_V1",
            keywords=self.KEYWORDS,
            related_urls=[
                {
                    "url": "https://www.earthdata.nasa.gov/data/catalog/asf-opera-l2-rtc-s1-v1-1",
                    "type": "landing page",
                    "title": "OPERA RTC-S1 V1 Product Page",
                },
                {
                    "url": "https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/",
                    "type": "user guide",
                    "title": "OPERA RTC-S1 Product Guide (ASF)",
                },
            ],
        )

    @staticmethod
    def parse_granule_ur(granule_ur: str) -> dict[str, Any]:
        """
        Decompose an RTC-S1 granule name into its components.

        Returns an empty dict for anything that does not match, so a change to
        the naming convention surfaces as missing fields rather than silently
        wrong values.

        Args:
            granule_ur: e.g. "OPERA_L2_RTC-S1_T137-292318-IW1_"
                             "20230401T140558Z_20230402T014543Z_S1A_30_v1.0"

        Returns:
            dict with burst_id, relative_orbit, acquired, produced, platform,
            posting, version -- or {} if unrecognised.
        """
        match = _GRANULE_UR_RE.match(granule_ur)
        if not match:
            return {}

        parsed = match.groupdict()
        # Relative orbit is the numeric part of the burst ID prefix. Burst
        # footprints are fixed per relative orbit, so this is the grouping key
        # for deciding which granules mosaic together.
        parsed["relative_orbit"] = int(parsed["relative_orbit"])
        parsed["posting"] = int(parsed["posting"])
        return parsed

    def post_process_granules(self, granules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Lift parsed granule-name fields into umm["RTCS1"].

        Granules whose names do not parse are left untouched, with no RTCS1
        key added.
        """
        for granule in granules:
            umm = granule.get("umm", {})
            parsed = self.parse_granule_ur(umm.get("GranuleUR", ""))
            if parsed:
                umm["RTCS1"] = parsed

        return granules
