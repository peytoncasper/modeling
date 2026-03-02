"""CAM 2D/2.5D milling operation handlers for Fusion 360 MCP Bridge.

All 2D operations: contour, pocket, adaptive, drilling, face, engrave,
trace, slot, chamfer, and miter clearing.

Every public function has the signature ``handle_*(body: dict) -> dict``
and is registered in CAM_2D_ROUTES.

Endpoints (16):
  2D OPERATIONS
    /cam_2d_contour          – 2D contour (profile cut)
    /cam_2d_contour_advanced – 2D contour with full parameter control
    /cam_2d_pocket           – 2D pocket (area clearance)
    /cam_2d_adaptive         – 2D adaptive clearing (constant engagement)
    /cam_2d_face             – facing operation (surface top)
    /cam_2d_engrave          – engrave (follow curves at depth)
    /cam_2d_trace            – trace (V-bit miter cuts, multi-depth)
    /cam_2d_drill            – drilling cycle
    /cam_2d_bore             – bore cycle
    /cam_2d_slot             – slot milling
    /cam_2d_chamfer          – 2D chamfer deburring
    /cam_2d_miter_clearing   – terraced clearing for miter joints
  OPERATION MANAGEMENT
    /cam_2d_edit_op          – edit operation parameters
    /cam_2d_suppress_op      – suppress/unsuppress an operation
    /cam_2d_reorder_op       – reorder an operation within its setup
    /cam_2d_delete_op        – delete an operation
"""

import json
import math
import os
import time
import traceback

import adsk.core
import adsk.fusion
import adsk.cam

try:
    from bridge_helpers import get_design, get_root
except ImportError:
    from .bridge_helpers import get_design, get_root


# ── Helpers ──────────────────────────────────────────────────

def _get_cam():
    app = adsk.core.Application.get()
    cam = adsk.cam.CAM.cast(app.activeProduct)
    if cam:
        return cam
    doc = app.activeDocument
    if doc:
        for product in doc.products:
            if product.productType == "CAMProductType":
                return adsk.cam.CAM.cast(product)
    raise Exception("CAM not available. Switch to Manufacturing workspace first.")


def _find_setup(cam, name):
    if name:
        for s in cam.setups:
            if s.name == name:
                return s
        raise Exception(f"Setup not found: {name}")
    if cam.setups.count > 0:
        return cam.setups.item(cam.setups.count - 1)
    raise Exception("No setup available. Create a setup first.")


def _find_op(cam, op_name):
    for setup in cam.setups:
        for op in setup.allOperations:
            if op.name == op_name:
                return op, setup
    raise Exception(f"Operation not found: {op_name}")


_LOCAL_LIB_PATH = os.path.join(
    os.path.expanduser("~"),
    "Library", "Application Support", "Autodesk", "CAM360", "libraries", "Local", "Library.json",
)


def _find_tool_by_number(tool_number, tool_description=None):
    """Search document operations, then API library, then JSON file for a tool.

    When tool_description is provided, it must be a case-insensitive substring
    of the tool's description — useful for disambiguation when multiple tools
    share the same number.
    """
    def _matches(tj):
        if tj.get("post-process", {}).get("number") != tool_number:
            return False
        if tool_description:
            desc = tj.get("description", "").lower()
            if tool_description.lower() not in desc:
                return False
        return True

    cam = _get_cam()
    for op in cam.allOperations:
        try:
            t = op.tool
            if t:
                tj = json.loads(t.toJson())
                if _matches(tj):
                    return t
        except Exception:
            pass

    mgr = adsk.cam.CAMManager.get()
    lib_mgr = mgr.libraryManager
    tool_libs = lib_mgr.toolLibraries
    local_url = tool_libs.urlByLocation(adsk.cam.LibraryLocations.LocalLibraryLocation)
    if local_url:
        child_urls = tool_libs.childAssetURLs(local_url)
        if child_urls:
            for curl in child_urls:
                try:
                    lib = tool_libs.toolLibraryAtURL(curl)
                    if not lib or lib.count == 0:
                        continue
                    for i in range(lib.count):
                        tool = lib.item(i)
                        if tool:
                            tj = json.loads(tool.toJson())
                            if _matches(tj):
                                return tool
                except Exception:
                    pass

    # Fallback: search the JSON library file directly (picks up newly added tools)
    try:
        if os.path.exists(_LOCAL_LIB_PATH):
            with open(_LOCAL_LIB_PATH) as f:
                lib_data = json.load(f)
            for td in lib_data.get("data", []):
                if _matches(td):
                    return adsk.cam.Tool.createFromJson(json.dumps(td))
    except Exception:
        pass
    return None


