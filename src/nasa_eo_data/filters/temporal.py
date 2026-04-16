"""
Temporal filters for date range search constraints.

Supports date range queries and future seasonal filtering.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from nasa_eo_data.filters.base import Filter

logger = logging.getLogger(__name__)


class DateRange(Filter):
    """
    Date range temporal filter.

    Constrains search to observations within a date range.

    Args:
        start_date: Start date in YYYY-MM-DD or ISO format
        end_date: End date in YYYY-MM-DD or ISO format

    Example:
        >>> # Search all of 2023
        >>> dr = DateRange("2023-01-01", "2023-12-31")
        >>> dr.validate()
        True
        >>> dr.to_params()
        {'start_date': '2023-01-01', 'end_date': '2023-12-31'}

    Raises:
        ValueError: If dates are invalid or start > end
    """

    def __init__(self, start_date: str, end_date: str):
        """Initialize date range."""
        self.start_date = start_date
        self.end_date = end_date

    def validate(self) -> bool:
        """
        Validate date range.

        Returns:
            True if valid

        Raises:
            ValueError: If invalid
        """
        # Parse dates
        try:
            start = self._parse_date(self.start_date)
            end = self._parse_date(self.end_date)
        except ValueError as e:
            raise ValueError(f"Invalid date format: {e}")

        # Check chronological order
        if start > end:
            raise ValueError(
                f"start_date ({self.start_date}) must be before end_date ({self.end_date})"
            )

        return True

    def to_params(self) -> Dict[str, Any]:
        """
        Convert to provider search parameters.

        Returns:
            Dictionary with 'start_date' and 'end_date' keys
        """
        self.validate()
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
        }

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """
        Parse date string in multiple formats.

        Accepts:
        - YYYY-MM-DD
        - YYYY-MM-DDTHH:MM:SSZ

        Args:
            date_str: Date string

        Returns:
            datetime object

        Raises:
            ValueError: If format not recognized
        """
        # Try ISO format with time
        if "T" in date_str:
            try:
                # Remove Z if present
                date_str_clean = date_str.rstrip("Z")
                return datetime.fromisoformat(date_str_clean)
            except ValueError:
                pass

        # Try simple YYYY-MM-DD
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                f"Date format not recognized: {date_str}. Use YYYY-MM-DD or ISO format."
            )

    def duration_days(self) -> int:
        """
        Get duration of date range in days.

        Returns:
            Number of days between start and end

        Example:
            >>> dr = DateRange("2023-01-01", "2023-12-31")
            >>> dr.duration_days()
            365
        """
        start = self._parse_date(self.start_date)
        end = self._parse_date(self.end_date)
        delta = end - start
        return delta.days

    def __repr__(self) -> str:
        """String representation."""
        return f"DateRange({self.start_date} to {self.end_date})"


# Future filters (stubs for Phase 2B+)


class Season(Filter):
    """
    Seasonal temporal filter.

    Future implementation: Search for specific seasons (spring, summer, fall, winter).
    """

    def __init__(self, season: str, years: list = None):
        """
        Initialize seasonal filter.

        Args:
            season: 'spring', 'summer', 'fall', or 'winter'
            years: List of years to include (optional, defaults to all)
        """
        self.season = season.lower()
        self.years = years or []

    def validate(self) -> bool:
        """Validate season."""
        valid_seasons = ["spring", "summer", "fall", "winter"]
        if self.season not in valid_seasons:
            raise ValueError(f"Season must be one of {valid_seasons}")
        return True

    def to_params(self) -> Dict[str, Any]:
        """Convert to provider parameters."""
        # TODO: Implement seasonal date range logic
        raise NotImplementedError("Season filter coming in Phase 2B+")


class YearMonthRange(Filter):
    """
    Year-month range temporal filter.

    Future implementation: Search by year and month ranges.
    """

    def __init__(
        self, start_year: int, start_month: int, end_year: int, end_month: int
    ):
        """Initialize year-month range."""
        self.start_year = start_year
        self.start_month = start_month
        self.end_year = end_year
        self.end_month = end_month

    def validate(self) -> bool:
        """Validate year-month ranges."""
        # TODO: Implement validation
        return True

    def to_params(self) -> Dict[str, Any]:
        """Convert to provider parameters."""
        # TODO: Implement conversion
        raise NotImplementedError("YearMonthRange filter coming in Phase 2B+")
