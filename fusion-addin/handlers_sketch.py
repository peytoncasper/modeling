"""Sketch handlers — creation, drawing, querying, constraints, gap analysis.

Every public function has the signature ``handle_*(body: dict) -> dict``
and is registered in ROUTES by the main bridge orchestrator.
"""
import math
import os

import adsk.core
import adsk.fusion

try:
    from .bridge_helpers import (
        get_root, get_sketch, get_sketch_with_component,
        get_component_by_name, point2d, point3d,
    )
except ImportError:
    from bridge_helpers import (
        get_root, get_sketch, get_sketch_with_component,
        get_component_by_name, point2d, point3d,
    )


# ── Sketch lifecycle ─────────────────────────────────────────

def handle_create_sketch(body):
    root = get_root()
    plane_id = body.get("plane", "xy")
    name = body.get("name")
    component_name = body.get("component")

    if component_name:
        target_component, target_occ = get_component_by_name(component_name)
        if not target_component:
            raise Exception(f"Component not found: {component_name}")
    else:
        target_component = root
        target_occ = None

    sketches = target_component.sketches

    if plane_id == "xy":
        plane = target_component.xYConstructionPlane
    elif plane_id == "xz":
        plane = target_component.xZConstructionPlane
    elif plane_id == "yz":
        plane = target_component.yZConstructionPlane
    else:
        plane = target_component.constructionPlanes.itemByName(plane_id)
        if not plane:
            plane = root.constructionPlanes.itemByName(plane_id)

    if not plane:
        raise Exception(f"Plane not found: {plane_id}")

    sketch = sketches.add(plane)
    adsk.doEvents()
    if name:
        sketch.name = name

    return {
        "sketch_id": sketch.name,
        "name": sketch.name,
        "component": target_component.name,
    }


def handle_create_sketch_on_face(body):
    """Create a sketch on a body face."""
    root = get_root()
    body_id = body.get("body_id")
    face_id = body.get("face_id")
    sketch_name = body.get("name", f"Sketch_on_{body_id}")
    component_name = body.get("component")

    if component_name:
        target_component, target_occ = get_component_by_name(component_name)
        if not target_component:
            raise Exception(f"Component not found: {component_name}")
    else:
        target_component = root

    target_body = None
    for b in target_component.bRepBodies:
        if b.name == body_id:
            target_body = b
            break
    if not target_body:
        raise Exception(f"Body not found: {body_id}")

    target_face = None
    if face_id.startswith(f"{body_id}_face_"):
        face_index = int(face_id.split("_")[-1])
        if 0 <= face_index < target_body.faces.count:
            target_face = target_body.faces.item(face_index)
    else:
        try:
            face_index = int(face_id)
            if 0 <= face_index < target_body.faces.count:
                target_face = target_body.faces.item(face_index)
        except ValueError:
            pass

    if not target_face:
        raise Exception(f"Face not found: {face_id}")

    sketches = target_component.sketches
    sketch = sketches.add(target_face)
    sketch.name = sketch_name

    plane_type = "face" if sketch.referencePlane else "unknown"
    return {
        "sketch_id": sketch.name,
        "name": sketch.name,
        "plane": plane_type,
        "on_body": body_id,
        "on_face": face_id,
    }


def handle_finish_sketch(body):
    sketch = get_sketch(body["sketch_id"])
    profile_count = sketch.profiles.count
    open_curves = 0
    for curve in sketch.sketchCurves:
        if hasattr(curve, "isClosed") and not curve.isClosed:
            open_curves += 1
    return {
        "success": True,
        "is_valid": profile_count > 0,
        "profile_count": profile_count,
        "open_curves": open_curves,
    }


def handle_delete_sketch(body):
    """Delete a sketch by name.  Searches root then all occurrences."""
    root = get_root()
    sketch_name = body.get("sketch_name")
    component_name = body.get("component")

    if not sketch_name:
        raise Exception("sketch_name is required")

    deleted = False
    if component_name:
        target_component, _ = get_component_by_name(component_name)
        if target_component:
            sketch = target_component.sketches.itemByName(sketch_name)
            if sketch:
                sketch.deleteMe()
                deleted = True
    else:
        sketch = root.sketches.itemByName(sketch_name)
        if sketch:
            sketch.deleteMe()
            deleted = True
        if not deleted:
            for occ in root.allOccurrences:
                sketch = occ.component.sketches.itemByName(sketch_name)
                if sketch:
                    sketch.deleteMe()
                    deleted = True
                    break

    if not deleted:
        raise Exception(f"Sketch not found: {sketch_name}")
    return {"success": True, "deleted_sketch": sketch_name}


def handle_list_sketches(body):
    """List all sketches with plane info and coordinate mapping guide."""
    root = get_root()
    sketches = []

    def _coord_mapping(plane_type, normal):
        if plane_type == "XY":
            return {
                "plane_type": "XY",
                "plane_nickname": "horizontal",
                "sketch_x_means": "World +X (left/right)",
                "sketch_y_means": "World +Y (front/back)",
                "extrude_positive": "World +Z (up)",
                "extrude_negative": "World -Z (down)",
                "gotcha": None,
            }
        if plane_type == "XZ":
            return {
                "plane_type": "XZ",
                "plane_nickname": "vertical_front",
                "sketch_x_means": "World +X (left/right)",
                "sketch_y_means": "World -Z (WARNING: +sketch_Y goes DOWN in world!)",
                "extrude_positive": "World +Y (into model, away from viewer)",
                "extrude_negative": "World -Y (toward viewer)",
                "gotcha": "CRITICAL: To create geometry at positive world Z, use NEGATIVE sketch Y values!",
            }
        if plane_type == "YZ":
            return {
                "plane_type": "YZ",
                "plane_nickname": "vertical_side",
                "sketch_x_means": "World -Z (WARNING: +sketch_X goes DOWN in world!)",
                "sketch_y_means": "World +Y (front/back)",
                "extrude_positive": "World +X (to the right)",
                "extrude_negative": "World -X (to the left)",
                "gotcha": "CRITICAL: To create geometry at positive world Z, use NEGATIVE sketch X values!",
            }
        return {
            "plane_type": "Custom",
            "plane_nickname": "custom",
            "normal": [round(normal.x, 3), round(normal.y, 3), round(normal.z, 3)],
            "gotcha": "Custom plane - verify coordinate mapping with sketch_to_3d_coords tool",
        }

    def _sketch_info(sketch, comp_name="root"):
        try:
            plane = sketch.referencePlane
        except Exception:
            return None
        if not plane:
            return None

        plane_type, plane_info, coord_mapping, origin_3d = "unknown", "unknown", {}, [0, 0, 0]
        try:
            if hasattr(plane, "geometry"):
                geo = plane.geometry
                if hasattr(geo, "normal"):
                    n = geo.normal
                    if abs(n.z) > 0.9:
                        plane_type, plane_info = "XY", "XY (horizontal)"
                    elif abs(n.y) > 0.9:
                        plane_type, plane_info = "XZ", "XZ (vertical-front)"
                    elif abs(n.x) > 0.9:
                        plane_type, plane_info = "YZ", "YZ (vertical-side)"
                    else:
                        plane_type = "Custom"
                        plane_info = f"Custom normal=[{round(n.x,2)}, {round(n.y,2)}, {round(n.z,2)}]"
                    coord_mapping = _coord_mapping(plane_type, n)
                if hasattr(geo, "origin"):
                    o = geo.origin
                    origin_3d = [round(o.x * 10, 2), round(o.y * 10, 2), round(o.z * 10, 2)]
                    plane_info += f" at origin {origin_3d} mm"
        except Exception:
            pass

        return {
            "sketch_id": sketch.name,
            "name": sketch.name,
            "component": comp_name,
            "profile_count": sketch.profiles.count,
            "curve_count": sketch.sketchCurves.count,
            "plane_info": plane_info,
            "origin_3d": origin_3d,
            "coordinate_mapping": coord_mapping,
            "is_fully_constrained": getattr(sketch, "isFullyConstrained", None),
        }

    for sketch in root.sketches:
        info = _sketch_info(sketch, "root")
        if info:
            sketches.append(info)
    for occ in root.allOccurrences:
        comp_name = occ.component.name
        for sketch in occ.component.sketches:
            info = _sketch_info(sketch, comp_name)
            if info:
                sketches.append(info)

    return {"sketches": sketches, "count": len(sketches)}