def _find_tool_by_type(tool_type_filter):
    """Search tool libraries for a tool matching a type string."""
    mgr = adsk.cam.CAMManager.get()
    lib_mgr = mgr.libraryManager
    tool_libs = lib_mgr.toolLibraries
    local_url = tool_libs.urlByLocation(adsk.cam.LibraryLocations.LocalLibraryLocation)
    if not local_url:
        return None
    child_urls = tool_libs.childAssetURLs(local_url)
    if not child_urls:
        return None
    filt = tool_type_filter.lower()
    for curl in child_urls:
        try:
            lib = tool_libs.toolLibraryAtURL(curl)
            if not lib or lib.count == 0:
                continue
            for i in range(lib.count):
                tool = lib.item(i)
                if tool:
                    tj = json.loads(tool.toJson())
                    tstr = tj.get("type", "").lower()
                    if filt in tstr:
                        return tool
        except Exception:
            pass
    return None


def _set_common_params(op, body, changes):
    """Set parameters common to most 2D operations."""
    params = op.parameters

    depth = body.get("depth")
    if depth:
        p = params.itemByName("bottomHeight_offset")
        if p:
            val = -abs(float(depth))
            p.expression = f"{val} mm"
            changes.append(f"Depth: {depth}mm")

    stepdown = body.get("stepdown")
    if stepdown:
        p = params.itemByName("useMultipleDepths")
        if p:
            p.expression = "true"
        p = params.itemByName("maximumStepdown")
        if p:
            p.expression = f"{stepdown} mm"
            changes.append(f"Stepdown: {stepdown}mm")

    stock_to_leave = body.get("stock_to_leave")
    if stock_to_leave is not None:
        p = params.itemByName("stockToLeave")
        if p:
            p.expression = f"{stock_to_leave} mm"
            changes.append(f"Stock to leave: {stock_to_leave}mm")

    floor_stock = body.get("floor_stock")
    if floor_stock is not None:
        p = params.itemByName("stockToLeaveFloor")
        if p:
            p.expression = f"{floor_stock} mm"
            changes.append(f"Floor stock to leave: {floor_stock}mm")

    compensation = body.get("compensation")
    if compensation:
        p = params.itemByName("sidewaysCompensation")
        if p:
            comp_map = {
                "left": "'left (climb)'",
                "right": "'right (conventional)'",
                "center": "'center'",
                "off": "'off'",
            }
            if compensation in comp_map:
                p.expression = comp_map[compensation]
                changes.append(f"Compensation: {compensation}")

    boundary = body.get("boundary")
    if boundary:
        p = params.itemByName("machiningBoundary")
        if p:
            if boundary == "silhouette":
                p.expression = "'silhouette'"
            elif boundary == "selection":
                p.expression = "'selection'"
            changes.append(f"Boundary: {boundary}")

    # Tabs
    use_tabs = body.get("tabs")
    if use_tabs:
        p = params.itemByName("tabbing")
        if p:
            p.expression = "true"
            changes.append("Tabs enabled")
        tab_width = body.get("tab_width")
        if tab_width:
            p = params.itemByName("tabWidth")
            if p:
                p.expression = f"{tab_width} mm"
                changes.append(f"Tab width: {tab_width}mm")
        tab_height = body.get("tab_height")
        if tab_height:
            p = params.itemByName("tabHeight")
            if p:
                p.expression = f"{tab_height} mm"
                changes.append(f"Tab height: {tab_height}mm")
        tab_count = body.get("tab_count")
        if tab_count:
            p = params.itemByName("tabCount")
            if p:
                p.expression = str(tab_count)
                changes.append(f"Tab count: {tab_count}")

    # Ramp / lead-in
    ramp_type = body.get("ramp")
    if ramp_type:
        p = params.itemByName("rampType")
        if p:
            ramp_map = {
                "helix": "'helix'",
                "plunge": "'plunge'",
                "ramp": "'ramp'",
                "profile": "'profile'",
            }
            if ramp_type in ramp_map:
                p.expression = ramp_map[ramp_type]
                changes.append(f"Ramp: {ramp_type}")

    # Heights
    for hname, key in [
        ("clearanceHeight", "clearance_height"),
        ("retractHeight", "retract_height"),
        ("feedHeight", "feed_height"),
    ]:
        val = body.get(key)
        if val is not None:
            mode_p = params.itemByName(f"{hname}_mode")
            if mode_p:
                mode_p.expression = "'from stock top'"
            offset_p = params.itemByName(f"{hname}_offset")
            if offset_p:
                offset_p.expression = f"{val} mm"
                changes.append(f"{hname}: {val}mm from stock top")


