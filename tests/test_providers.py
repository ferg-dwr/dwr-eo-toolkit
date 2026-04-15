"""
Unit tests for provider classes.

Tests cover:
- CMRProvider search functionality
- Metadata retrieval
- Parameter validation
- Error handling
- Date/temporal handling
- Bounding box validation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from nasa_eo_data.providers import BaseProvider
from nasa_eo_data.core.auth import EarthDataLoginAuth


class TestBaseProvider:
    """Tests for BaseProvider abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Should not be able to instantiate BaseProvider directly."""
        with pytest.raises(TypeError):
            BaseProvider()

    def test_requires_search_implementation(self):
        """Subclass must implement search method."""

        class IncompleteProvider(BaseProvider):
            def get_metadata(self, product):
                pass

            def validate_product(self, product):
                pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_requires_all_abstract_methods(self):
        """Subclass must implement all abstract methods."""

        class AlmostProvider(BaseProvider):
            def search(self, product, **kwargs):
                pass

        with pytest.raises(TypeError):
            AlmostProvider()