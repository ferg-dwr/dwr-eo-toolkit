"""
Abstract base class for instrument adapters.

Provides standardized metadata and processing for Earth observation products.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class InstrumentMetadata:
    """Metadata for an instrument/product."""

    short_name: str
    long_name: str
    description: str
    provider: str
    processing_level: str
    temporal_resolution: str
    spatial_resolution: str
    data_format: str
    doi: str
    keywords: list[str]
    related_urls: list[Dict[str, str]]


class InstrumentAdapter(ABC):
    """
    Abstract base class for instrument-specific adapters.

    Provides:
    - Standardized product metadata (resolution, DOI, processing level)
    - Product keyword matching for search
    - Optional granule post-processing

    Usage:
        >>> adapter = ECOSTRESSAdapter()
        >>> metadata = adapter.get_metadata()
        >>> keywords = adapter.get_keywords()
    """

    @abstractmethod
    def get_keywords(self) -> list[str]:
        """
        Get keywords that match this instrument.

        Example: ECOSTRESS adapter returns: ["ecostress", "eco", "thermal", "lste"]

        Returns:
            List of keywords that trigger this adapter
        """
        pass

    @abstractmethod
    def get_short_names(self) -> list[str]:
        """
        Get all short names for this instrument.

        Example: ECOSTRESS returns: ["ECO_L2T_LSTE", "ECO_L2T_QC", "ECO_L2T_RQC"]

        Returns:
            List of short names
        """
        pass

    @abstractmethod
    def get_metadata(self) -> InstrumentMetadata:
        """
        Get enriched metadata for this instrument.

        Returns:
            InstrumentMetadata instance with product details
        """
        pass

    def post_process_granules(
        self, granules: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """
        Post-process granules (optional).

        Subclasses can override to:
        - Extract instrument-specific metadata
        - Add custom fields
        - Compute quality scores

        Args:
            granules: Raw granules from search

        Returns:
            Enhanced granules
        """
        return granules
