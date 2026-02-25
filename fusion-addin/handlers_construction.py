"""Construction / reference geometry handlers — planes, axes, points, measurements.

Every public function has the signature ``handle_*(body: dict) -> dict``
and is registered in CONSTRUCTION_ROUTES by the main bridge orchestrator.
"""
import math
import traceback

import adsk.core
import adsk.fusion

try:
    from bridge_helpers import (
        get_design, get_root, get_component_by_name,
        get_sketch, point3d, vector3d,
    )
except ImportError:
    from .bridge_helpers import (
        get_design, get_root, get_component_by_name,
        get_sketch, point3d, vector3d,
    )


# ── Helpers ───────────────────────────────────────────────────

def _resolve_plane(root, plane_id):
    """Resolve a plane ID to a construction plane object."""
    builtins = {
        "xy": root.xYConstructionPlane,
        "xz": root.xZConstructionPlane,
        "yz": root.yZConstructionPlane,
    }
    if plane_id in builtins:
        return builtins[plane_id]
    p = root.constructionPlanes.itemByName(plane_id)
    if p:
        return p
    return None


def _resolve_axis(root, axis_id):
    """Resolve an axis ID to a construction axis object."""
    builtins = {
        "x": root.xConstructionAxis,
        "y": root.yConstructionAxis,
        "z": root.zConstructionAxis,
    }
    if axis_id in builtins:
        return builtins[axis_id]
    a = root.constructionAxes.itemByName(axis_id)
    if a:
        return a
    return None


def _resolve_body(root, body_name):
    for b in root.bRepBodies:
        if b.name == body_name:
            return b
    for occ in root.allOccurrences:
        for b in occ.component.bRepBodies:
            if b.name == body_name:
                return b
    return None


def _resolve_face(root, body_name, face_id):
    body = _resolve_body(root, body_name)
    if not body:
        raise Exception(f"Body not found: {body_name}")
    if "_face_" in face_id:
        idx = int(face_id.split("_face_")[-1])
    else:
        idx = int(face_id)
    if 0 <= idx < body.faces.count:
        return body.faces.item(idx)
    raise Exception(f"Face index {idx} out of range (body has {body.faces.count} faces)")


def _plane_info(plane):
    """Return a standard dict describing a construction plane."""
    geo = plane.geometry
    return {
        "plane_id": plane.name,
        "name": plane.name,
        "origin_mm": [round(geo.origin.x * 10, 4), round(geo.origin.y * 10, 4), round(geo.origin.z * 10, 4)],
        "normal": [round(geo.normal.x, 6), round(geo.normal.y, 6), round(geo.normal.z, 6)],
    }


def _axis_info(axis):
    """Return a standard dict describing a construction axis."""
    geo = axis.geometry
    origin = geo.origin
    direction = geo.direction
    return {
        "axis_id": axis.name,
        "name": axis.name,
        "origin_mm": [round(origin.x * 10, 4), round(origin.y * 10, 4), round(origin.z * 10, 4)],
        "direction": [round(direction.x, 6), round(direction.y, 6), round(direction.z, 6)],
    }


def _point_info(pt):
    """Return a standard dict describing a construction point."""
    geo = pt.geometry
    return {
        "point_id": pt.name,
        "name": pt.name,
        "position_mm": [round(geo.x * 10, 4), round(geo.y * 10, 4), round(geo.z * 10, 4)],
    }


# ══════════════════════════════════════════════════════════════
# PLANES
# ══════════════════════════════════════════════════════════════

