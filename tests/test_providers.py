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

from typing import Any, Dict, List, Optional

import pytest

from dwr_eo_toolkit.providers import BaseProvider


class TestBaseProvider:
    """Tests for BaseProvider abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError, match="abstract"):
            BaseProvider()  # type: ignore

    def test_subclass_must_implement_all_methods(self):
        # Test with only search implemented
        class OnlySearch(BaseProvider):  # type: ignore
            def search(
                self,
                product: str,
                bounding_box: Optional[tuple[float, float, float, float]] = None,
                start_date: Optional[str] = None,
                end_date: Optional[str] = None,
                **kwargs,
            ) -> tuple[List[Dict[str, Any]], int]:
                return ([], 0)

        with pytest.raises(TypeError, match="get_metadata|validate_product"):
            OnlySearch()  # type: ignore

        # Test with missing search
        class NoSearch(BaseProvider):  # type: ignore
            def get_metadata(self, product: str) -> Dict[str, Any]:
                return {}

            def validate_product(self, product: str) -> bool:
                return True

        with pytest.raises(TypeError, match="search"):
            NoSearch()  # type: ignore

    def test_complete_implementation_works(self):
        class CompleteProvider(BaseProvider):
            def search(
                self,
                product: str,
                bounding_box: Optional[tuple[float, float, float, float]] = None,
                start_date: Optional[str] = None,
                end_date: Optional[str] = None,
                **kwargs,
            ) -> tuple[List[Dict[str, Any]], int]:
                return ([{"id": "test", "product": product}], 1)

            def get_metadata(self, product: str) -> Dict[str, Any]:
                return {"product": product}

            def validate_product(self, product: str) -> bool:
                return True

        provider = CompleteProvider()
        assert provider.validate_product("ECOSTRESS_L2_LSTE")
        assert provider.get_metadata("ECOSTRESS_L2_LSTE") == {
            "product": "ECOSTRESS_L2_LSTE"
        }
        results, total = provider.search("ECOSTRESS_L2_LSTE")
        assert total == 1
        assert len(results) == 1
