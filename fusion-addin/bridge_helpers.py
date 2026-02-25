"""Shared state and utility functions for all Fusion bridge handler modules.

Every handler module imports from here. The `app` global is set once
during add-in startup by calling `set_app()`.
"""

import adsk.core
import adsk.fusion
import adsk.cam

# Shared state — set by FusionMCPBridge.run()
app = None
frame_manager = None
entity_resolver = None
cad_state = None
graph_extractor = None
patch_emitter = None
action_executor = None

PORT = 8080


def set_app(a):
    global app
    app = a


def set_frame_manager(fm):
    global frame_manager
    frame_manager = fm


def set_nav_state(er, cs, ge, pe, ae):
    global entity_resolver, cad_state, graph_extractor, patch_emitter, action_executor
    entity_resolver = er
    cad_state = cs
    graph_extractor = ge
    patch_emitter = pe
    action_executor = ae


# ── Design helpers ───────────────────────────────────────────

def get_design():
    """Get the Fusion design (works from any workspace)."""
    global app
    doc = app.activeDocument
    if not doc:
        raise Exception("No active document")
    design = app.activeProduct
    if design and design.productType == "DesignProductType":
        return design
    for product in doc.products:
        if product.productType == "DesignProductType":
            return product
    raise Exception("No Fusion design found in document")


def get_root():
    """Get the root component."""
    return get_design().rootComponent


# ── Geometry helpers ─────────────────────────────────────────

def point2d(coords):
    """Create a 2D point from [x, y] in mm, converted to cm for Fusion."""
    return adsk.core.Point3D.create(coords[0] / 10.0, coords[1] / 10.0, 0)


def point3d(coords):
    """Create a 3D point from [x, y, z] in mm, converted to cm for Fusion."""
    return adsk.core.Point3D.create(coords[0] / 10.0, coords[1] / 10.0, coords[2] / 10.0)


def vector3d(coords):
    """Create a 3D vector from [x, y, z]."""
    return adsk.core.Vector3D.create(coords[0], coords[1], coords[2])


# ── Lookup helpers ───────────────────────────────────────────

def get_component_by_name(name):
    """Get a component by name (e.g., 'Carcass' or 'Carcass:1')."""
    root = get_root()
    base_name = name.split(":")[0] if ":" in name else name
    for occ in root.allOccurrences:
        if occ.component.name == base_name or occ.name == name:
            return occ.component, occ
    return None, None


def get_sketch(sketch_id):
    """Get a sketch by name, searching root and all components."""
    root = get_root()
    sketch = root.sketches.itemByName(sketch_id)
    if sketch:
        return sketch
    for occ in root.allOccurrences:
        sketch = occ.component.sketches.itemByName(sketch_id)
        if sketch:
            return sketch
    raise Exception(f"Sketch not found: {sketch_id}")


def get_sketch_with_component(sketch_id, component_name=None):
    """Get a sketch, optionally from a specific component."""
    root = get_root()
    if component_name:
        target_component, _ = get_component_by_name(component_name)
        if target_component:
            sketch = target_component.sketches.itemByName(sketch_id)
            if sketch:
                return sketch, target_component
    sketch = root.sketches.itemByName(sketch_id)
    if sketch:
        return sketch, root
    for occ in root.allOccurrences:
        sketch = occ.component.sketches.itemByName(sketch_id)
        if sketch:
            return sketch, occ.component
    raise Exception(f"Sketch not found: {sketch_id}")


def find_body(body_name, component_name=None):
    """Find a BRepBody by name, optionally scoped to a component."""
    root = get_root()
    if component_name:
        comp, _ = get_component_by_name(component_name)
        if comp:
            for b in comp.bRepBodies:
                if b.name == body_name:
                    return b
    for b in root.bRepBodies:
        if b.name == body_name:
            return b
    for occ in root.allOccurrences:
        for b in occ.component.bRepBodies:
            if b.name == body_name:
                return b
    return None


# ── Spatial entity resolution ────────────────────────────────

def _pt_distance_mm(fusion_pt, target_mm):
    """Euclidean distance between a Fusion Point3D (cm) and a target [x,y,z] in mm."""
    dx = fusion_pt.x * 10 - target_mm[0]
    dy = fusion_pt.y * 10 - target_mm[1]
    dz = fusion_pt.z * 10 - target_mm[2]
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def find_nearest_edge(body, point_mm, tolerance_mm=10.0):
    """Find the closest edge on a body to a world-space point (mm).

    Uses pointOnEdge (midpoint) for distance. Returns (edge, distance_mm)
    or (None, inf) if nothing is within tolerance.
    """
    best_edge = None
    best_dist = float("inf")
    for i in range(body.edges.count):
        edge = body.edges.item(i)
        dist = _pt_distance_mm(edge.pointOnEdge, point_mm)
        if dist < best_dist:
            best_dist = dist
            best_edge = edge
    if best_dist <= tolerance_mm:
        return best_edge, best_dist
    return None, float("inf")


