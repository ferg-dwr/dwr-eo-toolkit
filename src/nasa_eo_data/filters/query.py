"""
Query builder with fluent interface for composing Earth observation searches.

Provides a clean, chainable API for building complex queries.

Example:
    >>> from nasa_eo_data.filters import Query
    >>> query = (Query()
    ...     .with_product("ECOSTRESS_L2_LSTE")
    ...     .with_spatial_bounds(-120, 30, -100, 40)
    ...     .with_date_range("2023-01-01", "2023-12-31")
    ...     .with_cloud_cover(10)
    ... )
    >>> results, total = query.execute(provider)
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

from nasa_eo_data.filters.base import Filter
from nasa_eo_data.filters.spatial import BoundingBox, Polygon, PointBuffer
from nasa_eo_data.filters.temporal import DateRange, Season
from nasa_eo_data.filters.product import CloudCover, QualityFlag, ProcessingLevel

logger = logging.getLogger(__name__)


class Query:
    """
    Fluent query builder for Earth observation searches.
    
    Supports method chaining for intuitive query construction.
    Converts all filters into provider-specific parameters.
    
    Example:
        >>> query = (Query()
        ...     .with_product("ECOSTRESS_L2_LSTE")
        ...     .with_spatial_bounds(-120, 30, -100, 40)
        ...     .with_date_range("2023-01-01", "2023-12-31")
        ...     .with_cloud_cover(10)
        ... )
        >>> results, total = query.execute(provider)
    """

    def __init__(
        self,
        product: Optional[str] = None,
        filters: Optional[List[Filter]] = None,
    ):
        """
        Initialize query builder.
        
        Args:
            product: Product short name (optional, can set with with_product())
            filters: List of Filter objects (optional)
        """
        self.product = product
        self.filters: List[Filter] = filters or []

    # ==================== Spatial Filters ====================

    def with_spatial_bounds(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
    ) -> "Query":
        """
        Add bounding box spatial constraint.
        
        Args:
            min_lon: Minimum longitude (-180 to 180)
            min_lat: Minimum latitude (-90 to 90)
            max_lon: Maximum longitude
            max_lat: Maximum latitude
        
        Returns:
            self for method chaining
        
        Raises:
            ValueError: If coordinates invalid
        
        Example:
            >>> query.with_spatial_bounds(-120, 30, -100, 40)
        """
        bbox = BoundingBox(min_lon, min_lat, max_lon, max_lat)
        self.filters.append(bbox)
        logger.debug(f"Added spatial filter: {bbox}")
        return self

    def with_polygon(self, coordinates: list) -> "Query":
        """
        Add polygon spatial constraint (future).
        
        Args:
            coordinates: List of (lon, lat) tuples defining polygon
        
        Returns:
            self for method chaining
        
        Note:
            This is a future feature. Currently raises NotImplementedError.
        """
        polygon = Polygon(coordinates)
        self.filters.append(polygon)
        logger.debug(f"Added polygon filter")
        return self

    def with_point_buffer(self, lon: float, lat: float, radius_km: float) -> "Query":
        """
        Add point + radius spatial constraint (future).
        
        Args:
            lon: Center longitude
            lat: Center latitude
            radius_km: Search radius in kilometers
        
        Returns:
            self for method chaining
        
        Note:
            This is a future feature. Currently raises NotImplementedError.
        """
        point_buf = PointBuffer(lon, lat, radius_km)
        self.filters.append(point_buf)
        logger.debug(f"Added point buffer filter: {lon}, {lat}, {radius_km}km")
        return self

    # ==================== Temporal Filters ====================

    def with_date_range(self, start_date: str, end_date: str) -> "Query":
        """
        Add date range temporal constraint.
        
        Args:
            start_date: Start date (YYYY-MM-DD or ISO format)
            end_date: End date (YYYY-MM-DD or ISO format)
        
        Returns:
            self for method chaining
        
        Raises:
            ValueError: If dates invalid or start > end
        
        Example:
            >>> query.with_date_range("2023-01-01", "2023-12-31")
        """
        date_range = DateRange(start_date, end_date)
        self.filters.append(date_range)
        logger.debug(f"Added temporal filter: {date_range}")
        return self

    def with_season(self, season: str, years: List[int] = None) -> "Query":
        """
        Add seasonal constraint (future).
        
        Args:
            season: 'spring', 'summer', 'fall', or 'winter'
            years: Years to include (optional)
        
        Returns:
            self for method chaining
        
        Note:
            This is a future feature. Currently raises NotImplementedError.
        """
        season_filter = Season(season, years)
        self.filters.append(season_filter)
        logger.debug(f"Added season filter: {season}")
        return self

    # ==================== Product Filters ====================

    def with_cloud_cover(self, max_percent: int) -> "Query":
        """
        Add cloud cover constraint.
        
        Args:
            max_percent: Maximum cloud cover percentage (0-100)
        
        Returns:
            self for method chaining
        
        Raises:
            ValueError: If max_percent not in 0-100
        
        Example:
            >>> query.with_cloud_cover(10)  # Max 10% cloud
        """
        cloud = CloudCover(max_percent)
        self.filters.append(cloud)
        logger.debug(f"Added cloud cover filter: {max_percent}%")
        return self

    def with_quality_flag(self, flag_name: str, flag_value: str) -> "Query":
        """
        Add quality flag constraint.
        
        Args:
            flag_name: Quality flag name (e.g., 'LST_QC')
            flag_value: Expected quality value (e.g., 'good')
        
        Returns:
            self for method chaining
        
        Example:
            >>> query.with_quality_flag('LST_QC', 'good')
        """
        qc = QualityFlag(flag_name, flag_value)
        self.filters.append(qc)
        logger.debug(f"Added quality filter: {flag_name}={flag_value}")
        return self

    def with_processing_level(self, level: str) -> "Query":
        """
        Add processing level constraint.
        
        Args:
            level: Processing level ('L1B', 'L2', 'L3', 'L4')
        
        Returns:
            self for method chaining
        
        Example:
            >>> query.with_processing_level('L2')
        """
        proc_level = ProcessingLevel(level)
        self.filters.append(proc_level)
        logger.debug(f"Added processing level filter: {level}")
        return self

    # ==================== Product Selection ====================

    def with_product(self, product: str) -> "Query":
        """
        Set product to search for.
        
        Args:
            product: Product short name (e.g., 'ECOSTRESS_L2_LSTE')
        
        Returns:
            self for method chaining
        
        Example:
            >>> query.with_product('ECOSTRESS_L2_LSTE')
        """
        self.product = product
        logger.debug(f"Set product: {product}")
        return self

    # ==================== Execution ====================

    def execute(self, provider) -> Tuple[List[Dict[str, Any]], int]:
        """
        Execute query against a provider.
        
        Args:
            provider: Provider instance (e.g., CMRProvider)
        
        Returns:
            Tuple of (results_list, total_count)
        
        Raises:
            ValueError: If no product set
            APIError: If provider API fails
        
        Example:
            >>> results, total = query.execute(provider)
            >>> print(f"Found {total} granules, retrieved {len(results)}")
        """
        if not self.product:
            raise ValueError("Product must be set before executing query")

        # Build provider parameters from filters
        params = {"product": self.product}
        for filter_obj in self.filters:
            filter_params = filter_obj.to_params()
            params.update(filter_params)

        logger.info(f"Executing query for {self.product} with {len(self.filters)} filters")
        logger.debug(f"Query parameters: {params}")

        # Execute against provider
        try:
            results, total = provider.search(**params)
            logger.info(f"Query succeeded: {total} granules found")
            return results, total
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    # ==================== Query Inspection ====================

    def filters_summary(self) -> str:
        """
        Get summary of all filters in query.
        
        Returns:
            Human-readable filter summary
        
        Example:
            >>> query.filters_summary()
            'Product: ECOSTRESS_L2_LSTE, Filters: BoundingBox(...), DateRange(...)'
        """
        filter_strs = [str(f) for f in self.filters]
        filters_str = ", ".join(filter_strs) if filter_strs else "None"
        return f"Product: {self.product}, Filters: {filters_str}"

    def to_params(self) -> Dict[str, Any]:
        """
        Convert query to provider parameters.
        
        Useful for debugging or logging.
        
        Returns:
            Dictionary of all parameters
        
        Example:
            >>> params = query.to_params()
            >>> print(params)
            {'product': 'ECOSTRESS_L2_LSTE', 'bounding_box': (...), ...}
        """
        if not self.product:
            raise ValueError("Product must be set")

        params = {"product": self.product}
        for filter_obj in self.filters:
            filter_params = filter_obj.to_params()
            params.update(filter_params)

        return params

    def __repr__(self) -> str:
        """String representation."""
        return f"Query({self.filters_summary()})"

    def __str__(self) -> str:
        """User-friendly string representation."""
        return self.filters_summary()

    # ==================== Builder Shortcuts ====================

    @staticmethod
    def for_product(product: str) -> "Query":
        """
        Create query for specific product (convenience method).
        
        Args:
            product: Product short name
        
        Returns:
            Query instance with product set
        
        Example:
            >>> query = Query.for_product('ECOSTRESS_L2_LSTE')
        """
        return Query(product=product)

    def copy(self) -> "Query":
        """
        Create a copy of this query.
        
        Useful for creating similar queries with minor modifications.
        
        Returns:
            New Query instance with same product and filters
        
        Example:
            >>> query2 = query1.copy().with_cloud_cover(5)
        """
        return Query(product=self.product, filters=self.filters.copy())

    def clear_filters(self) -> "Query":
        """
        Remove all filters (keep product).
        
        Returns:
            self for method chaining
        
        Example:
            >>> query.clear_filters().with_date_range(...)
        """
        self.filters = []
        logger.debug("Cleared all filters")
        return self