def handle_list_planes(body):
    """List all construction planes (built-in + user-created)."""
    root = get_root()
    planes = [
        {"id": "xy", "name": "XY Plane", "origin": [0, 0, 0], "normal": [0, 0, 1]},
        {"id": "xz", "name": "XZ Plane", "origin": [0, 0, 0], "normal": [0, 1, 0]},
        {"id": "yz", "name": "YZ Plane", "origin": [0, 0, 0], "normal": [1, 0, 0]},
    ]
    for p in root.constructionPlanes:
        geo = p.geometry
        planes.append({
            "id": p.name, "name": p.name,
            "origin": [round(geo.origin.x * 10, 4), round(geo.origin.y * 10, 4), round(geo.origin.z * 10, 4)],
            "normal": [round(geo.normal.x, 6), round(geo.normal.y, 6), round(geo.normal.z, 6)],
        })
    return {"planes": planes, "count": len(planes)}


def handle_create_offset_plane(body):
    """Create a plane offset from a base plane by a distance in mm."""
    root = get_root()
    base_plane_id = body.get("base_plane", "xy")
    offset = body.get("offset", 10)
    component_name = body.get("component")
    name = body.get("name")

    if component_name:
        target, _ = get_component_by_name(component_name)
        if not target:
            raise Exception(f"Component not found: {component_name}")
    else:
        target = root

    base = _resolve_plane(target, base_plane_id)
    if not base:
        base = _resolve_plane(root, base_plane_id)
    if not base:
        raise Exception(f"Plane not found: {base_plane_id}")

    planes = target.constructionPlanes
    pi = planes.createInput()
    pi.setByOffset(base, adsk.core.ValueInput.createByReal(offset / 10.0))
    cp = planes.add(pi)
    if name:
        cp.name = name
    adsk.doEvents()
    return _plane_info(cp)


