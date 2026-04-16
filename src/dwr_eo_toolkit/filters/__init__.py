"""
Query filters and builder for composing Earth observation searches.

Provides a fluent, composable API for building search queries.

Main Components:
- Query: Fluent query builder with method chaining
- Spatial Filters: BoundingBox, Polygon (future), PointBuffer (future)
- Temporal Filters: DateRange, Season (future)
- Product Filters: CloudCover, QualityFlag, ProcessingLevel

Quick Start:
    >>> from dwr_eo_toolkit.filters import Query
    >>> from dwr_eo_toolkit.providers import CMRProvider
    >>> from dwr_eo_toolkit.core.auth import EarthDataLoginAuth
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
from dwr_eo_toolkit.filters.base import Filter
# Product
from dwr_eo_toolkit.filters.product import (CloudCover, Instrument, Orbit,
                                          ProcessingLevel, QualityFlag)
# Query Builder
from dwr_eo_toolkit.filters.query import Query
# Spatial
from dwr_eo_toolkit.filters.spatial import BoundingBox, PointBuffer, Polygon
# Temporal
from dwr_eo_toolkit.filters.temporal import DateRange, Season, YearMonthRange

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