# ── Drawing primitives ───────────────────────────────────────

def handle_draw_line(body):
    sketch = get_sketch(body["sketch_id"])
    lines = sketch.sketchCurves.sketchLines
    curve_idx = sketch.sketchCurves.count
    start = point2d(body["start"])
    end = point2d(body["end"])
    line = lines.addByTwoPoints(start, end)
    adsk.doEvents()
    if body.get("construction", False):
        line.isConstruction = True
    return {"curve_id": f"{body['sketch_id']}_curve_{curve_idx}"}


def handle_draw_arc(body):
    sketch = get_sketch(body["sketch_id"])
    arcs = sketch.sketchCurves.sketchArcs
    curve_idx = sketch.sketchCurves.count
    center_coords = body["center"]
    radius = body["radius"] / 10.0
    start_angle = body["start_angle"] * math.pi / 180.0
    sweep_angle = body["sweep_angle"] * math.pi / 180.0
    center = point2d(center_coords)
    start_x = center_coords[0] / 10.0 + radius * math.cos(start_angle)
    start_y = center_coords[1] / 10.0 + radius * math.sin(start_angle)
    start_point = adsk.core.Point3D.create(start_x, start_y, 0)
    arcs.addByCenterStartSweep(center, start_point, sweep_angle)
    adsk.doEvents()
    return {"curve_id": f"{body['sketch_id']}_curve_{curve_idx}"}


def handle_draw_arc_3point(body):
    sketch = get_sketch(body["sketch_id"])
    arcs = sketch.sketchCurves.sketchArcs
    curve_idx = sketch.sketchCurves.count
    start = point2d(body["start"])
    mid = point2d(body["mid"])
    end = point2d(body["end"])
    arcs.addByThreePoints(start, mid, end)
    return {"curve_id": f"{body['sketch_id']}_curve_{curve_idx}"}


def handle_draw_circle(body):
    sketch = get_sketch(body["sketch_id"])
    circles = sketch.sketchCurves.sketchCircles
    curve_idx = sketch.sketchCurves.count
    center = point2d(body["center"])
    radius = body["radius"] / 10.0
    circles.addByCenterRadius(center, radius)
    adsk.doEvents()
    return {"curve_id": f"{body['sketch_id']}_curve_{curve_idx}"}


def handle_draw_rectangle(body):
    sketch = get_sketch(body["sketch_id"])
    lines = sketch.sketchCurves.sketchLines
    start_idx = sketch.sketchCurves.count
    corner1 = point2d(body["corner1"])
    corner2 = point2d(body["corner2"])
    rect_lines = lines.addTwoPointRectangle(corner1, corner2)
    adsk.doEvents()
    curve_ids = [f"{body['sketch_id']}_curve_{start_idx + i}" for i in range(len(rect_lines))]
    return {"curve_ids": curve_ids}


def handle_draw_rectangle_3d(body):
    """Draw rectangle using world 3D coordinates with auto plane-conversion."""
    sketch_id = body.get("sketch_id")
    world_corner1 = body.get("world_corner1")
    world_corner2 = body.get("world_corner2")
    if not sketch_id or not world_corner1 or not world_corner2:
        return {"error": True, "message": "Required: sketch_id, world_corner1, world_corner2"}

    sketch = get_sketch(sketch_id)
    plane = sketch.referencePlane
    plane_type = "unknown"
    try:
        if hasattr(plane, "geometry"):
            geo = plane.geometry
            if hasattr(geo, "normal"):
                n = geo.normal
                if abs(n.z) > 0.9:
                    plane_type = "XY"
                elif abs(n.y) > 0.9:
                    plane_type = "XZ"
                elif abs(n.x) > 0.9:
                    plane_type = "YZ"
    except Exception:
        return {"error": True, "message": "Could not determine sketch plane orientation"}

    if plane_type == "XY":
        s1 = [world_corner1[0], world_corner1[1]]
        s2 = [world_corner2[0], world_corner2[1]]
    elif plane_type == "XZ":
        s1 = [world_corner1[0], -world_corner1[2]]
        s2 = [world_corner2[0], -world_corner2[2]]
    elif plane_type == "YZ":
        s1 = [-world_corner1[2], world_corner1[1]]
        s2 = [-world_corner2[2], world_corner2[1]]
    else:
        return {"error": True, "message": f"Unsupported plane type: {plane_type}"}

    lines = sketch.sketchCurves.sketchLines
    start_idx = sketch.sketchCurves.count
    rect_lines = lines.addTwoPointRectangle(point2d(s1), point2d(s2))
    adsk.doEvents()
    curve_ids = [f"{sketch_id}_curve_{start_idx + i}" for i in range(len(rect_lines))]
    return {
        "curve_ids": curve_ids,
        "plane_type": plane_type,
        "world_input": {"corner1": world_corner1, "corner2": world_corner2},
        "sketch_coords_used": {
            "corner1": [round(s1[0], 3), round(s1[1], 3)],
            "corner2": [round(s2[0], 3), round(s2[1], 3)],
        },
        "conversion_note": f"World coords converted for {plane_type} plane",
    }


def handle_draw_spline(body):
    sketch = get_sketch(body["sketch_id"])
    splines = sketch.sketchCurves.sketchFittedSplines
    curve_idx = sketch.sketchCurves.count
    points = adsk.core.ObjectCollection.create()
    for p in body["points"]:
        points.add(point2d(p))
    spline = splines.add(points)
    if body.get("closed", False):
        spline.isClosed = True
    return {"curve_id": f"{body['sketch_id']}_curve_{curve_idx}"}


def handle_draw_polygon(body):
    """Draw a regular polygon inscribed in a circle."""
    sketch = get_sketch(body["sketch_id"])
    center = body["center"]
    radius = body["radius"]
    sides = body.get("sides", 6)
    rotation_deg = body.get("rotation", 0)

    start_idx = sketch.sketchCurves.count
    lines = sketch.sketchCurves.sketchLines
    verts = []
    for i in range(sides):
        angle = math.radians(rotation_deg + 360 * i / sides)
        verts.append([
            center[0] + radius * math.cos(angle),
            center[1] + radius * math.sin(angle),
        ])
    drawn = []
    for i in range(sides):
        s = point2d(verts[i])
        e = point2d(verts[(i + 1) % sides])
        drawn.append(lines.addByTwoPoints(s, e))
    adsk.doEvents()
    curve_ids = [f"{body['sketch_id']}_curve_{start_idx + i}" for i in range(len(drawn))]
    return {"curve_ids": curve_ids, "vertex_count": sides}