def handle_create_angled_plane(body):
    """Create a plane at arbitrary orientation via point+normal or three points.

    Tries setByPlane first (direct design). Falls back to setByThreePoints
    with helper sketch points for parametric mode.
    """
    try:
        root = get_root()
        planes = root.constructionPlanes
        name = body.get("name")
        tolerance_mm = body.get("tolerance", 1.0)
        three_points_input = body.get("three_points")
        point_coords = body.get("point")
        normal_coords = body.get("normal")

        if three_points_input and len(three_points_input) >= 3:
            pts_mm = [list(p) for p in three_points_input[:3]]
        elif point_coords and normal_coords:
            n = list(normal_coords)
            mag_n = math.sqrt(sum(x * x for x in n))
            n = [x / mag_n for x in n]
            ref = [0, 1, 0] if abs(n[1]) < 0.9 else [1, 0, 0]
            u = [ref[1]*n[2]-ref[2]*n[1], ref[2]*n[0]-ref[0]*n[2], ref[0]*n[1]-ref[1]*n[0]]
            mag_u = math.sqrt(sum(x * x for x in u))
            u = [x / mag_u for x in u]
            v = [n[1]*u[2]-n[2]*u[1], n[2]*u[0]-n[0]*u[2], n[0]*u[1]-n[1]*u[0]]
            sp = 100.0
            pts_mm = [
                list(point_coords),
                [point_coords[0]+u[0]*sp, point_coords[1]+u[1]*sp, point_coords[2]+u[2]*sp],
                [point_coords[0]+v[0]*sp, point_coords[1]+v[1]*sp, point_coords[2]+v[2]*sp],
            ]
        else:
            raise Exception("Provide 'three_points' or 'point' + 'normal'")

        v1 = [pts_mm[1][i]-pts_mm[0][i] for i in range(3)]
        v2 = [pts_mm[2][i]-pts_mm[0][i] for i in range(3)]
        cn = [v1[1]*v2[2]-v1[2]*v2[1], v1[2]*v2[0]-v1[0]*v2[2], v1[0]*v2[1]-v1[1]*v2[0]]
        mag = math.sqrt(sum(x * x for x in cn))
        if mag < 1e-10:
            raise Exception("Points are collinear — cannot define a plane")
        cn = [x / mag for x in cn]

        # Fast path: setByPlane (direct design)
        try:
            p_cm = adsk.core.Point3D.create(pts_mm[0][0]/10, pts_mm[0][1]/10, pts_mm[0][2]/10)
            nrm = adsk.core.Vector3D.create(*cn)
            nrm.normalize()
            pi = planes.createInput()
            pi.setByPlane(adsk.core.Plane.create(p_cm, nrm))
            cp = planes.add(pi)
            if name:
                cp.name = name
            adsk.doEvents()
            result = _plane_info(cp)
            result["method"] = "setByPlane"
            return result
        except Exception:
            pass

        # Parametric path: resolve/create sketch points, then setByThreePoints
        tol_cm = tolerance_mm / 10.0
        resolved = []
        helper_planes = []
        helper_sketches = []
        for i, coords in enumerate(pts_mm):
            target_cm = adsk.core.Point3D.create(coords[0]/10, coords[1]/10, coords[2]/10)
            best_sp = None
            best_dist = float('inf')
            for sk in root.sketches:
                for j in range(sk.sketchPoints.count):
                    sp = sk.sketchPoints.item(j)
                    try:
                        d = target_cm.distanceTo(sp.worldGeometry)
                        if d < best_dist:
                            best_dist = d
                            best_sp = sp
                    except Exception:
                        continue
            if best_sp and best_dist <= tol_cm:
                resolved.append(best_sp)
            else:
                oi = planes.createInput()
                oi.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(coords[2]/10))
                hp = planes.add(oi)
                hp.name = f"_ap_helper_plane_{i}"
                helper_planes.append(hp.name)
                hs = root.sketches.add(hp)
                hs.name = f"_ap_helper_sketch_{i}"
                helper_sketches.append(hs.name)
                sp = hs.sketchPoints.add(adsk.core.Point3D.create(coords[0]/10, coords[1]/10, 0))
                resolved.append(sp)

        pi = planes.createInput()
        pi.setByThreePoints(resolved[0], resolved[1], resolved[2])
        cp = planes.add(pi)
        if name:
            cp.name = name
        adsk.doEvents()
        result = _plane_info(cp)
        result["method"] = "setByThreePoints"
        if helper_planes:
            result["helper_geometry"] = {"planes": helper_planes, "sketches": helper_sketches}
        return result
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_plane_by_angle(body):
    """Create a plane at an angle to a base plane, rotating around a sketch line."""
    try:
        root = get_root()
        planes = root.constructionPlanes
        base_plane_id = body.get("base_plane", "xy")
        sketch_id = body.get("sketch_id")
        line_index = body.get("line_index", 0)
        angle_deg = body.get("angle", 0)
        name = body.get("name")

        base = _resolve_plane(root, base_plane_id)
        if not base:
            raise Exception(f"Base plane not found: {base_plane_id}")

        sk = get_sketch(sketch_id)
        if line_index >= sk.sketchCurves.sketchLines.count:
            raise Exception(f"Line index {line_index} out of range")
        line = sk.sketchCurves.sketchLines.item(line_index)

        pi = planes.createInput()
        pi.setByAngle(line, adsk.core.ValueInput.createByReal(angle_deg * math.pi / 180.0), base)
        cp = planes.add(pi)
        if name:
            cp.name = name
        adsk.doEvents()
        return _plane_info(cp)
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_midplane(body):
    """Create a midplane between two parallel planes or two planar faces.

    Args:
        plane1: First plane ID (xy/xz/yz/custom) or "body:face" reference
        plane2: Second plane ID or "body:face" reference
        name: Optional name
    """
    try:
        root = get_root()
        planes = root.constructionPlanes

        plane1_id = body.get("plane1")
        plane2_id = body.get("plane2")
        name = body.get("name")

        if not plane1_id or not plane2_id:
            raise Exception("Both plane1 and plane2 are required")

        def resolve_plane_or_face(pid):
            if ":" in str(pid):
                parts = pid.split(":")
                body_name = parts[0]
                face_id = parts[1]
                return _resolve_face(root, body_name, face_id)
            return _resolve_plane(root, pid)

        p1 = resolve_plane_or_face(plane1_id)
        p2 = resolve_plane_or_face(plane2_id)
        if not p1:
            raise Exception(f"First entity not found: {plane1_id}")
        if not p2:
            raise Exception(f"Second entity not found: {plane2_id}")

        pi = planes.createInput()
        pi.setByTwoPlanes(p1, p2)
        cp = planes.add(pi)
        if name:
            cp.name = name
        adsk.doEvents()
        return _plane_info(cp)
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_tangent_plane(body):
    """Create a plane tangent to a cylindrical or spherical face at a point.

    Args:
        body_id: Body containing the face
        face_id: Face ID (e.g., "Body1_face_3" or index)
        point: [x, y, z] point on the surface in mm
        name: Optional name
    """
    try:
        root = get_root()
        planes = root.constructionPlanes
        body_name = body.get("body_id")
        face_id = body.get("face_id")
        point_mm = body.get("point")
        name = body.get("name")

        if not body_name or not face_id:
            raise Exception("body_id and face_id are required")

        face = _resolve_face(root, body_name, face_id)
        pi = planes.createInput()

        if point_mm:
            pt = adsk.core.Point3D.create(point_mm[0]/10, point_mm[1]/10, point_mm[2]/10)
            pi.setByTangentAtPoint(face, pt)
        else:
            pi.setByTangent(face, adsk.core.ValueInput.createByReal(0))

        cp = planes.add(pi)
        if name:
            cp.name = name
        adsk.doEvents()
        return _plane_info(cp)
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_delete_plane(body):
    """Delete a user-created construction plane by name."""
    root = get_root()
    plane_name = body.get("name")
    if not plane_name:
        raise Exception("name is required")
    for p in root.constructionPlanes:
        if p.name == plane_name:
            p.deleteMe()
            adsk.doEvents()
            return {"success": True, "deleted": plane_name}
    raise Exception(f"Construction plane not found: {plane_name}")


