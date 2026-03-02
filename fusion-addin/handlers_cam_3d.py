"""CAM 3D milling operation handlers for Fusion 360 MCP Bridge.

All 3D surface machining operations: adaptive clearing, pocket, parallel,
scallop, pencil, contour, steep & shallow, morphed spiral, radial, and
flow. Also includes rest machining and stock-to-leave workflows.

Every public function has the signature ``handle_*(body: dict) -> dict``
and is registered in CAM_3D_ROUTES.

Endpoints (17):
  ROUGHING
    /cam_3d_adaptive       – 3D adaptive clearing (constant engagement)
    /cam_3d_pocket         – 3D pocket clearing
  FINISHING
    /cam_3d_parallel       – parallel (raster) finishing
    /cam_3d_scallop        – scallop finishing (constant scallop height)       [Extension]
    /cam_3d_pencil         – pencil finishing (inside corners)                 [Extension]
    /cam_3d_contour        – 3D contour (waterline / Z-level)                 [Extension]
    /cam_3d_steep_shallow  – steep & shallow (combined strategy)              [Extension]
    /cam_3d_horizontal     – horizontal finishing (flat areas)
    /cam_3d_radial         – radial finishing
    /cam_3d_spiral         – spiral finishing
    /cam_3d_morphed_spiral – morphed spiral finishing                         [Extension]
    /cam_3d_flow           – flow finishing (follow UV curves)                [Extension]
  OPERATION MANAGEMENT
    /cam_3d_edit_op        – edit/read operation parameters
    /cam_3d_suppress_op    – suppress/unsuppress an operation
    /cam_3d_delete_op      – delete an operation
    /cam_3d_duplicate_op   – duplicate an operation with all settings
"""

import json
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


EXTENSION_STRATEGIES = frozenset([
    "scallop", "pencil", "contour_new", "steep_and_shallow",
    "morphed_spiral", "flow",
])


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
    cam = _get_cam()
    filt = tool_type_filter.lower()
    for op in cam.allOperations:
        try:
            t = op.tool
            if t:
                tj = json.loads(t.toJson())
                if filt in tj.get("type", "").lower():
                    return t
        except Exception:
            pass

    mgr = adsk.cam.CAMManager.get()
    lib_mgr = mgr.libraryManager
    tool_libs = lib_mgr.toolLibraries
    local_url = tool_libs.urlByLocation(adsk.cam.LibraryLocations.LocalLibraryLocation)
    if not local_url:
        return None
    child_urls = tool_libs.childAssetURLs(local_url)
    if not child_urls:
        return None
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


def _set_tool_on_input(op_input, body, changes):
    tool_number = body.get("tool_number")
    tool_type = body.get("tool_type")
    tool_desc = body.get("tool_description")
    if tool_number is not None:
        tool = _find_tool_by_number(tool_number, tool_desc)
        if tool:
            op_input.tool = tool
            changes.append(f"Tool #{tool_number} from library")
            return True
        changes.append(f"Tool #{tool_number} not found")
    elif tool_type:
        tool = _find_tool_by_type(tool_type)
        if tool:
            op_input.tool = tool
            changes.append(f"Tool type '{tool_type}' from library")
            return True
        changes.append(f"Tool type '{tool_type}' not found")
    return False


def _set_3d_common(op, body, changes):
    """Set parameters common to 3D operations."""
    params = op.parameters

    stl = body.get("stock_to_leave")
    if stl is not None:
        p = params.itemByName("stockToLeave")
        if p:
            p.expression = f"{stl} mm"
            changes.append(f"Stock to leave: {stl}mm")

    astl = body.get("axial_stock_to_leave")
    if astl is not None:
        p = params.itemByName("stockToLeaveAxial")
        if not p:
            p = params.itemByName("stockToLeaveFloor")
        if p:
            p.expression = f"{astl} mm"
            changes.append(f"Axial stock to leave: {astl}mm")

    tol = body.get("tolerance")
    if tol is not None:
        p = params.itemByName("tolerance")
        if p:
            p.expression = f"{tol} mm"
            changes.append(f"Tolerance: {tol}mm")

    stepover = body.get("stepover")
    if stepover is not None:
        p = params.itemByName("stepover")
        if not p:
            p = params.itemByName("maximumStepover")
        if p:
            p.expression = f"{stepover} mm"
            changes.append(f"Stepover: {stepover}mm")

    stepdown = body.get("stepdown")
    if stepdown is not None:
        p = params.itemByName("maximumStepdown")
        if p:
            p.expression = f"{stepdown} mm"
            changes.append(f"Stepdown: {stepdown}mm")

    # Rest machining
    rest = body.get("rest_machining")
    if rest:
        p = params.itemByName("useRestMachining")
        if p:
            p.expression = "true"
            changes.append("Rest machining enabled")
        src = params.itemByName("restMaterialSource")
        if src:
            try:
                src.expression = "'previousOperations'"
            except Exception:
                pass

    # Boundary mode
    boundary = body.get("boundary")
    if boundary:
        for pname in ("boundaryMode", "machiningBoundary"):
            p = params.itemByName(pname)
            if p:
                p.expression = f"'{boundary}'"
                changes.append(f"Boundary: {boundary}")
                break

    # Heights — clearance, retract, feed
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
            off_p = params.itemByName(f"{hname}_offset")
            if off_p:
                off_p.expression = f"{val} mm"
                changes.append(f"{hname}: {val}mm from stock top")

    # Top height — always set mode + offset together
    top = body.get("top_height")
    top_from = body.get("top_from", "stock top")
    if top is not None:
        mode_p = params.itemByName("topHeight_mode")
        if mode_p:
            try:
                mode_p.expression = f"'from {top_from}'"
            except Exception:
                pass
        off_p = params.itemByName("topHeight_offset")
        if off_p:
            off_p.expression = f"{top} mm"
            changes.append(f"Top height: {top}mm from {top_from}")

    # Bottom height — always set mode + offset together
    bottom = body.get("bottom_height")
    bottom_from = body.get("bottom_from", "stock bottom")
    if bottom is not None:
        mode_p = params.itemByName("bottomHeight_mode")
        if mode_p:
            try:
                mode_p.expression = f"'from {bottom_from}'"
            except Exception:
                pass
        off_p = params.itemByName("bottomHeight_offset")
        if off_p:
            off_p.expression = f"{bottom} mm"
            changes.append(f"Bottom height: {bottom}mm from {bottom_from}")


