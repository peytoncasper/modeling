"""Tests for handlers_sketch.py — the sketch domain handler module.

Uses conftest.py's adsk mocks and FakeSketch objects so handlers can
be imported and run outside of Fusion 360.
"""

import sys
import math
import pytest


@pytest.fixture(autouse=True)
def _setup_path():
    p = "/Users/peytocas/Documents/modeling/fusion-addin"
    if p not in sys.path:
        sys.path.insert(0, p)
    yield
    if p in sys.path:
        sys.path.remove(p)


@pytest.fixture
def handlers(patch_helpers):
    """Import handlers_sketch after mocks are in place."""
    if "handlers_sketch" in sys.modules:
        del sys.modules["handlers_sketch"]
    import handlers_sketch as hs
    return hs


# ── Lifecycle ─────────────────────────────────────────────────

class TestCreateSketch:
    def test_creates_on_xy(self, handlers, fake_component):
        result = handlers.handle_create_sketch({"plane": "xy", "name": "S"})
        assert result["sketch_id"] == "NewSketch" or "name" in result
        assert "component" in result

    def test_creates_on_xz(self, handlers, fake_component):
        result = handlers.handle_create_sketch({"plane": "xz"})
        assert "sketch_id" in result

    def test_creates_on_yz(self, handlers, fake_component):
        result = handlers.handle_create_sketch({"plane": "yz"})
        assert "sketch_id" in result

    def test_unknown_plane_raises(self, handlers, fake_component):
        with pytest.raises(Exception, match="Plane not found"):
            handlers.handle_create_sketch({"plane": "nonexistent"})


class TestFinishSketch:
    def test_finish_returns_validation(self, handlers, fake_sketch):
        result = handlers.handle_finish_sketch({"sketch_id": "S1"})
        assert result["success"] is True
        assert "profile_count" in result
        assert "is_valid" in result


class TestDeleteSketch:
    def test_delete_requires_name(self, handlers):
        with pytest.raises(Exception, match="sketch_name is required"):
            handlers.handle_delete_sketch({})

    def test_delete_nonexistent_raises(self, handlers):
        with pytest.raises(Exception, match="Sketch not found"):
            handlers.handle_delete_sketch({"sketch_name": "NoSuchSketch"})


class TestListSketches:
    def test_list_returns_array(self, handlers):
        result = handlers.handle_list_sketches({})
        assert "sketches" in result
        assert "count" in result


# ── Drawing primitives ────────────────────────────────────────

