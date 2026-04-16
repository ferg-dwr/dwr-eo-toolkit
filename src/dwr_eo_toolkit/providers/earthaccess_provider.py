"""
NASA EO Data Provider using earthaccess library.

Simple, clean integration with NASA's official earthaccess library.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import earthaccess

from dwr_eo_toolkit.providers.adapters.base import InstrumentAdapter
from dwr_eo_toolkit.providers.adapters.ecostress import ECOSTRESSAdapter
from dwr_eo_toolkit.providers.adapters.modis import MODISAdapter
from dwr_eo_toolkit.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Registry for instrument adapters."""

    def __init__(self):
        self.adapters: Dict[str, InstrumentAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        """Register built-in adapters."""
        ecostress_adapter = ECOSTRESSAdapter()
        modis_adapter = MODISAdapter()

        for keyword in ecostress_adapter.get_keywords():
            self.adapters[keyword.lower()] = ecostress_adapter

        for keyword in modis_adapter.get_keywords():
            self.adapters[keyword.lower()] = modis_adapter

    def get_adapter(self, product: str) -> Optional[InstrumentAdapter]:
        """Get adapter for product keyword."""
        return self.adapters.get(product.lower())


class EarthAccessProvider(BaseProvider):
    """
    NASA EO Data Provider using earthaccess library.

    Simple interface for searching and downloading NASA Earth observation data.

    Example:
        >>> provider = EarthAccessProvider()
        >>> granules, total = provider.search(
        ...     product="ECOSTRESS",
        ...     bounding_box=(-122.82, 36.78, -120.94, 38.25),
        ...     start_date="2020-01-01",
        ...     end_date="2026-04-13"
        ... )
        >>> files = provider.download(granules, "./data")
    """

    def __init__(self):
        """Initialize provider with earthaccess."""
        self.adapter_registry = AdapterRegistry()
        self._ensure_authenticated()

    def _ensure_authenticated(self) -> None:
        """Ensure we're logged in with earthaccess."""
        if not earthaccess.login():
            logger.info("Logging in to earthaccess...")
            earthaccess.login(strategy="environment")
            logger.info("✅ Authenticated with earthaccess")

    def get_adapter(self, product: str):
        """Get adapter for a product."""
        return self.adapter_registry.get_adapter(product)

    def search(
        self,
        product: str,
        bounding_box: Optional[Tuple[float, float, float, float]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search for granules.

        Args:
            product: Product keyword (e.g., "ECOSTRESS")
            bounding_box: (min_lon, min_lat, max_lon, max_lat) or None
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            **kwargs: Additional parameters

        Returns:
            (granules_list, total_count)
        """
        logger.debug(f"Searching for product: {product}")

        # Get adapter if available
        adapter = self.get_adapter(product)

        # Get short_name from adapter, or use product as keyword
        if adapter:
            metadata = adapter.get_metadata()
            short_name = metadata.short_name
            search_param = {"short_name": short_name}
            logger.debug(f"Using adapter short_name: {short_name}")
        else:
            search_param = {"keyword": product}
            logger.debug(f"Using keyword: {product}")

        # Build search parameters
        search_params = {
            **search_param,
            "count": kwargs.get("max_results", 2000),
        }

        # Add spatial bounds if provided
        if bounding_box:
            min_lon, min_lat, max_lon, max_lat = bounding_box
            search_params["bounding_box"] = bounding_box
            logger.debug(f"Searching with bounding_box: {bounding_box}")

        # Add temporal range if provided
        if start_date or end_date:
            search_params["temporal"] = (start_date, end_date)
            logger.debug(f"Searching with temporal: {start_date} to {end_date}")

        # Search using earthaccess
        try:
            logger.info(f"Searching earthaccess for {product}...")
            granules = earthaccess.search_data(**search_params)

            logger.info(f"Found {len(granules)} granules for {product}")

            # Post-process with adapter if available
            if adapter and granules:
                results = [{"umm": g.get("umm", {})} for g in granules]
                results = adapter.post_process_granules(results)
                return results, len(results)

            return granules, len(granules)

        except Exception as e:
            logger.error(f"Search failed for {product}: {e}")
            raise

    def download(
        self, granules: List[Dict[str, Any]], output_dir: str, **kwargs
    ) -> List[str]:
        """
        Download granules.

        Args:
            granules: List of granules from search()
            output_dir: Directory to save files
            **kwargs: Additional parameters

        Returns:
            List of downloaded file paths
        """
        logger.info(f"Downloading {len(granules)} granules to {output_dir}...")

        try:
            files = earthaccess.download(
                granules, output_dir, threads=kwargs.get("max_workers", 4)
            )

            logger.info(f"✅ Downloaded {len(files)} files")
            return files

        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise

    def get_metadata(self, product: str) -> Dict[str, Any]:
        """Get metadata about a product."""
        adapter = self.get_adapter(product)
        if adapter:
            metadata = adapter.get_metadata()
            return {
                "short_name": metadata.short_name,
                "long_name": metadata.long_name,
                "description": metadata.description,
                "provider": metadata.provider,
                "processing_level": metadata.processing_level,
                "spatial_resolution": metadata.spatial_resolution,
                "temporal_resolution": metadata.temporal_resolution,
            }
        return {"keyword": product}

    def validate_product(self, product: str) -> bool:
        """
        Validate that a product is available.

        Args:
            product: Product keyword or short name

        Returns:
            True if product has an adapter or can be searched, False otherwise

        Example:
            >>> provider = EarthAccessProvider()
            >>> if provider.validate_product("ECOSTRESS"):
            ...     print("Valid product")
        """
        # Check if we have an adapter for this product
        adapter = self.get_adapter(product)
        if adapter:
            return True

        # If no adapter, assume it's a valid keyword (earthaccess will handle it)
        # This allows searching by keyword even without a specific adapter
        logger.debug(f"No adapter for {product}, but allowing search by keyword")
        return True