def _set_tool_on_input(op_input, body, changes):
    """Try to set tool on operation input from library."""
    tool_number = body.get("tool_number")
    tool_type = body.get("tool_type")
    tool_desc = body.get("tool_description")

    if tool_number is not None:
        tool = _find_tool_by_number(tool_number, tool_desc)
        if tool:
            op_input.tool = tool
            changes.append(f"Tool #{tool_number} from library")
            return True
        changes.append(f"Tool #{tool_number} not found in library")
    elif tool_type:
        tool = _find_tool_by_type(tool_type)
        if tool:
            op_input.tool = tool
            changes.append(f"Tool type '{tool_type}' from library")
            return True
        changes.append(f"Tool type '{tool_type}' not found")
    return False


# ── 2D Operations ────────────────────────────────────────────

def handle_cam_2d_contour(body):
    cam = _get_cam()
    root = get_root()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    sketch_id = body.get("sketch")
    sketch_curves = []
    if sketch_id:
        for sk in root.sketches:
            if sk.name == sketch_id:
                for c in sk.sketchCurves:
                    sketch_curves.append(c)
                changes.append(f"Found sketch '{sketch_id}': {len(sketch_curves)} curves")
                break

    op_input = setup.operations.createInput("contour2d")
    _set_tool_on_input(op_input, body, changes)

    if sketch_curves and hasattr(op_input, "curveSelections"):
        curves_selected = 0
        for c in sketch_curves:
            try:
                op_input.curveSelections.add(c)
                curves_selected += 1
            except Exception:
                pass
        if curves_selected:
            changes.append(f"Selected {curves_selected} curves from sketch")

    op = setup.operations.add(op_input)
    op.name = body.get("name", "2D Contour")

    edges_selected = 0
    if not sketch_curves:
        try:
            chain_input = op.chainSelections
            if chain_input:
                edges = adsk.core.ObjectCollection.create()
                for b in root.bRepBodies:
                    for edge in b.edges:
                        if abs(edge.pointOnEdge.z) < 0.1:
                            edges.add(edge)
                            edges_selected += 1
                for i in range(edges.count):
                    chain_input.add(edges.item(i))
        except Exception:
            pass

    params = op.parameters
    boundary_p = params.itemByName("machiningBoundary")
    if boundary_p and not body.get("boundary"):
        boundary_p.expression = "'silhouette'"
        changes.append("Boundary: silhouette (auto)")

    _set_common_params(op, body, changes)

    return {
        "operation": op.name,
        "edges_selected": edges_selected,
        "changes": changes,
    }


def handle_cam_2d_contour_advanced(body):
    cam = _get_cam()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    op_input = setup.operations.createInput("contour2d")
    _set_tool_on_input(op_input, body, changes)

    op = setup.operations.add(op_input)
    op.name = body.get("name", "2D Contour")

    _set_common_params(op, body, changes)

    params = op.parameters
    tool_diameter = body.get("tool_diameter")
    if tool_diameter:
        p = params.itemByName("tool_diameter")
        if p:
            p.expression = f"{tool_diameter} mm"
            changes.append(f"Tool diameter: {tool_diameter}mm")

    tool_angle = body.get("tool_angle")
    if tool_angle:
        p = params.itemByName("tool_tipAngle")
        if p:
            p.expression = f"{tool_angle} deg"
            changes.append(f"Tip angle: {tool_angle}deg")

    return {"operation": op.name, "changes": changes}


def handle_cam_2d_pocket(body):
    cam = _get_cam()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    op_input = setup.operations.createInput("pocket2d")
    _set_tool_on_input(op_input, body, changes)

    op = setup.operations.add(op_input)
    op.name = body.get("name", "2D Pocket")

    _set_common_params(op, body, changes)

    params = op.parameters
    stepover = body.get("stepover")
    if stepover:
        p = params.itemByName("stepover")
        if p:
            p.expression = f"{stepover} mm"
            changes.append(f"Stepover: {stepover}mm")

    return {"operation": op.name, "changes": changes}


