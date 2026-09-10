"""
Spatial filters for geographic search constraints.

Supports bounding box queries and future polygon/point+radius searches.
"""

import logging
from typing import Any

from dwr_eo_toolkit.filters.base import Filter

logger = logging.getLogger(__name__)


class BoundingBox(Filter):
    """
    Geographic bounding box filter.

    Constrains search to a rectangular region defined by min/max longitude and latitude.

    Args:
        min_lon: Minimum longitude (-180 to 180)
        min_lat: Minimum latitude (-90 to 90)
        max_lon: Maximum longitude (-180 to 180), must be > min_lon
        max_lat: Maximum latitude (-90 to 90), must be > min_lat

    Example:
        >>> # California bounding box
        >>> bbox = BoundingBox(-120, 30, -100, 40)
        >>> bbox.validate()
        True
        >>> bbox.to_params()
        {'bounding_box': (-120, 30, -100, 40)}

    Raises:
        ValueError: If coordinates are invalid or inverted
    """

    def __init__(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
    ):
        """Initialize bounding box with coordinates."""
        self.min_lon = min_lon
        self.min_lat = min_lat
        self.max_lon = max_lon
        self.max_lat = max_lat

    def validate(self) -> bool:
        """
        Validate bounding box coordinates.

        Returns:
            True if valid

        Raises:
            ValueError: If invalid
        """
        # Check longitude range
        if not (-180 <= self.min_lon <= 180 and -180 <= self.max_lon <= 180):
            raise ValueError(
                f"Longitude must be -180 to 180, got min={self.min_lon}, max={self.max_lon}"
            )

        # Check latitude range
        if not (-90 <= self.min_lat <= 90 and -90 <= self.max_lat <= 90):
            raise ValueError(
                f"Latitude must be -90 to 90, got min={self.min_lat}, max={self.max_lat}"
            )

        # Check min < max
        if self.min_lon >= self.max_lon:
            raise ValueError(
                f"""min_lon ({self.min_lon}) must be less than max_lon ({self.max_lon})"""
            )

        if self.min_lat >= self.max_lat:
            raise ValueError(
                f"""min_lat ({self.min_lat}) must be less than max_lat ({self.max_lat})"""
            )

        return True

    def to_params(self) -> dict[str, Any]:
        """
        Convert to provider search parameters.

        Returns:
            Dictionary with 'bounding_box' key
        """
        self.validate()
        return {"bounding_box": (self.min_lon, self.min_lat, self.max_lon, self.max_lat)}

    def center(self) -> tuple[float, float]:
        """
        Get bounding box center coordinates.

        Returns:
            (center_lon, center_lat) tuple

        Example:
            >>> bbox = BoundingBox(-120, 30, -100, 40)
            >>> bbox.center()
            (-110.0, 35.0)
        """
        center_lon = (self.min_lon + self.max_lon) / 2
        center_lat = (self.min_lat + self.max_lat) / 2
        return (center_lon, center_lat)

    def area(self) -> float:
        """
        Approximate area of bounding box in square degrees.

        Returns:
            Area in square degrees

        Example:
            >>> bbox = BoundingBox(-120, 30, -100, 40)
            >>> bbox.area()
            200.0
        """
        lon_range = self.max_lon - self.min_lon
        lat_range = self.max_lat - self.min_lat
        return lon_range * lat_range

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"BoundingBox(lon: {self.min_lon}→{self.max_lon}, lat: {self.min_lat}→{self.max_lat})"
        )


# Future filters (stubs for Phase 2B+)


class Polygon(Filter):
    """
    Polygon spatial filter for complex regions.

    Future implementation: Search within an arbitrary polygon boundary.
    """

    def __init__(self, coordinates: list):
        """Initialize with polygon coordinates."""
        self.coordinates = coordinates

    def validate(self) -> bool:
        """Validate polygon coordinates."""
        # TODO: Implement polygon validation
        return True

    def to_params(self) -> dict[str, Any]:
        """Convert to provider parameters."""
        # TODO: Implement polygon to CMR parameter conversion
        raise NotImplementedError("Polygon filter coming in Phase 2B+")


class PointBuffer(Filter):
    """
    Point with buffer/radius spatial filter.

    Future implementation: Search within X km of a point.
    """

    def __init__(self, lon: float, lat: float, radius_km: float):
        """Initialize with center point and radius."""
        self.lon = lon
        self.lat = lat
        self.radius_km = radius_km

    def validate(self) -> bool:
        """Validate point and radius."""
        # TODO: Implement validation
        return True

    def to_params(self) -> dict[str, Any]:
        """Convert to provider parameters."""
        # TODO: Implement point buffer to CMR parameter conversion
        raise NotImplementedError("PointBuffer filter coming in Phase 2B+")
