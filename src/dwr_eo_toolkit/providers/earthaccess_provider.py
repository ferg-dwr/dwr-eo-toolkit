"""
NASA EO Data Provider using earthaccess library.

Simple, clean integration with NASA's official earthaccess library.
"""

import logging
from typing import Any

import earthaccess

from dwr_eo_toolkit.providers.adapters.base import InstrumentAdapter
from dwr_eo_toolkit.providers.adapters.ecostress import ECOSTRESSAdapter
from dwr_eo_toolkit.providers.adapters.modis import MODISAdapter
from dwr_eo_toolkit.providers.adapters.opera_rtc_s1 import OperaRTCS1Adapter
from dwr_eo_toolkit.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """Registry for instrument adapters."""

    def __init__(self) -> None:
        self.adapters: dict[str, InstrumentAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        """Register built-in adapters."""
        for adapter in (ECOSTRESSAdapter(), MODISAdapter(), OperaRTCS1Adapter()):
            for keyword in adapter.get_keywords():
                key = keyword.lower()
                if key in self.adapters:
                    # A flat dict means a duplicate silently reroutes searches
                    # to the wrong collection. Surface it instead.
                    raise ValueError(
                        f"Adapter keyword collision on {key!r}: "
                        f"{type(self.adapters[key]).__name__} and "
                        f"{type(adapter).__name__} both claim it."
                    )
                self.adapters[key] = adapter

    def get_adapter(self, product: str) -> InstrumentAdapter | None:
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

    def __init__(self) -> None:
        """Initialize provider with earthaccess."""
        self.adapter_registry = AdapterRegistry()
        self._ensure_authenticated()

    def _ensure_authenticated(self) -> None:
        """Ensure we're logged in with earthaccess."""
        if not earthaccess.login():
            logger.info("Logging in to earthaccess...")
            earthaccess.login(strategy="environment")
            logger.info("Authenticated with earthaccess")

    def get_adapter(self, product: str) -> InstrumentAdapter | None:
        """Get adapter for a product."""
        return self.adapter_registry.get_adapter(product)

    def search(
        self,
        product: str,
        bounding_box: tuple[float, ...] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        **kwargs: Any,
    ) -> tuple[list[Any], int]:
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

        # Explicit short_name overrides adapter/keyword resolution. Needed for
        # adapters covering more than one collection -- reaching
        # OPERA_L2_RTC-S1-STATIC_V1 is only possible this way.
        if kwargs.get("short_name"):
            search_params.pop("keyword", None)
            search_params["short_name"] = kwargs["short_name"]
            logger.debug(f"Overriding with short_name: {kwargs['short_name']}")

        # Without a version, CMR returns every version of a collection
        # together, so repeated processings of one acquisition come back as
        # separate granules and any count taken from the result is inflated.
        if kwargs.get("version"):
            search_params["version"] = kwargs["version"]
            logger.debug(f"Restricting to version: {kwargs['version']}")

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

            # Return raw granules (DataGranule objects) for download() to work
            # Don't transform to dicts - that breaks earthaccess.download()
            return granules, len(granules)

        except Exception as e:
            logger.error(f"Search failed for {product}: {e}")
            raise

    def download(self, granules: list[Any], output_dir: str, **kwargs: Any) -> list[str]:
        """
        Download granules.

        Args:
            granules: List of granules from search() (must be DataGranule objects)
            output_dir: Directory to save files
            **kwargs: Additional parameters (max_workers, show_progress, etc.)

        Returns:
            List of downloaded file paths
        """
        logger.info(f"Downloading {len(granules)} granules to {output_dir}...")

        try:
            # earthaccess.download signature:
            # download(granules, local_path=None, provider=None, threads=8, ...)
            files = earthaccess.download(
                granules,
                local_path=str(output_dir),  # Use 'local_path' parameter name!
                threads=kwargs.get("max_workers", 4),
            )

            logger.info(f"✅ Downloaded {len(files)} files")
            return [str(f) for f in files]

        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise

    def get_metadata(self, product: str) -> dict[str, Any]:
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