def _create_3d_op(strategy_id, body, default_name):
    """Generic factory for creating a 3D operation."""
    cam = _get_cam()
    setup = _find_setup(cam, body.get("setup"))
    changes = []

    try:
        op_input = setup.operations.createInput(strategy_id)
    except RuntimeError as e:
        if "Unknown strategy" in str(e):
            is_ext = strategy_id in EXTENSION_STRATEGIES
            hint = " This strategy requires the Manufacturing Extension license." if is_ext else ""
            raise Exception(
                f"Strategy '{strategy_id}' is not available.{hint} "
                f"Use 'parallel', 'adaptive', or 'pocket' instead."
            )
        raise

    _set_tool_on_input(op_input, body, changes)

    try:
        op = setup.operations.add(op_input)
    except RuntimeError as e:
        msg = str(e)
        if "license" in msg.lower() or "not allowed" in msg.lower() or "not available" in msg.lower():
            raise Exception(
                f"License does not allow '{default_name}'. "
                f"This operation requires the Manufacturing Extension. "
                f"Use 'parallel', 'adaptive', or 'pocket' instead."
            )
        raise

    op.name = body.get("name", default_name)
    _set_3d_common(op, body, changes)
    return op, changes


# ── 3D Roughing ──────────────────────────────────────────────

def handle_cam_3d_adaptive(body):
    op, changes = _create_3d_op("adaptive", body, "3D Adaptive")

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

    flat_area_detection = body.get("flat_area_detection")
    if flat_area_detection is not None:
        p = params.itemByName("flatAreaDetection")
        if p:
            p.expression = "true" if flat_area_detection else "false"
            changes.append(f"Flat area detection: {flat_area_detection}")

    return {"operation": op.name, "changes": changes}


def handle_cam_3d_pocket(body):
    op, changes = _create_3d_op("pocket", body, "3D Pocket")

    params = op.parameters
    direction = body.get("direction")
    if direction:
        p = params.itemByName("machineDirection")
        if p:
            p.expression = f"'{direction}'"
            changes.append(f"Direction: {direction}")

    return {"operation": op.name, "changes": changes}


# ── 3D Finishing ─────────────────────────────────────────────

def handle_cam_3d_parallel(body):
    op, changes = _create_3d_op("parallel", body, "Parallel")

    params = op.parameters
    angle = body.get("pass_angle")
    if angle is not None:
        p = params.itemByName("passAngle")
        if p:
            p.expression = f"{angle} deg"
            changes.append(f"Pass angle: {angle}deg")

    direction = body.get("direction")
    if direction:
        p = params.itemByName("cuttingDirection")
        if p:
            p.expression = f"'{direction}'"
            changes.append(f"Cutting direction: {direction}")

    return {"operation": op.name, "changes": changes}


def handle_cam_3d_scallop(body):
    op, changes = _create_3d_op("scallop", body, "Scallop")

    params = op.parameters
    scallop_height = body.get("scallop_height")
    if scallop_height is not None:
        for pname in ("stepover", "maximumStepover"):
            p = params.itemByName(pname)
            if p:
                p.expression = f"{scallop_height} mm"
                changes.append(f"Scallop stepover: {scallop_height}mm")
                break

    return {"operation": op.name, "changes": changes}


def handle_cam_3d_pencil(body):
    op, changes = _create_3d_op("pencil", body, "Pencil")
    return {"operation": op.name, "changes": changes}


def handle_cam_3d_contour(body):
    op, changes = _create_3d_op("contour_new", body, "3D Contour")

    params = op.parameters
    max_stepdown = body.get("stepdown")
    if max_stepdown:
        p = params.itemByName("maximumStepdown")
        if p:
            p.expression = f"{max_stepdown} mm"
            changes.append(f"Z-level stepdown: {max_stepdown}mm")

    return {"operation": op.name, "changes": changes}