class TestDrawLine:
    def test_basic_line(self, handlers, fake_sketch):
        result = handlers.handle_draw_line({
            "sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        assert "curve_id" in result
        assert fake_sketch.sketchCurves.count == 1

    def test_construction_line(self, handlers, fake_sketch):
        result = handlers.handle_draw_line({
            "sketch_id": "S1", "start": [0, 0], "end": [10, 0],
            "construction": True})
        curve = fake_sketch.sketchCurves.item(0)
        assert curve.isConstruction is True


class TestDrawCircle:
    def test_basic_circle(self, handlers, fake_sketch):
        result = handlers.handle_draw_circle({
            "sketch_id": "S1", "center": [50, 50], "radius": 25})
        assert "curve_id" in result
        assert fake_sketch.sketchCurves.count == 1


class TestDrawArc:
    def test_center_radius_arc(self, handlers, fake_sketch):
        result = handlers.handle_draw_arc({
            "sketch_id": "S1", "center": [0, 0],
            "radius": 10, "start_angle": 0, "sweep_angle": 90})
        assert "curve_id" in result

    def test_three_point_arc(self, handlers, fake_sketch):
        result = handlers.handle_draw_arc_3point({
            "sketch_id": "S1",
            "start": [0, 0], "mid": [5, 5], "end": [10, 0]})
        assert "curve_id" in result


class TestDrawRectangle:
    def test_2d_rect(self, handlers, fake_sketch):
        result = handlers.handle_draw_rectangle({
            "sketch_id": "S1", "corner1": [0, 0], "corner2": [20, 30]})
        assert "curve_ids" in result
        assert len(result["curve_ids"]) == 4

    def test_3d_rect_xy(self, handlers, fake_sketch):
        result = handlers.handle_draw_rectangle_3d({
            "sketch_id": "S1",
            "world_corner1": [0, 0, 0], "world_corner2": [20, 30, 0]})
        assert "curve_ids" in result
        assert result["plane_type"] == "XY"


class TestDrawSpline:
    def test_open_spline(self, handlers, fake_sketch):
        result = handlers.handle_draw_spline({
            "sketch_id": "S1",
            "points": [[0, 0], [5, 10], [10, 0]]})
        assert "curve_id" in result

    def test_closed_spline(self, handlers, fake_sketch):
        result = handlers.handle_draw_spline({
            "sketch_id": "S1",
            "points": [[0, 0], [5, 10], [10, 0]],
            "closed": True})
        assert "curve_id" in result


class TestDrawPolygon:
    def test_hexagon(self, handlers, fake_sketch):
        result = handlers.handle_draw_polygon({
            "sketch_id": "S1", "center": [50, 50],
            "radius": 30, "sides": 6})
        assert "curve_ids" in result
        assert len(result["curve_ids"]) == 6
        assert result["vertex_count"] == 6

    def test_triangle(self, handlers, fake_sketch):
        result = handlers.handle_draw_polygon({
            "sketch_id": "S1", "center": [0, 0],
            "radius": 10, "sides": 3})
        assert len(result["curve_ids"]) == 3

    def test_rotated_polygon(self, handlers, fake_sketch):
        result = handlers.handle_draw_polygon({
            "sketch_id": "S1", "center": [0, 0],
            "radius": 10, "sides": 4, "rotation": 45})
        assert len(result["curve_ids"]) == 4


class TestDrawSlot:
    def test_basic_slot(self, handlers, fake_sketch):
        result = handlers.handle_draw_slot({
            "sketch_id": "S1",
            "center1": [10, 10], "center2": [40, 10], "radius": 5})
        assert "curve_ids" in result
        assert len(result["curve_ids"]) == 4

    def test_slot_same_centers_raises(self, handlers, fake_sketch):
        with pytest.raises(Exception, match="center1 and center2 must be different"):
            handlers.handle_draw_slot({
                "sketch_id": "S1",
                "center1": [10, 10], "center2": [10, 10], "radius": 5})


class TestDrawCenterline:
    def test_centerline_is_construction(self, handlers, fake_sketch):
        result = handlers.handle_draw_centerline({
            "sketch_id": "S1", "start": [0, 0], "end": [100, 0]})
        assert "curve_id" in result
        curve = fake_sketch.sketchCurves.item(0)
        assert curve.isConstruction is True


class TestDrawPoint:
    def test_place_point(self, handlers, fake_sketch):
        result = handlers.handle_draw_point({
            "sketch_id": "S1", "position": [25, 50]})
        assert "point_id" in result


# ── Modifications ─────────────────────────────────────────────

class TestSketchFillet:
    def test_fillet_two_lines(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        handlers.handle_draw_line({"sketch_id": "S1", "start": [10, 0], "end": [10, 10]})
        result = handlers.handle_sketch_fillet({
            "sketch_id": "S1", "curve1_id": "S1_curve_0",
            "curve2_id": "S1_curve_1", "radius": 2})
        assert "curve_id" in result

    def test_fillet_same_curve_raises(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        with pytest.raises(Exception, match="Cannot fillet a curve with itself"):
            handlers.handle_sketch_fillet({
                "sketch_id": "S1", "curve1_id": "S1_curve_0",
                "curve2_id": "S1_curve_0", "radius": 2})


class TestSketchTrim:
    def test_trim_curve(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        result = handlers.handle_sketch_trim({
            "sketch_id": "S1", "curve_id": "S1_curve_0", "point": [5, 0]})
        assert result["success"] is True

    def test_trim_invalid_id_raises(self, handlers, fake_sketch):
        with pytest.raises(Exception, match="Invalid curve_id format"):
            handlers.handle_sketch_trim({
                "sketch_id": "S1", "curve_id": "bad", "point": [5, 0]})


class TestSketchExtend:
    def test_extend_curve(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        result = handlers.handle_sketch_extend({
            "sketch_id": "S1", "curve_id": "S1_curve_0", "point": [20, 0]})
        assert result["success"] is True

    def test_extend_from_start(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        result = handlers.handle_sketch_extend({
            "sketch_id": "S1", "curve_id": "S1_curve_0",
            "point": [-5, 0], "from_start": True})
        assert result["success"] is True


class TestSketchOffset:
    def test_offset_curves(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        result = handlers.handle_sketch_offset({
            "sketch_id": "S1", "curve_ids": ["S1_curve_0"],
            "direction_point": [0, 5], "distance": 3})
        assert "curve_ids" in result

    def test_offset_no_curves_raises(self, handlers, fake_sketch):
        with pytest.raises(Exception, match="No valid curves found"):
            handlers.handle_sketch_offset({
                "sketch_id": "S1", "curve_ids": ["S1_curve_99"],
                "direction_point": [0, 5], "distance": 3})


class TestSketchMirror:
    def test_mirror_curves(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        handlers.handle_draw_centerline({"sketch_id": "S1", "start": [5, -10], "end": [5, 10]})
        result = handlers.handle_sketch_mirror({
            "sketch_id": "S1", "curve_ids": ["S1_curve_0"],
            "mirror_line_id": "S1_curve_1"})
        assert "curve_ids" in result


class TestSketchPatternRectangular:
    def test_rect_pattern(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [5, 0]})
        result = handlers.handle_sketch_pattern_rectangular({
            "sketch_id": "S1", "curve_ids": ["S1_curve_0"],
            "x_count": 3, "y_count": 2, "x_spacing": 10, "y_spacing": 10})
        assert "curve_ids" in result
        assert result["count"] == 5


class TestSketchPatternCircular:
    def test_circ_pattern(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [10, 0], "end": [15, 0]})
        result = handlers.handle_sketch_pattern_circular({
            "sketch_id": "S1", "curve_ids": ["S1_curve_0"],
            "center": [0, 0], "count": 4})
        assert "curve_ids" in result
        assert result["count"] == 3


# ── Constraints ───────────────────────────────────────────────

class TestApplyCoincidentConstraints:
    def test_no_gaps(self, handlers, fake_sketch):
        result = handlers.handle_apply_coincident_constraints({"sketch_id": "S1"})
        assert "constraints_added" in result
        assert "summary" in result


class TestAddConstraint:
    @pytest.mark.parametrize("ctype", [
        "horizontal", "vertical", "fix",
    ])
    def test_single_entity_constraints(self, handlers, fake_sketch, ctype):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        result = handlers.handle_add_constraint({
            "sketch_id": "S1", "constraint_type": ctype,
            "entity1": "S1_curve_0"})
        assert result["success"] is True

    @pytest.mark.parametrize("ctype", [
        "coincident", "perpendicular", "parallel", "tangent",
        "equal", "concentric", "midpoint", "collinear",
    ])
    def test_two_entity_constraints(self, handlers, fake_sketch, ctype):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        handlers.handle_draw_line({"sketch_id": "S1", "start": [10, 0], "end": [10, 10]})
        result = handlers.handle_add_constraint({
            "sketch_id": "S1", "constraint_type": ctype,
            "entity1": "S1_curve_0", "entity2": "S1_curve_1"})
        assert result["success"] is True

    def test_unknown_type_raises(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        with pytest.raises(Exception, match="Unknown constraint type"):
            handlers.handle_add_constraint({
                "sketch_id": "S1", "constraint_type": "bogus",
                "entity1": "S1_curve_0"})


class TestListConstraints:
    def test_empty_sketch(self, handlers, fake_sketch):
        result = handlers.handle_list_constraints({"sketch_id": "S1"})
        assert result["constraint_count"] == 0
        assert result["constraints"] == []


# ── Dimensions ────────────────────────────────────────────────

class TestListDimensions:
    def test_empty_sketch(self, handlers, fake_sketch):
        result = handlers.handle_list_sketch_dimensions({"sketch_id": "S1"})
        assert result["dimension_count"] == 0


class TestEditDimension:
    def test_edit_by_index(self, handlers, fake_sketch):
        fake_sketch.sketchDimensions._items.append(
            __import__("conftest", fromlist=["FakeDimension"]).FakeDimension())
        result = handlers.handle_edit_sketch_dimension({
            "sketch_id": "S1", "dimension_index": 0, "value": 25})
        assert result["success"] is True

    def test_missing_dim_raises(self, handlers, fake_sketch):
        with pytest.raises(Exception, match="Dimension not found"):
            handlers.handle_edit_sketch_dimension({
                "sketch_id": "S1", "dimension_index": 99, "value": 10})


class TestAddDimension:
    def test_distance_dim_one_entity(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [50, 0]})
        result = handlers.handle_add_dimension({
            "sketch_id": "S1", "dimension_type": "distance",
            "entity1": "S1_curve_0"})
        assert "dimension_id" in result

    def test_unknown_dim_type_raises(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        with pytest.raises(Exception, match="Unknown dimension type"):
            handlers.handle_add_dimension({
                "sketch_id": "S1", "dimension_type": "bogus",
                "entity1": "S1_curve_0"})


# ── Gap analysis ──────────────────────────────────────────────

class TestAnalyzeGaps:
    def test_empty_sketch(self, handlers, fake_sketch):
        result = handlers.handle_analyze_sketch_gaps({"sketch_id": "S1"})
        assert "gaps" in result
        assert "summary" in result

    def test_with_open_curves(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        handlers.handle_draw_line({"sketch_id": "S1", "start": [10.005, 0], "end": [20, 0]})
        result = handlers.handle_analyze_sketch_gaps({
            "sketch_id": "S1", "tolerance": 0.1})
        assert result["summary"]["total_gaps"] >= 0


class TestCloseGaps:
    def test_dry_run(self, handlers, fake_sketch):
        result = handlers.handle_close_sketch_gaps({
            "sketch_id": "S1", "dry_run": True})
        assert result["dry_run"] is True
        assert "actions" in result


class TestRecreateAsPolygon:
    def test_recreate_from_existing_curves(self, handlers, fake_sketch, fake_component):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        handlers.handle_draw_line({"sketch_id": "S1", "start": [10, 0], "end": [10, 10]})
        handlers.handle_draw_line({"sketch_id": "S1", "start": [10, 10], "end": [0, 0]})
        result = handlers.handle_recreate_sketch_as_polygon({"sketch_id": "S1"})
        assert result["success"] is True
        assert result["vertices_used"] == 3


# ── Query ─────────────────────────────────────────────────────

class TestGetSketchProfiles:
    def test_returns_profiles(self, handlers, fake_sketch):
        result = handlers.handle_get_sketch_profiles({"sketch_id": "S1"})
        assert result["profile_count"] == 1
        assert "profiles" in result


class TestSuggestSketchCoords:
    @pytest.mark.parametrize("plane", ["xy", "xz", "yz"])
    def test_each_plane(self, handlers, plane):
        result = handlers.handle_suggest_sketch_coords({
            "plane": plane,
            "world_min": [0, 0, 0], "world_max": [100, 100, 100]})
        assert "sketch_rectangle" in result
        assert "explanation" in result

    def test_unknown_plane_returns_error(self, handlers):
        result = handlers.handle_suggest_sketch_coords({"plane": "qq"})
        assert result.get("error") is True


class TestSketchTo3dCoords:
    def test_converts_points(self, handlers, fake_sketch):
        result = handlers.handle_sketch_to_3d_coords({
            "sketch_id": "S1", "points": [[0, 0], [10, 20]]})
        assert len(result["coordinate_mapping"]) == 2


class TestGetSketchInfo:
    def test_empty_sketch(self, handlers, fake_sketch):
        result = handlers.handle_get_sketch_info({"sketch_id": "S1"})
        assert result["curve_count"] == 0
        assert result["sketch_id"] == "S1"

    def test_with_curves(self, handlers, fake_sketch):
        handlers.handle_draw_line({"sketch_id": "S1", "start": [0, 0], "end": [10, 0]})
        handlers.handle_draw_circle({"sketch_id": "S1", "center": [5, 5], "radius": 3})
        result = handlers.handle_get_sketch_info({"sketch_id": "S1"})
        assert result["curve_count"] == 2


# ── Import / Text ─────────────────────────────────────────────

class TestImportSVG:
    def test_missing_path_raises(self, handlers):
        with pytest.raises(Exception, match="svg_path is required"):
            handlers.handle_import_svg({})

    def test_nonexistent_file_raises(self, handlers):
        with pytest.raises(Exception, match="SVG file not found"):
            handlers.handle_import_svg({"svg_path": "/tmp/nonexistent.svg"})


class TestAddText:
    def test_missing_text_raises(self, handlers):
        with pytest.raises(Exception, match="text is required"):
            handlers.handle_add_text({})

    def test_text_on_existing_sketch(self, handlers, fake_sketch, patch_helpers):
        result = handlers.handle_add_text({
            "text": "Hello", "sketch_id": "S1"})
        assert result["success"] is True


# ── Route table ───────────────────────────────────────────────

class TestSketchRoutes:
    def test_all_38_routes_registered(self, handlers):
        assert len(handlers.SKETCH_ROUTES) == 38

    def test_all_routes_are_callable(self, handlers):
        for route, fn in handlers.SKETCH_ROUTES.items():
            assert callable(fn), f"Route {route} is not callable"
            assert route.startswith("/"), f"Route {route} must start with /"
