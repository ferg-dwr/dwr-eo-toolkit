"""
CMR Provider with Adapter Pattern (Phase 2C Design).

This updated CMRProvider delegates instrument-specific logic to specialized adapters.
This design makes it easy to add new instruments without modifying CMRProvider itself.

Architecture:
  CMRProvider (generic CMR interface)
    ↓
  Adapter Selection (based on product keyword)
    ↓
  Specific Adapter (ECOSTRESS, MODIS, Landsat, etc.)
    ↓
  CMR API (search, metadata, filtering)
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

import requests

from nasa_eo_data.core.client import CMRClient
from nasa_eo_data.core.auth import EarthDataLoginAuth
from nasa_eo_data.providers.base import BaseProvider
from nasa_eo_data.providers.cmr_adapters.base import CMRAdapter
from nasa_eo_data.providers.cmr_adapters.ecostress import ECOSTRESSAdapter
from nasa_eo_data.providers.cmr_adapters.modis import MODISAdapter

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Registry for mapping product keywords to adapters."""

    def __init__(self):
        """Initialize adapter registry with built-in adapters."""
        self.adapters: Dict[str, CMRAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        """Register built-in adapters."""
        ecostress_adapter = ECOSTRESSAdapter()
        modis_adapter = MODISAdapter()
        
        # Register by keyword
        for keyword in ecostress_adapter.get_keywords():
            self.adapters[keyword.lower()] = ecostress_adapter
        
        for keyword in modis_adapter.get_keywords():
            self.adapters[keyword.lower()] = modis_adapter

    def register_adapter(self, adapter: CMRAdapter) -> None:
        """
        Register a custom adapter.
        
        Args:
            adapter: CMRAdapter instance
        """
        for keyword in adapter.get_keywords():
            self.adapters[keyword.lower()] = adapter
            logger.info(f"Registered adapter for keyword: {keyword}")

    def get_adapter(self, product: str) -> Optional[CMRAdapter]:
        """
        Get adapter for a product keyword.
        
        Args:
            product: Product keyword (case-insensitive)
        
        Returns:
            CMRAdapter instance or None if not found
        """
        adapter = self.adapters.get(product.lower())
        if adapter:
            logger.debug(f"Found adapter for product: {product}")
        return adapter

    def list_adapters(self) -> Dict[str, str]:
        """
        List all registered adapters.
        
        Returns:
            Dict of keyword -> adapter class name
        """
        return {
            keyword: adapter.__class__.__name__
            for keyword, adapter in self.adapters.items()
        }


class CMRProvider(BaseProvider):
    """    
    Example:
        >>> provider = CMRProvider(auth)
        >>> adapter = provider.get_adapter("ECOSTRESS")
        >>> metadata = adapter.get_metadata()
        >>> results, total = provider.search(product="ECOSTRESS", ...)
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
        self.adapter_registry = AdapterRegistry()

    def get_adapter(self, product: str) -> Optional[CMRAdapter]:
        """
        Get the adapter for a product.
        
        Args:
            product: Product keyword
        
        Returns:
            CMRAdapter instance or None
        """
        return self.adapter_registry.get_adapter(product)

    def search(
        self,
        product: str,
        bounding_box: Optional[tuple[float, float, float, float]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Search CMR for granules (now with adapter support).
        
        The adapter (if found) validates instrument-specific constraints
        and processes parameters before sending to CMR.
        
        Args:
            product: Product keyword (e.g., "ECOSTRESS")
            bounding_box: (min_lon, min_lat, max_lon, max_lat) or None
            start_date: Start date in YYYY-MM-DD or ISO format
            end_date: End date in YYYY-MM-DD or ISO format
            **kwargs: Additional parameters (passed to adapter)
        
        Returns:
            (results_list, total_count)
        """
        # Get adapter for this product (optional)
        adapter = self.get_adapter(product)
        
        if adapter:
            logger.debug(f"Using {adapter.__class__.__name__} for {product}")
            
            # Adapter validates instrument-specific constraints
            if start_date and end_date:
                adapter.validate_temporal_range(start_date, end_date)
            
            if bounding_box:
                min_lon, min_lat, max_lon, max_lat = bounding_box
                adapter.validate_spatial_bounds(min_lon, min_lat, max_lon, max_lat)
            
            # Let adapter process product-specific parameters
            adapter_params = adapter.process_search_params(**kwargs)
            # Merge adapter-specific params if needed
        
        # Get short_name (same as Phase 2B)
        try:
            short_name = self._get_short_name(product)
            if not short_name:
                raise ValueError(f"Product '{product}' not found in CMR collections")
        except Exception as e:
            logger.error(f"Failed to get short_name for {product}: {e}")
            raise

        # Build search parameters
        params = self._build_search_params(
            product=short_name,
            bounding_box=bounding_box,
            start_date=start_date,
            end_date=end_date,
            **kwargs,
        )

        # Search CMR
        try:
            results, total = self._search_granules(
                params=params,
                page_size=kwargs.get("page_size", 2000),
                max_results=kwargs.get("max_results", None),
            )

            # Post-process with adapter if available
            if adapter:
                results = adapter.post_process_granules(results)

            logger.info(f"Found {total} granules matching {product}")
            return results, total

        except Exception as e:
            logger.error(f"CMR search failed for {product}: {e}")
            raise

    def get_metadata(self, product: str) -> Dict[str, Any]:
        """
        Get metadata about a CMR collection.
        
        Uses adapter metadata if available; otherwise falls back to generic.
        
        Args:
            product: Product keyword
        
        Returns:
            Metadata dictionary
        """
        if product in self._product_cache:
            return self._product_cache[product]

        logger.debug(f"Fetching metadata for {product}")

        try:
            # Try to use adapter
            adapter = self.get_adapter(product)
            if adapter:
                adapter_metadata = adapter.get_metadata()
                metadata = {
                    "short_name": adapter_metadata.short_name,
                    "long_name": adapter_metadata.long_name,
                    "description": adapter_metadata.description,
                    "provider": adapter_metadata.provider,
                    "processing_level": adapter_metadata.processing_level,
                    "temporal_resolution": adapter_metadata.temporal_resolution,
                    "spatial_resolution": adapter_metadata.spatial_resolution,
                    "data_format": adapter_metadata.data_format,
                    "doi": adapter_metadata.doi,
                    "keywords": adapter_metadata.keywords,
                    "related_urls": adapter_metadata.related_urls,
                }
            else:
                # Fallback to generic metadata
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
                    "data_format": "Unknown",
                    "doi": "",
                    "keywords": [],
                    "related_urls": [],
                }

            self._product_cache[product] = metadata
            logger.debug(f"Retrieved metadata for {product}")
            return metadata

        except Exception as e:
            logger.error(f"Failed to get metadata for {product}: {e}")
            raise

    def validate_product(self, product: str) -> bool:
        """Validate that a product exists in CMR."""
        try:
            self._get_short_name(product)
            return True
        except (ValueError, Exception):
            return False

    # --- Below: Same as Phase 2B implementation ---
    
    def _search_granules(
        self,
        params: Dict[str, Any],
        page_size: int = 2000,
        max_results: Optional[int] = None,
    ) -> tuple[List[Dict[str, Any]], int]:
        """Execute paginated granule search (Phase 2B implementation)."""
        all_results = []
        total_hits = None
        page_num = 1
        
        while True:
            request_params = dict(params)
            request_params["page_size"] = page_size
            request_params["page_num"] = page_num
            
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
            feed = data.get('feed', {})
            entries = feed.get('entry', [])
            all_results.extend(entries)
            
            if total_hits is None:
                total_hits = int(feed.get('opensearch:totalResults', 0))
                logger.debug(f"Total hits: {total_hits}")
            
            if not entries or (max_results and len(all_results) >= max_results):
                if max_results and len(all_results) > max_results:
                    all_results = all_results[:max_results]
                break
            
            page_num += 1
        
        return all_results, total_hits or 0

    def _get_short_name(self, product: str) -> Optional[str]:
        """Get CMR short_name (Phase 2B implementation)."""
        try:
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
            
            if 'feed' in data and 'entry' in data['feed']:
                entries = data['feed'].get('entry', [])
                if entries:
                    return entries[0].get('short_name')
            
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
        """Build CMR search parameters (Phase 2B implementation)."""
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

        if "cloud_cover" in kwargs:
            logger.warning("cloud_cover filtering not yet implemented")

        return params

    def _build_temporal_range(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Optional[str]:
        """Build temporal range (Phase 2B implementation)."""
        if not start_date and not end_date:
            return None

        start_iso = self._normalize_date(start_date) if start_date else ""
        end_iso = self._normalize_date(end_date) if end_date else ""

        return f"{start_iso},{end_iso}"

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to ISO format (Phase 2B implementation)."""
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

    def _validate_bounding_box(self,
                               min_lon: float,
                               min_lat: float,
                               max_lon: float,
                               max_lat: float) -> None:
        """Validate bounding box (Phase 2B implementation)."""
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError("Longitude must be -180 to 180")

        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("Latitude must be -90 to 90")

        if min_lon >= max_lon:
            raise ValueError("min_lon must be less than max_lon")

        if min_lat >= max_lat:
            raise ValueError("min_lat must be less than max_lat")