def handle_draw_slot(body):
    """Draw a slot (oblong) — two semicircles connected by tangent lines."""
    sketch = get_sketch(body["sketch_id"])
    center1 = body["center1"]
    center2 = body["center2"]
    radius = body["radius"] / 10.0

    dx = center2[0] - center1[0]
    dy = center2[1] - center1[1]
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        raise Exception("center1 and center2 must be different")

    nx, ny = -dy / length, dx / length
    start_idx = sketch.sketchCurves.count

    p1 = point2d([center1[0] + nx * radius * 10, center1[1] + ny * radius * 10])
    p2 = point2d([center2[0] + nx * radius * 10, center2[1] + ny * radius * 10])
    p3 = point2d([center2[0] - nx * radius * 10, center2[1] - ny * radius * 10])
    p4 = point2d([center1[0] - nx * radius * 10, center1[1] - ny * radius * 10])

    lines = sketch.sketchCurves.sketchLines
    arcs = sketch.sketchCurves.sketchArcs
    lines.addByTwoPoints(p1, p2)
    c2 = point2d(center2)
    arcs.addByCenterStartSweep(c2, p2, math.pi)
    lines.addByTwoPoints(p3, p4)
    c1 = point2d(center1)
    arcs.addByCenterStartSweep(c1, p4, math.pi)
    adsk.doEvents()

    count = sketch.sketchCurves.count - start_idx
    curve_ids = [f"{body['sketch_id']}_curve_{start_idx + i}" for i in range(count)]
    return {"curve_ids": curve_ids}


def handle_draw_centerline(body):
    """Draw a construction line (centerline) between two points."""
    sketch = get_sketch(body["sketch_id"])
    lines = sketch.sketchCurves.sketchLines
    curve_idx = sketch.sketchCurves.count
    start = point2d(body["start"])
    end = point2d(body["end"])
    line = lines.addByTwoPoints(start, end)
    line.isConstruction = True
    adsk.doEvents()
    return {"curve_id": f"{body['sketch_id']}_curve_{curve_idx}"}


def handle_draw_point(body):
    """Place a sketch point."""
    sketch = get_sketch(body["sketch_id"])
    pts = sketch.sketchPoints
    idx = pts.count
    pt = point2d(body["position"])
    pts.add(pt)
    adsk.doEvents()
    return {"point_id": f"{body['sketch_id']}_point_{idx}"}


# ── Modifications ────────────────────────────────────────────

def handle_sketch_fillet(body):
    sketch = get_sketch(body["sketch_id"])
    sketch_id = body["sketch_id"]

    curve1_id = body["curve1_id"]
    curve2_id = body["curve2_id"]
    curve1 = curve2 = None

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

    radius = body["radius"] / 10.0
    fillets = sketch.sketchCurves.sketchArcs
    fillet_idx = sketch.sketchCurves.count
    fillets.addFillet(
        curve1, curve1.endSketchPoint.geometry,
        curve2, curve2.startSketchPoint.geometry,
        radius,
    )
    return {"curve_id": f"{sketch_id}_curve_{fillet_idx}"}


def handle_sketch_trim(body):
    """Trim a curve at a specified point.

    Uses Fusion's sketch.trim() API which removes the portion of a curve
    nearest to the given point.
    """
    sketch = get_sketch(body["sketch_id"])
    curve_id = body["curve_id"]
    parts = curve_id.rsplit("_curve_", 1)
    if len(parts) != 2:
        raise Exception(f"Invalid curve_id format: {curve_id}")
    idx = int(parts[1])
    if idx >= sketch.sketchCurves.count:
        raise Exception(f"Curve index {idx} out of range")
    curve = sketch.sketchCurves.item(idx)
    pt = point2d(body["point"])
    sketch.trim(curve, pt)
    adsk.doEvents()
    return {"success": True, "trimmed": curve_id}


def handle_sketch_extend(body):
    """Extend a curve to intersect another curve or a point boundary."""
    sketch = get_sketch(body["sketch_id"])
    curve_id = body["curve_id"]
    parts = curve_id.rsplit("_curve_", 1)
    if len(parts) != 2:
        raise Exception(f"Invalid curve_id format: {curve_id}")
    idx = int(parts[1])
    if idx >= sketch.sketchCurves.count:
        raise Exception(f"Curve index {idx} out of range")
    curve = sketch.sketchCurves.item(idx)
    pt = point2d(body["point"])
    is_start = body.get("from_start", False)
    endpoint = curve.startSketchPoint if is_start else curve.endSketchPoint
    sketch.extend(curve, pt, endpoint)
    adsk.doEvents()
    return {"success": True, "extended": curve_id}


def handle_sketch_offset(body):
    """Offset selected curves by a distance."""
    sketch = get_sketch(body["sketch_id"])
    curves = adsk.core.ObjectCollection.create()
    for cid in body["curve_ids"]:
        parts = cid.rsplit("_curve_", 1)
        if len(parts) == 2:
            idx = int(parts[1])
            if idx < sketch.sketchCurves.count:
                curves.add(sketch.sketchCurves.item(idx))
    if curves.count == 0:
        raise Exception("No valid curves found to offset")
    direction = point2d(body["direction_point"])
    offset_val = body["distance"] / 10.0
    start_idx = sketch.sketchCurves.count
    sketch.offset(curves, direction, offset_val)
    adsk.doEvents()
    new_count = sketch.sketchCurves.count - start_idx
    ids = [f"{body['sketch_id']}_curve_{start_idx + i}" for i in range(new_count)]
    return {"curve_ids": ids, "count": new_count}


def handle_sketch_mirror(body):
    """Mirror selected curves about a construction line."""
    sketch = get_sketch(body["sketch_id"])
    curves = adsk.core.ObjectCollection.create()
    for cid in body["curve_ids"]:
        parts = cid.rsplit("_curve_", 1)
        if len(parts) == 2:
            idx = int(parts[1])
            if idx < sketch.sketchCurves.count:
                curves.add(sketch.sketchCurves.item(idx))
    if curves.count == 0:
        raise Exception("No valid curves found to mirror")
    line_id = body["mirror_line_id"]
    parts = line_id.rsplit("_curve_", 1)
    if len(parts) != 2:
        raise Exception(f"Invalid mirror_line_id: {line_id}")
    line = sketch.sketchCurves.item(int(parts[1]))
    start_idx = sketch.sketchCurves.count
    sketch.mirror(curves, line)
    adsk.doEvents()
    new_count = sketch.sketchCurves.count - start_idx
    ids = [f"{body['sketch_id']}_curve_{start_idx + i}" for i in range(new_count)]
    return {"curve_ids": ids, "count": new_count}


