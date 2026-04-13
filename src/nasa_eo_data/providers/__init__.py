"""
Data providers for Earth observation datasets.

Providers abstract away the details of different data repositories and APIs,
providing a unified interface for searching and accessing satellite data.

Available Providers:
- CMRProvider: Search any dataset in NASA's Common Metadata Repository
- LPDaacProvider: Search LP DAAC (Distributed Active Archive Center) products (future)
- NsidcProvider: Search NSIDC (National Snow and Ice Data Center) products (future)

Example:
    >>> from nasa_eo_data.core.auth import EarthDataLoginAuth
    >>> from nasa_eo_data.providers import CMRProvider
    >>> 
    >>> auth = EarthDataLoginAuth()
    >>> provider = CMRProvider(auth)
    >>> 
    >>> results, total = provider.search(
    ...     product="ECOSTRESS_L2_LSTE",
    ...     bounding_box=(-120, 30, -100, 40),
    ...     start_date="2023-01-01",
    ...     end_date="2023-12-31",
    ... )
"""

from nasa_eo_data.providers.base import BaseProvider
from nasa_eo_data.providers.cmr_provider import CMRProvider

__all__ = [
    "BaseProvider",
    "CMRProvider",
]

__version__ = "0.1.0"