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

import requests

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
        ...     product="ECOSTRESS",
        ...     bounding_box=(-122.82, 36.78, -120.94, 38.25),
        ...     start_date="2020-01-01",
        ...     end_date="2026-04-13",
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
        self.base_url = "https://cmr.earthdata.nasa.gov"

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
            product: Product keyword (e.g., "ECOSTRESS", "MODIS", "VIIRS")
                     CMR will search and find the matching short_name
            bounding_box: (min_lon, min_lat, max_lon, max_lat) or None
            start_date: Start date in YYYY-MM-DD or ISO format
            end_date: End date in YYYY-MM-DD or ISO format
            **kwargs:
                page_size: Results per page (default 2000, max 2000)
                max_results: Maximum total results (default None = all)
                cloud_cover: Max cloud cover 0-100 (default None) - NOTE: Not yet implemented
        
        Returns:
            (results_list, total_count)
        
        Raises:
            ValueError: If parameters invalid
            AuthenticationError: If auth fails
            APIError: If CMR API fails
        """
        # First, get the actual short_name from collections
        try:
            short_name = self._get_short_name(product)
            if not short_name:
                raise ValueError(f"Product '{product}' not found in CMR collections")
        except Exception as e:
            logger.error(f"Failed to get short_name for {product}: {e}")
            raise

        # Build granule search parameters
        params = self._build_search_params(
            product=short_name,
            bounding_box=bounding_box,
            start_date=start_date,
            end_date=end_date,
            **kwargs,
        )

        logger.debug(f"Searching CMR for {product} (short_name: {short_name}) with params: {params}")

        # Search CMR using custom method that handles feed.entry format
        try:
            results, total = self._search_granules(
                params=params,
                page_size=kwargs.get("page_size", 2000),
                max_results=kwargs.get("max_results", None),
            )

            logger.info(f"Found {total} granules matching {product}")
            return results, total

        except Exception as e:
            logger.error(f"CMR search failed for {product}: {e}")
            raise

    def _search_granules(
        self,
        params: Dict[str, Any],
        page_size: int = 2000,
        max_results: Optional[int] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Execute paginated granule search against CMR.
        
        Handles the feed.entry response format from CMR.
        
        Args:
            params: Search parameters
            page_size: Results per page
            max_results: Maximum total results
        
        Returns:
            (results, total_hits) tuple
        """
        all_results = []
        total_hits = None
        page_num = 1
        
        while True:
            # Add pagination parameter
            request_params = dict(params)
            request_params["page_size"] = page_size
            request_params["page_num"] = page_num
            
            # Make request
            url = f"{self.base_url}/search/granules.json"
            response = requests.get(
                url,
                params=request_params,
                headers={"Authorization": f"Bearer {self.auth.get_bearer_token()}"},
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"CMR search failed: {response.status_code} - {response.text}")
            
            data = response.json()
            
            # Extract results from feed.entry format
            feed = data.get('feed', {})
            entries = feed.get('entry', [])
            all_results.extend(entries)
            
            # Get total hits from first response
            if total_hits is None:
                total_hits = int(feed.get('opensearch:totalResults', 0))
                logger.debug(f"Total hits: {total_hits}")
            
            # Check if we're done
            if not entries or (max_results and len(all_results) >= max_results):
                if max_results and len(all_results) > max_results:
                    all_results = all_results[:max_results]
                break
            
            page_num += 1
        
        return all_results, total_hits or 0

    def get_metadata(self, product: str) -> Dict[str, Any]:
        """
        Get metadata about a CMR collection.
        
        Args:
            product: Product keyword (e.g., "ECOSTRESS", "MODIS")
        
        Returns:
            Metadata dictionary with collection information
        
        Raises:
            ValueError: If product not found
            APIError: If CMR API fails
        """
        if product in self._product_cache:
            return self._product_cache[product]

        logger.debug(f"Fetching metadata for {product}")

        try:
            short_name = self._get_short_name(product)
            if not short_name:
                raise ValueError(f"Product '{product}' not found in CMR")

            metadata = {
                "short_name": short_name,
                "long_name": f"Collection {short_name}",
                "description": f"CMR Collection: {short_name}",
                "provider": "Unknown",
                "processing_level": "Unknown",
                "temporal_resolution": "Unknown",
                "spatial_resolution": "Unknown",
                "data_format": "NetCDF4",
                "doi": "",
                "related_urls": [],
            }

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
            product: Product keyword or short name
        
        Returns:
            True if valid, False otherwise
        """
        try:
            self._get_short_name(product)
            return True
        except (ValueError, Exception):
            return False

    def _get_short_name(self, product: str) -> Optional[str]:
        """
        Get the actual CMR short_name for a product keyword.
        
        Uses direct requests.get() to avoid bearer token issues.
        Collections endpoint is public and doesn't need authentication.
        
        Args:
            product: Product keyword (e.g., "ECOSTRESS")
        
        Returns:
            The CMR short_name (e.g., "ECO_L2T_LSTE") or None if not found
        """
        try:
            # Use requests directly without bearer token
            url = f"{self.base_url}/search/collections.json"
            response = requests.get(
                url,
                params={"keyword": product},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Collections search failed: {response.status_code}")
                return None
            
            data = response.json()
            
            # Handle feed.entry format
            if 'feed' in data and 'entry' in data['feed']:
                entries = data['feed'].get('entry', [])
                if entries:
                    return entries[0].get('short_name')
            
            # Handle items format
            if 'items' in data and data['items']:
                return data['items'][0].get('umm', {}).get('ShortName')
            
            return None

        except Exception as e:
            logger.error(f"Failed to get short_name for {product}: {e}")
            return None

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
            product: Product short_name (from CMR)
            bounding_box: (min_lon, min_lat, max_lon, max_lat)
            start_date: ISO or YYYY-MM-DD format
            end_date: ISO or YYYY-MM-DD format
            **kwargs: Additional parameters (cloud_cover is noted but not yet supported)
        
        Returns:
            Dictionary of CMR API parameters for granule search
        """
        params = {
            "short_name": product,
        }

        if bounding_box:
            min_lon, min_lat, max_lon, max_lat = bounding_box
            self._validate_bounding_box(min_lon, min_lat, max_lon, max_lat)
            params["bounding_box"] = f"{min_lon},{min_lat},{max_lon},{max_lat}"

        if start_date or end_date:
            temporal = self._build_temporal_range(start_date, end_date)
            if temporal:
                params["temporal"] = temporal

        # Note: cloud_cover parameter is not yet implemented
        # CMR's attribute[] syntax varies by product and is complex
        if "cloud_cover" in kwargs:
            logger.warning("cloud_cover filtering not yet implemented")

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

        start_iso = self._normalize_date(start_date) if start_date else ""
        end_iso = self._normalize_date(end_date) if end_date else ""

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

        if "T" in date_str:
            if not date_str.endswith("Z"):
                date_str += "Z"
            return date_str

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