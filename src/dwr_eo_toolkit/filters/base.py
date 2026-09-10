"""
Abstract base class for query filters.

Filters encapsulate search constraints and convert them to provider parameters.
All filters must implement to_params() and validate() methods.
"""

from abc import ABC, abstractmethod
from typing import Any


class Filter(ABC):
    """
    Abstract base class for search filters.

    Filters represent constraints on a search query (spatial, temporal, product-specific).
    They are composable and can be combined in a Query object.

    Example:
        >>> spatial = BoundingBox(-120, 30, -100, 40)
        >>> temporal = DateRange("2023-01-01", "2023-12-31")
        >>> query = Query(filters=[spatial, temporal])
    """

    @abstractmethod
    def to_params(self) -> dict[str, Any]:
        """
        Convert filter to provider search parameters.

        Returns:
            Dictionary of parameters ready for provider.search()

        Example:
            >>> bbox = BoundingBox(-120, 30, -100, 40)
            >>> bbox.to_params()
            {'bounding_box': (-120, 30, -100, 40)}
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate filter parameters.

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If parameters are invalid

        Example:
            >>> bbox = BoundingBox(-200, 30, -100, 40)  # Invalid longitude
            >>> bbox.validate()  # Raises ValueError
        """
        pass

    def __repr__(self) -> str:
        """String representation of filter."""
        return f"{self.__class__.__name__}({self.to_params()})"
