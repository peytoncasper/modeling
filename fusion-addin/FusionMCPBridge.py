"""
Fusion 360 MCP Bridge Add-in
Exposes an HTTP server inside Fusion 360 for external control.
"""

import adsk.core
import adsk.fusion
import adsk.cam
import threading
import json
import traceback
import base64
import tempfile
import os
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# Globals
app = None
ui = None
server = None
server_thread = None
custom_event = None
custom_event_handler = None

# For marshaling ALL calls to main thread
pending_command = None
pending_body = None
command_result = None
command_ready = threading.Event()

PORT = 8080


class FusionHandler(BaseHTTPRequestHandler):
    """Handle incoming HTTP requests and dispatch to Fusion API."""

    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def read_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            return json.loads(self.rfile.read(content_length).decode())
        return {}

    def do_GET(self):
        self.handle_request("GET")

    def do_POST(self):
        self.handle_request("POST")

    def handle_request(self, method):
        global pending_command, pending_body, command_result, command_ready, app
        
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.read_body() if method == "POST" else {}

        # Check if route exists
        if path not in ROUTES:
            self.send_json({"error": True, "message": f"Unknown endpoint: {path}"}, 404)
            return

        # ping can run directly (no Fusion API calls)
        if path == "/ping":
            self.send_json(ROUTES[path](body))
            return

        # Queue command for main thread execution
        command_ready.clear()
        command_result = None
        pending_command = path
        pending_body = body

        try:
            # Fire custom event to execute on main thread
            app.fireCustomEvent("FusionMCPCommandEvent")
            
            # Wait for result (timeout 30 seconds)
            if command_ready.wait(timeout=30):
                self.send_json(command_result if command_result else {"error": True, "message": "No result"})
            else:
                self.send_json({"error": True, "message": "Command timed out"})
        except Exception as e:
            self.send_json({
                "error": True,
                "message": str(e),
                "traceback": traceback.format_exc()
            }, 500)


# ============================================================================
# UTILITY HELPERS
# ============================================================================

def get_design():
    """Get the Fusion design (works from any workspace)."""
    global app
    doc = app.activeDocument
    if not doc:
        raise Exception("No active document")
    
    # Try active product first
    design = app.activeProduct
    if design and design.productType == 'DesignProductType':
        return design
    
    # If in CAM or other workspace, find design from products
    for product in doc.products:
        if product.productType == 'DesignProductType':
            return product
    
    raise Exception("No Fusion design found in document")


def get_root():
    """Get the root component."""
    return get_design().rootComponent


def point2d(coords):
    """Create a 2D point from [x, y] in mm, converted to cm for Fusion."""
    return adsk.core.Point3D.create(coords[0] / 10.0, coords[1] / 10.0, 0)


def point3d(coords):
    """Create a 3D point from [x, y, z] in mm, converted to cm for Fusion."""
    return adsk.core.Point3D.create(coords[0] / 10.0, coords[1] / 10.0, coords[2] / 10.0)


def vector3d(coords):
    """Create a 3D vector from [x, y, z]."""
    return adsk.core.Vector3D.create(coords[0], coords[1], coords[2])


# ============================================================================
# DOCUMENT LIFECYCLE
# ============================================================================

def handle_ping(body):
    return {
        "status": "ok",
        "message": "Fusion 360 MCP Bridge is running",
        "port": PORT
    }


def handle_info(body):
    global app
    design = app.activeProduct
    
    if design is None:
        return {"status": "ok", "document": None, "message": "No active document"}

    doc = app.activeDocument
    root = design.rootComponent if hasattr(design, 'rootComponent') else None
    
    bodies = []
    if root:
        for body in root.bRepBodies:
            bodies.append(body.name)
    
    return {
        "status": "ok",
        "document": {
            "name": doc.name if doc else "Untitled",
            "is_saved": doc.isSaved if doc else False,
        },
        "design": {
            "units": design.unitsManager.defaultLengthUnits if hasattr(design, 'unitsManager') else "unknown",
            "bodies": bodies
        }
    }


def handle_new_document(body):
    global app
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    adsk.doEvents()  # Let Fusion initialize the document
    design = app.activeProduct
    
    name = body.get("name", "Untitled")
    # Note: Can't rename unsaved documents directly in Fusion
    
    return {
        "status": "ok",
        "document_id": doc.name,
        "name": name
    }


def handle_save(body):
    global app
    doc = app.activeDocument
    if not doc:
        raise Exception("No active document")
    
    path = body.get("path")
    if path:
        # Export to local file
        design = app.activeProduct
        export_mgr = design.exportManager
        options = export_mgr.createFusionArchiveExportOptions(path)
        export_mgr.execute(options)
        return {"success": True, "path": path}
    else:
        doc.save("Saved by MCP Bridge")
        return {"success": True, "path": None}


# ============================================================================
# REFERENCE GEOMETRY
# ============================================================================

def handle_list_planes(body):
    root = get_root()
    planes = [
        {"id": "xy", "name": "XY Plane", "origin": [0, 0, 0], "normal": [0, 0, 1]},
        {"id": "xz", "name": "XZ Plane", "origin": [0, 0, 0], "normal": [0, 1, 0]},
        {"id": "yz", "name": "YZ Plane", "origin": [0, 0, 0], "normal": [1, 0, 0]},
    ]
    
    # Add any user-created construction planes
    for plane in root.constructionPlanes:
        geo = plane.geometry
        planes.append({
            "id": plane.name,
            "name": plane.name,
            "origin": [geo.origin.x, geo.origin.y, geo.origin.z],
            "normal": [geo.normal.x, geo.normal.y, geo.normal.z]
        })
    
    return {"planes": planes}


def handle_create_offset_plane(body):
    root = get_root()
    
    base_plane_id = body.get("base_plane", "xy")
    offset = body.get("offset", 10)
    component_name = body.get("component")  # Optional: target component
    
    # Determine which component to create the plane in
    if component_name:
        target_component, target_occ = get_component_by_name(component_name)
        if not target_component:
            raise Exception(f"Component not found: {component_name}")
    else:
        target_component = root
    
    planes = target_component.constructionPlanes
    plane_input = planes.createInput()
    
    # Get base plane from target component
    if base_plane_id == "xy":
        base = target_component.xYConstructionPlane
    elif base_plane_id == "xz":
        base = target_component.xZConstructionPlane
    elif base_plane_id == "yz":
        base = target_component.yZConstructionPlane
    else:
        # Try target component first, then root
        base = target_component.constructionPlanes.itemByName(base_plane_id)
        if not base:
            base = root.constructionPlanes.itemByName(base_plane_id)
    
    if not base:
        raise Exception(f"Plane not found: {base_plane_id}")
    
    offset_value = adsk.core.ValueInput.createByReal(offset / 10.0)  # Convert mm to cm
    plane_input.setByOffset(base, offset_value)
    
    new_plane = planes.add(plane_input)
    
    return {
        "plane_id": new_plane.name,
        "name": new_plane.name
    }


# ============================================================================
# SKETCH OPERATIONS
# ============================================================================

def get_component_by_name(name):
    """Get a component by name (e.g., 'Carcass' or 'Carcass:1')."""
    root = get_root()
    
    # Strip occurrence index if present (e.g., "Carcass:1" -> "Carcass")
    base_name = name.split(":")[0] if ":" in name else name
    
    # Check all occurrences
    for occ in root.allOccurrences:
        if occ.component.name == base_name or occ.name == name:
            return occ.component, occ
    
    return None, None


def handle_create_sketch(body):
    root = get_root()
    
    plane_id = body.get("plane", "xy")
    name = body.get("name")
    component_name = body.get("component")  # Optional: target component
    
    # Determine which component to create the sketch in
    if component_name:
        target_component, target_occ = get_component_by_name(component_name)
        if not target_component:
            raise Exception(f"Component not found: {component_name}")
    else:
        target_component = root
        target_occ = None
    
    sketches = target_component.sketches
    
    # Get plane from the target component
    if plane_id == "xy":
        plane = target_component.xYConstructionPlane
    elif plane_id == "xz":
        plane = target_component.xZConstructionPlane
    elif plane_id == "yz":
        plane = target_component.yZConstructionPlane
    else:
        # Try to find custom plane in target component first, then root
        plane = target_component.constructionPlanes.itemByName(plane_id)
        if not plane:
            plane = root.constructionPlanes.itemByName(plane_id)
    
    if not plane:
        raise Exception(f"Plane not found: {plane_id}")
    
    sketch = sketches.add(plane)
    adsk.doEvents()  # Let Fusion process
    if name:
        sketch.name = name
    
    return {
        "sketch_id": sketch.name,
        "name": sketch.name,
        "component": target_component.name
    }


def get_sketch(sketch_id):
    """Get a sketch by name, searching root and all components."""
    root = get_root()
    
    # Try root first
    sketch = root.sketches.itemByName(sketch_id)
    if sketch:
        return sketch
    
    # Search all component occurrences
    for occ in root.allOccurrences:
        sketch = occ.component.sketches.itemByName(sketch_id)
        if sketch:
            return sketch
    
    raise Exception(f"Sketch not found: {sketch_id}")


def handle_draw_line(body):
    sketch = get_sketch(body["sketch_id"])
    lines = sketch.sketchCurves.sketchLines
    
    # Get current curve count before adding
    curve_idx = sketch.sketchCurves.count
    
    start = point2d(body["start"])
    end = point2d(body["end"])
    
    line = lines.addByTwoPoints(start, end)
    adsk.doEvents()  # Let Fusion process
    
    if body.get("construction", False):
        line.isConstruction = True
    
    return {"curve_id": f"{body['sketch_id']}_curve_{curve_idx}"}


def handle_draw_arc(body):
    import math
    sketch = get_sketch(body["sketch_id"])
    arcs = sketch.sketchCurves.sketchArcs
    
    curve_idx = sketch.sketchCurves.count
    
    center_coords = body["center"]
    radius = body["radius"] / 10.0  # mm to cm
    start_angle = body["start_angle"] * math.pi / 180.0  # deg to rad
    sweep_angle = body["sweep_angle"] * math.pi / 180.0
    
    center = point2d(center_coords)
    
    # Calculate start point from center, radius, and start angle
    start_x = center_coords[0] / 10.0 + radius * math.cos(start_angle)
    start_y = center_coords[1] / 10.0 + radius * math.sin(start_angle)
    start_point = adsk.core.Point3D.create(start_x, start_y, 0)
    
    arc = arcs.addByCenterStartSweep(center, start_point, sweep_angle)
    adsk.doEvents()  # Let Fusion process
    
    return {"curve_id": f"{body['sketch_id']}_curve_{curve_idx}"}


def handle_draw_arc_3point(body):
    sketch = get_sketch(body["sketch_id"])
    arcs = sketch.sketchCurves.sketchArcs
    
    curve_idx = sketch.sketchCurves.count
    
    start = point2d(body["start"])
    mid = point2d(body["mid"])
    end = point2d(body["end"])
    
    arc = arcs.addByThreePoints(start, mid, end)
    
    return {"curve_id": f"{body['sketch_id']}_curve_{curve_idx}"}


def handle_draw_circle(body):
    sketch = get_sketch(body["sketch_id"])
    circles = sketch.sketchCurves.sketchCircles
    
    curve_idx = sketch.sketchCurves.count
    
    center = point2d(body["center"])
    radius = body["radius"] / 10.0  # mm to cm
    
    circle = circles.addByCenterRadius(center, radius)
    adsk.doEvents()  # Let Fusion process
    
    return {"curve_id": f"{body['sketch_id']}_curve_{curve_idx}"}


def handle_draw_rectangle(body):
    sketch = get_sketch(body["sketch_id"])
    lines = sketch.sketchCurves.sketchLines
    
    start_idx = sketch.sketchCurves.count
    
    corner1 = point2d(body["corner1"])
    corner2 = point2d(body["corner2"])
    
    rect_lines = lines.addTwoPointRectangle(corner1, corner2)
    adsk.doEvents()  # Let Fusion process the geometry
    
    curve_ids = [f"{body['sketch_id']}_curve_{start_idx + i}" for i in range(len(rect_lines))]
    
    return {"curve_ids": curve_ids}


def handle_draw_spline(body):
    sketch = get_sketch(body["sketch_id"])
    splines = sketch.sketchCurves.sketchFittedSplines
    
    curve_idx = sketch.sketchCurves.count
    
    points_data = body["points"]
    points = adsk.core.ObjectCollection.create()
    for p in points_data:
        points.add(point2d(p))
    
    spline = splines.add(points)
    
    if body.get("closed", False):
        spline.isClosed = True
    
    return {"curve_id": f"{body['sketch_id']}_curve_{curve_idx}"}


def handle_sketch_fillet(body):
    sketch = get_sketch(body["sketch_id"])
    sketch_id = body["sketch_id"]
    
    # Parse curve IDs like "SketchName_curve_0"
    curve1_id = body["curve1_id"]
    curve2_id = body["curve2_id"]
    
    curve1 = None
    curve2 = None
    
    # Extract curve indices
    parts1 = curve1_id.rsplit("_curve_", 1)
    parts2 = curve2_id.rsplit("_curve_", 1)
    
    if len(parts1) == 2:
        try:
            idx1 = int(parts1[1])
            if idx1 < sketch.sketchCurves.count:
                curve1 = sketch.sketchCurves.item(idx1)
        except ValueError:
            pass
    
    if len(parts2) == 2:
        try:
            idx2 = int(parts2[1])
            if idx2 < sketch.sketchCurves.count:
                curve2 = sketch.sketchCurves.item(idx2)
        except ValueError:
            pass
    
    if not curve1 or not curve2:
        raise Exception(f"Could not find curves for fillet: {curve1_id}, {curve2_id}")
    
    if curve1 == curve2:
        raise Exception("Cannot fillet a curve with itself")
    
    radius = body["radius"] / 10.0  # mm to cm
    
    # Find the shared point between the two curves
    fillets = sketch.sketchCurves.sketchArcs
    
    # Try to fillet at the end of curve1 and start of curve2
    fillet_idx = sketch.sketchCurves.count
    fillet = fillets.addFillet(curve1, curve1.endSketchPoint.geometry, 
                                curve2, curve2.startSketchPoint.geometry, radius)
    
    return {"curve_id": f"{sketch_id}_curve_{fillet_idx}"}