def handle_sketch_pattern_rectangular(body):
    """Create a rectangular pattern of curves in a sketch."""
    sketch = get_sketch(body["sketch_id"])
    curves = adsk.core.ObjectCollection.create()
    for cid in body["curve_ids"]:
        parts = cid.rsplit("_curve_", 1)
        if len(parts) == 2:
            idx = int(parts[1])
            if idx < sketch.sketchCurves.count:
                curves.add(sketch.sketchCurves.item(idx))
    if curves.count == 0:
        raise Exception("No valid curves found to pattern")

    x_count = body.get("x_count", 2)
    y_count = body.get("y_count", 1)
    x_spacing = body.get("x_spacing", 10) / 10.0
    y_spacing = body.get("y_spacing", 10) / 10.0

    x_dir = adsk.core.ValueInput.createByReal(x_spacing)
    y_dir = adsk.core.ValueInput.createByReal(y_spacing)

    start_idx = sketch.sketchCurves.count
    sketch.sketchCurves.sketchLines.item(0)  # ensure sketch is active
    pattern = sketch.geometricConstraints
    # Fusion doesn't have a direct rectangularPattern on sketch; simulate it
    drawn = []
    for xi in range(x_count):
        for yi in range(y_count):
            if xi == 0 and yi == 0:
                continue
            dx = xi * x_spacing * 10.0
            dy = yi * y_spacing * 10.0
            for i in range(curves.count):
                c = curves.item(i)
                if hasattr(c, "startSketchPoint") and hasattr(c, "endSketchPoint"):
                    s = c.startSketchPoint.geometry
                    e = c.endSketchPoint.geometry
                    ns = adsk.core.Point3D.create(s.x + dx / 10.0, s.y + dy / 10.0, 0)
                    ne = adsk.core.Point3D.create(e.x + dx / 10.0, e.y + dy / 10.0, 0)
                    drawn.append(sketch.sketchCurves.sketchLines.addByTwoPoints(ns, ne))
    adsk.doEvents()
    new_count = sketch.sketchCurves.count - start_idx
    ids = [f"{body['sketch_id']}_curve_{start_idx + i}" for i in range(new_count)]
    return {"curve_ids": ids, "count": new_count}


def handle_sketch_pattern_circular(body):
    """Create a circular pattern of curves in a sketch."""
    sketch = get_sketch(body["sketch_id"])
    curves = adsk.core.ObjectCollection.create()
    for cid in body["curve_ids"]:
        parts = cid.rsplit("_curve_", 1)
        if len(parts) == 2:
            idx = int(parts[1])
            if idx < sketch.sketchCurves.count:
                curves.add(sketch.sketchCurves.item(idx))
    if curves.count == 0:
        raise Exception("No valid curves found to pattern")

    center = body["center"]
    count = body.get("count", 4)
    total_angle = body.get("total_angle", 360)

    cx, cy = center[0] / 10.0, center[1] / 10.0
    start_idx = sketch.sketchCurves.count
    for ci in range(1, count):
        angle = math.radians(total_angle * ci / count)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        for i in range(curves.count):
            c = curves.item(i)
            if hasattr(c, "startSketchPoint") and hasattr(c, "endSketchPoint"):
                s = c.startSketchPoint.geometry
                e = c.endSketchPoint.geometry
                rs = adsk.core.Point3D.create(
                    cx + (s.x - cx) * cos_a - (s.y - cy) * sin_a,
                    cy + (s.x - cx) * sin_a + (s.y - cy) * cos_a, 0,
                )
                re = adsk.core.Point3D.create(
                    cx + (e.x - cx) * cos_a - (e.y - cy) * sin_a,
                    cy + (e.x - cx) * sin_a + (e.y - cy) * cos_a, 0,
                )
                sketch.sketchCurves.sketchLines.addByTwoPoints(rs, re)
    adsk.doEvents()
    new_count = sketch.sketchCurves.count - start_idx
    ids = [f"{body['sketch_id']}_curve_{start_idx + i}" for i in range(new_count)]
    return {"curve_ids": ids, "count": new_count}


# ── Constraints ──────────────────────────────────────────────

def handle_apply_coincident_constraints(body):
    """Apply coincident constraints between close endpoints to close a sketch."""
    sketch = get_sketch(body["sketch_id"])
    tolerance = body.get("tolerance", 0.1)
    tolerance_cm = tolerance / 10.0
    constraints = sketch.geometricConstraints

    endpoints = []
    for i, curve in enumerate(sketch.sketchCurves):
        if hasattr(curve, "isConstruction") and curve.isConstruction:
            continue
        if hasattr(curve, "startSketchPoint") and hasattr(curve, "endSketchPoint"):
            endpoints.append({
                "curve_index": i, "point_type": "start",
                "sketch_point": curve.startSketchPoint,
                "coords": [curve.startSketchPoint.geometry.x, curve.startSketchPoint.geometry.y],
            })
            endpoints.append({
                "curve_index": i, "point_type": "end",
                "sketch_point": curve.endSketchPoint,
                "coords": [curve.endSketchPoint.geometry.x, curve.endSketchPoint.geometry.y],
            })

    constraints_added = []
    processed = set()
    for i, ep1 in enumerate(endpoints):
        for j, ep2 in enumerate(endpoints):
            if i >= j:
                continue
            if ep1["curve_index"] == ep2["curve_index"]:
                continue
            if ep1["sketch_point"] == ep2["sketch_point"]:
                continue
            dx = ep1["coords"][0] - ep2["coords"][0]
            dy = ep1["coords"][1] - ep2["coords"][1]
            dist_cm = math.sqrt(dx * dx + dy * dy)
            dist_mm = dist_cm * 10
            if dist_mm > tolerance:
                continue
            key = tuple(sorted([(ep1["curve_index"], ep1["point_type"]),
                                (ep2["curve_index"], ep2["point_type"])]))
            if key in processed:
                continue
            processed.add(key)
            try:
                constraints.addCoincident(ep1["sketch_point"], ep2["sketch_point"])
                constraints_added.append({
                    "curve1": ep1["curve_index"], "point1": ep1["point_type"],
                    "curve2": ep2["curve_index"], "point2": ep2["point_type"],
                    "distance_mm": round(dist_mm, 6), "success": True,
                })
            except Exception as e:
                constraints_added.append({
                    "curve1": ep1["curve_index"], "point1": ep1["point_type"],
                    "curve2": ep2["curve_index"], "point2": ep2["point_type"],
                    "distance_mm": round(dist_mm, 6), "success": False, "error": str(e),
                })

    adsk.doEvents()
    return {
        "sketch_id": body["sketch_id"],
        "original_profile_count": sketch.profiles.count,
        "constraints_added": constraints_added,
        "new_profile_count": sketch.profiles.count,
        "summary": {
            "total_constraints": len(constraints_added),
            "successful": len([c for c in constraints_added if c["success"]]),
            "failed": len([c for c in constraints_added if not c["success"]]),
        },
    }