def handle_cam_2d_adaptive(body):
    cam = _get_cam()
    root = get_root()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    sketch_id = body.get("sketch")
    sketch_profiles = []
    sketch_curves = []
    if sketch_id:
        for sk in root.sketches:
            if sk.name == sketch_id:
                for p in sk.profiles:
                    sketch_profiles.append(p)
                for c in sk.sketchCurves:
                    sketch_curves.append(c)
                changes.append(f"Found sketch '{sketch_id}': {len(sketch_profiles)} profiles, {len(sketch_curves)} curves")
                break

    op_input = setup.operations.createInput("adaptive2d")
    _set_tool_on_input(op_input, body, changes)

    if sketch_profiles:
        try:
            coll = adsk.core.ObjectCollection.create()
            for p in sketch_profiles:
                coll.add(p)
            op_input.geometrySelections = coll
            changes.append(f"Set {len(sketch_profiles)} profiles as geometry")
        except Exception as e:
            changes.append(f"Profile selection failed ({e}), trying curves")
            try:
                for c in sketch_curves:
                    op_input.curveSelections.add(c)
                changes.append(f"Set {len(sketch_curves)} curves as geometry")
            except Exception as e2:
                changes.append(f"Curve selection also failed: {e2}")

    op = setup.operations.add(op_input)
    op.name = body.get("name", "2D Adaptive")

    _set_common_params(op, body, changes)

    params = op.parameters
    optimal_load = body.get("optimal_load")
    if optimal_load:
        p = params.itemByName("optimalLoad")
        if p:
            p.expression = f"{optimal_load} mm"
            changes.append(f"Optimal load: {optimal_load}mm")

    both_ways = body.get("both_ways")
    if both_ways is not None:
        p = params.itemByName("bothWays")
        if p:
            p.expression = "true" if both_ways else "false"
            changes.append(f"Both ways: {both_ways}")

    return {"operation": op.name, "changes": changes}


def handle_cam_2d_face(body):
    cam = _get_cam()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    op_input = setup.operations.createInput("face")
    _set_tool_on_input(op_input, body, changes)

    op = setup.operations.add(op_input)
    op.name = body.get("name", "Face")

    _set_common_params(op, body, changes)

    params = op.parameters
    stepover = body.get("stepover")
    if stepover:
        p = params.itemByName("stepover")
        if p:
            p.expression = f"{stepover} mm"
            changes.append(f"Stepover: {stepover}mm")

    return {"operation": op.name, "changes": changes}


def handle_cam_2d_engrave(body):
    cam = _get_cam()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    op_input = setup.operations.createInput("engrave")
    _set_tool_on_input(op_input, body, changes)

    op = setup.operations.add(op_input)
    op.name = body.get("name", "Engrave")

    params = op.parameters
    tolerance = body.get("tolerance", 0.01)
    p = params.itemByName("tolerance")
    if p:
        p.expression = f"{tolerance} mm"

    depth = body.get("depth")
    if depth:
        p = params.itemByName("bottomHeight_offset")
        if p:
            p.expression = f"-{depth} mm"
            changes.append(f"Depth: {depth}mm")

    return {"operation": op.name, "changes": changes}


def handle_cam_2d_trace(body):
    cam = _get_cam()
    root = get_root()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    # Find sketch curves first
    sketch_id = body.get("sketch")
    sketch_curves = []
    if sketch_id:
        for sk in root.sketches:
            if sk.name == sketch_id:
                for curve in sk.sketchCurves:
                    sketch_curves.append(curve)
                changes.append(f"Found {len(sketch_curves)} curves in {sketch_id}")
                break

    op_input = setup.operations.createInput("trace")
    _set_tool_on_input(op_input, body, changes)

    # Set curves on input
    curves_selected = 0
    if sketch_curves and hasattr(op_input, "curveSelections"):
        for curve in sketch_curves:
            try:
                op_input.curveSelections.add(curve)
                curves_selected += 1
            except Exception:
                pass
        if curves_selected > 0:
            changes.append(f"Selected {curves_selected} curves")

    op = setup.operations.add(op_input)
    op.name = body.get("name", "Trace")

    params = op.parameters

    # Axial offset (depth for V-bits)
    depth = body.get("depth")
    if depth:
        p = params.itemByName("axialOffset")
        if p:
            p.expression = f"-{depth} mm"
            changes.append(f"Axial offset: -{depth}mm")
        p = params.itemByName("bottomHeight_offset")
        if p:
            p.expression = f"-{depth} mm"

    # Multiple depths
    stepdown = body.get("stepdown")
    if stepdown:
        p = params.itemByName("doMultipleDepths")
        if p:
            p.expression = "true"
            changes.append("Multiple depths enabled")
        p = params.itemByName("maximumStepdown")
        if p:
            p.expression = f"{stepdown} mm"
            changes.append(f"Stepdown: {stepdown}mm")

    num_passes = body.get("passes")
    if num_passes:
        p = params.itemByName("numberOfStepdowns")
        if p:
            p.expression = str(num_passes)
            changes.append(f"Passes: {num_passes}")

    compensation = body.get("compensation", "center")
    p = params.itemByName("sidewaysCompensation")
    if p:
        comp_map = {
            "left": "'left (climb)'",
            "right": "'right (conventional)'",
            "center": "'center'",
            "off": "'off'",
        }
        if compensation in comp_map:
            p.expression = comp_map[compensation]
            changes.append(f"Compensation: {compensation}")

    # Heights
    for hname, key, default in [
        ("clearanceHeight", "clearance_height", 30),
        ("retractHeight", "retract_height", 10),
        ("feedHeight", "feed_height", 5),
    ]:
        val = body.get(key, default)
        mode_p = params.itemByName(f"{hname}_mode")
        if mode_p:
            mode_p.expression = "'from stock top'"
        off_p = params.itemByName(f"{hname}_offset")
        if off_p:
            off_p.expression = f"{val} mm"

    return {
        "operation": op.name,
        "curves_selected": curves_selected,
        "changes": changes,
    }