def handle_finish_sketch(body):
    sketch = get_sketch(body["sketch_id"])
    
    # Count profiles and check validity
    profile_count = sketch.profiles.count
    
    # Check for open curves
    open_curves = 0
    for curve in sketch.sketchCurves:
        if hasattr(curve, 'isClosed') and not curve.isClosed:
            open_curves += 1
    
    return {
        "success": True,
        "is_valid": profile_count > 0,
        "profile_count": profile_count,
        "open_curves": open_curves
    }


def handle_get_sketch_profiles(body):
    sketch = get_sketch(body["sketch_id"])
    
    profiles = []
    for i in range(sketch.profiles.count):
        profile = sketch.profiles.item(i)
        bbox = profile.boundingBox
        
        profiles.append({
            "profile_id": f"profile_{i}",
            "profile_index": i,
            "area": profile.areaProperties().area * 100,  # cm² to mm²
            "bounding_box": {
                "min": [bbox.minPoint.x * 10, bbox.minPoint.y * 10],
                "max": [bbox.maxPoint.x * 10, bbox.maxPoint.y * 10]
            }
        })
    
    return {"profiles": profiles}


def handle_list_sketch_dimensions(body):
    """List all dimensions in a sketch with their current values and expressions."""
    sketch = get_sketch(body["sketch_id"])
    
    dimensions = []
    
    # Iterate through sketch dimensions
    for i, dim in enumerate(sketch.sketchDimensions):
        dim_info = {
            "dimension_id": f"{body['sketch_id']}_dim_{i}",
            "index": i,
            "type": dim.objectType.split("::")[-1],  # Get just the type name
            "value_mm": dim.value * 10,  # cm to mm
        }
        
        # Get the parameter for expression info
        try:
            param = dim.parameter
            if param:
                dim_info["expression"] = param.expression
                dim_info["parameter_name"] = param.name
                dim_info["is_driven"] = param.isDrivenByConstraint if hasattr(param, 'isDrivenByConstraint') else False
        except:
            pass
        
        # Try to get additional type-specific info
        try:
            if hasattr(dim, 'textPosition'):
                pos = dim.textPosition
                dim_info["text_position"] = [pos.x * 10, pos.y * 10]
        except:
            pass
            
        dimensions.append(dim_info)
    
    return {
        "sketch_id": body["sketch_id"],
        "dimension_count": len(dimensions),
        "dimensions": dimensions
    }


def handle_edit_sketch_dimension(body):
    """Edit a sketch dimension by index or ID. Can set numeric value or parameter expression."""
    sketch = get_sketch(body["sketch_id"])
    
    dim_index = body.get("dimension_index")
    dim_id = body.get("dimension_id")
    
    # Find the dimension
    dimension = None
    if dim_index is not None:
        if dim_index < sketch.sketchDimensions.count:
            dimension = sketch.sketchDimensions.item(dim_index)
    elif dim_id:
        # Parse ID like "SketchName_dim_0"
        parts = dim_id.rsplit("_dim_", 1)
        if len(parts) == 2:
            try:
                idx = int(parts[1])
                if idx < sketch.sketchDimensions.count:
                    dimension = sketch.sketchDimensions.item(idx)
            except ValueError:
                pass
    
    if not dimension:
        raise Exception(f"Dimension not found: index={dim_index}, id={dim_id}")
    
    # Get the parameter associated with this dimension
    param = dimension.parameter
    if not param:
        raise Exception("Dimension has no associated parameter")
    
    old_expression = param.expression
    old_value = dimension.value * 10  # cm to mm
    
    # Set new value - either expression (string) or numeric value
    expression = body.get("expression")
    value = body.get("value")
    
    if expression is not None:
        # Set expression (can be parameter name like "overall_width" or formula)
        param.expression = expression
    elif value is not None:
        # Set numeric value in mm
        param.expression = f"{value} mm"
    else:
        raise Exception("Must provide either 'expression' or 'value'")
    
    # Refresh to see new value
    new_value = dimension.value * 10
    
    return {
        "success": True,
        "dimension_id": f"{body['sketch_id']}_dim_{dim_index if dim_index is not None else parts[1]}",
        "old_expression": old_expression,
        "old_value_mm": old_value,
        "new_expression": param.expression,
        "new_value_mm": new_value
    }


# ============================================================================
# 3D FEATURES
# ============================================================================

def get_sketch_with_component(sketch_id, component_name=None):
    """Get a sketch, optionally from a specific component."""
    root = get_root()
    
    if component_name:
        target_component, _ = get_component_by_name(component_name)
        if target_component:
            sketch = target_component.sketches.itemByName(sketch_id)
            if sketch:
                return sketch, target_component
    
    # Try root first
    sketch = root.sketches.itemByName(sketch_id)
    if sketch:
        return sketch, root
    
    # Search all components
    for occ in root.allOccurrences:
        sketch = occ.component.sketches.itemByName(sketch_id)
        if sketch:
            return sketch, occ.component
    
    raise Exception(f"Sketch not found: {sketch_id}")


def handle_extrude(body):
    design = get_design()
    root = get_root()
    
    sketch_id = body.get("sketch_id")
    profile_index = body.get("profile_index", 0)
    distance = body.get("distance", 10) / 10.0  # mm to cm
    direction = body.get("direction", "positive")
    operation = body.get("operation", "new_body")
    component_name = body.get("component")  # Optional: specify component
    target_body_name = body.get("target_body")  # Optional: for join/cut operations
    
    # Get sketch and its component
    sketch, sketch_component = get_sketch_with_component(sketch_id, component_name)
    profile = sketch.profiles.item(profile_index)
    
    if not profile:
        raise Exception(f"Profile not found at index {profile_index}")
    
    # Use the sketch's component for the extrusion
    extrudes = sketch_component.features.extrudeFeatures
    
    # Determine initial operation
    initial_op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    if operation == "join":
        initial_op = adsk.fusion.FeatureOperations.JoinFeatureOperation
    elif operation == "cut":
        initial_op = adsk.fusion.FeatureOperations.CutFeatureOperation
    elif operation == "intersect":
        initial_op = adsk.fusion.FeatureOperations.IntersectFeatureOperation
    
    extrude_input = extrudes.createInput(profile, initial_op)
    
    # If a target body is specified for join/cut, set the participant bodies
    if target_body_name and operation in ["join", "cut", "intersect"]:
        # Find the target body in this component
        target_body = None
        for b in sketch_component.bRepBodies:
            if b.name == target_body_name:
                target_body = b
                break
        
        if target_body:
            # participantBodies expects a list of BRepBody, not ObjectCollection
            extrude_input.participantBodies = [target_body]
    
    # Set distance
    if direction == "symmetric":
        extrude_input.setSymmetricExtent(adsk.core.ValueInput.createByReal(distance), True)
    elif direction == "negative":
        extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(distance))
    else:
        extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(distance))
    
    extrude = extrudes.add(extrude_input)
    adsk.doEvents()  # Let Fusion process
    
    body_name = extrude.bodies.item(0).name if extrude.bodies.count > 0 else target_body_name
    
    return {
        "feature_id": extrude.name,
        "body_id": body_name,
        "component": sketch_component.name
    }


def handle_fillet_edges(body):
    root = get_root()
    edge_ids = body.get("edge_ids", [])
    radius = body.get("radius", 1) / 10.0  # mm to cm
    
    # Collect edges - parse IDs like "Body1_edge_0"
    edges = adsk.core.ObjectCollection.create()
    
    for edge_id in edge_ids:
        parts = edge_id.rsplit("_edge_", 1)
        if len(parts) == 2:
            body_name, edge_idx_str = parts
            try:
                edge_idx = int(edge_idx_str)
                for body_obj in root.bRepBodies:
                    if body_obj.name == body_name:
                        if edge_idx < body_obj.edges.count:
                            edges.add(body_obj.edges.item(edge_idx))
                        break
            except ValueError:
                pass
    
    if edges.count == 0:
        raise Exception(f"No matching edges found for IDs: {edge_ids}")
    
    fillets = root.features.filletFeatures
    fillet_input = fillets.createInput()
    fillet_input.addConstantRadiusEdgeSet(edges, adsk.core.ValueInput.createByReal(radius), body.get("tangent_chain", True))
    
    fillet = fillets.add(fillet_input)
    
    return {"feature_id": fillet.name}


def handle_chamfer_edges(body):
    root = get_root()
    edge_ids = body.get("edge_ids", [])
    distance = body.get("distance", 1) / 10.0  # mm to cm
    
    # Collect edges - parse IDs like "Body1_edge_0"
    edges = adsk.core.ObjectCollection.create()
    
    for edge_id in edge_ids:
        parts = edge_id.rsplit("_edge_", 1)
        if len(parts) == 2:
            body_name, edge_idx_str = parts
            try:
                edge_idx = int(edge_idx_str)
                for body_obj in root.bRepBodies:
                    if body_obj.name == body_name:
                        if edge_idx < body_obj.edges.count:
                            edges.add(body_obj.edges.item(edge_idx))
                        break
            except ValueError:
                pass
    
    if edges.count == 0:
        raise Exception(f"No matching edges found for IDs: {edge_ids}")
    
    chamfers = root.features.chamferFeatures
    chamfer_input = chamfers.createInput2()
    chamfer_input.chamferEdgeSets.addEqualDistanceChamferEdgeSet(
        edges, 
        adsk.core.ValueInput.createByReal(distance),
        True
    )
    
    chamfer = chamfers.add(chamfer_input)
    
    return {"feature_id": chamfer.name}


def find_body_by_name_with_context(root, body_name):
    """Find a body by name, returns (body, native_body, component, occurrence) tuple.
    body = proxy body (or native if in root)
    native_body = the actual body in the component
    """
    # First check root bodies
    for b in root.bRepBodies:
        if b.name == body_name:
            return (b, b, root, None)
    
    # Then check all occurrences (components)
    for occ in root.allOccurrences:
        for b in occ.component.bRepBodies:
            if b.name == body_name:
                # Return both proxy and native body
                proxy = b.createForAssemblyContext(occ)
                return (proxy, b, occ.component, occ)
    
    return (None, None, None, None)


def find_body_by_name(root, body_name):
    """Find a body by name, searching root and all component occurrences."""
    body, _, _, _ = find_body_by_name_with_context(root, body_name)
    return body


def find_bodies_by_names(root, body_names):
    """Find multiple bodies by name, returns ObjectCollection of proxy bodies."""
    bodies = adsk.core.ObjectCollection.create()
    
    # Check root bodies
    for b in root.bRepBodies:
        if b.name in body_names:
            bodies.add(b)
    
    # Check all occurrences
    for occ in root.allOccurrences:
        for b in occ.component.bRepBodies:
            if b.name in body_names:
                bodies.add(b.createForAssemblyContext(occ))
    
    return bodies


def find_native_bodies_by_names(root, body_names):
    """Find multiple bodies by name, returns list of native bodies (not proxies)."""
    bodies = []
    
    # Check root bodies
    for b in root.bRepBodies:
        if b.name in body_names:
            bodies.append(b)
    
    # Check all occurrences  
    for occ in root.allOccurrences:
        for b in occ.component.bRepBodies:
            if b.name in body_names:
                bodies.append(b)  # Native body, not proxy
    
    return bodies


def handle_delete_body(body):
    """Delete a body by name."""
    root = get_root()
    body_name = body.get("body_name")
    component_name = body.get("component")  # Optional: specify component
    
    if not body_name:
        raise Exception("body_name is required")
    
    deleted = False
    
    # If component specified, search only there
    if component_name:
        target_component, target_occ = get_component_by_name(component_name)
        if target_component:
            for b in target_component.bRepBodies:
                if b.name == body_name:
                    b.deleteMe()
                    deleted = True
                    break
    else:
        # Search root first
        for b in root.bRepBodies:
            if b.name == body_name:
                b.deleteMe()
                deleted = True
                break
        
        # If not found in root, search components
        if not deleted:
            for occ in root.allOccurrences:
                for b in occ.component.bRepBodies:
                    if b.name == body_name:
                        b.deleteMe()
                        deleted = True
                        break
                if deleted:
                    break
    
    if not deleted:
        raise Exception(f"Body not found: {body_name}")
    
    return {
        "success": True,
        "deleted_body": body_name
    }


def handle_delete_sketch(body):
    """Delete a sketch by name."""
    root = get_root()
    sketch_name = body.get("sketch_name")
    component_name = body.get("component")  # Optional: specify component
    
    if not sketch_name:
        raise Exception("sketch_name is required")
    
    deleted = False
    
    # If component specified, search only there
    if component_name:
        target_component, target_occ = get_component_by_name(component_name)
        if target_component:
            sketch = target_component.sketches.itemByName(sketch_name)
            if sketch:
                sketch.deleteMe()
                deleted = True
    else:
        # Search root first
        sketch = root.sketches.itemByName(sketch_name)
        if sketch:
            sketch.deleteMe()
            deleted = True
        
        # If not found in root, search components
        if not deleted:
            for occ in root.allOccurrences:
                sketch = occ.component.sketches.itemByName(sketch_name)
                if sketch:
                    sketch.deleteMe()
                    deleted = True
                    break
    
    if not deleted:
        raise Exception(f"Sketch not found: {sketch_name}")
    
    return {
        "success": True,
        "deleted_sketch": sketch_name
    }