# ══════════════════════════════════════════════════════════════
# AXES
# ══════════════════════════════════════════════════════════════

def handle_list_axes(body):
    """List all construction axes (built-in + user-created)."""
    root = get_root()
    axes = [
        {"id": "x", "name": "X Axis", "origin": [0, 0, 0], "direction": [1, 0, 0]},
        {"id": "y", "name": "Y Axis", "origin": [0, 0, 0], "direction": [0, 1, 0]},
        {"id": "z", "name": "Z Axis", "origin": [0, 0, 0], "direction": [0, 0, 1]},
    ]
    for a in root.constructionAxes:
        geo = a.geometry
        axes.append({
            "id": a.name, "name": a.name,
            "origin": [round(geo.origin.x * 10, 4), round(geo.origin.y * 10, 4), round(geo.origin.z * 10, 4)],
            "direction": [round(geo.direction.x, 6), round(geo.direction.y, 6), round(geo.direction.z, 6)],
        })
    return {"axes": axes, "count": len(axes)}


def handle_create_axis_two_points(body):
    """Create a construction axis through two points.

    Args:
        point1: [x, y, z] first point in mm
        point2: [x, y, z] second point in mm
        name: Optional name
    """
    try:
        root = get_root()
        axes = root.constructionAxes
        p1_mm = body.get("point1")
        p2_mm = body.get("point2")
        name = body.get("name")

        if not p1_mm or not p2_mm:
            raise Exception("point1 and point2 are required")

        p1 = adsk.core.Point3D.create(p1_mm[0]/10, p1_mm[1]/10, p1_mm[2]/10)
        p2 = adsk.core.Point3D.create(p2_mm[0]/10, p2_mm[1]/10, p2_mm[2]/10)

        # Need sketch points or construction points for parametric mode
        # Use a helper sketch on XY offset plane
        helper_planes = []
        helper_sketches = []
        pts = []
        for i, (coords, pt) in enumerate([(p1_mm, p1), (p2_mm, p2)]):
            pi_plane = root.constructionPlanes.createInput()
            pi_plane.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(coords[2]/10))
            hp = root.constructionPlanes.add(pi_plane)
            hp.name = f"_ax_helper_plane_{i}"
            helper_planes.append(hp.name)
            hs = root.sketches.add(hp)
            hs.name = f"_ax_helper_sketch_{i}"
            helper_sketches.append(hs.name)
            sp = hs.sketchPoints.add(adsk.core.Point3D.create(coords[0]/10, coords[1]/10, 0))
            pts.append(sp)

        ai = axes.createInput()
        ai.setByTwoPoints(pts[0], pts[1])
        axis = axes.add(ai)
        if name:
            axis.name = name
        adsk.doEvents()
        result = _axis_info(axis)
        result["helper_geometry"] = {"planes": helper_planes, "sketches": helper_sketches}
        return result
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_axis_by_edge(body):
    """Create a construction axis along a body edge.

    Args:
        body_id: Body name
        edge_id: Edge ID (e.g., "Body1_edge_0")
        name: Optional name
    """
    try:
        root = get_root()
        axes = root.constructionAxes
        body_name = body.get("body_id")
        edge_id = body.get("edge_id")
        name = body.get("name")

        if not body_name or not edge_id:
            raise Exception("body_id and edge_id are required")

        target = _resolve_body(root, body_name)
        if not target:
            raise Exception(f"Body not found: {body_name}")

        parts = edge_id.rsplit("_edge_", 1)
        if len(parts) != 2:
            raise Exception(f"Invalid edge ID format: {edge_id}")
        idx = int(parts[1])
        if idx >= target.edges.count:
            raise Exception(f"Edge index {idx} out of range (body has {target.edges.count} edges)")
        edge = target.edges.item(idx)

        ai = axes.createInput()
        ai.setByLine(edge)
        axis = axes.add(ai)
        if name:
            axis.name = name
        adsk.doEvents()
        return _axis_info(axis)
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_axis_perpendicular(body):
    """Create a construction axis perpendicular to a face at a point.

    Args:
        body_id: Body name
        face_id: Face ID
        point: [x, y, z] point on face in mm (optional, uses centroid if omitted)
        name: Optional name
    """
    try:
        root = get_root()
        axes = root.constructionAxes
        body_name = body.get("body_id")
        face_id = body.get("face_id")
        name = body.get("name")

        if not body_name or not face_id:
            raise Exception("body_id and face_id are required")

        face = _resolve_face(root, body_name, face_id)
        ai = axes.createInput()
        ai.setByNormalToFaceAtPoint(face, face.pointOnFace)
        axis = axes.add(ai)
        if name:
            axis.name = name
        adsk.doEvents()
        return _axis_info(axis)
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_axis_intersection(body):
    """Create a construction axis at the intersection of two planes.

    Args:
        plane1: First plane ID (xy/xz/yz/custom)
        plane2: Second plane ID
        name: Optional name
    """
    try:
        root = get_root()
        axes = root.constructionAxes
        p1_id = body.get("plane1")
        p2_id = body.get("plane2")
        name = body.get("name")

        if not p1_id or not p2_id:
            raise Exception("plane1 and plane2 are required")

        p1 = _resolve_plane(root, p1_id)
        p2 = _resolve_plane(root, p2_id)
        if not p1:
            raise Exception(f"Plane not found: {p1_id}")
        if not p2:
            raise Exception(f"Plane not found: {p2_id}")

        ai = axes.createInput()
        ai.setByTwoPlanes(p1, p2)
        axis = axes.add(ai)
        if name:
            axis.name = name
        adsk.doEvents()
        return _axis_info(axis)
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_delete_axis(body):
    """Delete a user-created construction axis by name."""
    root = get_root()
    axis_name = body.get("name")
    if not axis_name:
        raise Exception("name is required")
    for a in root.constructionAxes:
        if a.name == axis_name:
            a.deleteMe()
            adsk.doEvents()
            return {"success": True, "deleted": axis_name}
    raise Exception(f"Construction axis not found: {axis_name}")


