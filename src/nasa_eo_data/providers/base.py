"""
Defines the interface that all data providers must implement.

Example:
    >>> from nasa_eo_data.providers import EarthAccessProvider
    >>> provider = EarthAccessProvider()
    >>> granules, total = provider.search(
    ...     product="ECOSTRESS",
    ...     bounding_box=(-120, 30, -100, 40),
    ...     start_date="2023-01-01",
    ...     end_date="2023-12-31"
    ... )
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseProvider(ABC):
    """
    Abstract base class for Earth observation data providers.

    Providers handle searches across different data repositories and APIs.
    Each provider must implement:
    - search: Query for granules/datasets
    - get_metadata: Get detailed information about a dataset
    """

    @abstractmethod
    def search(
        self,
        product: str,
        bounding_box: Optional[tuple[float, float, float, float]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs,
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        Search for granules matching the query parameters.

        Args:
            product: Product short name (e.g., "ECOSTRESS_L2_LSTE", "MODIS_TERRA_L2")
            bounding_box: (min_lon, min_lat, max_lon, max_lat) or None for global
            start_date: Start date in YYYY-MM-DD format or ISO format
            end_date: End date in YYYY-MM-DD format or ISO format
            **kwargs: Additional provider-specific parameters
                - page_size: Results per page (default 2000)
                - max_results: Maximum total results to return
                - cloud_cover: Maximum cloud cover percentage (0-100)
                - quality_flags: Quality filtering parameters

        Returns:
            Tuple of (results_list, total_count)
            - results_list: List of granule dictionaries
            - total_count: Total granules matching query (may exceed results_list length)

        Raises:
            ValueError: If parameters are invalid
            APIError: If provider API fails
            AuthenticationError: If authentication fails

        Example:
            >>> provider = CMRProvider(auth)
            >>> results, total = provider.search(
            ...     product="ECOSTRESS_L2_LSTE",
            ...     bounding_box=(-120, 30, -100, 40),
            ...     start_date="2023-01-01",
            ...     end_date="2023-12-31",
            ...     page_size=2000,
            ...     max_results=10000,
            ... )
            >>> print(f"Found {total} granules, returned {len(results)}")
        """
        pass

    @abstractmethod
    def get_metadata(self, product: str) -> Dict[str, Any]:
        """
        Get metadata about a product.

        Args:
            product: Product short name or ID

        Returns:
            Dictionary with product metadata:
            {
                "short_name": str,
                "long_name": str,
                "description": str,
                "provider": str,
                "temporal_resolution": str,  # e.g., "8-day", "daily"
                "spatial_resolution": str,   # e.g., "70 meters"
                "bands": List[Dict],         # Available bands/layers
                "data_format": str,          # e.g., "NetCDF4", "GeoTIFF"
            }

        Raises:
            ValueError: If product not found
            APIError: If provider API fails

        Example:
            >>> provider = CMRProvider(auth)
            >>> metadata = provider.get_metadata("ECOSTRESS_L2_LSTE")
            >>> print(f"Resolution: {metadata['spatial_resolution']}")
        """
        pass

    @abstractmethod
    def validate_product(self, product: str) -> bool:
        """
        Check if a product exists in this provider.

        Args:
            product: Product short name

        Returns:
            True if product exists, False otherwise

        Example:
            >>> provider = CMRProvider(auth)
            >>> if provider.validate_product("ECOSTRESS_L2_LSTE"):
            ...     print("Valid product")
        """
        pass


# Type hints for common return structures
GranuleResult = Dict[str, Any]
ProductMetadata = Dict[str, Any]