def handle_boolean(body):
    root = get_root()
    design = get_design()
    operation = body.get("operation", "union")
    target_body_id = body.get("target_body")
    tool_body_ids = body.get("tool_bodies", [])
    keep_tools = body.get("keep_tools", False)
    
    # Find target body with full context info
    target_proxy, target_native, target_component, target_occ = find_body_by_name_with_context(root, target_body_id)
    
    if not target_proxy:
        raise Exception(f"Target body not found: {target_body_id}")
    
    # Find tool bodies (as proxies for assembly context)
    tool_bodies = find_bodies_by_names(root, tool_body_ids)
    
    if tool_bodies.count == 0:
        raise Exception("No tool bodies found")
    
    # Check if this is a cross-component operation
    target_in_subcomponent = target_occ is not None
    
    # For cross-component operations, we need to verify bodies intersect/touch
    # The standard combine should work for both cut and join if using proxy bodies
    
    # Use the root's combine features - this works for assembly-level operations
    combines = root.features.combineFeatures
    combine_input = combines.createInput(target_proxy, tool_bodies)
    
    if operation == "union":
        combine_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
    elif operation == "subtract":
        combine_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    elif operation == "intersect":
        combine_input.operation = adsk.fusion.FeatureOperations.IntersectFeatureOperation
    
    combine_input.isKeepToolBodies = keep_tools
    
    try:
        combine = combines.add(combine_input)
        
        return {
            "success": True,
            "result_body": target_body_id,
            "operation": operation,
            "method": "standard_combine",
            "target_component": target_occ.name if target_occ else "root",
            "cross_component": target_in_subcomponent
        }
    except Exception as e:
        # If standard combine fails for cross-component, provide helpful error
        error_msg = str(e)
        if target_in_subcomponent and operation == "union":
            error_msg += " (Cross-component unions may require bodies to be in same component. Try creating geometry directly in target component.)"
        raise Exception(error_msg)


# ============================================================================
# SELECTION & QUERY
# ============================================================================

def handle_list_bodies(body):
    root = get_root()
    component_name = body.get("component")
    include_all = body.get("include_all", True)  # Default to traversing all components
    
    bodies = []
    debug_info = {
        "version": "2.0",
        "root_body_count": root.bRepBodies.count,
        "occurrence_count": root.occurrences.count,
        "all_occurrences_count": root.allOccurrences.count
    }
    
    def add_body_info(b, comp_name="root"):
        """Add body info to the list."""
        bbox = b.boundingBox
        # Calculate dimensions from bounding box
        width = (bbox.maxPoint.x - bbox.minPoint.x) * 10  # cm to mm
        depth = (bbox.maxPoint.y - bbox.minPoint.y) * 10
        height = (bbox.maxPoint.z - bbox.minPoint.z) * 10
        
        bodies.append({
            "body_id": b.name,
            "name": b.name,
            "component": comp_name,
            "is_solid": b.isSolid,
            "volume": b.volume * 1000,  # cm³ to mm³
            "dimensions": {
                "width": round(width, 2),
                "depth": round(depth, 2),
                "height": round(height, 2)
            },
            "bounding_box": {
                "min": [round(bbox.minPoint.x * 10, 2), round(bbox.minPoint.y * 10, 2), round(bbox.minPoint.z * 10, 2)],
                "max": [round(bbox.maxPoint.x * 10, 2), round(bbox.maxPoint.y * 10, 2), round(bbox.maxPoint.z * 10, 2)]
            }
        })
    
    def traverse_occurrences(occurrences, parent_name=""):
        """Recursively traverse all occurrences to find bodies."""
        for occ in occurrences:
            comp = occ.component
            comp_full_name = f"{parent_name}/{comp.name}" if parent_name else comp.name
            
            # Filter by component name if specified
            if component_name and component_name not in comp_full_name:
                continue
            
            # Add bodies from this component
            for b in comp.bRepBodies:
                add_body_info(b, comp_full_name)
            
            # Recurse into child occurrences
            if occ.childOccurrences:
                traverse_occurrences(occ.childOccurrences, comp_full_name)
    
    # Add bodies from root component
    if not component_name or component_name == "root":
        for b in root.bRepBodies:
            add_body_info(b, "root")
    
    # Traverse ALL occurrences (flattened) for simplicity
    if include_all:
        for occ in root.allOccurrences:
            comp = occ.component
            comp_name = occ.fullPathName if hasattr(occ, 'fullPathName') else comp.name
            for b in comp.bRepBodies:
                add_body_info(b, comp_name)
    
    return {"bodies": bodies, "count": len(bodies), "debug": debug_info}


def handle_list_edges(body):
    root = get_root()
    body_id = body.get("body_id")
    filter_opts = body.get("filter", {})
    
    target_body = None
    for b in root.bRepBodies:
        if b.name == body_id:
            target_body = b
            break
    
    if not target_body:
        raise Exception(f"Body not found: {body_id}")
    
    edges = []
    for idx, edge in enumerate(target_body.edges):
        edge_type = "linear"
        radius = None
        
        geo = edge.geometry
        if hasattr(geo, 'curveType'):
            if geo.curveType == adsk.core.Curve3DTypes.Circle3DCurveType:
                edge_type = "circular"
                radius = geo.radius * 10  # cm to mm
            elif geo.curveType == adsk.core.Curve3DTypes.Arc3DCurveType:
                edge_type = "circular"
                radius = geo.radius * 10
        
        # Apply filters
        filter_type = filter_opts.get("type", "all")
        if filter_type != "all" and filter_type != edge_type:
            continue
        
        if filter_opts.get("radius_min") and radius and radius < filter_opts["radius_min"]:
            continue
        if filter_opts.get("radius_max") and radius and radius > filter_opts["radius_max"]:
            continue
        
        midpoint = edge.pointOnEdge
        
        # Use index-based ID for reliability
        edges.append({
            "edge_id": f"{body_id}_edge_{idx}",
            "type": edge_type,
            "length": edge.length * 10,  # cm to mm
            "radius": radius,
            "midpoint": [midpoint.x * 10, midpoint.y * 10, midpoint.z * 10]
        })
    
    return {"edges": edges}


def handle_list_faces(body):
    root = get_root()
    body_id = body.get("body_id")
    filter_opts = body.get("filter", {})
    
    target_body = None
    for b in root.bRepBodies:
        if b.name == body_id:
            target_body = b
            break
    
    if not target_body:
        raise Exception(f"Body not found: {body_id}")
    
    faces = []
    for idx, face in enumerate(target_body.faces):
        face_type = "unknown"
        normal = None
        
        geo = face.geometry
        if hasattr(geo, 'surfaceType'):
            if geo.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                face_type = "planar"
                normal = [geo.normal.x, geo.normal.y, geo.normal.z]
            elif geo.surfaceType == adsk.core.SurfaceTypes.CylinderSurfaceType:
                face_type = "cylindrical"
            elif geo.surfaceType == adsk.core.SurfaceTypes.SphereSurfaceType:
                face_type = "spherical"
        
        # Apply filters
        filter_type = filter_opts.get("type", "all")
        if filter_type != "all" and filter_type != face_type:
            continue
        
        centroid = face.centroid
        
        # Use index-based ID for reliability
        faces.append({
            "face_id": f"{body_id}_face_{idx}",
            "type": face_type,
            "area": face.area * 100,  # cm² to mm²
            "normal": normal,
            "centroid": [centroid.x * 10, centroid.y * 10, centroid.z * 10]
        })
    
    return {"faces": faces}


def handle_select_by_position(body):
    root = get_root()
    point = point3d([c / 10.0 for c in body["point"]])  # mm to cm
    search_type = body.get("type", "edge")
    tolerance = body.get("tolerance", 1) / 10.0  # mm to cm
    
    matches = []
    
    for b in root.bRepBodies:
        if search_type == "edge":
            for edge in b.edges:
                dist = edge.pointOnEdge.distanceTo(point)
                if dist <= tolerance:
                    matches.append({"id": edge.entityToken[:8], "distance": dist * 10})
        elif search_type == "face":
            for face in b.faces:
                dist = face.centroid.distanceTo(point)
                if dist <= tolerance:
                    matches.append({"id": face.entityToken[:8], "distance": dist * 10})
        elif search_type == "body":
            bbox = b.boundingBox
            if (bbox.minPoint.x <= point.x <= bbox.maxPoint.x and
                bbox.minPoint.y <= point.y <= bbox.maxPoint.y and
                bbox.minPoint.z <= point.z <= bbox.maxPoint.z):
                matches.append({"id": b.name, "distance": 0})
    
    return {"matches": matches}


# ============================================================================
# TRANSFORM OPERATIONS
# ============================================================================

def handle_copy_body(body):
    root = get_root()
    body_id = body.get("body_id")
    new_name = body.get("name")
    
    source_body = None
    for b in root.bRepBodies:
        if b.name == body_id:
            source_body = b
            break
    
    if not source_body:
        raise Exception(f"Body not found: {body_id}")
    
    # Use copy/paste
    copy_features = root.features.copyPasteBodies
    bodies_to_copy = adsk.core.ObjectCollection.create()
    bodies_to_copy.add(source_body)
    
    copy_feature = copy_features.add(bodies_to_copy)
    new_body = copy_feature.bodies.item(0)
    
    if new_name:
        new_body.name = new_name
    
    return {
        "body_id": new_body.name,
        "name": new_body.name
    }


def handle_move_body(body):
    root = get_root()
    body_id = body.get("body_id")
    translation = body.get("translation")
    rotation = body.get("rotation")
    
    target_body = None
    for b in root.bRepBodies:
        if b.name == body_id:
            target_body = b
            break
    
    if not target_body:
        raise Exception(f"Body not found: {body_id}")
    
    move_features = root.features.moveFeatures
    bodies = adsk.core.ObjectCollection.create()
    bodies.add(target_body)
    
    move_input = move_features.createInput2(bodies)
    
    transform = adsk.core.Matrix3D.create()
    
    if translation:
        t = [c / 10.0 for c in translation]  # mm to cm
        transform.translation = adsk.core.Vector3D.create(t[0], t[1], t[2])
    
    if rotation:
        axis = vector3d(rotation.get("axis", [0, 0, 1]))
        angle = rotation.get("angle", 0) * 3.14159265359 / 180.0  # deg to rad
        origin = point3d([c / 10.0 for c in rotation.get("origin", [0, 0, 0])])
        transform.setToRotation(angle, axis, origin)
    
    move_input.defineAsFreeMove(transform)
    
    move_features.add(move_input)
    
    return {"success": True}


def handle_mirror_body(body):
    root = get_root()
    body_id = body.get("body_id")
    plane_id = body.get("plane", "xy")
    
    target_body = None
    for b in root.bRepBodies:
        if b.name == body_id:
            target_body = b
            break
    
    if not target_body:
        raise Exception(f"Body not found: {body_id}")
    
    # Get plane
    if plane_id == "xy":
        plane = root.xYConstructionPlane
    elif plane_id == "xz":
        plane = root.xZConstructionPlane
    elif plane_id == "yz":
        plane = root.yZConstructionPlane
    else:
        plane = root.constructionPlanes.itemByName(plane_id)
    
    if not plane:
        raise Exception(f"Plane not found: {plane_id}")
    
    mirror_features = root.features.mirrorFeatures
    bodies = adsk.core.ObjectCollection.create()
    bodies.add(target_body)
    
    mirror_input = mirror_features.createInput(bodies, plane)
    mirror = mirror_features.add(mirror_input)
    
    new_body = mirror.bodies.item(0)
    
    return {
        "body_id": new_body.name,
        "name": new_body.name
    }


def handle_pattern_rectangular(body):
    root = get_root()
    body_id = body.get("body_id")
    
    target_body = None
    for b in root.bRepBodies:
        if b.name == body_id:
            target_body = b
            break
    
    if not target_body:
        raise Exception(f"Body not found: {body_id}")
    
    direction1 = vector3d(body.get("direction1", [1, 0, 0]))
    count1 = body.get("count1", 2)
    spacing1 = body.get("spacing1", 10) / 10.0  # mm to cm
    
    direction2 = body.get("direction2")
    count2 = body.get("count2", 1)
    spacing2 = body.get("spacing2", 10) / 10.0 if body.get("spacing2") else spacing1
    
    pattern_features = root.features.rectangularPatternFeatures
    bodies = adsk.core.ObjectCollection.create()
    bodies.add(target_body)
    
    # Create a construction axis for direction
    # For simplicity, using X/Y/Z axes
    if direction1.x == 1:
        axis1 = root.xConstructionAxis
    elif direction1.y == 1:
        axis1 = root.yConstructionAxis
    else:
        axis1 = root.zConstructionAxis
    
    pattern_input = pattern_features.createInput(
        bodies,
        axis1,
        adsk.core.ValueInput.createByReal(count1),
        adsk.core.ValueInput.createByReal(spacing1),
        adsk.fusion.PatternDistanceType.SpacingPatternDistanceType
    )
    
    if direction2:
        if direction2[0] == 1:
            axis2 = root.xConstructionAxis
        elif direction2[1] == 1:
            axis2 = root.yConstructionAxis
        else:
            axis2 = root.zConstructionAxis
        
        pattern_input.setDirectionTwo(
            axis2,
            adsk.core.ValueInput.createByReal(count2),
            adsk.core.ValueInput.createByReal(spacing2)
        )
    
    pattern = pattern_features.add(pattern_input)
    
    body_ids = [b.name for b in pattern.bodies]
    
    return {
        "feature_id": pattern.name,
        "body_ids": body_ids
    }


# ============================================================================
# PARAMETERS
# ============================================================================

def handle_create_parameter(body):
    design = get_design()
    params = design.userParameters
    
    name = body.get("name")
    value = body.get("value", 0)
    unit = body.get("unit", "mm")
    comment = body.get("comment", "")
    
    value_input = adsk.core.ValueInput.createByString(f"{value} {unit}")
    param = params.add(name, value_input, unit, comment)
    
    return {"parameter_id": param.name}


def handle_modify_parameter(body):
    design = get_design()
    params = design.userParameters
    
    name = body.get("name")
    value = body.get("value")
    
    param = params.itemByName(name)
    if not param:
        raise Exception(f"Parameter not found: {name}")
    
    param.value = value / 10.0  # mm to cm (internal units)
    
    # Get affected features (simplified - just return count)
    return {
        "success": True,
        "affected_features": []
    }


def handle_list_parameters(body):
    design = get_design()
    params = design.userParameters
    
    result = []
    for param in params:
        result.append({
            "name": param.name,
            "value": param.value * 10,  # cm to mm
            "unit": param.unit,
            "comment": param.comment
        })
    
    return {"parameters": result}


# ============================================================================
# APPEARANCE
# ============================================================================