def find_nearest_face(body, point_mm, tolerance_mm=10.0):
    """Find the closest face on a body to a world-space point (mm).

    Uses face centroid for distance. Returns (face, distance_mm)
    or (None, inf) if nothing is within tolerance.
    """
    best_face = None
    best_dist = float("inf")
    for i in range(body.faces.count):
        face = body.faces.item(i)
        dist = _pt_distance_mm(face.centroid, point_mm)
        if dist < best_dist:
            best_dist = dist
            best_face = face
    if best_dist <= tolerance_mm:
        return best_face, best_dist
    return None, float("inf")


def parse_edge_ref(edge_str, root_component, tolerance_mm=10.0):
    """Resolve an edge string to a live BRepEdge.

    Supports three formats:
      - "Body1_edge_3"    — index-based lookup (legacy)
      - "Body1@170,0,542" — spatial lookup by nearest midpoint
      - "token:abc123..."  — entityToken lookup via resolver cache

    Returns (edge, body) or raises Exception.
    """
    # Format: token:...
    if edge_str.startswith("token:"):
        token = edge_str[6:]
        for b in root_component.bRepBodies:
            for i in range(b.edges.count):
                e = b.edges.item(i)
                if e.entityToken == token:
                    return e, b
        raise Exception(f"Edge token not found: {token[:20]}...")

    # Format: Body@x,y,z
    if "@" in edge_str:
        body_name, coords_str = edge_str.rsplit("@", 1)
        coords = [float(c) for c in coords_str.split(",")]
        if len(coords) != 3:
            raise Exception(f"Spatial ref needs 3 coords: {edge_str}")
        body = None
        for b in root_component.bRepBodies:
            if b.name == body_name:
                body = b
                break
        if not body:
            raise Exception(f"Body not found for spatial ref: {body_name}")
        edge, dist = find_nearest_edge(body, coords, tolerance_mm)
        if not edge:
            raise Exception(
                f"No edge within {tolerance_mm}mm of ({coords_str}) on {body_name}"
            )
        return edge, body

    # Format: Body1_edge_3 (legacy index)
    parts = edge_str.rsplit("_edge_", 1)
    if len(parts) == 2:
        body_name = parts[0]
        try:
            idx = int(parts[1])
        except ValueError:
            raise Exception(f"Invalid edge index: {edge_str}")
        for b in root_component.bRepBodies:
            if b.name == body_name and idx < b.edges.count:
                return b.edges.item(idx), b
        raise Exception(f"Edge not found: {edge_str}")

    raise Exception(
        f"Unrecognized edge ref format: {edge_str}. "
        "Use Body_edge_N, Body@x,y,z, or token:..."
    )


def parse_face_ref(face_str, root_component, tolerance_mm=10.0):
    """Resolve a face string to a live BRepFace.

    Supports three formats:
      - "Body1_face_3"    — index-based lookup (legacy)
      - "Body1@170,0,542" — spatial lookup by nearest centroid
      - "token:abc123..."  — entityToken lookup via resolver cache

    Returns (face, body) or raises Exception.
    """
    # Format: token:...
    if face_str.startswith("token:"):
        token = face_str[6:]
        for b in root_component.bRepBodies:
            for i in range(b.faces.count):
                f = b.faces.item(i)
                if f.entityToken == token:
                    return f, b
        raise Exception(f"Face token not found: {token[:20]}...")

    # Format: Body@x,y,z
    if "@" in face_str:
        body_name, coords_str = face_str.rsplit("@", 1)
        coords = [float(c) for c in coords_str.split(",")]
        if len(coords) != 3:
            raise Exception(f"Spatial ref needs 3 coords: {face_str}")
        body = None
        for b in root_component.bRepBodies:
            if b.name == body_name:
                body = b
                break
        if not body:
            raise Exception(f"Body not found for spatial ref: {body_name}")
        face, dist = find_nearest_face(body, coords, tolerance_mm)
        if not face:
            raise Exception(
                f"No face within {tolerance_mm}mm of ({coords_str}) on {body_name}"
            )
        return face, body

    # Format: Body1_face_3 (legacy index) or plain int
    body_ref = face_str
    idx = None

    if "_face_" in face_str:
        parts = face_str.rsplit("_face_", 1)
        body_ref = parts[0]
        try:
            idx = int(parts[1])
        except ValueError:
            raise Exception(f"Invalid face index: {face_str}")
    else:
        try:
            idx = int(face_str)
            body_ref = None
        except ValueError:
            raise Exception(
                f"Unrecognized face ref format: {face_str}. "
                "Use Body_face_N, Body@x,y,z, or token:..."
            )

    for b in root_component.bRepBodies:
        if body_ref is None or b.name == body_ref:
            if idx is not None and 0 <= idx < b.faces.count:
                return b.faces.item(idx), b

    raise Exception(f"Face not found: {face_str}")