# ══════════════════════════════════════════════════════════════
# CONSTRUCTION POINTS
# ══════════════════════════════════════════════════════════════

def handle_list_construction_points(body):
    """List all user-created construction points."""
    root = get_root()
    points = []
    for p in root.constructionPoints:
        geo = p.geometry
        points.append({
            "point_id": p.name, "name": p.name,
            "position_mm": [round(geo.x * 10, 4), round(geo.y * 10, 4), round(geo.z * 10, 4)],
        })
    return {"points": points, "count": len(points)}


def handle_create_construction_point(body):
    """Create a construction point at specific coordinates.

    Args:
        position: [x, y, z] in mm
        name: Optional name
    """
    try:
        root = get_root()
        pts = root.constructionPoints
        pos = body.get("position")
        name = body.get("name")

        if not pos:
            raise Exception("position [x, y, z] is required")

        pi = pts.createInput()
        pi.setByPoint(adsk.core.Point3D.create(pos[0]/10, pos[1]/10, pos[2]/10))
        cp = pts.add(pi)
        if name:
            cp.name = name
        adsk.doEvents()
        return _point_info(cp)
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_point_at_vertex(body):
    """Create a construction point at a body vertex.

    Args:
        body_id: Body name
        vertex_index: Vertex index
        name: Optional name
    """
    try:
        root = get_root()
        pts = root.constructionPoints
        body_name = body.get("body_id")
        vertex_index = body.get("vertex_index", 0)
        name = body.get("name")

        target = _resolve_body(root, body_name)
        if not target:
            raise Exception(f"Body not found: {body_name}")
        if vertex_index >= target.vertices.count:
            raise Exception(f"Vertex index {vertex_index} out of range ({target.vertices.count} vertices)")

        vertex = target.vertices.item(vertex_index)
        pi = pts.createInput()
        pi.setByPoint(vertex)
        cp = pts.add(pi)
        if name:
            cp.name = name
        adsk.doEvents()
        return _point_info(cp)
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_point_at_center(body):
    """Create a construction point at the center of an edge or face.

    For circular edges: center of the circle.
    For linear edges: midpoint.
    For faces: centroid.

    Args:
        body_id: Body name
        entity_id: Edge or face ID (e.g., "Body1_edge_0" or "Body1_face_2")
        name: Optional name
    """
    try:
        root = get_root()
        pts = root.constructionPoints
        body_name = body.get("body_id")
        entity_id = body.get("entity_id")
        name = body.get("name")

        if not body_name or not entity_id:
            raise Exception("body_id and entity_id are required")

        target = _resolve_body(root, body_name)
        if not target:
            raise Exception(f"Body not found: {body_name}")

        if "_edge_" in entity_id:
            idx = int(entity_id.split("_edge_")[-1])
            if idx >= target.edges.count:
                raise Exception(f"Edge index {idx} out of range")
            entity = target.edges.item(idx)
        elif "_face_" in entity_id:
            idx = int(entity_id.split("_face_")[-1])
            if idx >= target.faces.count:
                raise Exception(f"Face index {idx} out of range")
            entity = target.faces.item(idx)
        else:
            try:
                idx = int(entity_id)
                entity = target.edges.item(idx)
            except (ValueError, RuntimeError):
                raise Exception(f"Cannot parse entity ID: {entity_id}")

        pi = pts.createInput()
        pi.setByEdge(entity) if hasattr(entity, 'startVertex') else pi.setByPoint(entity.centroid)
        cp = pts.add(pi)
        if name:
            cp.name = name
        adsk.doEvents()
        return _point_info(cp)
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_delete_construction_point(body):
    """Delete a user-created construction point by name."""
    root = get_root()
    pt_name = body.get("name")
    if not pt_name:
        raise Exception("name is required")
    for p in root.constructionPoints:
        if p.name == pt_name:
            p.deleteMe()
            adsk.doEvents()
            return {"success": True, "deleted": pt_name}
    raise Exception(f"Construction point not found: {pt_name}")