def handle_apply_appearance(body):
    global app
    design = get_design()
    root = get_root()
    
    body_id = body.get("body_id")
    appearance_name = body.get("appearance")
    
    target_body = None
    for b in root.bRepBodies:
        if b.name == body_id:
            target_body = b
            break
    
    if not target_body:
        raise Exception(f"Body not found: {body_id}")
    
    # Search for appearance in libraries
    appearance = None
    for lib in app.materialLibraries:
        for appear in lib.appearances:
            if appear.name == appearance_name:
                appearance = appear
                break
        if appearance:
            break
    
    if not appearance:
        raise Exception(f"Appearance not found: {appearance_name}")
    
    target_body.appearance = appearance
    
    return {"success": True}


def handle_list_appearances(body):
    global app
    category = body.get("category")
    
    appearances = []
    for lib in app.materialLibraries:
        for appear in lib.appearances:
            # Simple category detection based on name
            appear_category = "Other"
            name_lower = appear.name.lower()
            if "wood" in name_lower or "oak" in name_lower or "walnut" in name_lower or "maple" in name_lower:
                appear_category = "Wood"
            elif "metal" in name_lower or "steel" in name_lower or "aluminum" in name_lower:
                appear_category = "Metal"
            elif "plastic" in name_lower:
                appear_category = "Plastic"
            
            if category and appear_category != category:
                continue
            
            appearances.append({
                "name": appear.name,
                "category": appear_category
            })
    
    return {"appearances": appearances[:50]}  # Limit to 50


# ============================================================================
# CUSTOM EVENT HANDLER FOR MAIN THREAD OPERATIONS
# ============================================================================

class CommandEventHandler(adsk.core.CustomEventHandler):
    """Handles ALL commands on the main thread for thread safety."""
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        global pending_command, pending_body, command_result, command_ready
        
        try:
            handler = ROUTES.get(pending_command)
            if handler:
                command_result = handler(pending_body)
            else:
                command_result = {"error": True, "message": f"Unknown command: {pending_command}"}
        except Exception as e:
            command_result = {
                "error": True,
                "message": str(e),
                "traceback": traceback.format_exc()
            }
        finally:
            command_ready.set()


# ============================================================================
# UTILITY
# ============================================================================

