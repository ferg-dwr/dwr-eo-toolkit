"""
Abstract base class for CMR instrument adapters.

Allows CMRProvider to delegate instrument-specific logic (metadata, constants, filtering)
to specialized adapter classes while maintaining a generic search interface.

Pattern: Strategy/Adapter Pattern
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


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


class CMRAdapter(ABC):
    """
    Abstract base class for CMR instrument adapters.
    
    Adapters encapsulate instrument-specific knowledge:
    - Product short names and aliases
    - Metadata extraction and enrichment
    - Supported filters (cloud cover, quality flags, etc.)
    - Data constants (default temporal range, spatial resolution, etc.)
    - Special handling for search parameters
    
    Example:
        >>> adapter = ECOSTRESSAdapter()
        >>> metadata = adapter.get_metadata()
        >>> params = adapter.process_search_params(cloud_cover=20)
    """

    def __init__(self):
        """Initialize adapter."""
        pass

    @abstractmethod
    def get_keywords(self) -> list[str]:
        """
        Get keywords that match this instrument/adapter.
        
        Used to identify when to use this adapter.
        E.g., ECOSTRESS adapter matches: "ECOSTRESS", "ECO", "thermal", "LSTE"
        
        Returns:
            List of keywords that trigger this adapter
        """
        pass

    @abstractmethod
    def get_short_names(self) -> list[str]:
        """
        Get all CMR short names for this instrument.
        
        E.g., ECOSTRESS has: ECO_L2T_LSTE, ECO_L2T_QC, etc.
        
        Returns:
            List of short names produced by this instrument
        """
        pass

    @abstractmethod
    def get_metadata(self) -> InstrumentMetadata:
        """
        Get enriched metadata for this instrument.
        
        Returns:
            InstrumentMetadata instance with full details
        """
        pass

    @abstractmethod
    def process_search_params(
        self, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process and validate instrument-specific search parameters.
        
        Allows adapters to:
        - Validate parameters specific to this instrument
        - Add default parameters
        - Transform high-level parameters to CMR format
        - Reject unsupported combinations
        
        Args:
            **kwargs: Search parameters (cloud_cover, quality_flags, etc.)
        
        Returns:
            Processed CMR parameters
        
        Raises:
            ValueError: If parameters invalid for this instrument
        """
        pass

    @abstractmethod
    def supports_cloud_cover(self) -> bool:
        """Check if this instrument supports cloud cover filtering."""
        pass

    @abstractmethod
    def supports_quality_flags(self) -> bool:
        """Check if this instrument supports quality flag filtering."""
        pass

    @abstractmethod
    def get_default_spatial_resolution(self) -> str:
        """Get default spatial resolution (e.g., "70m", "1km")."""
        pass

    @abstractmethod
    def get_default_temporal_resolution(self) -> str:
        """Get default temporal resolution (e.g., "1 day", "8 days")."""
        pass

    @abstractmethod
    def get_recommended_date_range(self) -> Tuple[str, str]:
        """
        Get recommended date range for this instrument.
        
        Returns:
            (start_date, end_date) as ISO strings
        """
        pass

    def post_process_granules(
        self, 
        granules: list[Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """
        Post-process granules after CMR search.
        
        Optional method for adapters that need to:
        - Extract instrument-specific metadata
        - Compute quality scores
        - Add custom fields
        
        Args:
            granules: Raw CMR granules
        
        Returns:
            Enhanced granules
        """
        return granules

    def validate_temporal_range(
        self, 
        start_date: str, 
        end_date: str
    ) -> bool:
        """
        Validate temporal range for this instrument.
        
        Optional: adapters can override to enforce constraints.
        
        Args:
            start_date: ISO format start date
            end_date: ISO format end date
        
        Returns:
            True if valid, False otherwise
        """
        return True

    def validate_spatial_bounds(
        self, 
        min_lon: float, 
        min_lat: float, 
        max_lon: float, 
        max_lat: float
    ) -> bool:
        """
        Validate spatial bounds for this instrument.
        
        Optional: adapters can override to enforce constraints.
        
        Args:
            min_lon, min_lat, max_lon, max_lat: Bounding box
        
        Returns:
            True if valid, False otherwise
        """
        return True