def handle_cam_2d_drill(body):
    cam = _get_cam()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    op_input = setup.operations.createInput("drill")
    _set_tool_on_input(op_input, body, changes)

    op = setup.operations.add(op_input)
    op.name = body.get("name", "Drill")

    params = op.parameters
    depth = body.get("depth")
    if depth:
        p = params.itemByName("bottomHeight_offset")
        if p:
            p.expression = f"-{depth} mm"
            changes.append(f"Depth: {depth}mm")

    peck_depth = body.get("peck_depth")
    if peck_depth:
        p = params.itemByName("peckingDepth")
        if p:
            p.expression = f"{peck_depth} mm"
            changes.append(f"Peck depth: {peck_depth}mm")

    dwell = body.get("dwell")
    if dwell is not None:
        p = params.itemByName("dwellTime")
        if p:
            p.expression = str(dwell)
            changes.append(f"Dwell: {dwell}s")

    cycle_type = body.get("cycle")
    if cycle_type:
        p = params.itemByName("cycleType")
        if p:
            cycle_map = {
                "drill": "'drilling'",
                "peck": "'chip breaking'",
                "deep_peck": "'deep drilling'",
                "tap": "'tapping'",
                "bore": "'boring'",
            }
            if cycle_type in cycle_map:
                p.expression = cycle_map[cycle_type]
                changes.append(f"Cycle: {cycle_type}")

    return {"operation": op.name, "changes": changes}


def handle_cam_2d_bore(body):
    cam = _get_cam()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    op_input = setup.operations.createInput("bore")
    _set_tool_on_input(op_input, body, changes)

    op = setup.operations.add(op_input)
    op.name = body.get("name", "Bore")

    params = op.parameters
    depth = body.get("depth")
    if depth:
        p = params.itemByName("bottomHeight_offset")
        if p:
            p.expression = f"-{depth} mm"
            changes.append(f"Depth: {depth}mm")

    diameter = body.get("diameter")
    if diameter:
        p = params.itemByName("holeDiameter")
        if p:
            p.expression = f"{diameter} mm"
            changes.append(f"Diameter: {diameter}mm")

    return {"operation": op.name, "changes": changes}


def handle_cam_2d_slot(body):
    cam = _get_cam()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    op_input = setup.operations.createInput("slot")
    _set_tool_on_input(op_input, body, changes)

    op = setup.operations.add(op_input)
    op.name = body.get("name", "Slot")

    _set_common_params(op, body, changes)

    return {"operation": op.name, "changes": changes}


def handle_cam_2d_chamfer(body):
    cam = _get_cam()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    op_input = setup.operations.createInput("chamfer2d")
    _set_tool_on_input(op_input, body, changes)

    op = setup.operations.add(op_input)
    op.name = body.get("name", "2D Chamfer")

    params = op.parameters
    chamfer_width = body.get("chamfer_width")
    if chamfer_width:
        p = params.itemByName("chamferWidth")
        if p:
            p.expression = f"{chamfer_width} mm"
            changes.append(f"Chamfer width: {chamfer_width}mm")

    tip_offset = body.get("tip_offset")
    if tip_offset is not None:
        p = params.itemByName("chamferTipOffset")
        if p:
            p.expression = f"{tip_offset} mm"
            changes.append(f"Tip offset: {tip_offset}mm")

    return {"operation": op.name, "changes": changes}