def handle_take_screenshot(body):
    global app
    
    try:
        width = body.get("width", 800)
        height = body.get("height", 600)
        view_preset = body.get("view")
        
        temp_path = os.path.join(tempfile.gettempdir(), "fusion_screenshot.png")
        
        viewport = app.activeViewport
        if not viewport:
            return {"error": True, "message": "No active viewport"}
        
        # Set view if requested
        if view_preset and view_preset != "current":
            try:
                camera = viewport.camera
                orientations = {
                    "top": adsk.core.ViewOrientations.TopViewOrientation,
                    "bottom": adsk.core.ViewOrientations.BottomViewOrientation,
                    "front": adsk.core.ViewOrientations.FrontViewOrientation,
                    "back": adsk.core.ViewOrientations.BackViewOrientation,
                    "left": adsk.core.ViewOrientations.LeftViewOrientation,
                    "right": adsk.core.ViewOrientations.RightViewOrientation,
                    "isometric": adsk.core.ViewOrientations.IsoTopRightViewOrientation,
                }
                if view_preset in orientations:
                    camera.viewOrientation = orientations[view_preset]
                    camera.isFitView = True
                    viewport.camera = camera
                    adsk.doEvents()
            except:
                pass
        
        # Save the image
        success = viewport.saveAsImageFile(temp_path, width, height)
        
        if not success or not os.path.exists(temp_path):
            return {"error": True, "message": "Failed to save screenshot"}
        
        with open(temp_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        try:
            os.remove(temp_path)
        except:
            pass
        
        return {
            "image_base64": image_data,
            "format": "png"
        }
    except Exception as e:
        return {
            "error": True,
            "message": f"Screenshot failed: {str(e)}",
            "traceback": traceback.format_exc()
        }


def handle_set_view(body):
    global app
    
    try:
        preset = body.get("preset", "isometric")
        fit = body.get("fit", True)
        
        viewport = app.activeViewport
        if not viewport:
            return {"error": True, "message": "No active viewport"}
        
        camera = viewport.camera
        
        orientations = {
            "top": adsk.core.ViewOrientations.TopViewOrientation,
            "bottom": adsk.core.ViewOrientations.BottomViewOrientation,
            "front": adsk.core.ViewOrientations.FrontViewOrientation,
            "back": adsk.core.ViewOrientations.BackViewOrientation,
            "left": adsk.core.ViewOrientations.LeftViewOrientation,
            "right": adsk.core.ViewOrientations.RightViewOrientation,
            "isometric": adsk.core.ViewOrientations.IsoTopRightViewOrientation,
        }
        
        if preset in orientations:
            camera.viewOrientation = orientations[preset]
        
        if fit:
            camera.isFitView = True
        
        viewport.camera = camera
        
        return {"success": True}
    except Exception as e:
        return {
            "error": True,
            "message": f"Set view failed: {str(e)}"
        }


def handle_undo(body):
    global app
    design = get_design()
    
    # Use the fusion undo manager via the design
    if design.timeline.count > 0:
        # Suppress the last feature as a workaround
        last_item = design.timeline.item(design.timeline.count - 1)
        last_name = last_item.name if hasattr(last_item, 'name') else "unknown"
        last_item.isSuppressed = True
        return {"success": True, "undone_feature": last_name}
    return {"success": False, "message": "Nothing to undo"}


def handle_redo(body):
    global app
    design = get_design()
    
    # Find first suppressed item and unsuppress it
    for i in range(design.timeline.count):
        item = design.timeline.item(i)
        if item.isSuppressed:
            item.isSuppressed = False
            return {"success": True}
    return {"success": False, "message": "Nothing to redo"}


def handle_get_timeline(body):
    design = get_design()
    timeline = design.timeline
    
    features = []
    for i in range(timeline.count):
        try:
            item = timeline.item(i)
            name = "unknown"
            entity_type = "unknown"
            suppressed = False
            
            try:
                name = item.name
            except:
                name = f"Item_{i}"
            
            try:
                entity_type = item.entity.objectType
            except:
                pass
            
            try:
                suppressed = item.isSuppressed
            except:
                pass
            
            features.append({
                "index": i,
                "name": name,
                "type": entity_type,
                "suppressed": suppressed
            })
        except:
            features.append({
                "index": i,
                "name": f"Item_{i}",
                "type": "unknown",
                "suppressed": False
            })
    
    return {"features": features}


def handle_get_feature_parameters(body):
    """Get all editable parameters for a feature by name or timeline index."""
    design = get_design()
    timeline = design.timeline
    
    feature_name = body.get("feature_name")
    feature_index = body.get("feature_index")
    
    # Find the feature
    feature = None
    timeline_item = None
    
    if feature_index is not None:
        if feature_index < timeline.count:
            timeline_item = timeline.item(feature_index)
            feature = timeline_item.entity
    elif feature_name:
        for i in range(timeline.count):
            item = timeline.item(i)
            try:
                if item.name == feature_name:
                    timeline_item = item
                    feature = item.entity
                    break
            except:
                pass
    
    if not feature:
        raise Exception(f"Feature not found: name={feature_name}, index={feature_index}")
    
    result = {
        "feature_name": timeline_item.name if timeline_item else "unknown",
        "feature_type": feature.objectType if feature else "unknown",
        "parameters": []
    }
    
    # Extract parameters based on feature type
    try:
        # For extrude features
        if hasattr(feature, 'extentOne'):
            extent = feature.extentOne
            if hasattr(extent, 'distance'):
                dist_param = extent.distance
                result["parameters"].append({
                    "name": "distance",
                    "type": "extent",
                    "value_mm": dist_param.value * 10,
                    "expression": dist_param.expression if hasattr(dist_param, 'expression') else None
                })
        
        # For general parametric features, try to get all parameters
        if hasattr(feature, 'parameters'):
            for param in feature.parameters:
                result["parameters"].append({
                    "name": param.name,
                    "value": param.value * 10 if param.unit == "cm" else param.value,
                    "expression": param.expression,
                    "unit": param.unit
                })
    except Exception as e:
        result["error"] = str(e)
    
    # Also check for model parameters that reference this feature
    try:
        all_params = design.allParameters
        feature_params = []
        for param in all_params:
            try:
                if timeline_item.name in param.name or timeline_item.name in (param.expression or ""):
                    feature_params.append({
                        "name": param.name,
                        "value": param.value * 10 if "mm" in (param.unit or "") or param.unit == "cm" else param.value,
                        "expression": param.expression,
                        "unit": param.unit
                    })
            except:
                pass
        if feature_params:
            result["related_parameters"] = feature_params
    except:
        pass
    
    return result


def handle_edit_feature_parameter(body):
    """Edit a feature's parameter by setting expression or value."""
    design = get_design()
    timeline = design.timeline
    
    feature_name = body.get("feature_name")
    feature_index = body.get("feature_index")
    param_name = body.get("parameter_name", "distance")  # Default to distance for extrudes
    expression = body.get("expression")
    value = body.get("value")
    
    # Find the feature
    feature = None
    timeline_item = None
    
    if feature_index is not None:
        if feature_index < timeline.count:
            timeline_item = timeline.item(feature_index)
            feature = timeline_item.entity
    elif feature_name:
        for i in range(timeline.count):
            item = timeline.item(i)
            try:
                if item.name == feature_name:
                    timeline_item = item
                    feature = item.entity
                    break
            except:
                pass
    
    if not feature:
        raise Exception(f"Feature not found: name={feature_name}, index={feature_index}")
    
    # Try to edit the parameter
    old_value = None
    old_expression = None
    new_value = None
    
    try:
        # Handle extrude features specially
        if hasattr(feature, 'extentOne') and param_name == "distance":
            extent = feature.extentOne
            if hasattr(extent, 'distance'):
                dist_param = extent.distance
                old_expression = dist_param.expression if hasattr(dist_param, 'expression') else str(dist_param.value)
                old_value = dist_param.value * 10
                
                # Set new value
                if expression is not None:
                    dist_param.expression = expression
                elif value is not None:
                    dist_param.expression = f"{value} mm"
                
                new_value = dist_param.value * 10
        
        # For other features, try via model parameters
        else:
            all_params = design.allParameters
            for param in all_params:
                if param_name in param.name:
                    old_expression = param.expression
                    old_value = param.value * 10 if param.unit == "cm" else param.value
                    
                    if expression is not None:
                        param.expression = expression
                    elif value is not None:
                        param.expression = f"{value} mm"
                    
                    new_value = param.value * 10 if param.unit == "cm" else param.value
                    break
        
        if old_value is None:
            raise Exception(f"Parameter '{param_name}' not found on feature")
            
    except Exception as e:
        raise Exception(f"Failed to edit parameter: {str(e)}")
    
    return {
        "success": True,
        "feature_name": timeline_item.name if timeline_item else feature_name,
        "parameter_name": param_name,
        "old_expression": old_expression,
        "old_value_mm": old_value,
        "new_expression": expression if expression else f"{value} mm",
        "new_value_mm": new_value
    }


def handle_list_all_parameters(body):
    """List ALL parameters in the model (user + model parameters)."""
    design = get_design()
    
    result = {
        "user_parameters": [],
        "model_parameters": []
    }
    
    # User parameters
    for param in design.userParameters:
        result["user_parameters"].append({
            "name": param.name,
            "value": param.value * 10 if param.unit == "cm" else param.value,
            "expression": param.expression,
            "unit": param.unit,
            "comment": param.comment
        })
    
    # Model parameters (from features)
    include_model = body.get("include_model_parameters", False)
    if include_model:
        try:
            for param in design.allParameters:
                # Skip user parameters (already listed)
                is_user = False
                for up in design.userParameters:
                    if up.name == param.name:
                        is_user = True
                        break
                
                if not is_user:
                    result["model_parameters"].append({
                        "name": param.name,
                        "value": param.value * 10 if param.unit == "cm" else param.value,
                        "expression": param.expression,
                        "unit": param.unit
                    })
        except:
            pass
    
    result["user_count"] = len(result["user_parameters"])
    result["model_count"] = len(result["model_parameters"]) if include_model else "not requested"
    
    return result


def handle_export(body):
    design = get_design()
    export_mgr = design.exportManager
    
    fmt = body.get("format", "stl")
    path = body.get("path")
    
    if not path:
        raise Exception("Export path is required")
    
    if fmt == "stl":
        options = export_mgr.createSTLExportOptions(design.rootComponent)
        options.filename = path
        refinement = body.get("options", {}).get("refinement", "medium")
        if refinement == "low":
            options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementLow
        elif refinement == "high":
            options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
        else:
            options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
    elif fmt == "step":
        options = export_mgr.createSTEPExportOptions(path)
    elif fmt == "iges":
        options = export_mgr.createIGESExportOptions(path)
    elif fmt == "f3d":
        options = export_mgr.createFusionArchiveExportOptions(path)
    else:
        raise Exception(f"Unsupported format: {fmt}")
    
    export_mgr.execute(options)
    
    file_size = os.path.getsize(path) if os.path.exists(path) else 0
    
    return {
        "success": True,
        "path": path,
        "file_size": file_size
    }


# ============================================================================
# WORKSPACE SWITCHING
# ============================================================================

def handle_switch_workspace(body):
    """Switch to a different workspace (Design, Manufacture, etc.)."""
    global app, ui
    
    workspace_name = body.get("workspace", "manufacture")
    
    # Map friendly names to workspace IDs
    workspace_ids = {
        "design": "FusionSolidEnvironment",
        "manufacture": "CAMEnvironment",
        "cam": "CAMEnvironment",
        "render": "RenderEnvironment",
        "animation": "AnimationEnvironment",
        "simulation": "SimulationEnvironment",
        "drawing": "FusionDrawingEnvironment",
    }
    
    workspace_id = workspace_ids.get(workspace_name.lower())
    if not workspace_id:
        raise Exception(f"Unknown workspace: {workspace_name}. Valid options: {list(workspace_ids.keys())}")
    
    # Find and activate the workspace
    workspace = ui.workspaces.itemById(workspace_id)
    if not workspace:
        raise Exception(f"Workspace not found: {workspace_id}")
    
    workspace.activate()
    adsk.doEvents()
    
    return {
        "success": True,
        "workspace": workspace_name,
        "workspace_id": workspace_id
    }


# ============================================================================
# CAM OPERATIONS
# ============================================================================

def get_cam():
    """Get CAM product - must be in Manufacturing workspace."""
    global app
    
    # Try to get CAM from active product first (when in Manufacturing workspace)
    cam = adsk.cam.CAM.cast(app.activeProduct)
    if cam:
        return cam
    
    # Try to get from document products
    doc = app.activeDocument
    if doc:
        for product in doc.products:
            if product.productType == 'CAMProductType':
                return adsk.cam.CAM.cast(product)
    
    raise Exception("CAM not available. Switch to Manufacturing workspace first.")


def handle_cam_list_setups(body):
    """List all CAM setups."""
    cam = get_cam()
    
    setups = []
    for setup in cam.setups:
        setup_info = {
            "name": setup.name,
            "operation_count": setup.allOperations.count,
        }
        try:
            setup_info["setup_type"] = str(setup.operationType)
        except:
            setup_info["setup_type"] = "unknown"
        try:
            setup_info["is_valid"] = setup.isValid
        except:
            pass
        
        # List all parameters for debugging
        if body.get("show_params"):
            param_list = []
            try:
                for param in setup.parameters:
                    param_list.append({
                        "name": param.name,
                        "expression": param.expression if hasattr(param, 'expression') else str(param.value)
                    })
            except:
                pass
            setup_info["parameters"] = param_list[:50]  # Limit
            
        setups.append(setup_info)
    
    return {"setups": setups}


def handle_cam_create_setup(body):
    """Create a new CAM setup."""
    cam = get_cam()
    root = get_root()
    
    name = body.get("name", "Setup")
    
    # Create setup 
    setups = cam.setups
    setup_input = setups.createInput(adsk.cam.OperationTypes.MillingOperation)
    
    setup = setups.add(setup_input)
    setup.name = name
    
    # Configure parameters
    try:
        params = setup.parameters
        
        # Fix WCS orientation - flip Z to point up correctly
        flip_z = params.itemByName("wcs_orientation_flipZ")
        if flip_z:
            flip_z.expression = "true"
        
        # Stock offsets
        stock_offset = body.get("stock_offset", 2)
        stock_top = body.get("stock_top", 4)
        
        stock_side_param = params.itemByName("job_stockOffsetSides")
        if stock_side_param:
            stock_side_param.expression = f"{stock_offset} mm"
        
        stock_top_param = params.itemByName("job_stockOffsetTop") 
        if stock_top_param:
            stock_top_param.expression = f"{stock_top} mm"
            
        stock_bottom_param = params.itemByName("job_stockOffsetBottom")
        if stock_bottom_param:
            stock_bottom_param.expression = "0 mm"
            
    except Exception as e:
        pass
    
    return {
        "setup_id": setup.name,
        "name": setup.name,
        "message": "Setup created with corrected WCS orientation."
    }


def handle_cam_fix_setup(body):
    """Fix WCS orientation on existing setup."""
    cam = get_cam()
    
    setup_name = body.get("setup")
    setup = None
    
    for s in cam.setups:
        if s.name == setup_name:
            setup = s
            break
    
    if not setup:
        raise Exception(f"Setup not found: {setup_name}")
    
    params = setup.parameters
    changes = []
    
    # Flip Z axis
    flip_z = params.itemByName("wcs_orientation_flipZ")
    if flip_z:
        flip_z.expression = "true"
        changes.append("Flipped Z axis")
    
    # Set stock offsets if provided
    if body.get("stock_offset"):
        offset = body.get("stock_offset")
        stock_side = params.itemByName("job_stockOffsetSides")
        if stock_side:
            stock_side.expression = f"{offset} mm"
            changes.append(f"Stock side offset: {offset}mm")
    
    if body.get("stock_top"):
        top = body.get("stock_top")
        stock_top = params.itemByName("job_stockOffsetTop")
        if stock_top:
            stock_top.expression = f"{top} mm"
            changes.append(f"Stock top offset: {top}mm")
    
    return {
        "success": True,
        "setup": setup_name,
        "changes": changes
    }


def handle_cam_list_tools(body):
    """List available tools from tool library."""
    cam = get_cam()
    
    tool_type = body.get("type")  # flat_end, ball_end, bull_nose, v_bit, drill
    
    tools = []
    
    # Access tool library
    lib_mgr = cam.toolLibraries
    
    # Get local tool library
    tool_libs = lib_mgr.toolLibraries
    if tool_libs.count > 0:
        lib = tool_libs.item(0)
        
        for i in range(min(lib.count, 50)):  # Limit to 50 tools
            tool = lib.item(i)
            
            tool_info = {
                "name": tool.description,
                "type": str(tool.type),
                "diameter": tool.diameter * 10,  # cm to mm
                "number": tool.number
            }
            
            # Filter by type if specified
            if tool_type:
                if tool_type == "flat_end" and tool.type != adsk.cam.ToolTypes.FlatEndMillTool:
                    continue
                elif tool_type == "ball_end" and tool.type != adsk.cam.ToolTypes.BallEndMillTool:
                    continue
            
            tools.append(tool_info)
    
    return {"tools": tools}


def handle_cam_create_2d_contour(body):
    """Create a 2D contour toolpath with auto geometry selection."""
    cam = get_cam()
    root = get_root()
    
    setup_name = body.get("setup")
    setup = None
    
    if setup_name:
        for s in cam.setups:
            if s.name == setup_name:
                setup = s
                break
        if not setup:
            raise Exception(f"Setup not found: {setup_name}")
    else:
        if cam.setups.count > 0:
            setup = cam.setups.item(cam.setups.count - 1)
    
    if not setup:
        raise Exception("No setup available. Create a setup first.")
    
    # Create 2D contour operation
    op_input = setup.operations.createInput('contour2d')
    op = setup.operations.add(op_input)
    
    op_name = body.get("name", "2D Contour")
    op.name = op_name
    
    # Try to auto-select bottom edges of all bodies
    edges_selected = 0
    try:
        # Get the cadcontours2dchain input
        chain_input = op.chainSelections
        if chain_input:
            # Collect bottom edges from all bodies
            edges = adsk.core.ObjectCollection.create()
            for b in root.bRepBodies:
                for edge in b.edges:
                    # Get edge midpoint Z coordinate
                    midpt = edge.pointOnEdge
                    # Select edges near Z=0 (bottom of model)
                    if abs(midpt.z) < 0.1:  # Within 1mm of Z=0
                        edges.add(edge)
                        edges_selected += 1
            
            if edges.count > 0:
                # Create chain selection
                for i in range(edges.count):
                    chain_input.add(edges.item(i))
    except Exception as e:
        pass
    
    # Set parameters
    depth = body.get("depth", 8)
    try:
        params = op.parameters
        
        # Try to set machining boundary to silhouette (auto-detect)
        silhouette_param = params.itemByName("machiningBoundary")
        if silhouette_param:
            silhouette_param.expression = "'silhouette'"
            
        # Set depth
        bottom_offset = params.itemByName("bottomHeight_offset")
        if bottom_offset:
            bottom_offset.expression = f"-{depth} mm"
            
    except:
        pass
    
    return {
        "operation_id": op.name,
        "name": op.name,
        "edges_selected": edges_selected,
        "message": "Operation created. Generate toolpath to continue."
    }


def handle_cam_create_2d_pocket(body):
    """Create a 2D pocket toolpath."""
    cam = get_cam()
    
    setup_name = body.get("setup")
    if setup_name:
        setup = None
        for s in cam.setups:
            if s.name == setup_name:
                setup = s
                break
        if not setup:
            raise Exception(f"Setup not found: {setup_name}")
    else:
        setup = cam.activeSetup or cam.setups.item(0)
    
    if not setup:
        raise Exception("No setup available. Create a setup first.")
    
    ops = setup.operations
    op_input = ops.createInput('pocket2d')
    
    op_input.displayName = body.get("name", "2D Pocket")
    
    depth = body.get("depth")
    if depth:
        op_input.parameters.itemByName("bottomHeight").expression = f"-{depth} mm"
    
    op = ops.add(op_input)
    
    future = cam.generateToolpath(op)
    
    return {
        "operation_id": op.name,
        "name": op.name
    }


def handle_cam_create_engrave(body):
    """Create an engrave toolpath."""
    cam = get_cam()
    
    setup_name = body.get("setup")
    if setup_name:
        setup = None
        for s in cam.setups:
            if s.name == setup_name:
                setup = s
                break
        if not setup:
            raise Exception(f"Setup not found: {setup_name}")
    else:
        setup = cam.activeSetup or cam.setups.item(0)
    
    if not setup:
        raise Exception("No setup available. Create a setup first.")
    
    ops = setup.operations
    op_input = ops.createInput('engrave')
    
    op_input.displayName = body.get("name", "Engrave")
    
    depth = body.get("depth", 0.5)
    op_input.parameters.itemByName("tolerance").expression = "0.01 mm"
    
    op = ops.add(op_input)
    
    future = cam.generateToolpath(op)
    
    return {
        "operation_id": op.name,
        "name": op.name
    }


def handle_cam_generate_all(body):
    """Generate all toolpaths."""
    cam = get_cam()
    
    setup_name = body.get("setup")
    setup = None
    
    if setup_name:
        for s in cam.setups:
            if s.name == setup_name:
                setup = s
                break
        if not setup:
            raise Exception(f"Setup not found: {setup_name}")
    
    try:
        if setup:
            future = cam.generateToolpath(setup)
        else:
            future = cam.generateAllToolpaths(True)
        
        # Wait for generation with timeout
        timeout = 60  # seconds
        start = time.time()
        while not future.isGenerationCompleted:
            if time.time() - start > timeout:
                return {"success": False, "message": "Generation timed out"}
            adsk.doEvents()
            time.sleep(0.2)
        
        return {
            "success": True,
            "operations_generated": future.numberOfOperations,
            "message": "Toolpaths generated successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Generation failed: {str(e)}. Ensure geometry is selected for operations."
        }


def handle_cam_post_process(body):
    """Post process toolpaths to G-code."""
    cam = get_cam()
    
    output_path = body.get("output_path")
    if not output_path:
        raise Exception("output_path is required")
    
    setup_name = body.get("setup")
    post_name = body.get("post_processor", "fanuc")  # Default to FANUC
    
    # Get setup
    if setup_name:
        setup = None
        for s in cam.setups:
            if s.name == setup_name:
                setup = s
                break
        if not setup:
            raise Exception(f"Setup not found: {setup_name}")
    else:
        setup = cam.activeSetup or cam.setups.item(0)
    
    if not setup:
        raise Exception("No setup available")
    
    # Get all operations
    operations = adsk.core.ObjectCollection.create()
    for op in setup.allOperations:
        if op.hasToolpath:
            operations.add(op)
    
    if operations.count == 0:
        raise Exception("No operations with toolpaths to post-process")
    
    # Create post input
    post_input = adsk.cam.PostProcessInput.create(
        output_path,
        post_name,
        "",  # Program name
        ""   # Program comment
    )
    post_input.isOpenInEditor = False
    
    # Post process
    cam.postProcess(setup, post_input)
    
    return {
        "success": True,
        "output_path": output_path,
        "operations_posted": operations.count
    }


def handle_cam_list_operations(body):
    """List all operations in a setup."""
    cam = get_cam()
    
    setup_name = body.get("setup")
    setup = None
    
    if setup_name:
        for s in cam.setups:
            if s.name == setup_name:
                setup = s
                break
        if not setup:
            raise Exception(f"Setup not found: {setup_name}")
    else:
        if cam.setups.count > 0:
            setup = cam.setups.item(0)
    
    if not setup:
        return {"operations": []}
    
    operations = []
    for op in setup.allOperations:
        op_info = {
            "name": op.name,
            "has_toolpath": op.hasToolpath,
            "is_suppressed": op.isSuppressed
        }
        try:
            op_info["strategy"] = op.strategy
        except:
            pass
        try:
            op_info["state"] = str(op.operationState)
        except:
            pass
        
        # Show parameters if requested
        if body.get("show_params"):
            param_list = []
            try:
                for param in op.parameters:
                    param_list.append({
                        "name": param.name,
                        "expression": param.expression if hasattr(param, 'expression') else str(param.value)
                    })
            except:
                pass
            op_info["parameters"] = param_list[:100]
            
        operations.append(op_info)
    
    return {"operations": operations}


def handle_cam_select_silhouette(body):
    """Set an operation to use silhouette (auto) geometry selection."""
    cam = get_cam()
    
    op_name = body.get("operation")
    if not op_name:
        raise Exception("Operation name required")
    
    # Find the operation
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
        
        # Set machining boundary to silhouette
        for param_name in ["machiningBoundary", "contour_mode", "boundaryMode"]:
            p = params.itemByName(param_name)
            if p:
                p.expression = "'silhouette'"
                changes.append(f"Set {param_name} to silhouette")
                break
                
        # Set bottom height mode
        bottom_mode = params.itemByName("bottomHeight_mode")
        if bottom_mode:
            bottom_mode.expression = "'model bottom'"
            changes.append("Set bottom to model bottom")
            
    except Exception as e:
        changes.append(f"Error: {str(e)}")
    
    return {
        "operation": op_name,
        "changes": changes
    }


def handle_cam_simulate(body):
    """Simulate a toolpath operation."""
    cam = get_cam()
    
    setup_name = body.get("setup")
    if setup_name:
        setup = None
        for s in cam.setups:
            if s.name == setup_name:
                setup = s
                break
        if not setup:
            raise Exception(f"Setup not found: {setup_name}")
    else:
        setup = cam.activeSetup or cam.setups.item(0)
    
    if not setup:
        raise Exception("No setup available")
    
    # Start simulation
    cam.startSimulation(setup)
    
    return {"success": True, "message": "Simulation started"}


# ============================================================================
# DELETE SKETCH
# ============================================================================

def handle_delete_sketch(body):
    """Delete a sketch by name."""
    root = get_root()
    
    sketch_name = body.get("sketch_name")
    if not sketch_name:
        raise Exception("sketch_name is required")
    
    deleted = []
    # Find and delete all sketches with this name
    sketches_to_delete = []
    for sketch in root.sketches:
        if sketch.name == sketch_name or sketch.name.startswith(sketch_name + " ("):
            sketches_to_delete.append(sketch)
    
    for sketch in sketches_to_delete:
        name = sketch.name
        sketch.deleteMe()
        deleted.append(name)
    
    adsk.doEvents()
    
    return {
        "success": True,
        "deleted": deleted,
        "count": len(deleted)
    }


# ============================================================================
# SVG & TEXT IMPORT
# ============================================================================

def handle_import_svg(body):
    """Import an SVG file into a sketch on a face or plane."""
    root = get_root()
    
    svg_path = body.get("svg_path")
    if not svg_path:
        raise Exception("svg_path is required")
    
    if not os.path.exists(svg_path):
        raise Exception(f"SVG file not found: {svg_path}")
    
    # Get target - either a face on a body or a plane
    target_face = None
    body_id = body.get("body_id")
    face_index = body.get("face_index", 0)  # Default to first face
    plane_id = body.get("plane")
    
    if body_id:
        # Find the body and get the specified face
        for b in root.bRepBodies:
            if b.name == body_id:
                # Find a planar face (top face usually)
                planar_faces = []
                for i, face in enumerate(b.faces):
                    geo = face.geometry
                    if hasattr(geo, 'surfaceType') and geo.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                        # Check if it's a top face (normal pointing up in Z)
                        if hasattr(geo, 'normal') and abs(geo.normal.z) > 0.9:
                            planar_faces.append((i, face, geo.normal.z))
                
                # Sort by Z normal to get top face (positive Z)
                planar_faces.sort(key=lambda x: x[2], reverse=True)
                
                if face_index < len(planar_faces):
                    target_face = planar_faces[face_index][1]
                elif len(planar_faces) > 0:
                    target_face = planar_faces[0][1]
                else:
                    raise Exception(f"No planar faces found on body: {body_id}")
                break
        
        if not target_face:
            raise Exception(f"Body not found: {body_id}")
    elif plane_id:
        # Use a construction plane
        if plane_id == "xy":
            target_face = root.xYConstructionPlane
        elif plane_id == "xz":
            target_face = root.xZConstructionPlane
        elif plane_id == "yz":
            target_face = root.yZConstructionPlane
        else:
            target_face = root.constructionPlanes.itemByName(plane_id)
        
        if not target_face:
            raise Exception(f"Plane not found: {plane_id}")
    else:
        raise Exception("Either body_id or plane is required")
    
    # Create a sketch on the target
    sketches = root.sketches
    sketch = sketches.add(target_face)
    
    # Set sketch name if provided
    sketch_name = body.get("sketch_name", "SVG_Import")
    sketch.name = sketch_name
    
    # Import the SVG
    # Position offset in cm (convert from mm)
    x_offset = body.get("x_offset", 0) / 10.0
    y_offset = body.get("y_offset", 0) / 10.0
    scale = body.get("scale", 1.0)
    
    # Use importSVG method
    import_result = sketch.importSVG(svg_path, x_offset, y_offset, scale)
    
    adsk.doEvents()
    
    # Get profile count
    profile_count = sketch.profiles.count
    curve_count = sketch.sketchCurves.count
    
    return {
        "success": True,
        "sketch_id": sketch.name,
        "profile_count": profile_count,
        "curve_count": curve_count,
        "message": f"SVG imported with {curve_count} curves and {profile_count} profiles"
    }


def handle_add_text(body):
    """Add text to a sketch."""
    root = get_root()
    
    text = body.get("text")
    if not text:
        raise Exception("text is required")
    
    font_name = body.get("font", "Arial")
    height = body.get("height", 10) / 10.0  # mm to cm
    
    # Get or create sketch
    sketch_id = body.get("sketch_id")
    body_id = body.get("body_id")
    plane_id = body.get("plane")
    
    sketch = None
    
    if sketch_id:
        # Use existing sketch
        sketch = root.sketches.itemByName(sketch_id)
        if not sketch:
            raise Exception(f"Sketch not found: {sketch_id}")
    elif body_id:
        # Create sketch on body's top face
        for b in root.bRepBodies:
            if b.name == body_id:
                # Find top planar face
                for face in b.faces:
                    geo = face.geometry
                    if hasattr(geo, 'surfaceType') and geo.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                        if hasattr(geo, 'normal') and geo.normal.z > 0.9:
                            sketch = root.sketches.add(face)
                            break
                break
        if not sketch:
            raise Exception(f"Could not create sketch on body: {body_id}")
    elif plane_id:
        # Create sketch on plane
        if plane_id == "xy":
            plane = root.xYConstructionPlane
        elif plane_id == "xz":
            plane = root.xZConstructionPlane
        elif plane_id == "yz":
            plane = root.yZConstructionPlane
        else:
            plane = root.constructionPlanes.itemByName(plane_id)
        
        if not plane:
            raise Exception(f"Plane not found: {plane_id}")
        sketch = root.sketches.add(plane)
    else:
        raise Exception("Either sketch_id, body_id, or plane is required")
    
    # Set sketch name
    if body.get("sketch_name"):
        sketch.name = body.get("sketch_name")
    
    # Position in cm
    x = body.get("x", 0) / 10.0
    y = body.get("y", 0) / 10.0
    
    # Create text using createInput(text, height, point)
    texts = sketch.sketchTexts
    
    # Position point
    position = adsk.core.Point3D.create(x, y, 0)
    
    # Get rotation angle in radians
    rotation_deg = body.get("rotation", 0)
    rotation_rad = rotation_deg * 3.14159265359 / 180.0
    
    # Create text input - API is: createInput(text, height, point)
    text_input = texts.createInput(text, height, position)
    text_input.fontName = font_name
    text_input.angle = rotation_rad
    
    if body.get("bold", False):
        text_input.isBold = True
    if body.get("italic", False):
        text_input.isItalic = True
    
    sketch_text = texts.add(text_input)
    
    adsk.doEvents()
    
    profile_count = sketch.profiles.count
    
    return {
        "success": True,
        "sketch_id": sketch.name,
        "profile_count": profile_count,
        "message": f"Text '{text}' added with {profile_count} profiles"
    }


# ============================================================================
# ORGANIC MODELING - LOFT, SWEEP, REVOLVE
# ============================================================================

def handle_loft(body):
    """Loft between multiple sketch profiles to create organic 3D forms.
    
    Args:
        sketch_ids: List of sketch names containing profiles to loft between
        profile_indices: Optional list of profile indices (default 0 for each sketch)
        operation: new_body, join, cut, intersect (default: new_body)
        is_solid: Whether to create solid (True) or surface (False)
        rails: Optional list of rail sketch IDs for guiding the loft
    """
    root = get_root()
    
    sketch_ids = body.get("sketch_ids", [])
    profile_indices = body.get("profile_indices", [])
    operation = body.get("operation", "new_body")
    is_solid = body.get("is_solid", True)
    
    if len(sketch_ids) < 2:
        raise Exception("At least 2 sketches are required for loft")
    
    # Collect profiles
    profiles = adsk.core.ObjectCollection.create()
    
    for i, sketch_id in enumerate(sketch_ids):
        sketch = get_sketch(sketch_id)
        profile_idx = profile_indices[i] if i < len(profile_indices) else 0
        
        if profile_idx >= sketch.profiles.count:
            raise Exception(f"Profile index {profile_idx} not found in sketch {sketch_id}")
        
        profiles.add(sketch.profiles.item(profile_idx))
    
    # Create loft feature
    lofts = root.features.loftFeatures
    loft_input = lofts.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    
    # Set operation type
    if operation == "join":
        loft_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
    elif operation == "cut":
        loft_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    elif operation == "intersect":
        loft_input.operation = adsk.fusion.FeatureOperations.IntersectFeatureOperation
    
    # Add profiles as loft sections
    for i in range(profiles.count):
        loft_input.loftSections.add(profiles.item(i))
    
    loft_input.isSolid = is_solid
    loft_input.isClosed = False
    loft_input.isTangentEdgesMerged = True
    
    # Add rails if provided
    rail_ids = body.get("rails", [])
    if rail_ids:
        for rail_id in rail_ids:
            rail_sketch = get_sketch(rail_id)
            if rail_sketch.sketchCurves.count > 0:
                # Get first curve as rail
                rail_curve = rail_sketch.sketchCurves.item(0)
                loft_input.centerLineOrRails.addRail(rail_curve)
    
    loft = lofts.add(loft_input)
    adsk.doEvents()
    
    body_name = loft.bodies.item(0).name if loft.bodies.count > 0 else "Unknown"
    
    return {
        "feature_id": loft.name,
        "body_id": body_name,
        "profiles_used": profiles.count
    }


def handle_sweep(body):
    """Sweep a profile along a path to create 3D geometry.
    
    Args:
        profile_sketch_id: Sketch containing the profile to sweep
        path_sketch_id: Sketch containing the path curve
        profile_index: Profile index in the sketch (default: 0)
        operation: new_body, join, cut, intersect (default: new_body)
        orientation: perpendicular, parallel (default: perpendicular)
        twist_angle: Optional twist angle in degrees along the sweep
    """
    root = get_root()
    
    profile_sketch_id = body.get("profile_sketch_id")
    path_sketch_id = body.get("path_sketch_id")
    profile_index = body.get("profile_index", 0)
    operation = body.get("operation", "new_body")
    
    if not profile_sketch_id or not path_sketch_id:
        raise Exception("Both profile_sketch_id and path_sketch_id are required")
    
    # Get profile
    profile_sketch = get_sketch(profile_sketch_id)
    if profile_index >= profile_sketch.profiles.count:
        raise Exception(f"Profile index {profile_index} not found in sketch {profile_sketch_id}")
    profile = profile_sketch.profiles.item(profile_index)
    
    # Get path - use first curve in the path sketch
    path_sketch = get_sketch(path_sketch_id)
    if path_sketch.sketchCurves.count == 0:
        raise Exception(f"No curves found in path sketch {path_sketch_id}")
    
    # Create a path from the sketch curves
    path = root.features.createPath(path_sketch.sketchCurves.item(0), False)
    
    # Create sweep feature
    sweeps = root.features.sweepFeatures
    
    # Determine operation
    op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    if operation == "join":
        op = adsk.fusion.FeatureOperations.JoinFeatureOperation
    elif operation == "cut":
        op = adsk.fusion.FeatureOperations.CutFeatureOperation
    elif operation == "intersect":
        op = adsk.fusion.FeatureOperations.IntersectFeatureOperation
    
    sweep_input = sweeps.createInput(profile, path, op)
    
    # Set orientation
    orientation = body.get("orientation", "perpendicular")
    if orientation == "parallel":
        sweep_input.orientation = adsk.fusion.SweepOrientationTypes.ParallelOrientationType
    else:
        sweep_input.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
    
    # Set twist if provided
    twist_angle = body.get("twist_angle")
    if twist_angle:
        sweep_input.twistAngle = adsk.core.ValueInput.createByReal(twist_angle * 3.14159265359 / 180.0)
    
    sweep = sweeps.add(sweep_input)
    adsk.doEvents()
    
    body_name = sweep.bodies.item(0).name if sweep.bodies.count > 0 else "Unknown"
    
    return {
        "feature_id": sweep.name,
        "body_id": body_name
    }


def handle_revolve(body):
    """Revolve a profile around an axis to create 3D geometry.
    
    Args:
        sketch_id: Sketch containing the profile to revolve
        profile_index: Profile index (default: 0)
        axis: "x", "y", "z", or axis sketch line ID
        axis_sketch_id: Sketch containing the axis line (if using sketch line)
        angle: Angle in degrees (default: 360 for full revolution)
        operation: new_body, join, cut, intersect (default: new_body)
    """
    root = get_root()
    
    sketch_id = body.get("sketch_id")
    profile_index = body.get("profile_index", 0)
    axis_type = body.get("axis", "x")
    angle = body.get("angle", 360)
    operation = body.get("operation", "new_body")
    
    if not sketch_id:
        raise Exception("sketch_id is required")
    
    # Get profile
    sketch = get_sketch(sketch_id)
    if profile_index >= sketch.profiles.count:
        raise Exception(f"Profile index {profile_index} not found in sketch {sketch_id}")
    profile = sketch.profiles.item(profile_index)
    
    # Determine axis
    axis = None
    axis_sketch_id = body.get("axis_sketch_id")
    axis_line_index = body.get("axis_line_index", 0)
    
    if axis_sketch_id:
        # Use a line from another sketch as axis
        axis_sketch = get_sketch(axis_sketch_id)
        if axis_line_index < axis_sketch.sketchCurves.sketchLines.count:
            axis = axis_sketch.sketchCurves.sketchLines.item(axis_line_index)
    elif axis_type == "x":
        axis = root.xConstructionAxis
    elif axis_type == "y":
        axis = root.yConstructionAxis
    elif axis_type == "z":
        axis = root.zConstructionAxis
    else:
        # Try to find a line in the profile sketch to use as axis
        for i in range(sketch.sketchCurves.sketchLines.count):
            line = sketch.sketchCurves.sketchLines.item(i)
            if line.isConstruction:
                axis = line
                break
    
    if not axis:
        raise Exception("Could not determine revolve axis. Specify axis or create a construction line.")
    
    # Determine operation
    op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    if operation == "join":
        op = adsk.fusion.FeatureOperations.JoinFeatureOperation
    elif operation == "cut":
        op = adsk.fusion.FeatureOperations.CutFeatureOperation
    elif operation == "intersect":
        op = adsk.fusion.FeatureOperations.IntersectFeatureOperation
    
    # Create revolve
    revolves = root.features.revolveFeatures
    revolve_input = revolves.createInput(profile, axis, op)
    
    # Set angle
    angle_rad = angle * 3.14159265359 / 180.0
    revolve_input.setAngleExtent(False, adsk.core.ValueInput.createByReal(angle_rad))
    
    revolve = revolves.add(revolve_input)
    adsk.doEvents()
    
    body_name = revolve.bodies.item(0).name if revolve.bodies.count > 0 else "Unknown"
    
    return {
        "feature_id": revolve.name,
        "body_id": body_name
    }


def handle_create_sphere(body):
    """Create a sphere primitive body.
    
    Args:
        center: [x, y, z] center point in mm
        radius: Radius in mm
        name: Optional name for the body
    """
    root = get_root()
    
    center = body.get("center", [0, 0, 0])
    radius = body.get("radius", 50)
    name = body.get("name")
    
    # Create sphere using sketch + revolve approach
    # Create a temporary sketch on XZ plane through the center
    sketches = root.sketches
    sketch = sketches.add(root.xZConstructionPlane)
    sketch.name = "_temp_sphere_sketch"
    
    # Draw a semicircle
    arcs = sketch.sketchCurves.sketchArcs
    lines = sketch.sketchCurves.sketchLines
    
    # Center point (in cm)
    cx = center[0] / 10.0
    cy = center[1] / 10.0
    cz = center[2] / 10.0
    r = radius / 10.0
    
    # On XZ plane, Y becomes the vertical axis
    # Draw arc from bottom to top
    center_pt = adsk.core.Point3D.create(cx, cz, 0)
    start_pt = adsk.core.Point3D.create(cx, cz - r, 0)
    
    import math
    arc = arcs.addByCenterStartSweep(center_pt, start_pt, math.pi)  # 180 degree arc
    
    # Draw closing line (diameter)
    end_pt = adsk.core.Point3D.create(cx, cz + r, 0)
    line = lines.addByTwoPoints(start_pt, end_pt)
    line.isConstruction = True  # Make it construction for the axis
    
    adsk.doEvents()
    
    # Get the profile
    if sketch.profiles.count == 0:
        raise Exception("Failed to create sphere profile")
    
    profile = sketch.profiles.item(0)
    
    # Revolve around the construction line (Y axis through center)
    revolves = root.features.revolveFeatures
    revolve_input = revolves.createInput(profile, line, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    revolve_input.setAngleExtent(False, adsk.core.ValueInput.createByReal(2 * math.pi))  # 360 degrees
    
    revolve = revolves.add(revolve_input)
    adsk.doEvents()
    
    # Get the created body
    sphere_body = revolve.bodies.item(0)
    if name:
        sphere_body.name = name
    
    # Move sphere if center Y != 0 (since we created on XZ plane)
    if center[1] != 0:
        move_features = root.features.moveFeatures
        bodies = adsk.core.ObjectCollection.create()
        bodies.add(sphere_body)
        move_input = move_features.createInput2(bodies)
        transform = adsk.core.Matrix3D.create()
        transform.translation = adsk.core.Vector3D.create(0, cy, 0)
        move_input.defineAsFreeMove(transform)
        move_features.add(move_input)
    
    # Clean up temp sketch
    sketch.deleteMe()
    
    return {
        "body_id": sphere_body.name,
        "name": sphere_body.name,
        "center": center,
        "radius": radius
    }


def handle_create_cylinder(body):
    """Create a cylinder primitive body.
    
    Args:
        center: [x, y, z] center point of base in mm
        radius: Radius in mm
        height: Height in mm
        axis: "x", "y", or "z" (default: "z")
        name: Optional name for the body
    """
    root = get_root()
    
    center = body.get("center", [0, 0, 0])
    radius = body.get("radius", 50)
    height = body.get("height", 100)
    axis = body.get("axis", "z")
    name = body.get("name")
    
    # Convert mm to cm
    cx = center[0] / 10.0
    cy = center[1] / 10.0
    cz = center[2] / 10.0
    r = radius / 10.0
    h = height / 10.0
    
    # Create an offset plane at the base Z position if needed
    if axis == "z":
        if abs(cz) > 0.001:
            planes = root.constructionPlanes
            plane_input = planes.createInput()
            plane_input.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(cz))
            sketch_plane = planes.add(plane_input)
        else:
            sketch_plane = root.xYConstructionPlane
        circle_center = adsk.core.Point3D.create(cx, cy, 0)
    elif axis == "y":
        # For Y-axis cylinder, sketch on XZ plane at the starting Y position
        # XZ plane: sketch X = global X, sketch Y = global Z (note: might be inverted)
        if abs(cy) > 0.001:
            planes = root.constructionPlanes
            plane_input = planes.createInput()
            plane_input.setByOffset(root.xZConstructionPlane, adsk.core.ValueInput.createByReal(cy))
            sketch_plane = planes.add(plane_input)
        else:
            sketch_plane = root.xZConstructionPlane
        # On XZ plane, sketch Y maps to global -Z (inverted), so negate cz
        circle_center = adsk.core.Point3D.create(cx, -cz, 0)
    else:  # x axis
        if abs(cx) > 0.001:
            planes = root.constructionPlanes
            plane_input = planes.createInput()
            plane_input.setByOffset(root.yZConstructionPlane, adsk.core.ValueInput.createByReal(cx))
            sketch_plane = planes.add(plane_input)
        else:
            sketch_plane = root.yZConstructionPlane
        circle_center = adsk.core.Point3D.create(cy, cz, 0)
    
    # Create sketch
    sketch = root.sketches.add(sketch_plane)
    sketch.name = "_temp_cylinder_sketch"
    
    # Draw circle at center
    circles = sketch.sketchCurves.sketchCircles
    circle = circles.addByCenterRadius(circle_center, r)
    adsk.doEvents()
    
    # Extrude
    profile = sketch.profiles.item(0)
    extrudes = root.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(h))
    
    extrude = extrudes.add(extrude_input)
    adsk.doEvents()
    
    # Get the created body
    cylinder_body = extrude.bodies.item(0)
    if name:
        cylinder_body.name = name
    
    # Clean up temp sketch
    sketch.deleteMe()
    
    # Calculate actual bounds for verification
    bbox = cylinder_body.boundingBox
    actual_min = [round(bbox.minPoint.x * 10, 2), round(bbox.minPoint.y * 10, 2), round(bbox.minPoint.z * 10, 2)]
    actual_max = [round(bbox.maxPoint.x * 10, 2), round(bbox.maxPoint.y * 10, 2), round(bbox.maxPoint.z * 10, 2)]
    
    return {
        "body_id": cylinder_body.name,
        "name": cylinder_body.name,
        "center": center,
        "radius": radius,
        "height": height,
        "axis": axis,
        "actual_bounds": {
            "min": actual_min,
            "max": actual_max
        }
    }