def handle_add_constraint(body):
    """Add a single geometric constraint to a sketch.

    Supported types: coincident, horizontal, vertical, perpendicular,
    parallel, tangent, equal, concentric, midpoint, fix, collinear.
    """
    sketch = get_sketch(body["sketch_id"])
    ctype = body["constraint_type"]
    gc = sketch.geometricConstraints

    def _get_entity(eid):
        parts = eid.rsplit("_curve_", 1)
        if len(parts) == 2:
            return sketch.sketchCurves.item(int(parts[1]))
        parts = eid.rsplit("_point_", 1)
        if len(parts) == 2:
            return sketch.sketchPoints.item(int(parts[1]))
        raise Exception(f"Cannot parse entity id: {eid}")

    e1 = _get_entity(body["entity1"])
    e2 = _get_entity(body["entity2"]) if body.get("entity2") else None

    if ctype == "coincident":
        gc.addCoincident(e1, e2)
    elif ctype == "horizontal":
        gc.addHorizontal(e1)
    elif ctype == "vertical":
        gc.addVertical(e1)
    elif ctype == "perpendicular":
        gc.addPerpendicular(e1, e2)
    elif ctype == "parallel":
        gc.addParallel(e1, e2)
    elif ctype == "tangent":
        gc.addTangent(e1, e2)
    elif ctype == "equal":
        gc.addEqual(e1, e2)
    elif ctype == "concentric":
        gc.addConcentric(e1, e2)
    elif ctype == "midpoint":
        gc.addMidPoint(e1, e2)
    elif ctype == "fix":
        gc.addFix(e1)
    elif ctype == "collinear":
        gc.addCollinear(e1, e2)
    else:
        raise Exception(f"Unknown constraint type: {ctype}")

    adsk.doEvents()
    return {"success": True, "constraint_type": ctype}


def handle_add_dimension(body):
    """Add a sketch dimension.

    Supported types: distance, diameter, radius, angular.
    """
    sketch = get_sketch(body["sketch_id"])
    dims = sketch.sketchDimensions
    dim_type = body["dimension_type"]

    def _get_entity(eid):
        parts = eid.rsplit("_curve_", 1)
        if len(parts) == 2:
            return sketch.sketchCurves.item(int(parts[1]))
        parts = eid.rsplit("_point_", 1)
        if len(parts) == 2:
            return sketch.sketchPoints.item(int(parts[1]))
        raise Exception(f"Cannot parse entity id: {eid}")

    text_pt = point2d(body.get("text_position", [0, 0]))

    if dim_type == "distance":
        e1 = _get_entity(body["entity1"])
        e2 = _get_entity(body["entity2"]) if body.get("entity2") else None
        if e2:
            dim = dims.addDistanceDimension(
                e1.startSketchPoint if hasattr(e1, "startSketchPoint") else e1,
                e2.startSketchPoint if hasattr(e2, "startSketchPoint") else e2,
                adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                text_pt,
            )
        else:
            dim = dims.addDistanceDimension(
                e1.startSketchPoint, e1.endSketchPoint,
                adsk.fusion.DimensionOrientations.AlignedDimensionOrientation,
                text_pt,
            )
    elif dim_type == "diameter":
        e1 = _get_entity(body["entity1"])
        dim = dims.addDiameterDimension(e1, text_pt)
    elif dim_type == "radius":
        e1 = _get_entity(body["entity1"])
        dim = dims.addRadialDimension(e1, text_pt)
    elif dim_type == "angular":
        e1 = _get_entity(body["entity1"])
        e2 = _get_entity(body["entity2"])
        dim = dims.addAngularDimension(e1, e2, text_pt)
    else:
        raise Exception(f"Unknown dimension type: {dim_type}")

    value_mm = body.get("value")
    if value_mm is not None:
        dim.parameter.expression = f"{value_mm} mm"

    adsk.doEvents()
    idx = sketch.sketchDimensions.count - 1
    return {
        "dimension_id": f"{body['sketch_id']}_dim_{idx}",
        "value_mm": dim.value * 10,
        "expression": dim.parameter.expression,
    }


def handle_list_constraints(body):
    """List all geometric constraints in a sketch."""
    sketch = get_sketch(body["sketch_id"])
    result = []
    for i in range(sketch.geometricConstraints.count):
        gc = sketch.geometricConstraints.item(i)
        result.append({
            "index": i,
            "type": gc.objectType.split("::")[-1],
            "is_driven": getattr(gc, "isDriven", False),
        })
    return {
        "sketch_id": body["sketch_id"],
        "constraint_count": len(result),
        "constraints": result,
    }


# ── Dimensions ───────────────────────────────────────────────

def handle_list_sketch_dimensions(body):
    """List all dimensions in a sketch with their values and expressions."""
    sketch = get_sketch(body["sketch_id"])
    dimensions = []
    for i, dim in enumerate(sketch.sketchDimensions):
        dim_info = {
            "dimension_id": f"{body['sketch_id']}_dim_{i}",
            "index": i,
            "type": dim.objectType.split("::")[-1],
            "value_mm": dim.value * 10,
        }
        try:
            param = dim.parameter
            if param:
                dim_info["expression"] = param.expression
                dim_info["parameter_name"] = param.name
                dim_info["is_driven"] = getattr(param, "isDrivenByConstraint", False)
        except Exception:
            pass
        try:
            if hasattr(dim, "textPosition"):
                pos = dim.textPosition
                dim_info["text_position"] = [pos.x * 10, pos.y * 10]
        except Exception:
            pass
        dimensions.append(dim_info)
    return {
        "sketch_id": body["sketch_id"],
        "dimension_count": len(dimensions),
        "dimensions": dimensions,
    }


def handle_edit_sketch_dimension(body):
    """Edit a sketch dimension by index or ID."""
    sketch = get_sketch(body["sketch_id"])
    dim_index = body.get("dimension_index")
    dim_id = body.get("dimension_id")
    dimension = None

    if dim_index is not None:
        if dim_index < sketch.sketchDimensions.count:
            dimension = sketch.sketchDimensions.item(dim_index)
    elif dim_id:
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

    param = dimension.parameter
    if not param:
        raise Exception("Dimension has no associated parameter")

    old_expression = param.expression
    old_value = dimension.value * 10

    expression = body.get("expression")
    value = body.get("value")
    if expression is not None:
        param.expression = expression
    elif value is not None:
        param.expression = f"{value} mm"
    else:
        raise Exception("Must provide either 'expression' or 'value'")

    new_value = dimension.value * 10
    resolved_idx = dim_index if dim_index is not None else parts[1]
    return {
        "success": True,
        "dimension_id": f"{body['sketch_id']}_dim_{resolved_idx}",
        "old_expression": old_expression,
        "old_value_mm": old_value,
        "new_expression": param.expression,
        "new_value_mm": new_value,
    }


# ── Gap analysis and repair ──────────────────────────────────