def handle_cam_3d_steep_shallow(body):
    op, changes = _create_3d_op("steep_and_shallow", body, "Steep & Shallow")

    params = op.parameters
    threshold = body.get("threshold_angle")
    if threshold is not None:
        p = params.itemByName("thresholdAngle")
        if p:
            p.expression = f"{threshold} deg"
            changes.append(f"Threshold angle: {threshold}deg")

    steep_stepdown = body.get("steep_stepdown")
    if steep_stepdown:
        p = params.itemByName("steepStepdown")
        if p:
            p.expression = f"{steep_stepdown} mm"
            changes.append(f"Steep stepdown: {steep_stepdown}mm")

    shallow_stepover = body.get("shallow_stepover")
    if shallow_stepover:
        p = params.itemByName("shallowStepover")
        if p:
            p.expression = f"{shallow_stepover} mm"
            changes.append(f"Shallow stepover: {shallow_stepover}mm")

    return {"operation": op.name, "changes": changes}


def handle_cam_3d_horizontal(body):
    op, changes = _create_3d_op("horizontal", body, "Horizontal")
    return {"operation": op.name, "changes": changes}


def handle_cam_3d_radial(body):
    op, changes = _create_3d_op("radial", body, "Radial")

    params = op.parameters
    center = body.get("center")
    if center and len(center) >= 2:
        cx = params.itemByName("radialCenterX")
        cy = params.itemByName("radialCenterY")
        if cx:
            cx.expression = f"{center[0]} mm"
        if cy:
            cy.expression = f"{center[1]} mm"
        changes.append(f"Center: {center[0]},{center[1]}mm")

    return {"operation": op.name, "changes": changes}


def handle_cam_3d_spiral(body):
    op, changes = _create_3d_op("spiral", body, "Spiral")
    return {"operation": op.name, "changes": changes}


def handle_cam_3d_morphed_spiral(body):
    op, changes = _create_3d_op("morphed_spiral", body, "Morphed Spiral")
    return {"operation": op.name, "changes": changes}


def handle_cam_3d_flow(body):
    op, changes = _create_3d_op("flow", body, "Flow")
    return {"operation": op.name, "changes": changes}


# ── Operation Management ─────────────────────────────────────

def handle_cam_3d_edit_op(body):
    cam = _get_cam()
    op_name = body.get("operation")
    if not op_name:
        raise Exception("operation name is required")
    op, setup = _find_op(cam, op_name)

    # Read mode: return param values without changing anything
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

    _set_3d_common(op, body, changes)

    new_name = body.get("new_name")
    if new_name:
        op.name = new_name
        changes.append(f"Renamed to {new_name}")

    return {"operation": op.name, "changes": changes}


def handle_cam_3d_suppress_op(body):
    cam = _get_cam()
    op_name = body.get("operation")
    if not op_name:
        raise Exception("operation name is required")
    op, setup = _find_op(cam, op_name)

    suppress = body.get("suppress", True)
    op.isSuppressed = suppress
    return {"operation": op.name, "suppressed": suppress}


def handle_cam_3d_delete_op(body):
    cam = _get_cam()
    op_name = body.get("operation")
    if not op_name:
        raise Exception("operation name is required")
    op, setup = _find_op(cam, op_name)
    op.deleteMe()
    return {"success": True, "deleted": op_name}


def handle_cam_3d_duplicate_op(body):
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
    skipped = []
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
                skipped.append(sp.name)

    changes = [f"Duplicated from '{src_name}'", f"Strategy: {strategy}", f"Params copied: {copied}"]
    if skipped:
        changes.append(f"Skipped (read-only): {len(skipped)}")

    _set_3d_common(new_op, body, changes)

    return {"operation": new_op.name, "source": src_name, "changes": changes}


# ── Route table ──────────────────────────────────────────────

CAM_3D_ROUTES = {
    # Roughing
    "/cam_3d_adaptive": handle_cam_3d_adaptive,
    "/cam_3d_pocket": handle_cam_3d_pocket,
    # Finishing
    "/cam_3d_parallel": handle_cam_3d_parallel,
    "/cam_3d_scallop": handle_cam_3d_scallop,
    "/cam_3d_pencil": handle_cam_3d_pencil,
    "/cam_3d_contour": handle_cam_3d_contour,
    "/cam_3d_steep_shallow": handle_cam_3d_steep_shallow,
    "/cam_3d_horizontal": handle_cam_3d_horizontal,
    "/cam_3d_radial": handle_cam_3d_radial,
    "/cam_3d_spiral": handle_cam_3d_spiral,
    "/cam_3d_morphed_spiral": handle_cam_3d_morphed_spiral,
    "/cam_3d_flow": handle_cam_3d_flow,
    # Operation management
    "/cam_3d_edit_op": handle_cam_3d_edit_op,
    "/cam_3d_suppress_op": handle_cam_3d_suppress_op,
    "/cam_3d_delete_op": handle_cam_3d_delete_op,
    "/cam_3d_duplicate_op": handle_cam_3d_duplicate_op,
}
