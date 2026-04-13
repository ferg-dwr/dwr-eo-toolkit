"""
CMR Provider for NASA Earth observation data.

Uses the CMR (Common Metadata Repository) API to search for granules.
Supports any dataset available in CMR including ECOSTRESS, MODIS, VIIRS, Landsat, etc.

References:
- https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from nasa_eo_data.core.client import CMRClient
from nasa_eo_data.core.auth import EarthDataLoginAuth
from nasa_eo_data.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class CMRProvider(BaseProvider):
    """
    Provider for searching NASA CMR (Common Metadata Repository).
    
    Supports searching any dataset available in CMR:
    - ECOSTRESS (thermal imagery)
    - MODIS (Terra/Aqua)
    - VIIRS (S-NPP, NOAA-20)
    - Landsat (8, 9)
    - Sentinel-1, Sentinel-2
    - And many more
    
    Example:
        >>> from nasa_eo_data.core.auth import EarthDataLoginAuth
        >>> from nasa_eo_data.providers import CMRProvider
        >>> 
        >>> auth = EarthDataLoginAuth()
        >>> provider = CMRProvider(auth)
        >>> 
        >>> results, total = provider.search(
        ...     product="ECOSTRESS_L2_LSTE",
        ...     bounding_box=(-120, 30, -100, 40),
        ...     start_date="2023-01-01",
        ...     end_date="2023-12-31",
        ... )
        >>> print(f"Found {total} granules")
    """

    def __init__(self, auth: EarthDataLoginAuth):
        """
        Initialize CMRProvider.
        
        Args:
            auth: EarthDataLoginAuth instance for API authentication
        """
        self.auth = auth
        self.cmr_client = CMRClient(auth_handler=auth)
        self._product_cache: Dict[str, Dict[str, Any]] = {}

    def search(
        self,
        product: str,
        bounding_box: Optional[tuple[float, float, float, float]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Search CMR for granules matching the query.
        
        Args:
            product: Product short name (e.g., "ECOSTRESS_L2_LSTE")
            bounding_box: (min_lon, min_lat, max_lon, max_lat) or None
            start_date: Start date in YYYY-MM-DD or ISO format
            end_date: End date in YYYY-MM-DD or ISO format
            **kwargs:
                page_size: Results per page (default 2000, max 2000)
                max_results: Maximum total results (default None = all)
                cloud_cover: Max cloud cover 0-100 (default None)
        
        Returns:
            (results_list, total_count)
        
        Raises:
            ValueError: If parameters invalid
            AuthenticationError: If auth fails
            APIError: If CMR API fails
        """
        # Validate and build CMR query parameters
        params = self._build_search_params(
            product=product,
            bounding_box=bounding_box,
            start_date=start_date,
            end_date=end_date,
            **kwargs,
        )

        logger.debug(f"Searching CMR for {product} with params: {params}")

        # Search CMR
        try:
            results, total = self.cmr_client.search(
                endpoint="search/granules",
                params=params,
                page_size=kwargs.get("page_size", 2000),
                max_results=kwargs.get("max_results", None),
            )

            logger.info(f"Found {total} granules matching {product}")
            return results, total

        except Exception as e:
            logger.error(f"CMR search failed for {product}: {e}")
            raise

    def get_metadata(self, product: str) -> Dict[str, Any]:
        """
        Get metadata about a CMR collection.
        
        Args:
            product: Product short name
        
        Returns:
            Metadata dictionary with collection information
        
        Raises:
            ValueError: If product not found
            APIError: If CMR API fails
        """
        # Check cache first
        if product in self._product_cache:
            return self._product_cache[product]

        logger.debug(f"Fetching metadata for {product}")

        try:
            # Search for collection
            results, total = self.cmr_client.search(
                endpoint="search/collections",
                params={"short_name": product, "page_size": 1},
                max_results=1,
            )

            if not results:
                raise ValueError(f"Product '{product}' not found in CMR")

            collection = results[0]
            umm = collection.get("umm", {})

            # Extract relevant metadata
            metadata = {
                "short_name": umm.get("ShortName", product),
                "long_name": umm.get("LongName", ""),
                "description": umm.get("Summary", ""),
                "provider": umm.get("Provider", {}).get("ShortName", ""),
                "processing_level": umm.get("ProcessingLevel", {}).get("Id", ""),
                "temporal_resolution": self._extract_temporal_resolution(umm),
                "spatial_resolution": self._extract_spatial_resolution(umm),
                "data_format": self._extract_data_format(umm),
                "doi": umm.get("DOI", {}).get("DOI", ""),
                "related_urls": umm.get("RelatedUrls", []),
            }

            # Cache it
            self._product_cache[product] = metadata

            logger.debug(f"Retrieved metadata for {product}")
            return metadata

        except Exception as e:
            logger.error(f"Failed to get metadata for {product}: {e}")
            raise

    def validate_product(self, product: str) -> bool:
        """
        Validate that a product exists in CMR.
        
        Args:
            product: Product short name
        
        Returns:
            True if valid, False otherwise
        """
        try:
            self.get_metadata(product)
            return True
        except (ValueError, Exception):
            return False

    # ==================== Helper Methods ====================

    def _build_search_params(
        self,
        product: str,
        bounding_box: Optional[tuple[float, float, float, float]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Build CMR API query parameters from high-level arguments.
        
        Args:
            product: Product short name
            bounding_box: (min_lon, min_lat, max_lon, max_lat)
            start_date: ISO or YYYY-MM-DD format
            end_date: ISO or YYYY-MM-DD format
            **kwargs: Additional parameters
        
        Returns:
            Dictionary of CMR API parameters
        """
        params = {
            "short_name": product,
        }

        # Add bounding box if provided
        if bounding_box:
            min_lon, min_lat, max_lon, max_lat = bounding_box
            self._validate_bounding_box(min_lon, min_lat, max_lon, max_lat)
            params["bounding_box"] = f"{min_lon},{min_lat},{max_lon},{max_lat}"

        # Add temporal range if provided
        if start_date or end_date:
            temporal = self._build_temporal_range(start_date, end_date)
            if temporal:
                params["temporal"] = temporal

        # Add optional cloud cover filter
        if "cloud_cover" in kwargs:
            cloud_cover = kwargs["cloud_cover"]
            if not 0 <= cloud_cover <= 100:
                raise ValueError("cloud_cover must be 0-100")
            # CMR uses different parameter names for different products
            # This is a common pattern for many optical sensors
            params["attribute[]"] = f"string,CloudCover,<=,{cloud_cover}"

        return params

    def _build_temporal_range(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Optional[str]:
        """
        Convert start/end dates to CMR temporal format.
        
        Args:
            start_date: ISO or YYYY-MM-DD format
            end_date: ISO or YYYY-MM-DD format
        
        Returns:
            Temporal string for CMR or None
        
        Raises:
            ValueError: If date format invalid
        """
        if not start_date and not end_date:
            return None

        # Normalize dates to ISO format
        start_iso = self._normalize_date(start_date) if start_date else ""
        end_iso = self._normalize_date(end_date) if end_date else ""

        # CMR temporal format: "YYYY-MM-DDTHH:MM:SSZ,YYYY-MM-DDTHH:MM:SSZ"
        return f"{start_iso},{end_iso}"

    def _normalize_date(self, date_str: str) -> str:
        """
        Convert date string to ISO format with time.
        
        Accepts:
        - YYYY-MM-DD → YYYY-MM-DDTHH:MM:SSZ (start of day)
        - YYYY-MM-DDTHH:MM:SSZ → unchanged
        - ISO format variants
        
        Args:
            date_str: Date string
        
        Returns:
            ISO format string with time
        
        Raises:
            ValueError: If format unrecognized
        """
        if not date_str:
            return ""

        # Already ISO format with time?
        if "T" in date_str:
            # Ensure it ends with Z
            if not date_str.endswith("Z"):
                date_str += "Z"
            return date_str

        # Parse YYYY-MM-DD format
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%dT00:00:00Z")
        except ValueError:
            raise ValueError(
                f"Date format not recognized: {date_str}. "
                "Use YYYY-MM-DD or ISO format."
            )

    def _validate_bounding_box(
        self, min_lon: float, min_lat: float, max_lon: float, max_lat: float
    ) -> None:
        """
        Validate bounding box parameters.
        
        Args:
            min_lon, min_lat, max_lon, max_lat: Bounding box coordinates
        
        Raises:
            ValueError: If invalid
        """
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError("Longitude must be -180 to 180")

        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("Latitude must be -90 to 90")

        if min_lon >= max_lon:
            raise ValueError("min_lon must be less than max_lon")

        if min_lat >= max_lat:
            raise ValueError("min_lat must be less than max_lat")

    def _extract_temporal_resolution(self, umm: Dict[str, Any]) -> str:
        """Extract temporal resolution from UMM metadata."""
        temporal_info = umm.get("TemporalExtents", [{}])[0]
        temporal_resolution = temporal_info.get("TemporalResolution", {})
        return temporal_resolution.get("value", "Unknown")

    def _extract_spatial_resolution(self, umm: Dict[str, Any]) -> str:
        """Extract spatial resolution from UMM metadata."""
        spatial_info = umm.get("SpatialExtent", {})
        resolution = spatial_info.get("HorizontalSpatialDomain", {}).get(
            "ResolutionAndCoordinateSystem", {}
        )
        if resolution:
            # Try different resolution formats
            val = (
                resolution.get("HorizontalDataResolution", [{}])[0]
                .get("XDimension", None)
            )
            if val:
                return str(val)

        return "Unknown"

    def _extract_data_format(self, umm: Dict[str, Any]) -> str:
        """Extract data format from UMM metadata."""
        archive_info = umm.get("ArchiveAndDistributionInformation", {})
        formats = archive_info.get("FileDistributionInformation", [])
        if formats:
            return formats[0].get("Format", "Unknown")
        return "Unknown"