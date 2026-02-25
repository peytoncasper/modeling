"""Tests for the fusion-sketch CLI — argument parsing and subcommand dispatch.

These tests verify that argparse accepts valid arguments and rejects bad ones.
We mock the HTTP call() function so no bridge connection is needed.
"""

import sys
import json
import importlib
import importlib.machinery
import types
import pytest
from unittest.mock import patch, MagicMock

CLI_PATH = "/Users/peytocas/Documents/modeling/tools/fusion-sketch"


@pytest.fixture
def cli():
    """Import the fusion-sketch CLI as a module (extensionless script)."""
    loader = importlib.machinery.SourceFileLoader("fusion_sketch_cli", CLI_PATH)
    spec = importlib.util.spec_from_loader("fusion_sketch_cli", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def mock_call(cli):
    """Replace call() with a recorder that captures invocations."""
    calls = []

    def fake_call(endpoint, body=None):
        calls.append({"endpoint": endpoint, "body": body or {}})
        return {"success": True, "mocked": True}

    original = cli.call
    cli.call = fake_call
    yield calls
    cli.call = original


# ── Parser tests ──────────────────────────────────────────────

class TestParserValidation:
    def test_create_defaults(self, cli):
        p = cli.build_parser()
        args = p.parse_args(["create"])
        assert args.plane == "xy"
        assert args.name is None

    def test_create_all_opts(self, cli):
        p = cli.build_parser()
        args = p.parse_args(["create", "--plane", "xz", "--name", "S", "--component", "C1"])
        assert args.plane == "xz"
        assert args.name == "S"
        assert args.component == "C1"

    def test_line_requires_sketch(self, cli):
        p = cli.build_parser()
        with pytest.raises(SystemExit):
            p.parse_args(["line", "--start", "0,0", "--end", "10,0"])

    def test_polygon_defaults(self, cli):
        p = cli.build_parser()
        args = p.parse_args(["polygon", "--sketch", "S", "--center", "0,0", "--radius", "10"])
        assert args.sides == 6
        assert args.rotation is None

    def test_constrain_choices(self, cli):
        p = cli.build_parser()
        args = p.parse_args(["constrain", "--sketch", "S", "--type", "perpendicular",
                             "--e1", "c0", "--e2", "c1"])
        assert args.type == "perpendicular"

    def test_constrain_invalid_type(self, cli):
        p = cli.build_parser()
        with pytest.raises(SystemExit):
            p.parse_args(["constrain", "--sketch", "S", "--type", "bogus", "--e1", "c0"])

    def test_add_dim_choices(self, cli):
        p = cli.build_parser()
        args = p.parse_args(["add-dim", "--sketch", "S", "--type", "distance", "--e1", "c0"])
        assert args.type == "distance"


# ── Point parsing ─────────────────────────────────────────────

class TestPointParsing:
    def test_p2_valid(self, cli):
        assert cli.p2("10,20") == [10.0, 20.0]

    def test_p2_with_spaces(self, cli):
        assert cli.p2("10 , 20") == [10.0, 20.0]

    def test_p2_negative(self, cli):
        assert cli.p2("-5.5,3.2") == [-5.5, 3.2]

    def test_p2_wrong_count_exits(self, cli):
        with pytest.raises(SystemExit):
            cli.p2("1,2,3")

    def test_p3_valid(self, cli):
        assert cli.p3("1,2,3") == [1.0, 2.0, 3.0]

    def test_p3_wrong_count_exits(self, cli):
        with pytest.raises(SystemExit):
            cli.p3("1,2")


# ── Subcommand dispatch ──────────────────────────────────────

class TestSubcommandDispatch:
    """Verify each subcommand calls the correct bridge endpoint."""

    def _run(self, cli, mock_call, argv):
        p = cli.build_parser()
        args = p.parse_args(argv)
        args.func(args)
        return mock_call

    def test_create(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["create", "--plane", "xz", "--name", "S"])
        assert calls[0]["endpoint"] == "/create_sketch"
        assert calls[0]["body"]["plane"] == "xz"
        assert calls[0]["body"]["name"] == "S"

    def test_create_on_face(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["create-on-face", "--body", "B1", "--face", "B1_face_0"])
        assert calls[0]["endpoint"] == "/create_sketch_on_face"

    def test_finish(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["finish", "--sketch", "S"])
        assert calls[0]["endpoint"] == "/finish_sketch"

    def test_delete(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["delete", "--sketch", "S"])
        assert calls[0]["endpoint"] == "/delete_sketch"

    def test_list(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["list"])
        assert calls[0]["endpoint"] == "/list_sketches"

    def test_line(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["line", "--sketch", "S", "--start", "0,0", "--end", "10,0"])
        assert calls[0]["endpoint"] == "/draw_line"
        assert calls[0]["body"]["start"] == [0.0, 0.0]
        assert calls[0]["body"]["end"] == [10.0, 0.0]

    def test_line_construction(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["line", "--sketch", "S", "--start", "0,0", "--end", "10,0",
                           "--construction"])
        assert calls[0]["body"]["construction"] is True

    def test_arc(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["arc", "--sketch", "S", "--center", "0,0",
                           "--radius", "10", "--start-angle", "0", "--sweep", "90"])
        assert calls[0]["endpoint"] == "/draw_arc"

    def test_arc3(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["arc3", "--sketch", "S", "--start", "0,0",
                           "--mid", "5,5", "--end", "10,0"])
        assert calls[0]["endpoint"] == "/draw_arc_3point"

    def test_circle(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["circle", "--sketch", "S", "--center", "0,0", "--radius", "25"])
        assert calls[0]["endpoint"] == "/draw_circle"
        assert calls[0]["body"]["radius"] == 25.0

    def test_rect(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["rect", "--sketch", "S", "--c1", "0,0", "--c2", "20,30"])
        assert calls[0]["endpoint"] == "/draw_rectangle"

    def test_rect3d(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["rect3d", "--sketch", "S", "--wc1", "0,0,0", "--wc2", "20,30,0"])
        assert calls[0]["endpoint"] == "/draw_rectangle_3d"

    def test_spline(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["spline", "--sketch", "S", "--points", "0,0", "5,10", "10,0"])
        assert calls[0]["endpoint"] == "/draw_spline"
        assert len(calls[0]["body"]["points"]) == 3

    def test_spline_closed(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["spline", "--sketch", "S", "--points", "0,0", "5,10", "10,0",
                           "--closed"])
        assert calls[0]["body"]["closed"] is True

    def test_polygon(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["polygon", "--sketch", "S", "--center", "50,50",
                           "--radius", "30", "--sides", "8"])
        assert calls[0]["endpoint"] == "/draw_polygon"
        assert calls[0]["body"]["sides"] == 8

    def test_slot(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["slot", "--sketch", "S", "--c1", "10,10",
                           "--c2", "40,10", "--radius", "5"])
        assert calls[0]["endpoint"] == "/draw_slot"

    def test_centerline(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["centerline", "--sketch", "S", "--start", "0,0", "--end", "100,0"])
        assert calls[0]["endpoint"] == "/draw_centerline"

    def test_point(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["point", "--sketch", "S", "--pos", "25,50"])
        assert calls[0]["endpoint"] == "/draw_point"

    def test_fillet(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["fillet", "--sketch", "S", "--c1", "S_curve_0",
                           "--c2", "S_curve_1", "--radius", "2"])
        assert calls[0]["endpoint"] == "/sketch_fillet"

    def test_trim(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["trim", "--sketch", "S", "--curve", "S_curve_0", "--point", "5,0"])
        assert calls[0]["endpoint"] == "/sketch_trim"
        assert calls[0]["body"]["point"] == [5.0, 0.0]

    def test_extend(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["extend", "--sketch", "S", "--curve", "S_curve_0",
                           "--point", "20,0"])
        assert calls[0]["endpoint"] == "/sketch_extend"

    def test_extend_from_start(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["extend", "--sketch", "S", "--curve", "S_curve_0",
                           "--point=-5,0", "--from-start"])
        assert calls[0]["body"]["from_start"] is True

    def test_offset(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["offset", "--sketch", "S", "--curves", "c0", "c1",
                           "--dist", "3", "--dir", "0,10"])
        assert calls[0]["endpoint"] == "/sketch_offset"
        assert calls[0]["body"]["curve_ids"] == ["c0", "c1"]

    def test_mirror(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["mirror", "--sketch", "S", "--curves", "c0",
                           "--line", "c4"])
        assert calls[0]["endpoint"] == "/sketch_mirror"

    def test_pattern_rect(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["pattern-rect", "--sketch", "S", "--curves", "c0",
                           "--xn", "3", "--yn", "2", "--xs", "15", "--ys", "20"])
        assert calls[0]["endpoint"] == "/sketch_pattern_rectangular"
        assert calls[0]["body"]["x_count"] == 3

    def test_pattern_circ(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["pattern-circ", "--sketch", "S", "--curves", "c0",
                           "--center", "0,0", "--count", "6"])
        assert calls[0]["endpoint"] == "/sketch_pattern_circular"
        assert calls[0]["body"]["count"] == 6

    def test_coincident(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["coincident", "--sketch", "S"])
        assert calls[0]["endpoint"] == "/apply_coincident_constraints"

    def test_constrain(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["constrain", "--sketch", "S", "--type", "horizontal",
                           "--e1", "c0"])
        assert calls[0]["endpoint"] == "/add_constraint"
        assert calls[0]["body"]["constraint_type"] == "horizontal"

    def test_list_constraints(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["list-constraints", "--sketch", "S"])
        assert calls[0]["endpoint"] == "/list_constraints"

    def test_dims(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["dims", "--sketch", "S"])
        assert calls[0]["endpoint"] == "/list_sketch_dimensions"

    def test_dim_edit_value(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["dim-edit", "--sketch", "S", "--dim", "0", "--value", "25"])
        assert calls[0]["endpoint"] == "/edit_sketch_dimension"
        assert calls[0]["body"]["value"] == 25.0

    def test_dim_edit_expr(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["dim-edit", "--sketch", "S", "--dim", "0", "--expr", "d1 * 2"])
        assert calls[0]["body"]["expression"] == "d1 * 2"

    def test_add_dim(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["add-dim", "--sketch", "S", "--type", "radius", "--e1", "c0",
                           "--value", "5"])
        assert calls[0]["endpoint"] == "/add_dimension"
        assert calls[0]["body"]["dimension_type"] == "radius"

    def test_gaps(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["gaps", "--sketch", "S", "--tolerance", "0.05"])
        assert calls[0]["endpoint"] == "/analyze_sketch_gaps"
        assert calls[0]["body"]["tolerance"] == 0.05

    def test_close_gaps_dry_run(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["close-gaps", "--sketch", "S", "--dry-run"])
        assert calls[0]["endpoint"] == "/close_sketch_gaps"
        assert calls[0]["body"]["dry_run"] is True

    def test_recreate(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["recreate", "--sketch", "S", "--new-name", "S_fixed",
                           "--delete-orig"])
        assert calls[0]["endpoint"] == "/recreate_sketch_as_polygon"
        assert calls[0]["body"]["delete_original"] is True

    def test_profiles(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["profiles", "--sketch", "S"])
        assert calls[0]["endpoint"] == "/get_sketch_profiles"

    def test_info(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["info", "--sketch", "S"])
        assert calls[0]["endpoint"] == "/get_sketch_info"

    def test_coords(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["coords", "--sketch", "S", "--points", "0,0", "10,20"])
        assert calls[0]["endpoint"] == "/sketch_to_3d_coords"
        assert len(calls[0]["body"]["points"]) == 2

    def test_suggest(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["suggest", "--plane", "xz", "--wmin", "0,0,0",
                           "--wmax", "100,100,100"])
        assert calls[0]["endpoint"] == "/suggest_sketch_coords"
        assert calls[0]["body"]["plane"] == "xz"

    def test_graph(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["graph", "--sketch", "S"])
        assert calls[0]["endpoint"] == "/get_local_graph"
        assert calls[0]["body"]["focus_id"] == "S"

    def test_graph_auto(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["graph"])
        assert calls[0]["body"]["focus_kind"] == "auto"

    def test_state(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["state"])
        assert calls[0]["endpoint"] == "/get_state"

    def test_state_compact(self, cli, mock_call):
        calls = self._run(cli, mock_call, ["state", "--compact"])
        assert calls[0]["endpoint"] == "/get_state_compact"

    def test_import_svg(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["import-svg", "--path", "/tmp/test.svg", "--plane", "xy"])
        assert calls[0]["endpoint"] == "/import_svg"
        assert calls[0]["body"]["svg_path"] == "/tmp/test.svg"

    def test_text(self, cli, mock_call):
        calls = self._run(cli, mock_call,
                          ["text", "--text", "Hello", "--sketch", "S",
                           "--font", "Courier", "--height", "12"])
        assert calls[0]["endpoint"] == "/add_text"
        assert calls[0]["body"]["text"] == "Hello"
        assert calls[0]["body"]["font"] == "Courier"
        assert calls[0]["body"]["height"] == 12.0


# ── Completeness check ───────────────────────────────────────

class TestCompleteness:
    """Every SKETCH_ROUTES endpoint should have a CLI subcommand."""

    EXPECTED_ENDPOINTS = [
        "/create_sketch", "/create_sketch_on_face", "/finish_sketch",
        "/delete_sketch", "/list_sketches",
        "/draw_line", "/draw_arc", "/draw_arc_3point", "/draw_circle",
        "/draw_rectangle", "/draw_rectangle_3d", "/draw_spline",
        "/draw_polygon", "/draw_slot", "/draw_centerline", "/draw_point",
        "/sketch_fillet", "/sketch_trim", "/sketch_extend",
        "/sketch_offset", "/sketch_mirror",
        "/sketch_pattern_rectangular", "/sketch_pattern_circular",
        "/apply_coincident_constraints", "/add_constraint",
        "/add_dimension", "/list_constraints",
        "/list_sketch_dimensions", "/edit_sketch_dimension",
        "/analyze_sketch_gaps", "/close_sketch_gaps",
        "/recreate_sketch_as_polygon",
        "/get_sketch_profiles", "/suggest_sketch_coords",
        "/sketch_to_3d_coords", "/get_sketch_info",
        "/import_svg", "/add_text",
    ]

    def test_count_matches(self):
        assert len(self.EXPECTED_ENDPOINTS) == 38

    def test_all_endpoints_have_cli_subcommand(self, cli, mock_call):
        """Ensures that every known endpoint is reachable by some CLI subcommand."""
        reached = set()

        # Run every subcommand with minimal valid args
        commands = [
            ["create"],
            ["create-on-face", "--body", "B", "--face", "F"],
            ["finish", "--sketch", "S"],
            ["delete", "--sketch", "S"],
            ["list"],
            ["line", "--sketch", "S", "--start", "0,0", "--end", "1,0"],
            ["arc", "--sketch", "S", "--center", "0,0", "--radius", "1",
             "--start-angle", "0", "--sweep", "90"],
            ["arc3", "--sketch", "S", "--start", "0,0", "--mid", "1,1", "--end", "2,0"],
            ["circle", "--sketch", "S", "--center", "0,0", "--radius", "1"],
            ["rect", "--sketch", "S", "--c1", "0,0", "--c2", "1,1"],
            ["rect3d", "--sketch", "S", "--wc1", "0,0,0", "--wc2", "1,1,0"],
            ["spline", "--sketch", "S", "--points", "0,0", "1,1"],
            ["polygon", "--sketch", "S", "--center", "0,0", "--radius", "1"],
            ["slot", "--sketch", "S", "--c1", "0,0", "--c2", "1,0", "--radius", "1"],
            ["centerline", "--sketch", "S", "--start", "0,0", "--end", "1,0"],
            ["point", "--sketch", "S", "--pos", "0,0"],
            ["fillet", "--sketch", "S", "--c1", "c0", "--c2", "c1", "--radius", "1"],
            ["trim", "--sketch", "S", "--curve", "c0", "--point", "0,0"],
            ["extend", "--sketch", "S", "--curve", "c0", "--point", "0,0"],
            ["offset", "--sketch", "S", "--curves", "c0", "--dist", "1", "--dir", "0,1"],
            ["mirror", "--sketch", "S", "--curves", "c0", "--line", "c1"],
            ["pattern-rect", "--sketch", "S", "--curves", "c0"],
            ["pattern-circ", "--sketch", "S", "--curves", "c0", "--center", "0,0"],
            ["coincident", "--sketch", "S"],
            ["constrain", "--sketch", "S", "--type", "horizontal", "--e1", "c0"],
            ["add-dim", "--sketch", "S", "--type", "distance", "--e1", "c0"],
            ["list-constraints", "--sketch", "S"],
            ["dims", "--sketch", "S"],
            ["dim-edit", "--sketch", "S", "--dim", "0", "--value", "1"],
            ["gaps", "--sketch", "S"],
            ["close-gaps", "--sketch", "S"],
            ["recreate", "--sketch", "S"],
            ["profiles", "--sketch", "S"],
            ["suggest", "--wmin", "0,0,0", "--wmax", "1,1,1"],
            ["coords", "--sketch", "S", "--points", "0,0"],
            ["info", "--sketch", "S"],
            ["import-svg", "--path", "/tmp/x.svg"],
            ["text", "--text", "T"],
        ]

        p = cli.build_parser()
        for argv in commands:
            args = p.parse_args(argv)
            args.func(args)

        for c in mock_call:
            reached.add(c["endpoint"])

        # graph and state are nav endpoints, not in SKETCH_ROUTES
        for ep in self.EXPECTED_ENDPOINTS:
            assert ep in reached, f"Endpoint {ep} has no CLI subcommand"