def handle_analyze_sketch_gaps(body):
    """Find gaps between curve endpoints that prevent profile closure."""
    sketch = get_sketch(body["sketch_id"])
    tolerance = body.get("tolerance", 0.01)

    endpoints = []
    curves_info = []
    for i, curve in enumerate(sketch.sketchCurves):
        curve_type = type(curve).__name__
        curve_data = {
            "index": i,
            "type": curve_type,
            "is_construction": getattr(curve, "isConstruction", False),
        }
        if curve_data["is_construction"]:
            curves_info.append(curve_data)
            continue
        if hasattr(curve, "startSketchPoint") and hasattr(curve, "endSketchPoint"):
            s = curve.startSketchPoint.geometry
            e = curve.endSketchPoint.geometry
            sc = [s.x * 10, s.y * 10]
            ec = [e.x * 10, e.y * 10]
            curve_data["start"] = sc
            curve_data["end"] = ec
            endpoints.append({"curve_index": i, "point_type": "start", "coords": sc,
                              "sketch_point": curve.startSketchPoint})
            endpoints.append({"curve_index": i, "point_type": "end", "coords": ec,
                              "sketch_point": curve.endSketchPoint})
        elif hasattr(curve, "centerSketchPoint"):
            center = curve.centerSketchPoint.geometry
            curve_data["center"] = [center.x * 10, center.y * 10]
            curve_data["is_closed"] = True
        curves_info.append(curve_data)

    gaps = []
    connected_pairs = set()
    for i, ep1 in enumerate(endpoints):
        for j, ep2 in enumerate(endpoints):
            if i >= j or ep1["curve_index"] == ep2["curve_index"]:
                continue
            dx = ep1["coords"][0] - ep2["coords"][0]
            dy = ep1["coords"][1] - ep2["coords"][1]
            dist = math.sqrt(dx * dx + dy * dy)
            same_point = ep1["sketch_point"] == ep2["sketch_point"]
            if same_point:
                connected_pairs.add((ep1["curve_index"], ep2["curve_index"]))
            elif dist < tolerance * 10:
                gaps.append({
                    "curve1_index": ep1["curve_index"], "curve1_point": ep1["point_type"],
                    "curve2_index": ep2["curve_index"], "curve2_point": ep2["point_type"],
                    "distance_mm": round(dist, 6),
                    "point1": ep1["coords"], "point2": ep2["coords"],
                    "can_auto_close": dist <= tolerance,
                })

    dangling = []
    for ep in endpoints:
        idx = ep["curve_index"]
        is_connected = False
        for c1, c2 in connected_pairs:
            if idx == c1 or idx == c2:
                is_connected = True
                break
        if not is_connected:
            for gap in gaps:
                if gap["curve1_index"] == idx or gap["curve2_index"] == idx:
                    is_connected = True
                    break
        if not is_connected:
            dangling.append({"curve_index": idx, "point_type": ep["point_type"], "coords": ep["coords"]})

    gaps.sort(key=lambda g: g["distance_mm"])
    return {
        "sketch_id": body["sketch_id"],
        "profile_count": sketch.profiles.count,
        "curve_count": sketch.sketchCurves.count,
        "tolerance_mm": tolerance,
        "curves": curves_info,
        "gaps": gaps,
        "dangling_endpoints": dangling,
        "connected_curve_pairs": [[c1, c2] for c1, c2 in connected_pairs],
        "summary": {
            "total_gaps": len(gaps),
            "auto_closeable_gaps": len([g for g in gaps if g["can_auto_close"]]),
            "dangling_count": len(dangling),
            "needs_fixing": len(gaps) > 0 or len(dangling) > 0,
        },
    }


def handle_close_sketch_gaps(body):
    """Close gaps by merging close endpoints or adding bridge lines."""
    sketch = get_sketch(body["sketch_id"])
    tolerance = body.get("tolerance", 0.01)
    max_line_gap = body.get("max_line_gap", 1.0)
    dry_run = body.get("dry_run", False)

    analysis = handle_analyze_sketch_gaps({"sketch_id": body["sketch_id"], "tolerance": tolerance})
    actions = []
    merged_count = lines_added = 0

    endpoint_map = {}
    for i, curve in enumerate(sketch.sketchCurves):
        if getattr(curve, "isConstruction", False):
            continue
        if hasattr(curve, "startSketchPoint") and hasattr(curve, "endSketchPoint"):
            endpoint_map[(i, "start")] = curve.startSketchPoint
            endpoint_map[(i, "end")] = curve.endSketchPoint

    processed_points = set()
    for gap in analysis["gaps"]:
        c1_idx, c1_pt = gap["curve1_index"], gap["curve1_point"]
        c2_idx, c2_pt = gap["curve2_index"], gap["curve2_point"]
        dist = gap["distance_mm"]
        key1, key2 = (c1_idx, c1_pt), (c2_idx, c2_pt)
        if key1 in processed_points or key2 in processed_points:
            continue
        if key1 not in endpoint_map or key2 not in endpoint_map:
            continue
        sp1, sp2 = endpoint_map[key1], endpoint_map[key2]

        if dist <= tolerance:
            action = {"type": "merge", "from_curve": c2_idx, "from_point": c2_pt,
                      "to_curve": c1_idx, "to_point": c1_pt, "distance_mm": dist}
            if not dry_run:
                try:
                    sp2.move(adsk.core.Vector3D.create(
                        sp1.geometry.x - sp2.geometry.x,
                        sp1.geometry.y - sp2.geometry.y, 0))
                    merged_count += 1
                    action["success"] = True
                except Exception as e:
                    action["success"] = False
                    action["error"] = str(e)
            actions.append(action)
            processed_points.update([key1, key2])
        elif dist <= max_line_gap:
            action = {"type": "bridge_line", "from_curve": c1_idx, "from_point": c1_pt,
                      "to_curve": c2_idx, "to_point": c2_pt, "distance_mm": dist}
            if not dry_run:
                try:
                    sketch.sketchCurves.sketchLines.addByTwoPoints(sp1.geometry, sp2.geometry)
                    lines_added += 1
                    action["success"] = True
                except Exception as e:
                    action["success"] = False
                    action["error"] = str(e)
            actions.append(action)
            processed_points.update([key1, key2])

    adsk.doEvents()
    return {
        "sketch_id": body["sketch_id"],
        "dry_run": dry_run,
        "original_profile_count": analysis["profile_count"],
        "new_profile_count": sketch.profiles.count,
        "actions": actions,
        "summary": {
            "points_merged": merged_count,
            "lines_added": lines_added,
            "total_actions": len(actions),
            "profiles_created": sketch.profiles.count - analysis["profile_count"],
        },
    }


def handle_recreate_sketch_as_polygon(body):
    """Recreate a sketch as a proper closed polygon."""
    sketch_id = body.get("sketch_id")
    new_name = body.get("new_sketch_name", f"{sketch_id}_fixed")
    vertices = body.get("vertices")
    delete_original = body.get("delete_original", False)
    orig_sketch = get_sketch(sketch_id)
    sketch_plane = orig_sketch.referencePlane

    if not vertices:
        vert_set = set()
        edges = []
        for curve in orig_sketch.sketchCurves:
            if getattr(curve, "isConstruction", False):
                continue
            if hasattr(curve, "startSketchPoint") and hasattr(curve, "endSketchPoint"):
                s = curve.startSketchPoint.geometry
                e = curve.endSketchPoint.geometry
                sv = (round(s.x * 10, 4), round(s.y * 10, 4))
                ev = (round(e.x * 10, 4), round(e.y * 10, 4))
                vert_set.add(sv)
                vert_set.add(ev)
                edges.append((sv, ev))
        verts = list(vert_set)
        cx = sum(v[0] for v in verts) / len(verts)
        cy = sum(v[1] for v in verts) / len(verts)
        verts.sort(key=lambda v: math.atan2(v[1] - cy, v[0] - cx))
        vertices = [[v[0], v[1]] for v in verts]

    root = get_root()
    new_sketch = root.sketches.add(sketch_plane)
    new_sketch.name = new_name
    lines = new_sketch.sketchCurves.sketchLines
    for i in range(len(vertices)):
        s = vertices[i]
        e = vertices[(i + 1) % len(vertices)]
        sp = adsk.core.Point3D.create(s[0] / 10.0, s[1] / 10.0, 0)
        ep = adsk.core.Point3D.create(e[0] / 10.0, e[1] / 10.0, 0)
        lines.addByTwoPoints(sp, ep)
    adsk.doEvents()

    if delete_original:
        try:
            orig_sketch.deleteMe()
        except Exception:
            pass

    return {
        "success": True,
        "original_sketch": sketch_id,
        "new_sketch": new_name,
        "vertices_used": len(vertices),
        "lines_drawn": len(vertices),
        "profile_count": new_sketch.profiles.count,
        "is_closed": new_sketch.profiles.count > 0,
        "vertices": vertices,
    }