def handle_extrude_with_draft(body):
    """Extrude a profile with a draft/taper angle.
    
    Args:
        sketch_id: Sketch containing the profile
        profile_index: Profile index (default: 0)
        distance: Extrusion distance in mm
        draft_angle: Taper angle in degrees (positive = outward, negative = inward)
        direction: positive, negative, symmetric
        operation: new_body, join, cut, intersect
    """
    root = get_root()
    
    sketch_id = body.get("sketch_id")
    profile_index = body.get("profile_index", 0)
    distance = body.get("distance", 10) / 10.0  # mm to cm
    draft_angle = body.get("draft_angle", 0)  # degrees
    direction = body.get("direction", "positive")
    operation = body.get("operation", "new_body")
    target_body_name = body.get("target_body")
    
    sketch = get_sketch(sketch_id)
    profile = sketch.profiles.item(profile_index)
    
    if not profile:
        raise Exception(f"Profile not found at index {profile_index}")
    
    # Determine operation
    op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    if operation == "join":
        op = adsk.fusion.FeatureOperations.JoinFeatureOperation
    elif operation == "cut":
        op = adsk.fusion.FeatureOperations.CutFeatureOperation
    elif operation == "intersect":
        op = adsk.fusion.FeatureOperations.IntersectFeatureOperation
    
    extrudes = root.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, op)
    
    # Set target body for cut/join operations
    if target_body_name and operation in ["join", "cut", "intersect"]:
        target_body = find_body_by_name(root, target_body_name)
        if target_body:
            extrude_input.participantBodies = [target_body]
    
    # Set distance with taper
    draft_rad = draft_angle * 3.14159265359 / 180.0
    
    if direction == "symmetric":
        extent = adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(distance))
        extrude_input.setSymmetricExtent(adsk.core.ValueInput.createByReal(distance), True)
        # Note: symmetric with taper requires different approach
        if draft_angle != 0:
            extrude_input.taperAngle = adsk.core.ValueInput.createByReal(draft_rad)
    else:
        is_negative = direction == "negative"
        extrude_input.setOneSideExtent(
            adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(distance)),
            adsk.fusion.ExtentDirections.NegativeExtentDirection if is_negative else adsk.fusion.ExtentDirections.PositiveExtentDirection
        )
        if draft_angle != 0:
            extrude_input.taperAngle = adsk.core.ValueInput.createByReal(draft_rad)
    
    extrude = extrudes.add(extrude_input)
    adsk.doEvents()
    
    body_name = extrude.bodies.item(0).name if extrude.bodies.count > 0 else target_body_name
    
    return {
        "feature_id": extrude.name,
        "body_id": body_name,
        "draft_angle": draft_angle
    }


