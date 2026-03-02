"""CAM Setup / Tools / Post-processing handlers for Fusion 360 MCP Bridge.

Manages the manufacturing infrastructure: setups, stock, WCS, tool
libraries, post-processing, simulation, and machining time.

Every public function has the signature ``handle_*(body: dict) -> dict``
and is registered in CAM_SETUP_ROUTES.

Endpoints (27):
  SETUP MANAGEMENT
    /cam_list_setups       – list all CAM setups
    /cam_create_setup      – create a milling setup (stock, WCS, orientation)
    /cam_edit_setup        – modify an existing setup's parameters
    /cam_delete_setup      – delete a setup
    /cam_duplicate_setup   – clone a setup
    /cam_fix_setup         – fix WCS orientation on a setup
    /cam_get_setup_params  – dump all parameters for discovery/debugging
  STOCK / MODEL / FIXTURE
    /cam_set_model         – set machining model bodies
    /cam_set_fixture       – set fixture bodies (clamp avoidance)
    /cam_derive_body       – import a body from an external .f3d file
    /cam_create_keepout    – create keep-out zone sketches
  TOOL MANAGEMENT
    /cam_list_tools        – list tools from document + libraries
    /cam_create_tool       – create a new tool (and add to local library)
  LIBRARY MANAGEMENT
    /cam_library_list      – list tools in the persistent Local library
    /cam_library_add       – add a tool to the Local library
    /cam_library_remove    – remove a tool from the Local library by index
    /cam_library_import_doc – bulk import document tools into Local library
    /cam_library_export    – export Local library to a JSON file
    /cam_library_import_file – import tools from a JSON file
  OPERATIONS QUERY
    /cam_list_operations   – list all operations in a setup
    /cam_select_silhouette – set an operation to use silhouette geometry
  POST-PROCESSING & SIMULATION
    /cam_generate          – generate toolpaths (one setup or all)
    /cam_post_process      – post-process to G-code
    /cam_simulate          – start simulation
    /cam_cycle_time        – estimate machining cycle time
  WORKSPACE
    /cam_switch            – switch to Manufacturing workspace
    /cam_info              – manufacturing workspace overview
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

def get_cam():
    """Get CAM product — must be in Manufacturing workspace."""
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
    """Find a setup by name, or return the last one."""
    if name:
        for s in cam.setups:
            if s.name == name:
                return s
        raise Exception(f"Setup not found: {name}")
    if cam.setups.count > 0:
        return cam.setups.item(cam.setups.count - 1)
    raise Exception("No setup available. Create a setup first.")


def _find_bodies(root, names):
    """Resolve a list of body names into body objects."""
    bodies = []
    not_found = []
    for name in names:
        found = False
        for b in root.bRepBodies:
            if b.name == name:
                bodies.append(b)
                found = True
                break
        if not found:
            for occ in root.allOccurrences:
                for b in occ.bRepBodies:
                    if b.name == name:
                        bodies.append(b)
                        found = True
                        break
                if found:
                    break
        if not found:
            not_found.append(name)
    return bodies, not_found


# ── Setup Management ─────────────────────────────────────────

def handle_cam_list_setups(body):
    cam = get_cam()
    setups = []
    for setup in cam.setups:
        info = {
            "name": setup.name,
            "operation_count": setup.allOperations.count,
        }
        try:
            info["setup_type"] = str(setup.operationType)
        except Exception:
            info["setup_type"] = "unknown"
        try:
            info["is_valid"] = setup.isValid
        except Exception:
            pass
        if body.get("show_params"):
            param_list = []
            try:
                for param in setup.parameters:
                    param_list.append({
                        "name": param.name,
                        "expression": param.expression
                        if hasattr(param, "expression")
                        else str(param.value),
                    })
            except Exception:
                pass
            info["parameters"] = param_list
        setups.append(info)
    return {"setups": setups, "count": len(setups)}


def handle_cam_create_setup(body):
    cam = get_cam()
    root = get_root()
    name = body.get("name", "Setup")

    setup_input = cam.setups.createInput(
        adsk.cam.OperationTypes.MillingOperation
    )
    setup = cam.setups.add(setup_input)
    setup.name = name

    changes = []
    try:
        params = setup.parameters

        # Stock mode
        stock_mode = body.get("stock_mode", "relative")
        if stock_mode == "fixed":
            mode_param = params.itemByName("job_stockMode")
            if mode_param:
                mode_param.expression = "'fixed size box'"
                changes.append("Stock mode: fixed size box")
            for axis, dim_key in [("X", "stock_x"), ("Y", "stock_y"), ("Z", "stock_z")]:
                val = body.get(dim_key)
                if val:
                    p = params.itemByName(f"job_stockSize{axis}")
                    if p:
                        p.expression = f"{val} mm"
                        changes.append(f"Stock {axis}: {val}mm")
        else:
            stock_offset = body.get("stock_offset", 2)
            stock_top = body.get("stock_top", 4)
            p = params.itemByName("job_stockOffsetSides")
            if p:
                p.expression = f"{stock_offset} mm"
                changes.append(f"Stock side offset: {stock_offset}mm")
            p = params.itemByName("job_stockOffsetTop")
            if p:
                p.expression = f"{stock_top} mm"
                changes.append(f"Stock top offset: {stock_top}mm")
            p = params.itemByName("job_stockOffsetBottom")
            if p:
                p.expression = "0 mm"

        # WCS orientation
        flip_z_val = body.get("flip_z", True)
        flip_z = params.itemByName("wcs_orientation_flipZ")
        if flip_z:
            flip_z.expression = "true" if flip_z_val else "false"
            if flip_z_val:
                changes.append("Z-axis flipped (pointing up)")

        # Stock point (WCS origin)
        stock_point = body.get("stock_point")
        if stock_point:
            sp = params.itemByName("job_stockPoint")
            if sp:
                point_map = {
                    "center": "'center'",
                    "top-center": "'top center'",
                    "top center": "'top center'",
                    "bottom-center": "'bottom center'",
                    "bottom center": "'bottom center'",
                    "corner": "'stock box point1'",
                    "top-left": "'stock box point2'",
                    "top-right": "'stock box point3'",
                    "bottom-left": "'stock box point4'",
                    "bottom-right": "'stock box point5'",
                    "top-left-bottom": "'stock box point6'",
                    "top-right-bottom": "'stock box point7'",
                    "bottom-left-bottom": "'stock box point8'",
                    "bottom-right-bottom": "'stock box point9'",
                }
                if stock_point in point_map:
                    sp.expression = point_map[stock_point]
                    changes.append(f"Stock point: {stock_point}")
                else:
                    sp.expression = f"'{stock_point}'"
                    changes.append(f"Stock point (raw): {stock_point}")
    except Exception as e:
        changes.append(f"Error: {str(e)}")

    return {
        "setup_id": setup.name,
        "name": setup.name,
        "changes": changes,
    }


def handle_cam_edit_setup(body):
    cam = get_cam()
    setup = _find_setup(cam, body.get("setup"))
    params = setup.parameters
    changes = []

    param_updates = body.get("params", {})
    for param_name, expression in param_updates.items():
        p = params.itemByName(param_name)
        if p:
            p.expression = str(expression)
            changes.append(f"{param_name} = {expression}")
        else:
            changes.append(f"Parameter not found: {param_name}")

    stock_mode = body.get("stock_mode")
    if stock_mode == "fixed":
        p = params.itemByName("job_stockMode")
        if p:
            p.expression = "'fixed size box'"
            changes.append("Stock mode: fixed size box")
        for axis, dim_key in [("X", "stock_x"), ("Y", "stock_y"), ("Z", "stock_z")]:
            val = body.get(dim_key)
            if val:
                p = params.itemByName(f"job_stockSize{axis}")
                if p:
                    p.expression = f"{val} mm"
                    changes.append(f"Stock {axis}: {val}mm")
    elif stock_mode == "relative":
        p = params.itemByName("job_stockMode")
        if p:
            p.expression = "'relative size box'"
            changes.append("Stock mode: relative")
        offset = body.get("stock_offset")
        if offset is not None:
            p = params.itemByName("job_stockOffsetSides")
            if p:
                p.expression = f"{offset} mm"
                changes.append(f"Stock side offset: {offset}mm")
        top = body.get("stock_top")
        if top is not None:
            p = params.itemByName("job_stockOffsetTop")
            if p:
                p.expression = f"{top} mm"
                changes.append(f"Stock top offset: {top}mm")

    flip_z = body.get("flip_z")
    if flip_z is not None:
        p = params.itemByName("wcs_orientation_flipZ")
        if p:
            p.expression = "true" if flip_z else "false"
            changes.append(f"Flip Z: {flip_z}")

    stock_point = body.get("stock_point")
    if stock_point:
        sp = params.itemByName("job_stockPoint")
        if sp:
            point_map = {
                "center": "'center'",
                "top-center": "'top center'",
                "corner": "'stock box point1'",
                "bottom-center": "'bottom center'",
            }
            if stock_point in point_map:
                sp.expression = point_map[stock_point]
                changes.append(f"Stock point: {stock_point}")

    return {"success": True, "setup": setup.name, "changes": changes}


def handle_cam_delete_setup(body):
    cam = get_cam()
    setup_name = body.get("setup")
    if not setup_name:
        raise Exception("setup name is required")
    for s in cam.setups:
        if s.name == setup_name:
            s.deleteMe()
            return {"success": True, "deleted": setup_name}
    raise Exception(f"Setup not found: {setup_name}")


def handle_cam_duplicate_setup(body):
    cam = get_cam()
    setup = _find_setup(cam, body.get("setup"))
    new_name = body.get("new_name")

    new_input = cam.setups.createInput(adsk.cam.OperationTypes.MillingOperation)
    new_setup = cam.setups.add(new_input)
    new_setup.name = new_name or f"{setup.name} Copy"

    src_params = setup.parameters
    dst_params = new_setup.parameters
    copied = 0
    for i in range(src_params.count):
        sp = src_params.item(i)
        dp = dst_params.itemByName(sp.name)
        if dp:
            try:
                dp.expression = sp.expression
                copied += 1
            except Exception:
                pass

    return {
        "success": True,
        "original": setup.name,
        "new_setup": new_setup.name,
        "params_copied": copied,
    }


def handle_cam_fix_setup(body):
    cam = get_cam()
    setup = _find_setup(cam, body.get("setup"))
    params = setup.parameters
    changes = []

    flip_z = params.itemByName("wcs_orientation_flipZ")
    if flip_z:
        flip_z.expression = "true"
        changes.append("Flipped Z axis")

    if body.get("stock_offset"):
        offset = body["stock_offset"]
        p = params.itemByName("job_stockOffsetSides")
        if p:
            p.expression = f"{offset} mm"
            changes.append(f"Stock side offset: {offset}mm")
    if body.get("stock_top"):
        top = body["stock_top"]
        p = params.itemByName("job_stockOffsetTop")
        if p:
            p.expression = f"{top} mm"
            changes.append(f"Stock top offset: {top}mm")

    return {"success": True, "setup": setup.name, "changes": changes}


def handle_cam_get_setup_params(body):
    cam = get_cam()
    setup = _find_setup(cam, body.get("setup"))
    filter_prefix = body.get("filter", "")
    param_list = []
    try:
        for param in setup.parameters:
            if filter_prefix and not param.name.startswith(filter_prefix):
                continue
            info = {"name": param.name}
            try:
                info["expression"] = param.expression
            except Exception:
                pass
            try:
                info["value"] = str(param.value)
            except Exception:
                pass
            param_list.append(info)
    except Exception as e:
        return {"error": str(e)}
    return {"setup": setup.name, "parameters": param_list, "count": len(param_list)}


# ── Stock / Model / Fixture ──────────────────────────────────

def handle_cam_set_model(body):
    cam = get_cam()
    root = get_root()
    setup = _find_setup(cam, body.get("setup"))
    body_names = body.get("bodies", [])

    bodies, not_found = _find_bodies(root, body_names)
    if not bodies:
        available = [b.name for b in root.bRepBodies]
        raise Exception(f"No bodies found matching {body_names}. Available: {available}")

    coll = adsk.core.ObjectCollection.create()
    for b in bodies:
        coll.add(b)
    try:
        setup.models = coll
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {
        "success": True,
        "bodies": [b.name for b in bodies],
        "message": f"Set {len(bodies)} bodies as machining model",
    }


def handle_cam_set_fixture(body):
    cam = get_cam()
    root = get_root()
    setup = _find_setup(cam, body.get("setup"))
    fixture_names = body.get("fixtures", [])
    if not fixture_names:
        raise Exception("fixtures parameter required — list of body names")

    fixture_bodies, not_found = _find_bodies(root, fixture_names)
    if not fixture_bodies:
        available = [b.name for b in root.bRepBodies]
        raise Exception(f"No fixture bodies found. Available: {available}")

    methods_tried = []

    try:
        if hasattr(setup, "fixture") and setup.fixture is not None:
            existing = setup.fixture
            for b in fixture_bodies:
                existing.add(b)
            methods_tried.append("setup.fixture.add()")
            return {
                "success": True,
                "setup": setup.name,
                "fixtures_set": [b.name for b in fixture_bodies],
                "method": "setup.fixture.add",
            }
    except Exception as e:
        methods_tried.append(f"setup.fixture.add failed: {str(e)[:50]}")

    try:
        coll = adsk.core.ObjectCollection.create()
        for b in fixture_bodies:
            coll.add(b)
        setup.fixture = coll
        methods_tried.append("setup.fixture = collection")
        return {
            "success": True,
            "setup": setup.name,
            "fixtures_set": [b.name for b in fixture_bodies],
            "method": "setup.fixture = ObjectCollection",
        }
    except Exception as e:
        methods_tried.append(f"setup.fixture= failed: {str(e)[:50]}")

    try:
        params = setup.parameters
        fp = params.itemByName("job_fixture")
        if fp:
            pv = adsk.cam.CadObjectParameterValue.cast(fp.value)
            if pv:
                pv.value = fixture_bodies
                methods_tried.append("param_value.value = list")
                return {
                    "success": True,
                    "setup": setup.name,
                    "fixtures_set": [b.name for b in fixture_bodies],
                    "method": "CadObjectParameterValue",
                }
    except Exception as e:
        methods_tried.append(f"param failed: {str(e)[:50]}")

    return {
        "success": False,
        "methods_tried": methods_tried,
        "message": "Could not set fixtures programmatically. Set them manually in the Setup dialog.",
        "bodies_ready": [b.name for b in fixture_bodies],
    }


def handle_cam_derive_body(body):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent

    source_path = body.get("source_path")
    body_name = body.get("body_name")
    if not source_path:
        raise Exception("source_path is required (path to .f3d file)")
    if not os.path.exists(source_path):
        raise Exception(f"Source file not found: {source_path}")

    current_doc = app.activeDocument
    source_doc = app.documents.open(source_path)
    if not source_doc:
        raise Exception("Failed to open source document")
    adsk.doEvents()
    time.sleep(0.5)
    adsk.doEvents()

    try:
        source_design = adsk.fusion.Design.cast(
            source_doc.products.itemByProductType("Design")
        )
        if not source_design:
            raise Exception("Source document does not contain a Design")
        source_root = source_design.rootComponent

        source_body = None
        for b in source_root.bRepBodies:
            if b.name == body_name:
                source_body = b
                break
        if not source_body:
            for occ in source_root.allOccurrences:
                for b in occ.bRepBodies:
                    if b.name == body_name:
                        source_body = b
                        break
                if source_body:
                    break
        if not source_body:
            available = [b.name for b in source_root.bRepBodies]
            for occ in source_root.allOccurrences:
                for b in occ.bRepBodies:
                    available.append(f"{occ.name}/{b.name}")
            source_doc.close(False)
            raise Exception(f"Body '{body_name}' not found. Available: {available[:20]}")

        current_doc.activate()
        adsk.doEvents()
        target_root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
        copy_body = source_body.copyToComponent(target_root)

        if copy_body:
            derived_name = body.get("new_name", body_name)
            copy_body.name = derived_name
            bbox = copy_body.boundingBox
            dims = {
                "x": round((bbox.maxPoint.x - bbox.minPoint.x) * 10, 2),
                "y": round((bbox.maxPoint.y - bbox.minPoint.y) * 10, 2),
                "z": round((bbox.maxPoint.z - bbox.minPoint.z) * 10, 2),
            }
            result = {
                "success": True,
                "body_name": copy_body.name,
                "dimensions_mm": dims,
            }
        else:
            result = {"success": False, "message": "Failed to copy body"}
        source_doc.close(False)
        return result
    except Exception as e:
        try:
            source_doc.close(False)
        except Exception:
            pass
        raise e


def handle_cam_create_keepout(body):
    root = get_root()
    setup = _find_setup(get_cam(), body.get("setup"))

    corner_size = body.get("corner_size")
    if not corner_size:
        return {"success": False, "message": "Specify corner_size (mm)"}

    try:
        params = setup.parameters
        stock_x = 500
        stock_y = 460
        sx = params.itemByName("job_stockSizeX")
        if sx:
            try:
                stock_x = float(sx.value.value) * 10
            except Exception:
                pass
        sy = params.itemByName("job_stockSizeY")
        if sy:
            try:
                stock_y = float(sy.value.value) * 10
            except Exception:
                pass

        sketch = root.sketches.add(root.xYConstructionPlane)
        sketch.name = "KeepOut_Corners"
        sz = corner_size
        hx, hy = stock_x / 2, stock_y / 2
        corners = [
            (-hx, -hy, -hx + sz, -hy + sz),
            (hx - sz, -hy, hx, -hy + sz),
            (-hx, hy - sz, -hx + sz, hy),
            (hx - sz, hy - sz, hx, hy),
        ]
        created = []
        for i, (x1, y1, x2, y2) in enumerate(corners):
            lines = sketch.sketchCurves.sketchLines
            p1 = adsk.core.Point3D.create(x1 / 10, y1 / 10, 0)
            p2 = adsk.core.Point3D.create(x2 / 10, y1 / 10, 0)
            p3 = adsk.core.Point3D.create(x2 / 10, y2 / 10, 0)
            p4 = adsk.core.Point3D.create(x1 / 10, y2 / 10, 0)
            lines.addByTwoPoints(p1, p2)
            lines.addByTwoPoints(p2, p3)
            lines.addByTwoPoints(p3, p4)
            lines.addByTwoPoints(p4, p1)
            created.append(f"Corner {i+1}: {sz}x{sz}mm")
        return {
            "success": True,
            "sketch_name": sketch.name,
            "zones": created,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Tool Management ──────────────────────────────────────────

def handle_cam_list_tools(body):
    cam = get_cam()
    tool_type_filter = body.get("type")
    tools = []
    sources = []

    # Document tools (from existing operations)
    try:
        doc_tools = set()
        for setup in cam.setups:
            for op in setup.allOperations:
                try:
                    tool = getattr(op, "tool", None) or getattr(op, "activeTool", None)
                    if not tool:
                        continue
                    try:
                        tool_json = json.loads(tool.toJson())
                    except Exception:
                        tool_json = {
                            "description": getattr(tool, "description", "Unknown"),
                            "type": str(getattr(tool, "type", "Unknown")),
                        }
                    geom = tool_json.get("geometry", {})
                    uid = tool_json.get("description", "") + str(geom.get("DC", 0))
                    if uid in doc_tools:
                        continue
                    doc_tools.add(uid)
                    info = {
                        "source": "Document",
                        "from_operation": op.name,
                        "description": tool_json.get("description", ""),
                        "type": tool_json.get("type", ""),
                    }
                    if geom:
                        info["diameter_mm"] = geom.get("DC", 0)
                        info["flute_length_mm"] = geom.get("LCF", 0)
                        info["taper_angle"] = geom.get("TA", 0)
                        info["tip_angle"] = geom.get("SIG", 0)
                    post = tool_json.get("post-process", {})
                    if post:
                        info["tool_number"] = post.get("number", 0)
                    if tool_type_filter:
                        combined = (str(info.get("type", "")) + str(info.get("description", ""))).lower()
                        fl = tool_type_filter.lower()
                        if fl in ("chamfer", "v_bit", "v-bit", "vbit"):
                            if "chamfer" not in combined and "v-bit" not in combined and "v bit" not in combined:
                                continue
                        elif fl not in combined:
                            continue
                    tools.append(info)
                except Exception:
                    pass
        sources.append(f"Document: {len(doc_tools)} unique tools")
    except Exception as e:
        sources.append(f"Document: error — {e}")

    # Library tools
    try:
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
                        for i in range(min(lib.count, 50)):
                            tool = lib.item(i)
                            if not tool:
                                continue
                            tj = json.loads(tool.toJson())
                            info = {
                                "source": "Local",
                                "index": i,
                                "description": tj.get("description", ""),
                                "type": tj.get("type", ""),
                                "tool_number": tj.get("post-process", {}).get("number", i + 1),
                            }
                            geom = tj.get("geometry", {})
                            if geom:
                                info["diameter_mm"] = geom.get("DC", 0)
                                info["taper_angle"] = geom.get("TA", 0)
                            if tool_type_filter:
                                tstr = str(info.get("type", "")).lower()
                                fl = tool_type_filter.lower()
                                if fl in ("chamfer", "v_bit"):
                                    if "chamfer" not in tstr:
                                        continue
                                elif fl not in tstr:
                                    continue
                            tools.append(info)
                    except Exception:
                        pass
            has_children = False
            for _ in child_urls:
                has_children = True
                break
            if has_children:
                sources.append(f"Local library: {sum(1 for t in tools if t.get('source') == 'Local')} tools")
            else:
                sources.append("Local library: no child libraries found")
    except Exception as e:
        sources.append(f"Libraries: error — {e}")

    return {"sources_checked": sources, "tool_count": len(tools), "tools": tools}


def handle_cam_create_tool(body):
    """Create a new cutting tool and add to the local library."""
    tool_def = _build_tool_def(body)
    tool_type = tool_def["type"]
    diameter = tool_def["geometry"]["DC"]

    try:
        tool = adsk.cam.Tool.createFromJson(json.dumps(tool_def))
        result = {
            "success": True,
            "description": tool_def["description"],
            "type": tool_type,
            "diameter_mm": diameter,
            "tool_number": tool_def["post-process"]["number"],
        }
        if body.get("add_to_library", True):
            try:
                lib_data = _read_local_library_json()
                lib_data["data"].append(json.loads(tool.toJson()))
                _write_local_library_json(lib_data)
                result["added_to_library"] = _LOCAL_LIB_PATH
            except Exception as le:
                result["library_warning"] = str(le)
        return result
    except Exception as e:
        return {"success": False, "error": str(e), "tool_json": tool_def}


# ── Library helpers ──────────────────────────────────────────

_LOCAL_LIB_PATH = os.path.join(
    os.path.expanduser("~"),
    "Library", "Application Support", "Autodesk", "CAM360", "libraries", "Local", "Library.json",
)


def _read_local_library_json():
    """Read the Local library JSON file, returning the parsed data dict."""
    if os.path.exists(_LOCAL_LIB_PATH):
        with open(_LOCAL_LIB_PATH) as f:
            return json.load(f)
    return {"version": 36, "data": []}


def _write_local_library_json(data):
    """Write the Local library JSON file."""
    os.makedirs(os.path.dirname(_LOCAL_LIB_PATH), exist_ok=True)
    with open(_LOCAL_LIB_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _get_api_library_for_read():
    """Get API ToolLibrary for reading (tool lookup). Returns ToolLibrary or None."""
    try:
        mgr = adsk.cam.CAMManager.get()
        tool_libs = mgr.libraryManager.toolLibraries
        local_url = tool_libs.urlByLocation(adsk.cam.LibraryLocations.LocalLibraryLocation)
        if not local_url:
            return None
        child_urls = tool_libs.childAssetURLs(local_url)
        if child_urls:
            for curl in child_urls:
                lib = tool_libs.toolLibraryAtURL(curl)
                if lib:
                    return lib
                break
    except Exception:
        pass
    return None


def _tool_uid(tj):
    """Stable identity key for dedup: description + type + diameter."""
    geom = tj.get("geometry", {})
    return (tj.get("description", ""), tj.get("type", ""), geom.get("DC", 0))


def _build_tool_def(body):
    """Build a tool JSON dict from request body (shared by create_tool and library_add)."""
    tool_type = body.get("type", "flat end mill")
    diameter = body.get("diameter")
    if not diameter:
        raise Exception("diameter (mm) is required")
    tool_def = {
        "description": body.get("description", f"{diameter}mm {tool_type}"),
        "type": tool_type,
        "unit": "millimeters",
        "geometry": {
            "DC": diameter,
            "LCF": body.get("flute_length", diameter * 3),
            "OAL": body.get("overall_length", diameter * 5),
            "NOF": body.get("flutes", 2),
            "SFDM": body.get("shaft_diameter", diameter),
        },
        "post-process": {
            "number": body.get("tool_number", 1),
            "comment": body.get("description", ""),
        },
    }
    if body.get("taper_angle"):
        tool_def["geometry"]["TA"] = body["taper_angle"]
    if body.get("tip_angle"):
        tool_def["geometry"]["SIG"] = body["tip_angle"]
    if body.get("corner_radius"):
        tool_def["geometry"]["RE"] = body["corner_radius"]
    shaft_diameter = body.get("shaft_diameter")
    if shaft_diameter:
        tool_def["shaft"] = {"DC": shaft_diameter}
    feeds = body.get("feeds_speeds", {})
    rpm = feeds.get("spindle_speed", 18000)
    cut_feed = feeds.get("cutting_feedrate", 2000)
    plunge_feed = feeds.get("plunge_feedrate", round(cut_feed / 3))
    ramp_feed = feeds.get("ramp_feedrate", plunge_feed)
    tool_def["start-values"] = {
        "presets": [{
            "name": "Default preset",
            "n": rpm,
            "n_ramp": rpm,
            "v_f": cut_feed,
            "v_f_leadIn": cut_feed,
            "v_f_leadOut": cut_feed,
            "v_f_plunge": plunge_feed,
            "v_f_ramp": ramp_feed,
            "v_f_transition": cut_feed,
            "tool-coolant": "disabled",
            "expressions": {
                "tool_spindleSpeed": f"{rpm} rpm",
                "tool_feedCutting": f"{cut_feed} mmpm",
                "tool_coolant": "'disabled'",
            },
        }]
    }
    return tool_def


# ── Library Management ───────────────────────────────────────

def handle_cam_library_add(body):
    """Add a tool to the persistent Local library.

    Modes:
      - from_operation: copy tool from a named operation in the current document
      - from definition: provide type, diameter, etc. (same as create_tool)
    """
    lib_data = _read_local_library_json()
    from_op = body.get("from_operation")

    if from_op:
        cam = get_cam()
        found = None
        for op in cam.allOperations:
            if op.name == from_op:
                found = op
                break
        if not found:
            raise Exception(f"Operation '{from_op}' not found")
        tool = found.tool
        if not tool:
            raise Exception(f"Operation '{from_op}' has no tool assigned")
        tj = json.loads(tool.toJson())
        lib_data["data"].append(tj)
        _write_local_library_json(lib_data)
        geom = tj.get("geometry", {})
        return {
            "success": True,
            "action": "added_from_operation",
            "operation": from_op,
            "description": tj.get("description", ""),
            "type": tj.get("type", ""),
            "diameter_mm": geom.get("DC", 0),
            "tool_number": tj.get("post-process", {}).get("number", 0),
            "library": _LOCAL_LIB_PATH,
            "library_count": len(lib_data["data"]),
        }

    tool_def = _build_tool_def(body)
    tool = adsk.cam.Tool.createFromJson(json.dumps(tool_def))
    tool_json = json.loads(tool.toJson())
    lib_data["data"].append(tool_json)
    _write_local_library_json(lib_data)
    return {
        "success": True,
        "action": "added_from_definition",
        "description": tool_def["description"],
        "type": tool_def["type"],
        "diameter_mm": body["diameter"],
        "tool_number": tool_def["post-process"]["number"],
        "library": _LOCAL_LIB_PATH,
        "library_count": len(lib_data["data"]),
    }


def handle_cam_library_remove(body):
    """Remove a tool from the Local library by index."""
    index = body.get("index")
    if index is None:
        raise Exception("index is required")
    lib_data = _read_local_library_json()
    tools = lib_data["data"]
    if index < 0 or index >= len(tools):
        raise Exception(f"Index {index} out of range (library has {len(tools)} tools)")
    removed = tools.pop(index)
    _write_local_library_json(lib_data)
    return {
        "success": True,
        "removed_index": index,
        "removed_description": removed.get("description", ""),
        "removed_type": removed.get("type", ""),
        "library_count": len(tools),
    }


def handle_cam_library_import_doc(body):
    """Bulk import unique tools from all document operations into the Local library."""
    cam = get_cam()
    lib_data = _read_local_library_json()

    existing_uids = set()
    for td in lib_data["data"]:
        existing_uids.add(_tool_uid(td))

    added = []
    skipped = []
    for op in cam.allOperations:
        try:
            tool = op.tool
            if not tool:
                continue
            tj = json.loads(tool.toJson())
            uid = _tool_uid(tj)
            if uid in existing_uids:
                skipped.append({"operation": op.name, "description": tj.get("description", ""), "reason": "duplicate"})
                continue
            existing_uids.add(uid)
            lib_data["data"].append(tj)
            geom = tj.get("geometry", {})
            added.append({
                "operation": op.name,
                "description": tj.get("description", ""),
                "type": tj.get("type", ""),
                "diameter_mm": geom.get("DC", 0),
                "tool_number": tj.get("post-process", {}).get("number", 0),
            })
        except Exception:
            pass

    if added:
        _write_local_library_json(lib_data)

    return {
        "success": True,
        "added_count": len(added),
        "skipped_count": len(skipped),
        "added": added,
        "skipped": skipped,
        "library_count": len(lib_data["data"]),
    }


def handle_cam_library_list(body):
    """List tools in the persistent Local library only (not document operations)."""
    lib_data = _read_local_library_json()
    tools = []
    for i, td in enumerate(lib_data["data"]):
        geom = td.get("geometry", {})
        info = {
            "index": i,
            "description": td.get("description", ""),
            "type": td.get("type", ""),
            "diameter_mm": geom.get("DC", 0),
            "flute_length_mm": geom.get("LCF", 0),
            "flutes": geom.get("NOF", 0),
            "overall_length_mm": geom.get("OAL", 0),
            "taper_angle": geom.get("TA", 0),
            "tip_angle": geom.get("SIG", 0),
            "tool_number": td.get("post-process", {}).get("number", 0),
        }
        tools.append(info)
    return {"library": _LOCAL_LIB_PATH, "tool_count": len(tools), "tools": tools}


def handle_cam_library_export(body):
    """Export the Local library to a JSON file."""
    output_path = body.get("output")
    if not output_path:
        raise Exception("output path is required")
    lib_data = _read_local_library_json()
    output_path = os.path.expanduser(output_path)
    with open(output_path, "w") as f:
        json.dump(lib_data, f, indent=2)
    return {"success": True, "path": output_path, "tool_count": len(lib_data["data"])}


def handle_cam_library_import_file(body):
    """Import tools from a JSON file into the Local library."""
    input_path = body.get("input")
    if not input_path:
        raise Exception("input path is required")
    input_path = os.path.expanduser(input_path)
    if not os.path.exists(input_path):
        raise Exception(f"File not found: {input_path}")
    with open(input_path) as f:
        data = json.load(f)

    lib_data = _read_local_library_json()
    existing_uids = set()
    for td in lib_data["data"]:
        existing_uids.add(_tool_uid(td))

    tool_defs = data.get("data", data) if isinstance(data, dict) else data
    added = 0
    skipped = 0
    for td in tool_defs:
        uid = _tool_uid(td)
        if uid in existing_uids:
            skipped += 1
            continue
        lib_data["data"].append(td)
        existing_uids.add(uid)
        added += 1

    if added > 0:
        _write_local_library_json(lib_data)

    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "library_count": len(lib_data["data"]),
    }


# ── Operations Query ─────────────────────────────────────────

def handle_cam_list_operations(body):
    cam = get_cam()
    setup_name = body.get("setup")

    if setup_name:
        setup = _find_setup(cam, setup_name)
        setups_to_scan = [setup]
    else:
        setups_to_scan = [cam.setups.item(i) for i in range(cam.setups.count)]

    all_ops = []
    for setup in setups_to_scan:
        for op in setup.allOperations:
            info = {
                "name": op.name,
                "setup": setup.name,
                "has_toolpath": op.hasToolpath,
                "is_suppressed": op.isSuppressed,
            }
            try:
                info["strategy"] = op.strategy
            except Exception:
                pass
            try:
                info["state"] = str(op.operationState)
            except Exception:
                pass
            if body.get("show_params"):
                params = []
                skip_prefixes = ("tool_", "holder_")
                op_filter = body.get("operation")
                try:
                    for param in op.parameters:
                        if not op_filter and param.name.startswith(skip_prefixes):
                            continue
                        params.append({
                            "name": param.name,
                            "expression": param.expression
                            if hasattr(param, "expression")
                            else str(param.value),
                        })
                except Exception:
                    pass
                info["parameters"] = params
            all_ops.append(info)

    return {"operations": all_ops, "count": len(all_ops)}


def handle_cam_select_silhouette(body):
    cam = get_cam()
    op_name = body.get("operation")
    if not op_name:
        raise Exception("operation name required")

    op = None
    for setup in cam.setups:
        for o in setup.allOperations:
            if o.name == op_name:
                op = o
                break
        if op:
            break
    if not op:
        raise Exception(f"Operation not found: {op_name}")

    changes = []
    try:
        params = op.parameters
        for pname in ("machiningBoundary", "contour_mode", "boundaryMode"):
            p = params.itemByName(pname)
            if p:
                p.expression = "'silhouette'"
                changes.append(f"Set {pname} to silhouette")
                break
        bm = params.itemByName("bottomHeight_mode")
        if bm:
            bm.expression = "'model bottom'"
            changes.append("Set bottom to model bottom")
    except Exception as e:
        changes.append(f"Error: {e}")

    return {"operation": op_name, "changes": changes}


# ── Post-processing & Simulation ─────────────────────────────

def handle_cam_generate(body):
    cam = get_cam()
    setup_name = body.get("setup")

    if setup_name:
        setup = _find_setup(cam, setup_name)
        future = cam.generateToolpath(setup)
    else:
        future = cam.generateAllToolpaths(True)

    timeout = body.get("timeout", 120)
    start = time.time()
    while not future.isGenerationCompleted:
        if time.time() - start > timeout:
            return {"success": False, "message": "Generation timed out"}
        adsk.doEvents()
        time.sleep(0.2)

    return {
        "success": True,
        "operations_generated": future.numberOfOperations,
    }


def handle_cam_post_process(body):
    cam = get_cam()
    output_path = body.get("output_path")
    if not output_path:
        raise Exception("output_path is required")

    setup = _find_setup(cam, body.get("setup"))
    post_name = body.get("post_processor", "fanuc")

    operations = adsk.core.ObjectCollection.create()
    for op in setup.allOperations:
        if op.hasToolpath:
            operations.add(op)
    if operations.count == 0:
        raise Exception("No operations with toolpaths to post-process")

    post_input = adsk.cam.PostProcessInput.create(output_path, post_name, "", "")
    post_input.isOpenInEditor = body.get("open_editor", False)
    cam.postProcess(setup, post_input)

    return {
        "success": True,
        "output_path": output_path,
        "operations_posted": operations.count,
    }


def handle_cam_simulate(body):
    cam = get_cam()
    setup = _find_setup(cam, body.get("setup"))
    cam.startSimulation(setup)
    return {"success": True, "message": "Simulation started"}


def handle_cam_cycle_time(body):
    cam = get_cam()
    setup = _find_setup(cam, body.get("setup"))

    total_time = 0.0
    op_times = []
    for op in setup.allOperations:
        if op.hasToolpath and not op.isSuppressed:
            try:
                ct = op.machiningTime
                op_times.append({"name": op.name, "time_seconds": round(ct, 1)})
                total_time += ct
            except Exception:
                op_times.append({"name": op.name, "time_seconds": None})

    return {
        "setup": setup.name,
        "total_seconds": round(total_time, 1),
        "total_minutes": round(total_time / 60, 1),
        "operations": op_times,
    }


# ── Workspace ────────────────────────────────────────────────

def handle_cam_switch(body):
    app = adsk.core.Application.get()
    ui = app.userInterface
    ws = ui.workspaces.itemById("CAMEnvironment")
    if ws:
        ws.activate()
        adsk.doEvents()
        return {"success": True, "message": "Switched to Manufacturing workspace"}
    raise Exception("Manufacturing workspace not found")


def handle_cam_info(body):
    try:
        cam = get_cam()
    except Exception:
        return {
            "in_cam_workspace": False,
            "message": "Not in Manufacturing workspace. Use cam_switch first.",
        }

    setups = []
    for s in cam.setups:
        setups.append({
            "name": s.name,
            "operations": s.allOperations.count,
        })

    return {
        "in_cam_workspace": True,
        "setup_count": len(setups),
        "setups": setups,
    }


# ── Route table ──────────────────────────────────────────────

CAM_SETUP_ROUTES = {
    # Setup management
    "/cam_list_setups": handle_cam_list_setups,
    "/cam_create_setup": handle_cam_create_setup,
    "/cam_edit_setup": handle_cam_edit_setup,
    "/cam_delete_setup": handle_cam_delete_setup,
    "/cam_duplicate_setup": handle_cam_duplicate_setup,
    "/cam_fix_setup": handle_cam_fix_setup,
    "/cam_get_setup_params": handle_cam_get_setup_params,
    # Stock / Model / Fixture
    "/cam_set_model": handle_cam_set_model,
    "/cam_set_fixture": handle_cam_set_fixture,
    "/cam_derive_body": handle_cam_derive_body,
    "/cam_create_keepout": handle_cam_create_keepout,
    # Tool management
    "/cam_list_tools": handle_cam_list_tools,
    "/cam_create_tool": handle_cam_create_tool,
    # Library management
    "/cam_library_list": handle_cam_library_list,
    "/cam_library_add": handle_cam_library_add,
    "/cam_library_remove": handle_cam_library_remove,
    "/cam_library_import_doc": handle_cam_library_import_doc,
    "/cam_library_export": handle_cam_library_export,
    "/cam_library_import_file": handle_cam_library_import_file,
    # Operations query
    "/cam_list_operations": handle_cam_list_operations,
    "/cam_select_silhouette": handle_cam_select_silhouette,
    # Post-processing & simulation
    "/cam_generate": handle_cam_generate,
    "/cam_post_process": handle_cam_post_process,
    "/cam_simulate": handle_cam_simulate,
    "/cam_cycle_time": handle_cam_cycle_time,
    # Workspace
    "/cam_switch": handle_cam_switch,
    "/cam_info": handle_cam_info,
}