# ── Query / coordinate helpers ───────────────────────────────

def handle_get_sketch_profiles(body):
    sketch = get_sketch(body["sketch_id"])
    plane = sketch.referencePlane
    plane_origin = plane_normal = None
    plane_type = "unknown"
    try:
        if hasattr(plane, "geometry"):
            geo = plane.geometry
            plane_origin = [geo.origin.x * 10, geo.origin.y * 10, geo.origin.z * 10]
            plane_normal = [geo.normal.x, geo.normal.y, geo.normal.z]
            nx, ny, nz = abs(geo.normal.x), abs(geo.normal.y), abs(geo.normal.z)
            if nz > 0.9:
                plane_type = "XY"
            elif ny > 0.9:
                plane_type = "XZ"
            elif nx > 0.9:
                plane_type = "YZ"
    except Exception:
        pass

    profiles = []
    for i in range(sketch.profiles.count):
        profile = sketch.profiles.item(i)
        bbox = profile.boundingBox
        smin = [bbox.minPoint.x * 10, bbox.minPoint.y * 10]
        smax = [bbox.maxPoint.x * 10, bbox.maxPoint.y * 10]
        world_min_3d = world_max_3d = None
        try:
            transform = sketch.transform
            mn = adsk.core.Point3D.create(bbox.minPoint.x, bbox.minPoint.y, 0)
            mx = adsk.core.Point3D.create(bbox.maxPoint.x, bbox.maxPoint.y, 0)
            mn.transformBy(transform)
            mx.transformBy(transform)
            world_min_3d = [mn.x * 10, mn.y * 10, mn.z * 10]
            world_max_3d = [mx.x * 10, mx.y * 10, mx.z * 10]
        except Exception:
            pass
        info = {
            "profile_id": f"profile_{i}",
            "profile_index": i,
            "area_mm2": profile.areaProperties().area * 100,
            "sketch_bounds": {"min": smin, "max": smax},
        }
        if world_min_3d and world_max_3d:
            info["world_bounds_3d"] = {"min": world_min_3d, "max": world_max_3d}
        profiles.append(info)

    result = {"sketch_id": body["sketch_id"], "profile_count": len(profiles),
              "profiles": profiles, "plane_type": plane_type}
    if plane_origin:
        result["plane_origin"] = plane_origin
    if plane_normal:
        result["plane_normal"] = plane_normal
    return result


def handle_suggest_sketch_coords(body):
    """Suggest sketch coordinates for a desired 3D bounding box."""
    plane = body.get("plane", "xy").lower()
    world_min = body.get("world_min", [0, 0, 0])
    world_max = body.get("world_max", [100, 100, 100])

    if plane in ("xy", "horizontal"):
        sc1 = [world_min[0], world_min[1]]
        sc2 = [world_max[0], world_max[1]]
        extrude = {
            "to_reach_z_min": {"direction": "negative", "distance": abs(world_min[2])},
            "to_reach_z_max": {"direction": "positive", "distance": abs(world_max[2])},
            "plane_at_z": 0,
        }
        explanation = "On XY plane: sketch coordinates map directly to world X and Y"
    elif plane in ("xz", "vertical_front"):
        sc1 = [world_min[0], -world_max[2]]
        sc2 = [world_max[0], -world_min[2]]
        extrude = {
            "to_reach_y_min": {"direction": "negative", "distance": abs(world_min[1])},
            "to_reach_y_max": {"direction": "positive", "distance": abs(world_max[1])},
            "plane_at_y": 0,
        }
        explanation = "On XZ plane: sketch_x = world_x, but sketch_y = NEGATIVE world_z (flipped!)"
    elif plane in ("yz", "vertical_side"):
        sc1 = [-world_max[2], world_min[1]]
        sc2 = [-world_min[2], world_max[1]]
        extrude = {
            "to_reach_x_min": {"direction": "negative", "distance": abs(world_min[0])},
            "to_reach_x_max": {"direction": "positive", "distance": abs(world_max[0])},
            "plane_at_x": 0,
        }
        explanation = "On YZ plane: sketch_x = NEGATIVE world_z (flipped!), sketch_y = world_y"
    else:
        return {"error": True, "message": f"Unknown plane: {plane}. Use xy, xz, or yz."}

    return {
        "plane": plane,
        "input_world_bounds": {"min": world_min, "max": world_max},
        "sketch_rectangle": {
            "corner1": [round(sc1[0], 3), round(sc1[1], 3)],
            "corner2": [round(sc2[0], 3), round(sc2[1], 3)],
        },
        "extrude_guidance": extrude,
        "explanation": explanation,
        "example_usage": f"draw_rectangle(corner1={[round(sc1[0],1), round(sc1[1],1)]}, corner2={[round(sc2[0],1), round(sc2[1],1)]})",
    }


def handle_sketch_to_3d_coords(body):
    """Convert 2D sketch coordinates to 3D world coordinates."""
    sketch = get_sketch(body["sketch_id"])
    points_2d = body.get("points", [[0, 0]])
    transform = sketch.transform
    plane = sketch.referencePlane

    results = []
    for pt_2d in points_2d:
        pt = adsk.core.Point3D.create(pt_2d[0] / 10.0, pt_2d[1] / 10.0, 0)
        pt.transformBy(transform)
        results.append({
            "input_2d": pt_2d,
            "output_3d": [round(pt.x * 10, 2), round(pt.y * 10, 2), round(pt.z * 10, 2)],
        })

    plane_info = {}
    try:
        if hasattr(plane, "geometry"):
            geo = plane.geometry
            if hasattr(geo, "normal"):
                plane_info["normal"] = [geo.normal.x, geo.normal.y, geo.normal.z]
            if hasattr(geo, "origin"):
                plane_info["origin_mm"] = [geo.origin.x * 10, geo.origin.y * 10, geo.origin.z * 10]
    except Exception:
        pass

    return {
        "sketch_id": body["sketch_id"],
        "plane_info": plane_info,
        "coordinate_mapping": results,
        "note": "2D sketch coords [x, y] map to 3D coords based on plane orientation",
    }