def handle_cam_2d_miter_clearing(body):
    cam = _get_cam()
    setup = _find_setup(cam, body.get("setup"))

    total_depth = body.get("depth", 18)
    num_steps = body.get("steps", 4)
    tool_diameter = body.get("tool_diameter", 6)
    stock_for_finish = body.get("stock_for_finish", 1.0)
    miter_angle = body.get("miter_angle", 45)
    stepdown = body.get("stepdown", 4)

    tan_angle = math.tan(math.radians(miter_angle))
    step_depth = total_depth / num_steps
    operations_created = []

    for i in range(num_steps):
        terrace_depth = step_depth * (i + 1)
        horizontal_offset = terrace_depth * tan_angle + stock_for_finish

        op_input = setup.operations.createInput("contour2d")
        op = setup.operations.add(op_input)
        op.name = f"Miter Clear {i+1} - {terrace_depth:.1f}mm"

        try:
            params = op.parameters
            p = params.itemByName("bottomHeight_offset")
            if p:
                p.expression = f"-{terrace_depth} mm"
            p = params.itemByName("stockToLeave")
            if p:
                p.expression = f"{horizontal_offset} mm"
            p = params.itemByName("stockToLeaveFloor")
            if p:
                p.expression = f"{stock_for_finish} mm"
            p = params.itemByName("useMultipleDepths")
            if p:
                p.expression = "true"
            p = params.itemByName("maximumStepdown")
            if p:
                p.expression = f"{stepdown} mm"
            p = params.itemByName("machiningBoundary")
            if p:
                p.expression = "'silhouette'"
            p = params.itemByName("tool_diameter")
            if p:
                p.expression = f"{tool_diameter} mm"
        except Exception:
            pass

        operations_created.append({
            "name": op.name,
            "depth": terrace_depth,
            "offset": horizontal_offset,
        })

    return {
        "success": True,
        "operations": operations_created,
        "summary": (
            f"Created {num_steps} terraced clearing ops for "
            f"{total_depth}mm deep {miter_angle} deg miter"
        ),
    }


# ── Operation Management ─────────────────────────────────────