# ============================================================================
# ROUTE TABLE
# ============================================================================

# ============================================================================
# NEW IMPROVED TOOLS (Based on Project Learnings)
# ============================================================================

def handle_create_box(body):
    """Create a box primitive body - much easier than sketch+extrude for boolean operations.
    
    Args:
        corner1: [x, y, z] first corner in mm
        corner2: [x, y, z] opposite corner in mm (or use center+dimensions)
        center: [x, y, z] center point in mm (alternative to corner1/corner2)
        width: Width (X) in mm (used with center)
        depth: Depth (Y) in mm (used with center)
        height: Height (Z) in mm (used with center)
        name: Optional name for the body
    """
    root = get_root()
    
    # Determine box bounds
    if body.get("center"):
        center = body.get("center")
        width = body.get("width", 100)
        depth = body.get("depth", 100)
        height = body.get("height", 100)
        
        # Calculate corners from center
        corner1 = [
            center[0] - width/2,
            center[1] - depth/2,
            center[2] - height/2
        ]
        corner2 = [
            center[0] + width/2,
            center[1] + depth/2,
            center[2] + height/2
        ]
    else:
        corner1 = body.get("corner1", [0, 0, 0])
        corner2 = body.get("corner2", [100, 100, 100])
        width = abs(corner2[0] - corner1[0])
        depth = abs(corner2[1] - corner1[1])
        height = abs(corner2[2] - corner1[2])
    
    name = body.get("name")
    
    # Create sketch on XY plane at the Z position of corner1
    z_offset = min(corner1[2], corner2[2]) / 10.0  # cm
    
    # If Z is not 0, create offset plane
    if abs(z_offset) > 0.001:
        planes = root.constructionPlanes
        plane_input = planes.createInput()
        plane_input.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(z_offset))
        sketch_plane = planes.add(plane_input)
    else:
        sketch_plane = root.xYConstructionPlane
    
    # Create sketch and draw rectangle
    sketch = root.sketches.add(sketch_plane)
    sketch.name = "_temp_box_sketch"
    
    lines = sketch.sketchCurves.sketchLines
    
    # Rectangle corners in cm (on XY plane)
    c1 = adsk.core.Point3D.create(corner1[0] / 10.0, corner1[1] / 10.0, 0)
    c2 = adsk.core.Point3D.create(corner2[0] / 10.0, corner2[1] / 10.0, 0)
    
    lines.addTwoPointRectangle(c1, c2)
    adsk.doEvents()
    
    # Extrude
    profile = sketch.profiles.item(0)
    extrudes = root.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extrude_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(height / 10.0))
    
    extrude = extrudes.add(extrude_input)
    adsk.doEvents()
    
    # Get the created body
    box_body = extrude.bodies.item(0)
    if name:
        box_body.name = name
    
    # Clean up temp sketch
    sketch.deleteMe()
    
    return {
        "body_id": box_body.name,
        "name": box_body.name,
        "corner1": corner1,
        "corner2": corner2,
        "dimensions": {
            "width": width,
            "depth": depth,
            "height": height
        }
    }


def handle_list_sketches(body):
    """List all sketches in the design with their plane information.
    
    Returns sketch names, plane info, profile counts, and 3D position hints.
    """
    root = get_root()
    
    sketches = []
    
    def get_sketch_info(sketch, component_name="root"):
        """Extract info from a sketch."""
        plane = sketch.referencePlane
        
        # Try to determine plane orientation
        plane_info = "unknown"
        try:
            if hasattr(plane, 'geometry'):
                geo = plane.geometry
                if hasattr(geo, 'normal'):
                    n = geo.normal
                    if abs(n.z) > 0.9:
                        plane_info = "XY (horizontal)"
                    elif abs(n.y) > 0.9:
                        plane_info = "XZ (vertical-front)"
                    elif abs(n.x) > 0.9:
                        plane_info = "YZ (vertical-side)"
                    else:
                        plane_info = f"Custom [{round(n.x,2)}, {round(n.y,2)}, {round(n.z,2)}]"
                if hasattr(geo, 'origin'):
                    o = geo.origin
                    plane_info += f" at origin [{round(o.x*10,1)}, {round(o.y*10,1)}, {round(o.z*10,1)}] mm"
        except:
            pass
        
        return {
            "sketch_id": sketch.name,
            "name": sketch.name,
            "component": component_name,
            "profile_count": sketch.profiles.count,
            "curve_count": sketch.sketchCurves.count,
            "plane_info": plane_info,
            "is_fully_constrained": sketch.isFullyConstrained if hasattr(sketch, 'isFullyConstrained') else None
        }
    
    # Root sketches
    for sketch in root.sketches:
        sketches.append(get_sketch_info(sketch, "root"))
    
    # Component sketches
    for occ in root.allOccurrences:
        comp_name = occ.component.name
        for sketch in occ.component.sketches:
            sketches.append(get_sketch_info(sketch, comp_name))
    
    return {
        "sketches": sketches,
        "count": len(sketches)
    }