def handle_get_sketch_info(body):
    """Get detailed info about a single sketch — curves, points, constraints, dims."""
    sketch = get_sketch(body["sketch_id"])
    curves = []
    for i in range(sketch.sketchCurves.count):
        c = sketch.sketchCurves.item(i)
        info = {
            "index": i,
            "curve_id": f"{body['sketch_id']}_curve_{i}",
            "type": type(c).__name__,
            "is_construction": getattr(c, "isConstruction", False),
        }
        if hasattr(c, "startSketchPoint") and hasattr(c, "endSketchPoint"):
            s = c.startSketchPoint.geometry
            e = c.endSketchPoint.geometry
            info["start"] = [round(s.x * 10, 4), round(s.y * 10, 4)]
            info["end"] = [round(e.x * 10, 4), round(e.y * 10, 4)]
            if hasattr(c, "length"):
                info["length_mm"] = round(c.length * 10, 4)
        if hasattr(c, "centerSketchPoint"):
            cp = c.centerSketchPoint.geometry
            info["center"] = [round(cp.x * 10, 4), round(cp.y * 10, 4)]
        if hasattr(c, "radius"):
            info["radius_mm"] = round(c.radius * 10, 4)
        curves.append(info)

    points = []
    for i in range(sketch.sketchPoints.count):
        p = sketch.sketchPoints.item(i)
        g = p.geometry
        points.append({
            "index": i,
            "point_id": f"{body['sketch_id']}_point_{i}",
            "coords": [round(g.x * 10, 4), round(g.y * 10, 4)],
            "is_connected": p.connectedEntities.count > 0,
        })

    return {
        "sketch_id": body["sketch_id"],
        "curve_count": len(curves),
        "point_count": len(points),
        "profile_count": sketch.profiles.count,
        "is_fully_constrained": getattr(sketch, "isFullyConstrained", None),
        "curves": curves,
        "points": points,
    }


# ── Import / Text ────────────────────────────────────────────

def handle_import_svg(body):
    """Import an SVG file into a sketch on a face or plane."""
    root = get_root()
    svg_path = body.get("svg_path")
    if not svg_path:
        raise Exception("svg_path is required")
    if not os.path.exists(svg_path):
        raise Exception(f"SVG file not found: {svg_path}")

    target_face = None
    body_id = body.get("body_id")
    face_index = body.get("face_index", 0)
    plane_id = body.get("plane")

    if body_id:
        for b in root.bRepBodies:
            if b.name == body_id:
                planar_faces = []
                for i, face in enumerate(b.faces):
                    geo = face.geometry
                    if hasattr(geo, "surfaceType") and geo.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                        if hasattr(geo, "normal") and abs(geo.normal.z) > 0.9:
                            planar_faces.append((i, face, geo.normal.z))
                planar_faces.sort(key=lambda x: x[2], reverse=True)
                if face_index < len(planar_faces):
                    target_face = planar_faces[face_index][1]
                elif planar_faces:
                    target_face = planar_faces[0][1]
                else:
                    raise Exception(f"No planar faces found on body: {body_id}")
                break
        if not target_face:
            raise Exception(f"Body not found: {body_id}")
    elif plane_id:
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

    sketch = root.sketches.add(target_face)
    sketch.name = body.get("sketch_name", "SVG_Import")
    x_off = body.get("x_offset", 0) / 10.0
    y_off = body.get("y_offset", 0) / 10.0
    scale = body.get("scale", 1.0)
    sketch.importSVG(svg_path, x_off, y_off, scale)
    adsk.doEvents()
    return {
        "success": True,
        "sketch_id": sketch.name,
        "profile_count": sketch.profiles.count,
        "curve_count": sketch.sketchCurves.count,
        "message": f"SVG imported with {sketch.sketchCurves.count} curves and {sketch.profiles.count} profiles",
    }


def handle_add_text(body):
    """Add text to a sketch."""
    root = get_root()
    text = body.get("text")
    if not text:
        raise Exception("text is required")
    font_name = body.get("font", "Arial")
    height = body.get("height", 10) / 10.0

    sketch_id = body.get("sketch_id")
    body_id = body.get("body_id")
    plane_id = body.get("plane")
    sketch = None

    if sketch_id:
        sketch = root.sketches.itemByName(sketch_id)
        if not sketch:
            raise Exception(f"Sketch not found: {sketch_id}")
    elif body_id:
        for b in root.bRepBodies:
            if b.name == body_id:
                for face in b.faces:
                    geo = face.geometry
                    if hasattr(geo, "surfaceType") and geo.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                        if hasattr(geo, "normal") and geo.normal.z > 0.9:
                            sketch = root.sketches.add(face)
                            break
                break
        if not sketch:
            raise Exception(f"Could not create sketch on body: {body_id}")
    elif plane_id:
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

    if body.get("sketch_name"):
        sketch.name = body["sketch_name"]

    x = body.get("x", 0) / 10.0
    y = body.get("y", 0) / 10.0
    position = adsk.core.Point3D.create(x, y, 0)
    rotation_rad = body.get("rotation", 0) * math.pi / 180.0

    texts = sketch.sketchTexts
    text_input = texts.createInput(text, height, position)
    text_input.fontName = font_name
    text_input.angle = rotation_rad
    if body.get("bold", False):
        text_input.isBold = True
    if body.get("italic", False):
        text_input.isItalic = True
    texts.add(text_input)
    adsk.doEvents()

    return {
        "success": True,
        "sketch_id": sketch.name,
        "profile_count": sketch.profiles.count,
        "message": f"Text '{text}' added with {sketch.profiles.count} profiles",
    }


# ── Route table fragment ─────────────────────────────────────

SKETCH_ROUTES = {
    "/create_sketch": handle_create_sketch,
    "/create_sketch_on_face": handle_create_sketch_on_face,
    "/finish_sketch": handle_finish_sketch,
    "/delete_sketch": handle_delete_sketch,
    "/list_sketches": handle_list_sketches,
    "/draw_line": handle_draw_line,
    "/draw_arc": handle_draw_arc,
    "/draw_arc_3point": handle_draw_arc_3point,
    "/draw_circle": handle_draw_circle,
    "/draw_rectangle": handle_draw_rectangle,
    "/draw_rectangle_3d": handle_draw_rectangle_3d,
    "/draw_spline": handle_draw_spline,
    "/draw_polygon": handle_draw_polygon,
    "/draw_slot": handle_draw_slot,
    "/draw_centerline": handle_draw_centerline,
    "/draw_point": handle_draw_point,
    "/sketch_fillet": handle_sketch_fillet,
    "/sketch_trim": handle_sketch_trim,
    "/sketch_extend": handle_sketch_extend,
    "/sketch_offset": handle_sketch_offset,
    "/sketch_mirror": handle_sketch_mirror,
    "/sketch_pattern_rectangular": handle_sketch_pattern_rectangular,
    "/sketch_pattern_circular": handle_sketch_pattern_circular,
    "/apply_coincident_constraints": handle_apply_coincident_constraints,
    "/add_constraint": handle_add_constraint,
    "/add_dimension": handle_add_dimension,
    "/list_constraints": handle_list_constraints,
    "/list_sketch_dimensions": handle_list_sketch_dimensions,
    "/edit_sketch_dimension": handle_edit_sketch_dimension,
    "/analyze_sketch_gaps": handle_analyze_sketch_gaps,
    "/close_sketch_gaps": handle_close_sketch_gaps,
    "/recreate_sketch_as_polygon": handle_recreate_sketch_as_polygon,
    "/get_sketch_profiles": handle_get_sketch_profiles,
    "/suggest_sketch_coords": handle_suggest_sketch_coords,
    "/sketch_to_3d_coords": handle_sketch_to_3d_coords,
    "/get_sketch_info": handle_get_sketch_info,
    "/import_svg": handle_import_svg,
    "/add_text": handle_add_text,
}