def handle_cam_2d_edit_op(body):
    cam = _get_cam()
    op_name = body.get("operation")
    if not op_name:
        raise Exception("operation name is required")
    op, setup = _find_op(cam, op_name)

    if body.get("dump_all_params"):
        params = op.parameters
        all_params = []
        for i in range(params.count):
            p = params.item(i)
            try:
                expr = p.expression
            except Exception:
                expr = "(no expression)"
            all_params.append({"name": p.name, "expression": expr, "type": str(type(p.value).__name__)})
        return {"operation": op.name, "param_count": len(all_params), "params": all_params}

    if body.get("inspect_pockets"):
        param_name = body.get("inspect_param", "pockets")
        params = op.parameters
        geo_param = params.itemByName(param_name)
        if not geo_param:
            return {"error": f"{param_name} parameter not found"}
        pv = geo_param.value
        info = {"param_name": param_name, "param_type": str(type(pv).__name__)}
        try:
            cs = pv.getCurveSelections()
            info["count"] = cs.count
            items = []
            for i in range(cs.count):
                item = cs.item(i)
                item_info = {
                    "index": i,
                    "type": str(type(item).__name__),
                    "hasError": item.hasError,
                    "hasWarning": item.hasWarning,
                }
                if item.hasError:
                    item_info["error"] = item.error
                if item.hasWarning:
                    item_info["warning"] = item.warning
                try:
                    ig = item.inputGeometry
                    item_info["inputGeometry_count"] = len(ig) if ig else 0
                    item_info["inputGeometry_types"] = [str(type(g).__name__) for g in ig] if ig else []
                except Exception as e:
                    item_info["inputGeometry_error"] = str(e)
                try:
                    og = item.outputGeometry
                    item_info["outputGeometry_count"] = len(og) if og else 0
                except Exception:
                    pass
                # Check for loopType/sideType on SketchSelection
                for attr in ("loopType", "sideType"):
                    if hasattr(item, attr):
                        try:
                            val = getattr(item, attr)
                            item_info[attr] = str(val)
                        except Exception:
                            pass
                items.append(item_info)
            info["items"] = items

            # Also test: create a new sketch sel and inspect loopType/sideType defaults
            test_sel = cs.createNewSketchSelection()
            test_info = {}
            for attr in ("loopType", "sideType"):
                try:
                    val = getattr(test_sel, attr)
                    test_info[attr + "_value"] = str(val)
                    test_info[attr + "_type"] = str(type(val).__name__)
                    test_info[attr + "_dir"] = [m for m in dir(type(val)) if not m.startswith("_")] if hasattr(type(val), "__members__") or not isinstance(val, (str, int, float, bool)) else None
                except Exception as e:
                    test_info[attr + "_error"] = str(e)
            info["new_sketch_sel_defaults"] = test_info
        except Exception as e:
            info["error"] = str(e)
        return {"operation": op.name, "pockets_info": info}

    if body.get("clear_geometry"):
        param_name = body["clear_geometry"]
        params = op.parameters
        geo_param = params.itemByName(param_name)
        if geo_param:
            pv = geo_param.value
            cs = pv.getCurveSelections()
            cs.clear()
            pv.applyCurveSelections(cs)
            return {"operation": op.name, "cleared": param_name, "count": cs.count}
        return {"error": f"Parameter '{param_name}' not found"}

    if body.get("set_loop_type") is not None or body.get("set_side_type") is not None:
        param_name = body.get("param_name", "pockets")
        params = op.parameters
        geo_param = params.itemByName(param_name)
        if not geo_param:
            raise Exception(f"Parameter '{param_name}' not found")
        pv = geo_param.value
        cs = pv.getCurveSelections()
        results = []
        for i in range(cs.count):
            item = cs.item(i)
            if body.get("set_loop_type") is not None and hasattr(item, "loopType"):
                old = item.loopType
                item.loopType = body["set_loop_type"]
                results.append(f"item[{i}] loopType: {old} -> {item.loopType}")
            if body.get("set_side_type") is not None and hasattr(item, "sideType"):
                old = item.sideType
                item.sideType = body["set_side_type"]
                results.append(f"item[{i}] sideType: {old} -> {item.sideType}")
        pv.applyCurveSelections(cs)
        cs2 = pv.getCurveSelections()
        for i in range(cs2.count):
            item = cs2.item(i)
            results.append(f"verify item[{i}]: loopType={item.loopType}, sideType={item.sideType}, outputCount={len(item.outputGeometry) if item.outputGeometry else 0}")
        return {"operation": op.name, "results": results}

    if body.get("set_sketch_pockets") or body.get("set_sketch_contours"):
        root = get_root()
        sketch_id = body.get("set_sketch_pockets") or body.get("set_sketch_contours")
        param_name = "contours" if body.get("set_sketch_contours") else "pockets"
        params = op.parameters
        pockets_param = params.itemByName(param_name)
        if not pockets_param:
            raise Exception("pockets parameter not found")
        sketch_obj = None
        for sk in root.sketches:
            if sk.name == sketch_id:
                sketch_obj = sk
                break
        if not sketch_obj:
            raise Exception(f"Sketch '{sketch_id}' not found")
        pv = pockets_param.value
        cs = pv.getCurveSelections()
        cs.clear()
        results = []

        candidates = [
            ("SketchSel+[sketch]", "sketch", [sketch_obj]),
            ("SketchSel+[sketch]+curves", "sketch", [sketch_obj] + [c for c in sketch_obj.sketchCurves]),
            ("PocketSel+[sketch]", "pocket", [sketch_obj]),
        ]

        # Also try body faces from the setup
        body_faces = []
        try:
            cam = _get_cam()
            setup_obj = _find_setup(cam, body.get("setup"))
            for mdl in setup_obj.models:
                for face in mdl.bRepBodies.item(0).faces:
                    body_faces.append(face)
        except Exception:
            pass
        if body_faces:
            candidates.append(("PocketSel+body_faces", "pocket", body_faces))

        # Also try individual sketch lines
        lines = [c for c in sketch_obj.sketchCurves]
        candidates.append(("ChainSel+curves", "chain", lines))

        for label, sel_type, geom in candidates:
            cs.clear()
            try:
                if sel_type == "sketch":
                    sel = cs.createNewSketchSelection()
                elif sel_type == "pocket":
                    sel = cs.createNewPocketSelection()
                else:
                    sel = cs.createNewChainSelection()
                sel.inputGeometry = geom
                has_err = sel.hasError
                err_msg = sel.error if has_err else None
                results.append({"method": label, "ok": not has_err, "hasError": has_err, "error": err_msg,
                                "count": cs.count})
                if not has_err:
                    pv.applyCurveSelections(cs)
                    results.append({"applied": label, "final_count": cs.count})
                    return {"operation": op.name, "results": results}
            except Exception as e:
                results.append({"method": label, "error": str(e)})

        return {"operation": op.name, "results": results, "note": "all methods failed"}

    read_list = body.get("read_params")
    if read_list:
        params = op.parameters
        result = {}
        for pname in read_list:
            p = params.itemByName(pname)
            if p:
                result[pname] = p.expression
            else:
                result[pname] = "NOT_FOUND"
        return {"operation": op.name, "param_values": result}

    changes = []
    params = op.parameters
    param_updates = body.get("params", {})
    for pname, expression in param_updates.items():
        p = params.itemByName(pname)
        if p:
            try:
                p.expression = str(expression)
                changes.append(f"{pname} = {expression}")
            except Exception as e:
                changes.append(f"{pname}: current='{p.expression}', set failed: {e}")
        else:
            changes.append(f"Parameter not found: {pname}")

    _set_common_params(op, body, changes)

    new_name = body.get("new_name")
    if new_name:
        op.name = new_name
        changes.append(f"Renamed to {new_name}")

    return {"operation": op.name, "changes": changes}