def handle_create_hole(body):
    """Create a hole (cylindrical cut) through a body - simpler than cylinder + boolean.
    
    Args:
        body_id: Target body to cut the hole in
        center: [x, y, z] center point of hole in mm (on the face where hole starts)
        diameter: Hole diameter in mm
        depth: Hole depth in mm (use large value for through-all)
        axis: "x", "y", or "z" - direction of hole (default: z = vertical)
        through_all: If True, cuts through the entire body (ignores depth)
    """
    root = get_root()
    
    body_id = body.get("body_id")
    center = body.get("center", [0, 0, 0])
    diameter = body.get("diameter", 10)
    depth = body.get("depth", 100)
    axis = body.get("axis", "z")
    through_all = body.get("through_all", False)
    
    # Find target body
    target_body = find_body_by_name(root, body_id)
    if not target_body:
        raise Exception(f"Body not found: {body_id}")
    
    # Get body bounds to help position the hole
    bbox = target_body.boundingBox
    
    # Determine sketch plane based on axis
    # For each axis, we create an offset plane at the hole start position,
    # then extrude in the positive direction through the body
    planes = root.constructionPlanes
    
    if axis == "z":
        # Hole goes in Z direction - sketch on XY plane offset to hole start Z
        base_plane = root.xYConstructionPlane
        circle_center = adsk.core.Point3D.create(center[0] / 10.0, center[1] / 10.0, 0)
        offset_distance = center[2] / 10.0  # Z position in cm
        extrude_dir = "negative"  # Cut downward (-Z)
        if through_all:
            depth = (bbox.maxPoint.z - bbox.minPoint.z) * 10 + 20
    elif axis == "y":
        # Hole goes in Y direction - sketch on XZ plane
        # Position sketch slightly BEFORE the body start to ensure intersection
        base_plane = root.xZConstructionPlane
        # On XZ plane, sketch Y maps to global -Z (inverted), so negate center[2]
        circle_center = adsk.core.Point3D.create(center[0] / 10.0, -center[2] / 10.0, 0)
        # Offset to just before the body's min Y (1mm margin)
        offset_distance = (bbox.minPoint.y - 0.1)  # Already in cm, subtract 1mm
        extrude_dir = "positive"  # Cut forward (+Y) from back to front
        if through_all:
            depth = (bbox.maxPoint.y - bbox.minPoint.y) * 10 + 20
        else:
            # Add margin to depth to account for offset
            depth = depth + 1
    else:  # x
        # Hole goes in X direction - sketch on YZ plane offset to hole start X
        base_plane = root.yZConstructionPlane
        circle_center = adsk.core.Point3D.create(center[1] / 10.0, center[2] / 10.0, 0)
        offset_distance = center[0] / 10.0  # X position in cm
        extrude_dir = "positive"  # Cut in +X direction
        if through_all:
            depth = (bbox.maxPoint.x - bbox.minPoint.x) * 10 + 20
    
    # Create offset plane at the specified position
    if abs(offset_distance) > 0.001:
        plane_input = planes.createInput()
        plane_input.setByOffset(base_plane, adsk.core.ValueInput.createByReal(offset_distance))
        plane = planes.add(plane_input)
    else:
        plane = base_plane
    
    # Create sketch with circle
    sketch = root.sketches.add(plane)
    sketch.name = "_temp_hole_sketch"
    
    circles = sketch.sketchCurves.sketchCircles
    circle = circles.addByCenterRadius(circle_center, diameter / 20.0)  # radius in cm
    adsk.doEvents()
    
    # Extrude as cut
    profile = sketch.profiles.item(0)
    extrudes = root.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrude_input.participantBodies = [target_body]
    
    # Set extrusion direction
    if extrude_dir == "positive":
        extent_direction = adsk.fusion.ExtentDirections.PositiveExtentDirection
    else:
        extent_direction = adsk.fusion.ExtentDirections.NegativeExtentDirection
    
    if through_all:
        extrude_input.setAllExtent(extent_direction)
    else:
        extrude_input.setOneSideExtent(
            adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(depth / 10.0)),
            extent_direction
        )
    
    extrude = extrudes.add(extrude_input)
    adsk.doEvents()
    
    # Clean up temp sketch
    sketch.deleteMe()
    
    return {
        "success": True,
        "body_id": body_id,
        "hole_center": center,
        "hole_diameter": diameter,
        "hole_depth": depth if not through_all else "through_all"
    }


def handle_get_body_center(body):
    """Get the center point and bounding box of a body.
    
    Useful for positioning cuts, holes, and other operations relative to existing geometry.
    """
    root = get_root()
    
    body_id = body.get("body_id")
    
    target_body = find_body_by_name(root, body_id)
    if not target_body:
        raise Exception(f"Body not found: {body_id}")
    
    bbox = target_body.boundingBox
    
    # Calculate center
    center = [
        round((bbox.minPoint.x + bbox.maxPoint.x) / 2 * 10, 2),  # cm to mm
        round((bbox.minPoint.y + bbox.maxPoint.y) / 2 * 10, 2),
        round((bbox.minPoint.z + bbox.maxPoint.z) / 2 * 10, 2)
    ]
    
    # Calculate dimensions
    width = round((bbox.maxPoint.x - bbox.minPoint.x) * 10, 2)
    depth = round((bbox.maxPoint.y - bbox.minPoint.y) * 10, 2)
    height = round((bbox.maxPoint.z - bbox.minPoint.z) * 10, 2)
    
    return {
        "body_id": body_id,
        "center": center,
        "bounding_box": {
            "min": [round(bbox.minPoint.x * 10, 2), round(bbox.minPoint.y * 10, 2), round(bbox.minPoint.z * 10, 2)],
            "max": [round(bbox.maxPoint.x * 10, 2), round(bbox.maxPoint.y * 10, 2), round(bbox.maxPoint.z * 10, 2)]
        },
        "dimensions": {
            "width": width,
            "depth": depth,
            "height": height
        },
        "volume_mm3": round(target_body.volume * 1000, 2)
    }


def handle_sketch_to_3d_coords(body):
    """Convert 2D sketch coordinates to 3D world coordinates.
    
    This helps understand where sketch geometry will end up in 3D space.
    Essential for positioning cuts and joins correctly.
    
    Args:
        sketch_id: The sketch name
        points: List of [x, y] 2D points to convert
    """
    sketch = get_sketch(body["sketch_id"])
    
    points_2d = body.get("points", [[0, 0]])
    
    # Get the sketch plane transform
    plane = sketch.referencePlane
    transform = sketch.transform
    
    results = []
    for pt_2d in points_2d:
        # Create 2D point and transform to 3D
        pt = adsk.core.Point3D.create(pt_2d[0] / 10.0, pt_2d[1] / 10.0, 0)
        pt.transformBy(transform)
        
        results.append({
            "input_2d": pt_2d,
            "output_3d": [round(pt.x * 10, 2), round(pt.y * 10, 2), round(pt.z * 10, 2)]
        })
    
    # Also return general plane info
    plane_info = {}
    try:
        if hasattr(plane, 'geometry'):
            geo = plane.geometry
            if hasattr(geo, 'normal'):
                plane_info["normal"] = [geo.normal.x, geo.normal.y, geo.normal.z]
            if hasattr(geo, 'origin'):
                plane_info["origin_mm"] = [geo.origin.x * 10, geo.origin.y * 10, geo.origin.z * 10]
    except:
        pass
    
    return {
        "sketch_id": body["sketch_id"],
        "plane_info": plane_info,
        "coordinate_mapping": results,
        "note": "2D sketch coords [x, y] map to 3D coords based on plane orientation"
    }


def handle_get_all_parts(body):
    """Get all parts/bodies from all components with dimensions."""
    root = get_root()
    
    parts = []
    
    def get_dims(b, comp_path):
        bbox = b.boundingBox
        w = round((bbox.maxPoint.x - bbox.minPoint.x) * 10, 1)
        d = round((bbox.maxPoint.y - bbox.minPoint.y) * 10, 1)
        h = round((bbox.maxPoint.z - bbox.minPoint.z) * 10, 1)
        return {
            "name": b.name,
            "component": comp_path,
            "width_mm": w,
            "depth_mm": d,
            "height_mm": h,
            "volume_mm3": round(b.volume * 1000, 1)
        }
    
    # Root bodies
    for b in root.bRepBodies:
        parts.append(get_dims(b, "root"))
    
    # All component bodies
    for occ in root.allOccurrences:
        comp_path = occ.fullPathName if hasattr(occ, 'fullPathName') else occ.component.name
        for b in occ.component.bRepBodies:
            parts.append(get_dims(b, comp_path))
    
    return {
        "version": "2.1",
        "total_parts": len(parts),
        "root_bodies": root.bRepBodies.count,
        "occurrences": root.allOccurrences.count,
        "parts": parts
    }


ROUTES = {
    # Document
    "/ping": handle_ping,
    "/get_all_parts": handle_get_all_parts,
    "/info": handle_info,
    "/new_document": handle_new_document,
    "/save": handle_save,
    
    # Reference Geometry
    "/list_planes": handle_list_planes,
    "/create_offset_plane": handle_create_offset_plane,
    
    # Sketch
    "/create_sketch": handle_create_sketch,
    "/draw_line": handle_draw_line,
    "/draw_arc": handle_draw_arc,
    "/draw_arc_3point": handle_draw_arc_3point,
    "/draw_circle": handle_draw_circle,
    "/draw_rectangle": handle_draw_rectangle,
    "/draw_spline": handle_draw_spline,
    "/sketch_fillet": handle_sketch_fillet,
    "/finish_sketch": handle_finish_sketch,
    "/get_sketch_profiles": handle_get_sketch_profiles,
    "/list_sketch_dimensions": handle_list_sketch_dimensions,
    "/edit_sketch_dimension": handle_edit_sketch_dimension,
    "/import_svg": handle_import_svg,
    "/add_text": handle_add_text,
    "/delete_sketch": handle_delete_sketch,
    "/list_sketches": handle_list_sketches,
    "/sketch_to_3d_coords": handle_sketch_to_3d_coords,
    
    # 3D Features
    "/extrude": handle_extrude,
    "/extrude_with_draft": handle_extrude_with_draft,
    "/fillet_edges": handle_fillet_edges,
    "/chamfer_edges": handle_chamfer_edges,
    "/boolean": handle_boolean,
    
    # Organic Modeling & Primitives
    "/loft": handle_loft,
    "/sweep": handle_sweep,
    "/revolve": handle_revolve,
    "/create_sphere": handle_create_sphere,
    "/create_cylinder": handle_create_cylinder,
    "/create_box": handle_create_box,
    "/create_hole": handle_create_hole,
    
    # Selection & Query
    "/list_bodies": handle_list_bodies,
    "/list_edges": handle_list_edges,
    "/list_faces": handle_list_faces,
    "/select_by_position": handle_select_by_position,
    "/get_body_center": handle_get_body_center,
    
    # Delete
    "/delete_body": handle_delete_body,
    "/delete_sketch": handle_delete_sketch,
    
    # Transform
    "/copy_body": handle_copy_body,
    "/move_body": handle_move_body,
    "/mirror_body": handle_mirror_body,
    "/pattern_rectangular": handle_pattern_rectangular,
    
    # Parameters
    "/create_parameter": handle_create_parameter,
    "/modify_parameter": handle_modify_parameter,
    "/list_parameters": handle_list_parameters,
    "/list_all_parameters": handle_list_all_parameters,
    
    # Feature Editing
    "/get_feature_parameters": handle_get_feature_parameters,
    "/edit_feature_parameter": handle_edit_feature_parameter,
    
    # Appearance
    "/apply_appearance": handle_apply_appearance,
    "/list_appearances": handle_list_appearances,
    
    # Utility
    "/take_screenshot": handle_take_screenshot,
    "/set_view": handle_set_view,
    "/undo": handle_undo,
    "/redo": handle_redo,
    "/get_timeline": handle_get_timeline,
    "/export": handle_export,
    
    # Workspace
    "/switch_workspace": handle_switch_workspace,
    
    # CAM
    "/cam_list_setups": handle_cam_list_setups,
    "/cam_create_setup": handle_cam_create_setup,
    "/cam_fix_setup": handle_cam_fix_setup,
    "/cam_list_tools": handle_cam_list_tools,
    "/cam_create_2d_contour": handle_cam_create_2d_contour,
    "/cam_create_2d_pocket": handle_cam_create_2d_pocket,
    "/cam_create_engrave": handle_cam_create_engrave,
    "/cam_generate_all": handle_cam_generate_all,
    "/cam_post_process": handle_cam_post_process,
    "/cam_list_operations": handle_cam_list_operations,
    "/cam_simulate": handle_cam_simulate,
    "/cam_select_silhouette": handle_cam_select_silhouette,
}


# ============================================================================
# SERVER LIFECYCLE
# ============================================================================

def start_server():
    global server
    try:
        server = HTTPServer(("localhost", PORT), FusionHandler)
        server.serve_forever()
    except Exception as e:
        global ui
        if ui:
            ui.messageBox(f"Server error: {str(e)}")


def run(context):
    global app, ui, server_thread, custom_event, custom_event_handler

    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Register custom event for ALL commands (thread safety)
        custom_event = app.registerCustomEvent("FusionMCPCommandEvent")
        custom_event_handler = CommandEventHandler()
        custom_event.add(custom_event_handler)

        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

        ui.messageBox(f"MCP Bridge running on localhost:{PORT}")

    except Exception as e:
        if ui:
            ui.messageBox(f"Failed to start: {str(e)}\n{traceback.format_exc()}")


def stop(context):
    global server, ui, app, custom_event, custom_event_handler

    try:
        if server:
            server.shutdown()
            server = None
        
        # Unregister custom event
        if custom_event:
            if custom_event_handler:
                custom_event.remove(custom_event_handler)
            app.unregisterCustomEvent("FusionMCPCommandEvent")
            custom_event = None
            custom_event_handler = None

        if ui:
            ui.messageBox("MCP Bridge stopped")

    except Exception as e:
        if ui:
            ui.messageBox(f"Error stopping: {str(e)}")
