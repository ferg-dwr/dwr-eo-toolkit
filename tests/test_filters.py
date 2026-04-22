"""
Unit tests for filter classes and Query builder.

Test coverage:
- Base Filter abstract class
- Spatial filters (BoundingBox)
- Temporal filters (DateRange)
- Product filters (CloudCover, QualityFlag, ProcessingLevel)
- Query builder and fluent API
- Filter composition
- Parameter conversion
"""

from typing import Any, Dict
from unittest.mock import Mock

import pytest

from dwr_eo_toolkit.filters import (
    BoundingBox,
    CloudCover,
    DateRange,
    Filter,
    ProcessingLevel,
    QualityFlag,
    Query,
)


class TestBaseFilter:
    """Tests for abstract Filter base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Filter cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            Filter()  # type: ignore

    def test_subclass_must_implement_both_methods(self):
        """Subclass must implement both abstract methods."""

        # Missing to_params
        class NoToParams(Filter):
            def validate(self) -> bool:
                return True

        with pytest.raises(TypeError, match="to_params"):
            NoToParams()  # type: ignore

        # Missing validate
        class NoValidate(Filter):
            def to_params(self) -> Dict[str, Any]:
                return {}

        with pytest.raises(TypeError, match="validate"):
            NoValidate()  # type: ignore

    def test_complete_implementation_works(self):
        """Subclass with all methods implemented can be instantiated."""

        class CompleteFilter(Filter):
            def to_params(self) -> Dict[str, Any]:
                return {"test": "params"}

            def validate(self) -> bool:
                return True

        f = CompleteFilter()
        assert f.to_params() == {"test": "params"}
        assert f.validate() is True


class TestBoundingBox:
    """Tests for BoundingBox spatial filter."""

    def test_initialization(self):
        """Should initialize with coordinates."""
        bbox = BoundingBox(-120, 30, -100, 40)
        assert bbox.min_lon == -120
        assert bbox.min_lat == 30
        assert bbox.max_lon == -100
        assert bbox.max_lat == 40

    def test_validate_valid_coordinates(self):
        """Should accept valid coordinates."""
        bbox = BoundingBox(-120, 30, -100, 40)
        assert bbox.validate() is True

    def test_validate_global_extent(self):
        """Should accept global bounding box."""
        bbox = BoundingBox(-180, -90, 180, 90)
        assert bbox.validate() is True

    def test_validate_invalid_longitude(self):
        """Should reject invalid longitude."""
        with pytest.raises(ValueError, match="Longitude"):
            BoundingBox(-200, 30, -100, 40).validate()

        with pytest.raises(ValueError, match="Longitude"):
            BoundingBox(-120, 30, 200, 40).validate()

    def test_validate_invalid_latitude(self):
        """Should reject invalid latitude."""
        with pytest.raises(ValueError, match="Latitude"):
            BoundingBox(-120, -100, -100, 40).validate()

        with pytest.raises(ValueError, match="Latitude"):
            BoundingBox(-120, 30, -100, 100).validate()

    def test_validate_inverted_longitude(self):
        """Should reject inverted longitude."""
        with pytest.raises(ValueError, match="min_lon"):
            BoundingBox(-100, 30, -120, 40).validate()

    def test_validate_inverted_latitude(self):
        """Should reject inverted latitude."""
        with pytest.raises(ValueError, match="min_lat"):
            BoundingBox(-120, 40, -100, 30).validate()

    def test_to_params(self):
        """Should convert to provider parameters."""
        bbox = BoundingBox(-120, 30, -100, 40)
        params = bbox.to_params()
        assert params == {"bounding_box": (-120, 30, -100, 40)}

    def test_center(self):
        """Should calculate bounding box center."""
        bbox = BoundingBox(-120, 30, -100, 40)
        center = bbox.center()
        assert center == (-110, 35)

    def test_area(self):
        """Should calculate bounding box area."""
        bbox = BoundingBox(-120, 30, -100, 40)
        area = bbox.area()
        assert area == 200  # (120-100) * (40-30)

    def test_repr(self):
        """Should have meaningful string representation."""
        bbox = BoundingBox(-120, 30, -100, 40)
        repr_str = repr(bbox)
        assert "BoundingBox" in repr_str
        assert "-120" in repr_str


class TestDateRange:
    """Tests for DateRange temporal filter."""

    def test_initialization(self):
        """Should initialize with dates."""
        dr = DateRange("2023-01-01", "2023-12-31")
        assert dr.start_date == "2023-01-01"
        assert dr.end_date == "2023-12-31"

    def test_validate_valid_dates(self):
        """Should accept valid date range."""
        dr = DateRange("2023-01-01", "2023-12-31")
        assert dr.validate() is True

    def test_validate_iso_format(self):
        """Should accept ISO format dates."""
        dr = DateRange("2023-01-01T00:00:00Z", "2023-12-31T23:59:59Z")
        assert dr.validate() is True

    def test_validate_invalid_date_format(self):
        """Should reject invalid date format."""
        with pytest.raises(ValueError, match="Date format"):
            DateRange("01/01/2023", "12/31/2023").validate()

    def test_validate_start_after_end(self):
        """Should reject start date after end date."""
        with pytest.raises(ValueError, match="start_date"):
            DateRange("2023-12-31", "2023-01-01").validate()

    def test_to_params(self):
        """Should convert to provider parameters."""
        dr = DateRange("2023-01-01", "2023-12-31")
        params = dr.to_params()
        assert params == {
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
        }

    def test_duration_days(self):
        """Should calculate date range duration."""
        dr = DateRange("2023-01-01", "2023-01-31")
        assert dr.duration_days() == 30

    def test_duration_full_year(self):
        """Should handle full year."""
        dr = DateRange("2023-01-01", "2023-12-31")
        assert dr.duration_days() == 364  # Dec 31 - Jan 1 = 364 days

    def test_repr(self):
        """Should have meaningful string representation."""
        dr = DateRange("2023-01-01", "2023-12-31")
        repr_str = repr(dr)
        assert "DateRange" in repr_str
        assert "2023-01-01" in repr_str


class TestCloudCover:
    """Tests for CloudCover product filter."""

    def test_initialization(self):
        """Should initialize with percentage."""
        cloud = CloudCover(max_percent=10)
        assert cloud.max_percent == 10

    def test_validate_valid_range(self):
        """Should accept 0-100 range."""
        assert CloudCover(0).validate() is True
        assert CloudCover(50).validate() is True
        assert CloudCover(100).validate() is True

    def test_validate_invalid_range_low(self):
        """Should reject negative values."""
        with pytest.raises(ValueError, match="0-100"):
            CloudCover(-10).validate()

    def test_validate_invalid_range_high(self):
        """Should reject > 100."""
        with pytest.raises(ValueError, match="0-100"):
            CloudCover(150).validate()

    def test_validate_invalid_type(self):
        """Should reject non-numeric types."""
        cc = CloudCover(150)
        with pytest.raises(ValueError, match="numeric|0-100"):
            cc.validate()

    def test_to_params(self):
        """Should convert to provider parameters."""
        cloud = CloudCover(max_percent=10)
        params = cloud.to_params()
        assert params == {"cloud_cover": 10}

    def test_repr(self):
        """Should have meaningful string representation."""
        cloud = CloudCover(10)
        assert "CloudCover" in repr(cloud)
        assert "10" in repr(cloud)


class TestQualityFlag:
    """Tests for QualityFlag product filter."""

    def test_initialization(self):
        """Should initialize with flag name and value."""
        qc = QualityFlag("LST_QC", "good")
        assert qc.flag_name == "LST_QC"
        assert qc.flag_value == "good"

    def test_validate_valid_flag(self):
        """Should accept valid flags."""
        qc = QualityFlag("LST_QC", "good")
        assert qc.validate() is True

    def test_validate_empty_name(self):
        """Should reject empty flag name."""
        with pytest.raises(ValueError, match="flag name"):
            QualityFlag("", "good").validate()

    def test_validate_empty_value(self):
        """Should reject empty flag value."""
        with pytest.raises(ValueError, match="flag value"):
            QualityFlag("LST_QC", "").validate()

    def test_to_params(self):
        """Should convert to provider parameters."""
        qc = QualityFlag("LST_QC", "good")
        params = qc.to_params()
        assert params == {"quality_flag": {"LST_QC": "good"}}

    def test_repr(self):
        """Should have meaningful string representation."""
        qc = QualityFlag("LST_QC", "good")
        repr_str = repr(qc)
        assert "QualityFlag" in repr_str
        assert "LST_QC" in repr_str


class TestProcessingLevel:
    """Tests for ProcessingLevel product filter."""

    def test_initialization(self):
        """Should initialize with level."""
        level = ProcessingLevel("L2")
        assert level.level == "L2"

    def test_normalize_case(self):
        """Should normalize to uppercase."""
        level = ProcessingLevel("l2")
        assert level.level == "L2"

    def test_validate_valid_level(self):
        """Should accept valid processing levels."""
        for valid_level in ["L0", "L1A", "L1B", "L2", "L3", "L4"]:
            assert ProcessingLevel(valid_level).validate() is True

    def test_validate_invalid_level(self):
        """Should reject invalid levels."""
        with pytest.raises(ValueError, match="Processing level"):
            ProcessingLevel("L5").validate()

    def test_to_params(self):
        """Should convert to provider parameters."""
        level = ProcessingLevel("L2")
        params = level.to_params()
        assert params == {"processing_level": "L2"}

    def test_repr(self):
        """Should have meaningful string representation."""
        level = ProcessingLevel("L2")
        assert "ProcessingLevel" in repr(level)
        assert "L2" in repr(level)


class TestQuery:
    """Tests for Query builder."""

    def test_initialization_empty(self):
        """Should initialize empty query."""
        query = Query()
        assert query.product is None
        assert query.filters == []

    def test_initialization_with_product(self):
        """Should initialize with product."""
        query = Query(product="ECOSTRESS_L2_LSTE")
        assert query.product == "ECOSTRESS_L2_LSTE"

    def test_with_product(self):
        """Should set product."""
        query = Query().with_product("ECOSTRESS_L2_LSTE")
        assert query.product == "ECOSTRESS_L2_LSTE"

    def test_with_spatial_bounds(self):
        """Should add spatial filter."""
        query = Query().with_spatial_bounds(-120, 30, -100, 40)
        assert len(query.filters) == 1
        assert isinstance(query.filters[0], BoundingBox)

    def test_with_date_range(self):
        """Should add temporal filter."""
        query = Query().with_date_range("2023-01-01", "2023-12-31")
        assert len(query.filters) == 1
        assert isinstance(query.filters[0], DateRange)

    def test_with_cloud_cover(self):
        """Should add cloud cover filter."""
        query = Query().with_cloud_cover(10)
        assert len(query.filters) == 1
        assert isinstance(query.filters[0], CloudCover)

    def test_with_quality_flag(self):
        """Should add quality flag filter."""
        query = Query().with_quality_flag("LST_QC", "good")
        assert len(query.filters) == 1
        assert isinstance(query.filters[0], QualityFlag)

    def test_with_processing_level(self):
        """Should add processing level filter."""
        query = Query().with_processing_level("L2")
        assert len(query.filters) == 1
        assert isinstance(query.filters[0], ProcessingLevel)

    def test_method_chaining(self):
        """Should support fluent chaining."""
        query = (
            Query()
            .with_product("ECOSTRESS_L2_LSTE")
            .with_spatial_bounds(-120, 30, -100, 40)
            .with_date_range("2023-01-01", "2023-12-31")
            .with_cloud_cover(10)
        )
        assert query.product == "ECOSTRESS_L2_LSTE"
        assert len(query.filters) == 3

    def test_execute_without_product(self):
        """Should raise error if no product set."""
        query = Query().with_spatial_bounds(-120, 30, -100, 40)
        mock_provider = Mock()

        with pytest.raises(ValueError, match="Product must be set"):
            query.execute(mock_provider)

    def test_execute_with_product(self):
        """Should execute query with product."""
        mock_provider = Mock()
        mock_provider.search.return_value = ([{"id": "g1"}], 1)

        query = (
            Query()
            .with_product("ECOSTRESS_L2_LSTE")
            .with_spatial_bounds(-120, 30, -100, 40)
            .with_date_range("2023-01-01", "2023-12-31")
        )

        results, total = query.execute(mock_provider)

        assert len(results) == 1
        assert total == 1
        mock_provider.search.assert_called_once()

    def test_execute_passes_all_parameters(self):
        """Should convert all filters to parameters."""
        mock_provider = Mock()
        mock_provider.search.return_value = ([], 0)

        query = (
            Query()
            .with_product("ECOSTRESS_L2_LSTE")
            .with_spatial_bounds(-120, 30, -100, 40)
            .with_date_range("2023-01-01", "2023-12-31")
            .with_cloud_cover(10)
        )

        query.execute(mock_provider)

        call_args = mock_provider.search.call_args[1]
        assert call_args["product"] == "ECOSTRESS_L2_LSTE"
        assert "bounding_box" in call_args
        assert "start_date" in call_args
        assert "cloud_cover" in call_args

    def test_to_params(self):
        """Should convert query to parameters dict."""
        query = (
            Query()
            .with_product("ECOSTRESS_L2_LSTE")
            .with_spatial_bounds(-120, 30, -100, 40)
            .with_date_range("2023-01-01", "2023-12-31")
        )

        params = query.to_params()
        assert params["product"] == "ECOSTRESS_L2_LSTE"
        assert "bounding_box" in params
        assert "start_date" in params

    def test_filters_summary(self):
        """Should provide filter summary."""
        query = Query().with_product("ECOSTRESS_L2_LSTE").with_spatial_bounds(-120, 30, -100, 40)

        summary = query.filters_summary()
        assert "ECOSTRESS_L2_LSTE" in summary
        assert "BoundingBox" in summary

    def test_copy(self):
        """Should create independent copy."""
        original = Query().with_product("ECOSTRESS_L2_LSTE").with_spatial_bounds(-120, 30, -100, 40)

        copy = original.copy().with_cloud_cover(10)

        assert original.product == copy.product
        assert len(original.filters) == 1
        assert len(copy.filters) == 2

    def test_clear_filters(self):
        """Should clear filters but keep product."""
        query = (
            Query()
            .with_product("ECOSTRESS_L2_LSTE")
            .with_spatial_bounds(-120, 30, -100, 40)
            .clear_filters()
        )

        assert query.product == "ECOSTRESS_L2_LSTE"
        assert len(query.filters) == 0

    def test_for_product_convenience(self):
        """Should create query for product."""
        query = Query.for_product("ECOSTRESS_L2_LSTE")
        assert query.product == "ECOSTRESS_L2_LSTE"

    def test_repr(self):
        """Should have meaningful representation."""
        query = Query().with_product("ECOSTRESS_L2_LSTE").with_spatial_bounds(-120, 30, -100, 40)
        repr_str = repr(query)
        assert "Query" in repr_str
        assert "ECOSTRESS_L2_LSTE" in repr_str


class TestFilterComposition:
    """Tests for combining multiple filters."""

    def test_multiple_spatial_filters(self):
        """Should support multiple filters of same type."""
        query = (
            Query()
            .with_product("TEST")
            .with_cloud_cover(10)
            .with_cloud_cover(5)  # Second one should replace or add
        )

        # Both cloud cover filters are added
        cloud_filters = [f for f in query.filters if isinstance(f, CloudCover)]
        assert len(cloud_filters) == 2

    def test_mixed_filter_types(self):
        """Should support mixed filter types."""
        query = (
            Query()
            .with_product("TEST")
            .with_spatial_bounds(-120, 30, -100, 40)
            .with_date_range("2023-01-01", "2023-12-31")
            .with_cloud_cover(10)
            .with_processing_level("L2")
        )

        assert len(query.filters) == 4
        assert any(isinstance(f, BoundingBox) for f in query.filters)
        assert any(isinstance(f, DateRange) for f in query.filters)
        assert any(isinstance(f, CloudCover) for f in query.filters)
        assert any(isinstance(f, ProcessingLevel) for f in query.filters)


class TestStubFiltersCoverage:
    """Cover stub filter classes: Polygon, PointBuffer, Season, YearMonthRange,
    Orbit, Instrument — and Filter.__repr__ via uninherited subclass."""

    def test_filter_repr_via_subclass(self):
        """Filter.__repr__ returns class name + to_params (base.py line 59)."""

        class SimpleFilter(Filter):
            def validate(self) -> bool:
                return True

            def to_params(self):
                return {"key": "value"}

        f = SimpleFilter()
        r = repr(f)
        assert "SimpleFilter" in r
        assert "key" in r

    def test_polygon_instantiation_and_validate(self):
        """Polygon can be created and validate() returns True (spatial.py 148, 153)."""
        from dwr_eo_toolkit.filters.spatial import Polygon

        p = Polygon([(0, 0), (1, 0), (1, 1)])
        assert p.validate() is True

    def test_polygon_to_params_raises_not_implemented(self):
        """Polygon.to_params raises NotImplementedError (spatial.py 158)."""
        from dwr_eo_toolkit.filters.spatial import Polygon

        p = Polygon([(0, 0), (1, 0), (1, 1)])
        with pytest.raises(NotImplementedError):
            p.to_params()

    def test_point_buffer_instantiation_and_validate(self):
        """PointBuffer can be created and validate() returns True (spatial.py 170-172, 177)."""
        from dwr_eo_toolkit.filters.spatial import PointBuffer

        pb = PointBuffer(lon=-120.0, lat=38.0, radius_km=50.0)
        assert pb.lon == -120.0
        assert pb.lat == 38.0
        assert pb.radius_km == 50.0
        assert pb.validate() is True

    def test_point_buffer_to_params_raises_not_implemented(self):
        """PointBuffer.to_params raises NotImplementedError (spatial.py 182)."""
        from dwr_eo_toolkit.filters.spatial import PointBuffer

        pb = PointBuffer(lon=-120.0, lat=38.0, radius_km=50.0)
        with pytest.raises(NotImplementedError):
            pb.to_params()

    def test_season_validate_valid(self):
        """Season.validate returns True for valid season (temporal.py 161-164)."""
        from dwr_eo_toolkit.filters.temporal import Season

        s = Season("summer")
        assert s.validate() is True

    def test_season_validate_invalid_raises(self):
        """Season.validate raises ValueError for invalid season."""
        from dwr_eo_toolkit.filters.temporal import Season

        s = Season("monsoon")
        with pytest.raises(ValueError):
            s.validate()

    def test_season_to_params_raises_not_implemented(self):
        """Season.to_params raises NotImplementedError (temporal.py 156-157, 169)."""
        from dwr_eo_toolkit.filters.temporal import Season

        s = Season("spring")
        with pytest.raises(NotImplementedError):
            s.to_params()

    def test_year_month_range_instantiation(self):
        """YearMonthRange stores all init params (temporal.py 181-184)."""
        from dwr_eo_toolkit.filters.temporal import YearMonthRange

        ymr = YearMonthRange(2022, 1, 2023, 12)
        assert ymr.start_year == 2022
        assert ymr.start_month == 1
        assert ymr.end_year == 2023
        assert ymr.end_month == 12

    def test_year_month_range_validate_returns_true(self):
        """YearMonthRange.validate returns True (temporal.py 189)."""
        from dwr_eo_toolkit.filters.temporal import YearMonthRange

        ymr = YearMonthRange(2022, 1, 2023, 12)
        assert ymr.validate() is True

    def test_year_month_range_to_params_raises(self):
        """YearMonthRange.to_params raises NotImplementedError (temporal.py 194)."""
        from dwr_eo_toolkit.filters.temporal import YearMonthRange

        ymr = YearMonthRange(2022, 1, 2023, 12)
        with pytest.raises(NotImplementedError):
            ymr.to_params()

    def test_cloud_cover_type_error_for_non_int(self):
        """CloudCover.validate raises TypeError when max_percent is not int (product.py 52)."""
        from dwr_eo_toolkit.filters.product import CloudCover

        cloud = CloudCover(max_percent=10.5)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="must be int"):
            cloud.validate()

    def test_orbit_instantiation_and_validate(self):
        """Orbit can be created and validate returns True (product.py 204-206, 211)."""
        from dwr_eo_toolkit.filters.product import Orbit

        o = Orbit(orbit_number=100, track=5)
        assert o.orbit_number == 100
        assert o.validate() is True

    def test_orbit_to_params_raises(self):
        """Orbit.to_params raises NotImplementedError (product.py 216)."""
        from dwr_eo_toolkit.filters.product import Orbit

        o = Orbit()
        with pytest.raises(NotImplementedError):
            o.to_params()

    def test_instrument_instantiation_and_validate(self):
        """Instrument can be created and validate returns True (product.py 228, 233)."""
        from dwr_eo_toolkit.filters.product import Instrument

        i = Instrument("TIR")
        assert i.instrument_name == "TIR"
        assert i.validate() is True

    def test_instrument_to_params_raises(self):
        """Instrument.to_params raises NotImplementedError (product.py 238)."""
        from dwr_eo_toolkit.filters.product import Instrument

        i = Instrument("TIR")
        with pytest.raises(NotImplementedError):
            i.to_params()

    def test_date_range_parse_iso_with_z(self):
        """DateRange._parse_date handles ISO format with Z suffix (temporal.py 102-104)."""
        from dwr_eo_toolkit.filters.temporal import DateRange

        dr = DateRange("2023-01-01T00:00:00Z", "2023-12-31T23:59:59Z")
        assert dr.validate() is True

    def test_date_range_parse_iso_invalid_after_t_raises(self):
        """DateRange._parse_date hits except ValueError on bad T-format (temporal.py 105-106)."""
        from dwr_eo_toolkit.filters.temporal import DateRange

        dr = DateRange("2023-01-01Tbadtime", "2023-12-31")
        with pytest.raises(ValueError):
            dr.validate()


class TestQueryCoverageExtra:
    """Cover query.py lines 103-106, 123-126, 164-167, 279-281, 313, 328."""

    def test_with_polygon_adds_filter(self):
        """with_polygon appends a Polygon filter (query.py 103-106)."""
        from dwr_eo_toolkit.filters.spatial import Polygon

        q = Query().with_polygon([(0, 0), (1, 0), (1, 1)])
        assert any(isinstance(f, Polygon) for f in q.filters)

    def test_with_point_buffer_adds_filter(self):
        """with_point_buffer appends a PointBuffer filter (query.py 123-126)."""
        from dwr_eo_toolkit.filters.spatial import PointBuffer

        q = Query().with_point_buffer(-120.0, 38.0, 50.0)
        assert any(isinstance(f, PointBuffer) for f in q.filters)

    def test_with_season_adds_filter(self):
        """with_season appends a Season filter (query.py 164-167)."""
        from dwr_eo_toolkit.filters.temporal import Season

        q = Query().with_season("summer")
        assert any(isinstance(f, Season) for f in q.filters)

    def test_execute_raises_when_provider_fails(self):
        """execute propagates exceptions from provider.search (query.py 279-281)."""
        provider = Mock()
        provider.search.side_effect = RuntimeError("provider error")
        q = Query(product="MODIS").with_date_range("2023-01-01", "2023-12-31")
        with pytest.raises(RuntimeError, match="provider error"):
            q.execute(provider)

    def test_to_params_raises_when_no_product(self):
        """to_params raises ValueError when product is not set (query.py 313)."""
        q = Query()
        with pytest.raises(ValueError, match="Product must be set"):
            q.to_params()

    def test_repr_includes_product_and_filters(self):
        """__repr__ returns a human-readable string (query.py 328)."""
        q = Query(product="ECOSTRESS").with_date_range("2023-01-01", "2023-12-31")
        r = repr(q)
        assert "ECOSTRESS" in r