# ══════════════════════════════════════════════════════════════
# MEASUREMENTS
# ══════════════════════════════════════════════════════════════

def handle_measure_distance(body):
    """Measure the minimum distance between two entities.

    Entities can be: bodies, faces, edges, vertices, construction planes, points.

    Args:
        entity1: Dict with type + id, e.g. {"type": "body", "name": "Body1"}
                 or {"type": "face", "body": "Body1", "face": "Body1_face_0"}
                 or {"type": "point", "position": [x, y, z]}
                 or {"type": "plane", "name": "xy"}
        entity2: Same format as entity1
    """
    try:
        root = get_root()
        design = get_design()
        mm = design.fusionUnitsManager if hasattr(design, 'fusionUnitsManager') else None

        e1_spec = body.get("entity1", {})
        e2_spec = body.get("entity2", {})

        def resolve_entity(spec):
            t = spec.get("type", "")
            if t == "body":
                b = _resolve_body(root, spec["name"])
                if not b:
                    raise Exception(f"Body not found: {spec['name']}")
                return b
            elif t == "face":
                return _resolve_face(root, spec["body"], spec["face"])
            elif t == "edge":
                b = _resolve_body(root, spec["body"])
                if not b:
                    raise Exception(f"Body not found: {spec['body']}")
                idx = int(spec["edge"].split("_edge_")[-1]) if "_edge_" in spec["edge"] else int(spec["edge"])
                return b.edges.item(idx)
            elif t == "point":
                pos = spec["position"]
                return adsk.core.Point3D.create(pos[0]/10, pos[1]/10, pos[2]/10)
            elif t == "plane":
                p = _resolve_plane(root, spec["name"])
                if not p:
                    raise Exception(f"Plane not found: {spec['name']}")
                return p
            elif t == "axis":
                a = _resolve_axis(root, spec["name"])
                if not a:
                    raise Exception(f"Axis not found: {spec['name']}")
                return a
            else:
                raise Exception(f"Unknown entity type: {t}")

        ent1 = resolve_entity(e1_spec)
        ent2 = resolve_entity(e2_spec)

        # Use measureManager for BRep entities, manual calc for points
        if isinstance(ent1, adsk.core.Point3D) and isinstance(ent2, adsk.core.Point3D):
            dist_cm = ent1.distanceTo(ent2)
        else:
            mgr = adsk.core.Application.get().measureManager
            result = mgr.measureMinimumDistance(ent1, ent2)
            dist_cm = result.value

        return {
            "distance_mm": round(dist_cm * 10, 6),
            "entity1": e1_spec,
            "entity2": e2_spec,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_measure_angle(body):
    """Measure the angle between two planar entities (planes or planar faces).

    Args:
        entity1: {"type": "plane", "name": "xy"} or {"type": "face", "body": "B", "face": "B_face_0"}
        entity2: Same format
    """
    try:
        root = get_root()

        def resolve_planar(spec):
            t = spec.get("type", "")
            if t == "plane":
                p = _resolve_plane(root, spec["name"])
                if not p:
                    raise Exception(f"Plane not found: {spec['name']}")
                return p.geometry.normal
            elif t == "face":
                face = _resolve_face(root, spec["body"], spec["face"])
                geo = face.geometry
                if hasattr(geo, 'normal'):
                    return geo.normal
                raise Exception(f"Face is not planar: {spec['face']}")
            else:
                raise Exception(f"Expected plane or face, got: {t}")

        n1 = resolve_planar(body.get("entity1", {}))
        n2 = resolve_planar(body.get("entity2", {}))

        angle_rad = n1.angleTo(n2)
        angle_deg = math.degrees(angle_rad)

        return {
            "angle_degrees": round(angle_deg, 4),
            "angle_radians": round(angle_rad, 6),
            "supplementary_degrees": round(180 - angle_deg, 4),
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_measure_body(body):
    """Get physical properties of a body — volume, surface area, center of mass.

    Args:
        body_id: Body name
    """
    try:
        root = get_root()
        body_name = body.get("body_id")
        target = _resolve_body(root, body_name)
        if not target:
            raise Exception(f"Body not found: {body_name}")

        props = target.physicalProperties
        bb = target.boundingBox

        result = {
            "body_id": body_name,
            "is_solid": target.isSolid,
            "surface_area_mm2": round(target.area * 100, 4),
        }

        if target.isSolid:
            result["volume_mm3"] = round(target.volume * 1000, 4)
            result["center_of_mass_mm"] = [
                round(props.centerOfMass.x * 10, 4),
                round(props.centerOfMass.y * 10, 4),
                round(props.centerOfMass.z * 10, 4),
            ]

        result["bounding_box"] = {
            "min": [round(bb.minPoint.x*10, 2), round(bb.minPoint.y*10, 2), round(bb.minPoint.z*10, 2)],
            "max": [round(bb.maxPoint.x*10, 2), round(bb.maxPoint.y*10, 2), round(bb.maxPoint.z*10, 2)],
        }
        result["dimensions_mm"] = {
            "width": round((bb.maxPoint.x - bb.minPoint.x) * 10, 2),
            "depth": round((bb.maxPoint.y - bb.minPoint.y) * 10, 2),
            "height": round((bb.maxPoint.z - bb.minPoint.z) * 10, 2),
        }
        result["face_count"] = target.faces.count
        result["edge_count"] = target.edges.count
        result["vertex_count"] = target.vertices.count

        return result
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_list_vertices(body):
    """List all vertices of a body with their 3D positions.

    Args:
        body_id: Body name
        component: Optional component name
    """
    root = get_root()
    body_name = body.get("body_id")
    target = _resolve_body(root, body_name)
    if not target:
        raise Exception(f"Body not found: {body_name}")

    verts = []
    for i in range(target.vertices.count):
        v = target.vertices.item(i)
        geo = v.geometry
        verts.append({
            "vertex_id": f"{body_name}_vertex_{i}",
            "index": i,
            "position_mm": [round(geo.x * 10, 4), round(geo.y * 10, 4), round(geo.z * 10, 4)],
        })
    return {"vertices": verts, "count": len(verts), "body_id": body_name}


# ══════════════════════════════════════════════════════════════
# ROUTE TABLE
# ══════════════════════════════════════════════════════════════

CONSTRUCTION_ROUTES = {
    # Planes
    "/list_planes": handle_list_planes,
    "/create_offset_plane": handle_create_offset_plane,
    "/create_angled_plane": handle_create_angled_plane,
    "/create_plane_by_angle": handle_create_plane_by_angle,
    "/create_midplane": handle_create_midplane,
    "/create_tangent_plane": handle_create_tangent_plane,
    "/delete_plane": handle_delete_plane,

    # Axes
    "/list_axes": handle_list_axes,
    "/create_axis_two_points": handle_create_axis_two_points,
    "/create_axis_by_edge": handle_create_axis_by_edge,
    "/create_axis_perpendicular": handle_create_axis_perpendicular,
    "/create_axis_intersection": handle_create_axis_intersection,
    "/delete_axis": handle_delete_axis,

    # Construction Points
    "/list_construction_points": handle_list_construction_points,
    "/create_construction_point": handle_create_construction_point,
    "/create_point_at_vertex": handle_create_point_at_vertex,
    "/create_point_at_center": handle_create_point_at_center,
    "/delete_construction_point": handle_delete_construction_point,

    # Measurements
    "/measure_distance": handle_measure_distance,
    "/measure_angle": handle_measure_angle,
    "/measure_body": handle_measure_body,

    # Body topology (vertex listing)
    "/list_vertices": handle_list_vertices,
}
