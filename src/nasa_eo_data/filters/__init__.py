"""
Query filters and builder for composing Earth observation searches.

Provides a fluent, composable API for building search queries.

Main Components:
- Query: Fluent query builder with method chaining
- Spatial Filters: BoundingBox, Polygon (future), PointBuffer (future)
- Temporal Filters: DateRange, Season (future)
- Product Filters: CloudCover, QualityFlag, ProcessingLevel

Quick Start:
    >>> from nasa_eo_data.filters import Query
    >>> from nasa_eo_data.providers import CMRProvider
    >>> from nasa_eo_data.core.auth import EarthDataLoginAuth
    >>>
    >>> auth = EarthDataLoginAuth()
    >>> provider = CMRProvider(auth)
    >>>
    >>> results, total = (Query()
    ...     .with_product("ECOSTRESS_L2_LSTE")
    ...     .with_spatial_bounds(-120, 30, -100, 40)
    ...     .with_date_range("2023-01-01", "2023-12-31")
    ...     .with_cloud_cover(10)
    ...     .execute(provider)
    ... )
"""

# Base
from nasa_eo_data.filters.base import Filter
# Product
from nasa_eo_data.filters.product import (CloudCover, Instrument, Orbit,
                                          ProcessingLevel, QualityFlag)
# Query Builder
from nasa_eo_data.filters.query import Query
# Spatial
from nasa_eo_data.filters.spatial import BoundingBox, PointBuffer, Polygon
# Temporal
from nasa_eo_data.filters.temporal import DateRange, Season, YearMonthRange

__all__ = [
    "Filter",
    "BoundingBox",
    "Polygon",
    "PointBuffer",
    "DateRange",
    "Season",
    "YearMonthRange",
    "CloudCover",
    "QualityFlag",
    "ProcessingLevel",
    "Orbit",
    "Instrument",
    "Query",
]

__version__ = "0.1.0"