def handle_cam_2d_duplicate_op(body):
    """Duplicate an operation — copies tool, params, and boundary."""
    cam = _get_cam()
    src_name = body.get("operation")
    if not src_name:
        raise Exception("operation name is required")
    src_op, setup = _find_op(cam, src_name)

    strategy = src_op.strategy
    op_input = setup.operations.createInput(strategy)

    src_tool = src_op.tool
    if src_tool:
        op_input.tool = src_tool

    new_op = setup.operations.add(op_input)
    new_op.name = body.get("new_name", f"{src_name} Copy")

    copied = 0
    src_params = src_op.parameters
    dst_params = new_op.parameters
    for i in range(src_params.count):
        sp = src_params.item(i)
        dp = dst_params.itemByName(sp.name)
        if dp:
            try:
                dp.expression = sp.expression
                copied += 1
            except Exception:
                pass

    changes = [f"Duplicated from '{src_name}'", f"Strategy: {strategy}", f"Params copied: {copied}"]

    _set_common_params(new_op, body, changes)

    return {"operation": new_op.name, "source": src_name, "changes": changes}


def handle_cam_2d_suppress_op(body):
    cam = _get_cam()
    op_name = body.get("operation")
    if not op_name:
        raise Exception("operation name is required")
    op, setup = _find_op(cam, op_name)

    suppress = body.get("suppress", True)
    op.isSuppressed = suppress
    return {
        "operation": op.name,
        "suppressed": suppress,
    }


def handle_cam_2d_reorder_op(body):
    cam = _get_cam()
    op_name = body.get("operation")
    if not op_name:
        raise Exception("operation name is required")
    op, setup = _find_op(cam, op_name)

    direction = body.get("direction", "down")
    try:
        if direction == "up":
            op.moveUp()
        else:
            op.moveDown()
        return {"success": True, "operation": op.name, "moved": direction}
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_cam_2d_delete_op(body):
    cam = _get_cam()
    op_name = body.get("operation")
    if not op_name:
        raise Exception("operation name is required")
    op, setup = _find_op(cam, op_name)
    op.deleteMe()
    return {"success": True, "deleted": op_name}


# ── Route table ──────────────────────────────────────────────

CAM_2D_ROUTES = {
    # 2D operations
    "/cam_2d_contour": handle_cam_2d_contour,
    "/cam_2d_contour_advanced": handle_cam_2d_contour_advanced,
    "/cam_2d_pocket": handle_cam_2d_pocket,
    "/cam_2d_adaptive": handle_cam_2d_adaptive,
    "/cam_2d_face": handle_cam_2d_face,
    "/cam_2d_engrave": handle_cam_2d_engrave,
    "/cam_2d_trace": handle_cam_2d_trace,
    "/cam_2d_drill": handle_cam_2d_drill,
    "/cam_2d_bore": handle_cam_2d_bore,
    "/cam_2d_slot": handle_cam_2d_slot,
    "/cam_2d_chamfer": handle_cam_2d_chamfer,
    "/cam_2d_miter_clearing": handle_cam_2d_miter_clearing,
    # Operation management
    "/cam_2d_edit_op": handle_cam_2d_edit_op,
    "/cam_2d_suppress_op": handle_cam_2d_suppress_op,
    "/cam_2d_reorder_op": handle_cam_2d_reorder_op,
    "/cam_2d_delete_op": handle_cam_2d_delete_op,
    "/cam_2d_duplicate_op": handle_cam_2d_duplicate_op,
}
