"""
Data providers for Earth observation datasets.

Available Providers:
- EarthAccessProvider: Search and download using NASA's earthaccess library
"""

from dwr_eo_toolkit.providers.base import BaseProvider
from dwr_eo_toolkit.providers.earthaccess_provider import EarthAccessProvider

__all__ = [
    "BaseProvider",
    "EarthAccessProvider",
]
