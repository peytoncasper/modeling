"""Solid/body handlers — extrude, revolve, loft, sweep, booleans, query, transforms.

Every public function has the signature ``handle_*(body: dict) -> dict``
and is registered in SOLID_ROUTES by the main bridge orchestrator.
"""
import math
import traceback

import adsk.core
import adsk.fusion

try:
    from bridge_helpers import (
        get_design, get_root, get_component_by_name,
        get_sketch, get_sketch_with_component,
        point2d, point3d, vector3d,
        parse_edge_ref, parse_face_ref,
    )
except ImportError:
    from .bridge_helpers import (
        get_design, get_root, get_component_by_name,
        get_sketch, get_sketch_with_component,
        point2d, point3d, vector3d,
        parse_edge_ref, parse_face_ref,
    )


# ── Body lookup helpers (assembly-context aware) ──────────────

def _find_body_with_context(root, body_name):
    """Return (proxy_body, native_body, component, occurrence) or four Nones."""
    for b in root.bRepBodies:
        if b.name == body_name:
            return (b, b, root, None)
    for occ in root.allOccurrences:
        for b in occ.component.bRepBodies:
            if b.name == body_name:
                proxy = b.createForAssemblyContext(occ)
                return (proxy, b, occ.component, occ)
    return (None, None, None, None)


def _find_body(root, body_name):
    body, _, _, _ = _find_body_with_context(root, body_name)
    return body


def _find_bodies_collection(root, body_names):
    """ObjectCollection of proxy bodies matching *body_names*."""
    bodies = adsk.core.ObjectCollection.create()
    for b in root.bRepBodies:
        if b.name in body_names:
            bodies.add(b)
    for occ in root.allOccurrences:
        for b in occ.component.bRepBodies:
            if b.name in body_names:
                bodies.add(b.createForAssemblyContext(occ))
    return bodies


# ── Reference geometry ────────────────────────────────────────

def handle_list_planes(body):
    root = get_root()
    planes = [
        {"id": "xy", "name": "XY Plane", "origin": [0, 0, 0], "normal": [0, 0, 1]},
        {"id": "xz", "name": "XZ Plane", "origin": [0, 0, 0], "normal": [0, 1, 0]},
        {"id": "yz", "name": "YZ Plane", "origin": [0, 0, 0], "normal": [1, 0, 0]},
    ]
    for plane in root.constructionPlanes:
        geo = plane.geometry
        planes.append({
            "id": plane.name, "name": plane.name,
            "origin": [geo.origin.x, geo.origin.y, geo.origin.z],
            "normal": [geo.normal.x, geo.normal.y, geo.normal.z],
        })
    return {"planes": planes}


def handle_create_offset_plane(body):
    root = get_root()
    base_plane_id = body.get("base_plane", "xy")
    offset = body.get("offset", 10)
    component_name = body.get("component")

    if component_name:
        target_component, _ = get_component_by_name(component_name)
        if not target_component:
            raise Exception(f"Component not found: {component_name}")
    else:
        target_component = root

    planes = target_component.constructionPlanes
    plane_input = planes.createInput()
    if base_plane_id == "xy":
        base = target_component.xYConstructionPlane
    elif base_plane_id == "xz":
        base = target_component.xZConstructionPlane
    elif base_plane_id == "yz":
        base = target_component.yZConstructionPlane
    else:
        base = target_component.constructionPlanes.itemByName(base_plane_id)
        if not base:
            base = root.constructionPlanes.itemByName(base_plane_id)
    if not base:
        raise Exception(f"Plane not found: {base_plane_id}")

    plane_input.setByOffset(base, adsk.core.ValueInput.createByReal(offset / 10.0))
    new_plane = planes.add(plane_input)
    return {"plane_id": new_plane.name, "name": new_plane.name}


# ── 3-D features ─────────────────────────────────────────────

def handle_extrude(body):
    design = get_design()
    root = get_root()
    sketch_id = body.get("sketch_id")
    profile_index = body.get("profile_index", 0)
    distance = body.get("distance", 10) / 10.0
    direction = body.get("direction", "positive")
    operation = body.get("operation", "new_body")
    component_name = body.get("component")
    target_body_name = body.get("target_body")
    new_body_name = body.get("body_name")

    sketch, sketch_component = get_sketch_with_component(sketch_id, component_name)
    profile = sketch.profiles.item(profile_index)
    if not profile:
        raise Exception(f"Profile not found at index {profile_index}")

    bodies_before = sketch_component.bRepBodies.count
    extrudes = sketch_component.features.extrudeFeatures

    op_map = {
        "new_body": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
        "cut": adsk.fusion.FeatureOperations.CutFeatureOperation,
        "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation,
    }
    extrude_input = extrudes.createInput(profile, op_map.get(operation, op_map["new_body"]))

    target_body = None
    if target_body_name and operation in ("join", "cut", "intersect"):
        for b in sketch_component.bRepBodies:
            if b.name == target_body_name:
                target_body = b
                break
        if not target_body:
            target_body = _find_body(root, target_body_name)
        if not target_body:
            available = [b.name for b in sketch_component.bRepBodies]
            raise Exception(f"Target body '{target_body_name}' not found. Available: {available}")
        extrude_input.participantBodies = [target_body]

    if direction == "symmetric":
        extrude_input.setSymmetricExtent(adsk.core.ValueInput.createByReal(distance), True)
    else:
        extent = adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(distance))
        ext_dir = (adsk.fusion.ExtentDirections.NegativeExtentDirection
                    if direction == "negative"
                    else adsk.fusion.ExtentDirections.PositiveExtentDirection)
        extrude_input.setOneSideExtent(extent, ext_dir)

    extrude = extrudes.add(extrude_input)
    adsk.doEvents()

    bodies_after = sketch_component.bRepBodies.count
    if operation == "cut":
        body_name = target_body_name or "multiple"
    else:
        body_name = extrude.bodies.item(0).name if extrude.bodies.count > 0 else target_body_name

    if new_body_name and extrude.bodies.count > 0 and operation == "new_body":
        try:
            extrude.bodies.item(0).name = new_body_name
            body_name = new_body_name
        except Exception:
            pass

    result = {"feature_id": extrude.name, "body_id": body_name,
              "component": sketch_component.name, "source_sketch": sketch_id, "operation": operation}

    if operation == "cut" and not target_body_name:
        result["warning"] = "CUT_NO_TARGET_SPECIFIED"
    if operation == "join" and bodies_after > bodies_before:
        result["warning"] = "JOIN_CREATED_ORPHAN_BODY"
        result["warning_detail"] = (
            f"Expected join to '{target_body_name}' but new body '{body_name}' created. "
            "Geometry must intersect the target body for join to work.")
    return result


def handle_extrude_with_draft(body):
    root = get_root()
    sketch_id = body.get("sketch_id")
    profile_index = body.get("profile_index", 0)
    distance = body.get("distance", 10) / 10.0
    draft_angle = body.get("draft_angle", 0)
    direction = body.get("direction", "positive")
    operation = body.get("operation", "new_body")
    target_body_name = body.get("target_body")

    sketch = get_sketch(sketch_id)
    profile = sketch.profiles.item(profile_index)
    if not profile:
        raise Exception(f"Profile not found at index {profile_index}")

    op_map = {
        "new_body": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
        "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
        "cut": adsk.fusion.FeatureOperations.CutFeatureOperation,
        "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation,
    }
    extrudes = root.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, op_map.get(operation, op_map["new_body"]))

    if target_body_name and operation in ("join", "cut", "intersect"):
        tb = _find_body(root, target_body_name)
        if tb:
            extrude_input.participantBodies = [tb]

    draft_rad = draft_angle * math.pi / 180.0
    if direction == "symmetric":
        extrude_input.setSymmetricExtent(adsk.core.ValueInput.createByReal(distance), True)
        if draft_angle != 0:
            extrude_input.taperAngle = adsk.core.ValueInput.createByReal(draft_rad)
    else:
        ext_dir = (adsk.fusion.ExtentDirections.NegativeExtentDirection
                    if direction == "negative"
                    else adsk.fusion.ExtentDirections.PositiveExtentDirection)
        extrude_input.setOneSideExtent(
            adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(distance)), ext_dir)
        if draft_angle != 0:
            extrude_input.taperAngle = adsk.core.ValueInput.createByReal(draft_rad)

    extrude = extrudes.add(extrude_input)
    adsk.doEvents()
    body_name = extrude.bodies.item(0).name if extrude.bodies.count > 0 else target_body_name
    return {"feature_id": extrude.name, "body_id": body_name, "draft_angle": draft_angle}


def handle_fillet_edges(body):
    root = get_root()
    edge_ids = body.get("edge_ids", [])
    radius = body.get("radius", 1) / 10.0
    edges = adsk.core.ObjectCollection.create()
    errors = []
    for eid in edge_ids:
        try:
            edge, _ = parse_edge_ref(eid, root)
            edges.add(edge)
        except Exception as e:
            errors.append(f"{eid}: {e}")
    if edges.count == 0:
        raise Exception(f"No matching edges found for IDs: {edge_ids}. Errors: {errors}")
    fillets = root.features.filletFeatures
    fi = fillets.createInput()
    fi.addConstantRadiusEdgeSet(edges, adsk.core.ValueInput.createByReal(radius), body.get("tangent_chain", True))
    return {"feature_id": fillets.add(fi).name}


def handle_chamfer_edges(body):
    root = get_root()
    edge_ids = body.get("edge_ids", [])
    distance = body.get("distance", 1) / 10.0
    edges = adsk.core.ObjectCollection.create()
    for eid in edge_ids:
        try:
            edge, _ = parse_edge_ref(eid, root)
            edges.add(edge)
        except Exception:
            pass
    if edges.count == 0:
        raise Exception(f"No matching edges found for IDs: {edge_ids}")
    chamfers = root.features.chamferFeatures
    ci = chamfers.createInput2()
    ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges, adsk.core.ValueInput.createByReal(distance), True)
    return {"feature_id": chamfers.add(ci).name}


def handle_boolean(body):
    root = get_root()
    operation = body.get("operation", "union")
    target_body_id = body.get("target_body")
    tool_body_ids = body.get("tool_bodies", [])
    keep_tools = body.get("keep_tools", False)

    target_proxy, target_native, target_component, target_occ = _find_body_with_context(root, target_body_id)
    if not target_proxy:
        raise Exception(f"Target body not found: {target_body_id}")
    tool_bodies = _find_bodies_collection(root, tool_body_ids)
    if tool_bodies.count == 0:
        raise Exception("No tool bodies found")

    combines = root.features.combineFeatures
    combine_input = combines.createInput(target_proxy, tool_bodies)
    op_map = {"union": adsk.fusion.FeatureOperations.JoinFeatureOperation,
              "subtract": adsk.fusion.FeatureOperations.CutFeatureOperation,
              "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation}
    combine_input.operation = op_map.get(operation, op_map["union"])
    combine_input.isKeepToolBodies = keep_tools

    try:
        combines.add(combine_input)
        return {"success": True, "result_body": target_body_id, "operation": operation,
                "target_component": target_occ.name if target_occ else "root",
                "cross_component": target_occ is not None}
    except Exception as e:
        raise Exception(str(e))


def handle_shell(body):
    try:
        root = get_root()
        body_name = body.get("body_id")
        thickness = body.get("thickness")
        remove_face_ids = body.get("remove_faces", [])
        direction = body.get("direction", "inside")
        if not body_name:
            raise Exception("body_id is required")
        if thickness is None or thickness <= 0:
            raise Exception("thickness must be a positive number (in mm)")

        target_body = _find_body(root, body_name)
        if not target_body:
            raise Exception(f"Body not found: {body_name}")

        faces_to_remove = adsk.core.ObjectCollection.create()
        for fid in remove_face_ids:
            try:
                face, _ = parse_face_ref(str(fid), root)
                faces_to_remove.add(face)
            except Exception:
                raise Exception(f"Face not found: {fid} (body has {target_body.faces.count} faces)")

        thickness_cm = thickness / 10.0
        shell_input = root.features.shellFeatures.createInput(faces_to_remove)
        if direction == "outside":
            shell_input.outsideThickness = adsk.core.ValueInput.createByReal(thickness_cm)
        elif direction == "both":
            shell_input.insideThickness = adsk.core.ValueInput.createByReal(thickness_cm / 2.0)
            shell_input.outsideThickness = adsk.core.ValueInput.createByReal(thickness_cm / 2.0)
        else:
            shell_input.insideThickness = adsk.core.ValueInput.createByReal(thickness_cm)

        feat = root.features.shellFeatures.add(shell_input)
        adsk.doEvents()
        return {"success": True, "body_id": body_name, "thickness_mm": thickness,
                "direction": direction, "faces_removed": len(remove_face_ids),
                "feature_name": feat.name if feat else "Shell"}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_split_body(body):
    try:
        root = get_root()
        body_name = body.get("body_id")
        tool_name = body.get("splitting_tool")
        keep = body.get("keep", "both")
        if not body_name:
            raise Exception("body_id is required")
        if not tool_name:
            raise Exception("splitting_tool is required")

        target_body = _find_body(root, body_name)
        if not target_body:
            raise Exception(f"Body not found: {body_name}")

        split_entity = None
        tool_type = None
        if tool_name in ("xy", "xz", "yz"):
            split_entity = {"xy": root.xYConstructionPlane, "xz": root.xZConstructionPlane,
                            "yz": root.yZConstructionPlane}[tool_name]
            tool_type = "plane"
        else:
            for p in root.constructionPlanes:
                if p.name == tool_name:
                    split_entity = p
                    tool_type = "plane"
                    break
            if not split_entity:
                split_entity = _find_body(root, tool_name)
                if split_entity:
                    tool_type = "body"
        if not split_entity:
            raise Exception(f"Splitting tool not found: {tool_name}")

        split_feats = root.features.splitBodyFeatures
        si = split_feats.createInput(target_body, split_entity, True)
        feat = split_feats.add(si)
        adsk.doEvents()

        result_bodies = []
        for i in range(feat.bodies.count):
            b = feat.bodies.item(i)
            result_bodies.append({"name": b.name,
                                  "volume_mm3": round(b.volume * 1000, 3) if b.isSolid else None})
        return {"success": True, "original_body": body_name, "splitting_tool": tool_name,
                "tool_type": tool_type, "keep": keep, "result_bodies": result_bodies,
                "body_count": len(result_bodies), "feature_name": feat.name}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_patch(body):
    try:
        root = get_root()
        sketch_id = body.get("sketch_id")
        profile_index = body.get("profile_index", 0)
        component_name = body.get("component")
        new_body_name = body.get("body_name")
        if not sketch_id:
            raise Exception("sketch_id is required")

        sketch, sketch_comp = get_sketch_with_component(sketch_id, component_name)
        if profile_index >= sketch.profiles.count:
            raise Exception(f"Profile index {profile_index} out of range")
        profile = sketch.profiles.item(profile_index)

        patches = sketch_comp.features.patchFeatures
        pi = patches.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        feat = patches.add(pi)
        adsk.doEvents()

        rb = feat.bodies.item(0) if feat.bodies.count > 0 else None
        if new_body_name and rb:
            rb.name = new_body_name
        return {"success": True, "body_id": rb.name if rb else "unknown",
                "is_solid": rb.isSolid if rb else False,
                "area_mm2": rb.area * 100 if rb else 0,
                "feature_name": feat.name, "source_sketch": sketch_id}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_stitch(body):
    try:
        root = get_root()
        body_ids = body.get("body_ids", [])
        tolerance_mm = body.get("tolerance", 0.1)
        new_body_name = body.get("body_name")
        if len(body_ids) < 2:
            raise Exception("body_ids must contain at least 2 names")

        coll = adsk.core.ObjectCollection.create()
        for bid in body_ids:
            b = _find_body(root, bid)
            if not b:
                raise Exception(f"Body not found: {bid}")
            coll.add(b)

        feat = root.features.stitchFeatures.add(
            root.features.stitchFeatures.createInput(
                coll, adsk.core.ValueInput.createByReal(tolerance_mm / 10.0)))
        adsk.doEvents()

        rb = feat.bodies.item(0) if feat.bodies.count > 0 else None
        if new_body_name and rb:
            rb.name = new_body_name
        is_solid = rb.isSolid if rb else False
        return {"success": True, "body_id": rb.name if rb else "unknown",
                "is_solid": is_solid, "watertight": is_solid,
                "volume_mm3": rb.volume * 1000 if (rb and is_solid) else 0,
                "bodies_stitched": body_ids, "feature_name": feat.name}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_loft(body):
    root = get_root()
    sketch_ids = body.get("sketch_ids", [])
    profile_indices = body.get("profile_indices", [])
    operation = body.get("operation", "new_body")
    is_solid = body.get("is_solid", True)
    if len(sketch_ids) < 2:
        raise Exception("At least 2 sketches required for loft")

    profiles = adsk.core.ObjectCollection.create()
    for i, sid in enumerate(sketch_ids):
        sk = get_sketch(sid)
        pidx = profile_indices[i] if i < len(profile_indices) else 0
        if pidx >= sk.profiles.count:
            raise Exception(f"Profile index {pidx} not found in sketch {sid}")
        profiles.add(sk.profiles.item(pidx))

    lofts = root.features.loftFeatures
    li = lofts.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    op_map = {"join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
              "cut": adsk.fusion.FeatureOperations.CutFeatureOperation,
              "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation}
    if operation in op_map:
        li.operation = op_map[operation]
    for i in range(profiles.count):
        li.loftSections.add(profiles.item(i))
    li.isSolid = is_solid
    li.isClosed = False
    li.isTangentEdgesMerged = True

    for rail_id in body.get("rails", []):
        rs = get_sketch(rail_id)
        if rs.sketchCurves.count > 0:
            li.centerLineOrRails.addRail(rs.sketchCurves.item(0))

    feat = lofts.add(li)
    adsk.doEvents()
    return {"feature_id": feat.name,
            "body_id": feat.bodies.item(0).name if feat.bodies.count > 0 else "Unknown",
            "profiles_used": profiles.count}


def handle_sweep(body):
    root = get_root()
    profile_sketch_id = body.get("profile_sketch_id")
    path_sketch_id = body.get("path_sketch_id")
    profile_index = body.get("profile_index", 0)
    operation = body.get("operation", "new_body")
    if not profile_sketch_id or not path_sketch_id:
        raise Exception("Both profile_sketch_id and path_sketch_id required")

    ps = get_sketch(profile_sketch_id)
    if profile_index >= ps.profiles.count:
        raise Exception(f"Profile index {profile_index} not found")
    profile = ps.profiles.item(profile_index)

    path_sk = get_sketch(path_sketch_id)
    if path_sk.sketchCurves.count == 0:
        raise Exception(f"No curves in path sketch {path_sketch_id}")
    path = root.features.createPath(path_sk.sketchCurves.item(0), False)

    op_map = {"new_body": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
              "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
              "cut": adsk.fusion.FeatureOperations.CutFeatureOperation,
              "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation}
    si = root.features.sweepFeatures.createInput(profile, path, op_map.get(operation, op_map["new_body"]))

    if body.get("orientation") == "parallel":
        si.orientation = adsk.fusion.SweepOrientationTypes.ParallelOrientationType
    else:
        si.orientation = adsk.fusion.SweepOrientationTypes.PerpendicularOrientationType
    twist = body.get("twist_angle")
    if twist:
        si.twistAngle = adsk.core.ValueInput.createByReal(twist * math.pi / 180.0)

    feat = root.features.sweepFeatures.add(si)
    adsk.doEvents()
    return {"feature_id": feat.name,
            "body_id": feat.bodies.item(0).name if feat.bodies.count > 0 else "Unknown"}


def handle_revolve(body):
    root = get_root()
    sketch_id = body.get("sketch_id")
    profile_index = body.get("profile_index", 0)
    axis_type = body.get("axis", "x")
    angle = body.get("angle", 360)
    operation = body.get("operation", "new_body")
    if not sketch_id:
        raise Exception("sketch_id is required")

    sk = get_sketch(sketch_id)
    if profile_index >= sk.profiles.count:
        raise Exception(f"Profile index {profile_index} not found")
    profile = sk.profiles.item(profile_index)

    axis = None
    axis_sketch_id = body.get("axis_sketch_id")
    axis_line_index = body.get("axis_line_index", 0)
    if axis_sketch_id:
        ask = get_sketch(axis_sketch_id)
        if axis_line_index < ask.sketchCurves.sketchLines.count:
            axis = ask.sketchCurves.sketchLines.item(axis_line_index)
    elif axis_type == "x":
        axis = root.xConstructionAxis
    elif axis_type == "y":
        axis = root.yConstructionAxis
    elif axis_type == "z":
        axis = root.zConstructionAxis
    else:
        for i in range(sk.sketchCurves.sketchLines.count):
            line = sk.sketchCurves.sketchLines.item(i)
            if line.isConstruction:
                axis = line
                break
    if not axis:
        raise Exception("Could not determine revolve axis")

    op_map = {"new_body": adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
              "join": adsk.fusion.FeatureOperations.JoinFeatureOperation,
              "cut": adsk.fusion.FeatureOperations.CutFeatureOperation,
              "intersect": adsk.fusion.FeatureOperations.IntersectFeatureOperation}
    ri = root.features.revolveFeatures.createInput(profile, axis, op_map.get(operation, op_map["new_body"]))
    ri.setAngleExtent(False, adsk.core.ValueInput.createByReal(angle * math.pi / 180.0))
    feat = root.features.revolveFeatures.add(ri)
    adsk.doEvents()
    return {"feature_id": feat.name,
            "body_id": feat.bodies.item(0).name if feat.bodies.count > 0 else "Unknown"}


def handle_create_sphere(body):
    root = get_root()
    center = body.get("center", [0, 0, 0])
    radius = body.get("radius", 50)
    name = body.get("name")
    cx, cy, cz, r = center[0] / 10.0, center[1] / 10.0, center[2] / 10.0, radius / 10.0

    sketch = root.sketches.add(root.xZConstructionPlane)
    sketch.name = "_temp_sphere_sketch"
    center_pt = adsk.core.Point3D.create(cx, cz, 0)
    start_pt = adsk.core.Point3D.create(cx, cz - r, 0)
    arc = sketch.sketchCurves.sketchArcs.addByCenterStartSweep(center_pt, start_pt, math.pi)
    end_pt = adsk.core.Point3D.create(cx, cz + r, 0)
    line = sketch.sketchCurves.sketchLines.addByTwoPoints(start_pt, end_pt)
    line.isConstruction = True
    adsk.doEvents()
    if sketch.profiles.count == 0:
        raise Exception("Failed to create sphere profile")

    ri = root.features.revolveFeatures.createInput(
        sketch.profiles.item(0), line, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ri.setAngleExtent(False, adsk.core.ValueInput.createByReal(2 * math.pi))
    feat = root.features.revolveFeatures.add(ri)
    adsk.doEvents()
    sphere = feat.bodies.item(0)
    if name:
        sphere.name = name
    if center[1] != 0:
        bodies = adsk.core.ObjectCollection.create()
        bodies.add(sphere)
        mi = root.features.moveFeatures.createInput2(bodies)
        t = adsk.core.Matrix3D.create()
        t.translation = adsk.core.Vector3D.create(0, cy, 0)
        mi.defineAsFreeMove(t)
        root.features.moveFeatures.add(mi)
    sketch.deleteMe()
    return {"body_id": sphere.name, "name": sphere.name, "center": center, "radius": radius}


def handle_create_cylinder(body):
    root = get_root()
    center = body.get("center", [0, 0, 0])
    radius = body.get("radius", 50)
    height = body.get("height", 100)
    axis = body.get("axis", "z")
    name = body.get("name")
    cx, cy, cz, r, h = center[0]/10, center[1]/10, center[2]/10, radius/10, height/10

    if axis == "z":
        base_plane = root.xYConstructionPlane
        cc = adsk.core.Point3D.create(cx, cy, 0)
        off = cz
    elif axis == "y":
        base_plane = root.xZConstructionPlane
        cc = adsk.core.Point3D.create(cx, -cz, 0)
        off = cy
    else:
        base_plane = root.yZConstructionPlane
        cc = adsk.core.Point3D.create(cy, cz, 0)
        off = cx

    if abs(off) > 0.001:
        pi = root.constructionPlanes.createInput()
        pi.setByOffset(base_plane, adsk.core.ValueInput.createByReal(off))
        plane = root.constructionPlanes.add(pi)
    else:
        plane = base_plane

    sketch = root.sketches.add(plane)
    sketch.name = "_temp_cylinder_sketch"
    sketch.sketchCurves.sketchCircles.addByCenterRadius(cc, r)
    adsk.doEvents()
    ei = root.features.extrudeFeatures.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(h))
    feat = root.features.extrudeFeatures.add(ei)
    adsk.doEvents()
    cyl = feat.bodies.item(0)
    if name:
        cyl.name = name
    sketch.deleteMe()
    bb = cyl.boundingBox
    return {"body_id": cyl.name, "name": cyl.name, "center": center, "radius": radius,
            "height": height, "axis": axis,
            "actual_bounds": {
                "min": [round(bb.minPoint.x*10, 2), round(bb.minPoint.y*10, 2), round(bb.minPoint.z*10, 2)],
                "max": [round(bb.maxPoint.x*10, 2), round(bb.maxPoint.y*10, 2), round(bb.maxPoint.z*10, 2)]}}


def handle_create_box(body):
    root = get_root()
    if body.get("center"):
        c = body["center"]
        w, d, h = body.get("width", 100), body.get("depth", 100), body.get("height", 100)
        corner1 = [c[0]-w/2, c[1]-d/2, c[2]-h/2]
        corner2 = [c[0]+w/2, c[1]+d/2, c[2]+h/2]
    else:
        corner1 = body.get("corner1", [0, 0, 0])
        corner2 = body.get("corner2", [100, 100, 100])
        w = abs(corner2[0]-corner1[0]); d = abs(corner2[1]-corner1[1]); h = abs(corner2[2]-corner1[2])
    name = body.get("name")
    z_off = min(corner1[2], corner2[2]) / 10.0

    if abs(z_off) > 0.001:
        pi = root.constructionPlanes.createInput()
        pi.setByOffset(root.xYConstructionPlane, adsk.core.ValueInput.createByReal(z_off))
        plane = root.constructionPlanes.add(pi)
    else:
        plane = root.xYConstructionPlane

    sketch = root.sketches.add(plane)
    sketch.name = "_temp_box_sketch"
    c1 = adsk.core.Point3D.create(corner1[0]/10, corner1[1]/10, 0)
    c2 = adsk.core.Point3D.create(corner2[0]/10, corner2[1]/10, 0)
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(c1, c2)
    adsk.doEvents()
    ei = root.features.extrudeFeatures.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ei.setDistanceExtent(False, adsk.core.ValueInput.createByReal(h/10.0))
    feat = root.features.extrudeFeatures.add(ei)
    adsk.doEvents()
    bx = feat.bodies.item(0)
    if name:
        bx.name = name
    sketch.deleteMe()
    return {"body_id": bx.name, "name": bx.name, "corner1": corner1, "corner2": corner2,
            "dimensions": {"width": w, "depth": d, "height": h}}


def handle_create_hole(body):
    root = get_root()
    body_id = body.get("body_id")
    center = body.get("center", [0, 0, 0])
    diameter = body.get("diameter", 10)
    depth = body.get("depth", 100)
    axis = body.get("axis", "z")
    through_all = body.get("through_all", False)

    target_body = _find_body(root, body_id)
    if not target_body:
        raise Exception(f"Body not found: {body_id}")
    bb = target_body.boundingBox

    if axis == "z":
        base_plane = root.xYConstructionPlane
        cc = adsk.core.Point3D.create(center[0]/10, center[1]/10, 0)
        off = center[2]/10
        ext_dir = adsk.fusion.ExtentDirections.NegativeExtentDirection
        if through_all:
            depth = (bb.maxPoint.z - bb.minPoint.z)*10 + 20
    elif axis == "y":
        base_plane = root.xZConstructionPlane
        cc = adsk.core.Point3D.create(center[0]/10, -center[2]/10, 0)
        off = bb.minPoint.y - 0.1
        ext_dir = adsk.fusion.ExtentDirections.PositiveExtentDirection
        if through_all:
            depth = (bb.maxPoint.y - bb.minPoint.y)*10 + 20
    else:
        base_plane = root.yZConstructionPlane
        cc = adsk.core.Point3D.create(center[1]/10, center[2]/10, 0)
        off = center[0]/10
        ext_dir = adsk.fusion.ExtentDirections.PositiveExtentDirection
        if through_all:
            depth = (bb.maxPoint.x - bb.minPoint.x)*10 + 20

    if abs(off) > 0.001:
        pi = root.constructionPlanes.createInput()
        pi.setByOffset(base_plane, adsk.core.ValueInput.createByReal(off))
        plane = root.constructionPlanes.add(pi)
    else:
        plane = base_plane

    sketch = root.sketches.add(plane)
    sketch.name = "_temp_hole_sketch"
    sketch.sketchCurves.sketchCircles.addByCenterRadius(cc, diameter / 20.0)
    adsk.doEvents()
    ei = root.features.extrudeFeatures.createInput(
        sketch.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
    ei.participantBodies = [target_body]
    if through_all:
        ei.setAllExtent(ext_dir)
    else:
        ei.setOneSideExtent(
            adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(depth/10)), ext_dir)
    root.features.extrudeFeatures.add(ei)
    adsk.doEvents()
    sketch.deleteMe()
    return {"success": True, "body_id": body_id, "hole_center": center,
            "hole_diameter": diameter, "hole_depth": depth if not through_all else "through_all"}


def handle_create_box_joint(body):
    root = get_root()
    receiving_name = body.get("receiving_body")
    mating_name = body.get("mating_body")
    joint_edge = body.get("joint_edge")
    finger_width = body.get("finger_width", 12.7)
    finger_depth = body.get("finger_depth", 12.7)
    component_name = body.get("component")

    if component_name:
        target_component, _ = get_component_by_name(component_name)
        if not target_component:
            raise Exception(f"Component not found: {component_name}")
    else:
        target_component = root

    rec = mat = None
    for b in target_component.bRepBodies:
        if b.name == receiving_name: rec = b
        if b.name == mating_name: mat = b
    if not rec:
        raise Exception(f"Receiving body not found: {receiving_name}")
    if not mat:
        raise Exception(f"Mating body not found: {mating_name}")

    r_bb = rec.boundingBox
    r_min = [r_bb.minPoint.x*10, r_bb.minPoint.y*10, r_bb.minPoint.z*10]
    r_max = [r_bb.maxPoint.x*10, r_bb.maxPoint.y*10, r_bb.maxPoint.z*10]
    m_bb = mat.boundingBox
    m_min = [m_bb.minPoint.x*10, m_bb.minPoint.y*10, m_bb.minPoint.z*10]
    m_max = [m_bb.maxPoint.x*10, m_bb.maxPoint.y*10, m_bb.maxPoint.z*10]

    if joint_edge in ("front", "back"):
        edge_length = r_max[0] - r_min[0]
    elif joint_edge in ("left", "right"):
        edge_length = r_max[1] - r_min[1]
    else:
        raise Exception(f"Invalid joint_edge: {joint_edge}")

    num_fingers = int(edge_length / finger_width)
    return {"status": "guidance", "receiving_body": receiving_name,
            "receiving_bounds": {"min": r_min, "max": r_max},
            "mating_body": mating_name, "mating_bounds": {"min": m_min, "max": m_max},
            "joint_edge": joint_edge, "edge_length_mm": edge_length,
            "finger_width_mm": finger_width, "finger_depth_mm": finger_depth,
            "num_fingers": num_fingers}


# ── Polyhedron / faceted geometry ─────────────────────────────

def handle_create_angled_plane(body):
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
            mag_n = math.sqrt(sum(x*x for x in n))
            n = [x/mag_n for x in n]
            ref = [0, 1, 0] if abs(n[1]) < 0.9 else [1, 0, 0]
            u = [ref[1]*n[2]-ref[2]*n[1], ref[2]*n[0]-ref[0]*n[2], ref[0]*n[1]-ref[1]*n[0]]
            mag_u = math.sqrt(sum(x*x for x in u))
            u = [x/mag_u for x in u]
            v = [n[1]*u[2]-n[2]*u[1], n[2]*u[0]-n[0]*u[2], n[0]*u[1]-n[1]*u[0]]
            sp = 100.0
            pts_mm = [list(point_coords),
                       [point_coords[0]+u[0]*sp, point_coords[1]+u[1]*sp, point_coords[2]+u[2]*sp],
                       [point_coords[0]+v[0]*sp, point_coords[1]+v[1]*sp, point_coords[2]+v[2]*sp]]
        else:
            raise Exception("Provide 'three_points' or 'point' + 'normal'")

        v1 = [pts_mm[1][i]-pts_mm[0][i] for i in range(3)]
        v2 = [pts_mm[2][i]-pts_mm[0][i] for i in range(3)]
        cn = [v1[1]*v2[2]-v1[2]*v2[1], v1[2]*v2[0]-v1[0]*v2[2], v1[0]*v2[1]-v1[1]*v2[0]]
        mag = math.sqrt(sum(x*x for x in cn))
        if mag < 1e-10:
            raise Exception("Points are collinear")
        cn = [x/mag for x in cn]

        try:
            p_cm = adsk.core.Point3D.create(pts_mm[0][0]/10, pts_mm[0][1]/10, pts_mm[0][2]/10)
            nrm = adsk.core.Vector3D.create(*cn)
            nrm.normalize()
            plane_geom = adsk.core.Plane.create(p_cm, nrm)
            pi = planes.createInput()
            pi.setByPlane(plane_geom)
            cp = planes.add(pi)
            if name:
                cp.name = name
            adsk.doEvents()
            geo = cp.geometry
            return {"success": True, "method": "setByPlane", "plane_id": cp.name, "name": cp.name,
                    "origin_mm": [geo.origin.x*10, geo.origin.y*10, geo.origin.z*10],
                    "normal": [geo.normal.x, geo.normal.y, geo.normal.z]}
        except Exception:
            pass

        tol_cm = tolerance_mm / 10.0
        resolved = []
        helpers_p = []
        helpers_s = []
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
                helpers_p.append(hp.name)
                hs = root.sketches.add(hp)
                hs.name = f"_ap_helper_sketch_{i}"
                helpers_s.append(hs.name)
                sp = hs.sketchPoints.add(adsk.core.Point3D.create(coords[0]/10, coords[1]/10, 0))
                resolved.append(sp)

        pi = planes.createInput()
        pi.setByThreePoints(resolved[0], resolved[1], resolved[2])
        cp = planes.add(pi)
        if name:
            cp.name = name
        adsk.doEvents()
        geo = cp.geometry
        return {"success": True, "method": "setByThreePoints", "plane_id": cp.name, "name": cp.name,
                "origin_mm": [geo.origin.x*10, geo.origin.y*10, geo.origin.z*10],
                "normal": [geo.normal.x, geo.normal.y, geo.normal.z]}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_plane_by_angle(body):
    try:
        root = get_root()
        planes = root.constructionPlanes
        base_plane_id = body.get("base_plane", "xy")
        sketch_id = body.get("sketch_id")
        line_index = body.get("line_index", 0)
        angle_deg = body.get("angle", 0)
        name = body.get("name")

        base_map = {"xy": root.xYConstructionPlane, "xz": root.xZConstructionPlane,
                     "yz": root.yZConstructionPlane}
        base = base_map.get(base_plane_id)
        if not base:
            for p in root.constructionPlanes:
                if p.name == base_plane_id:
                    base = p
                    break
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
        geo = cp.geometry
        return {"success": True, "plane_id": cp.name, "name": cp.name,
                "origin_mm": [geo.origin.x*10, geo.origin.y*10, geo.origin.z*10],
                "normal": [geo.normal.x, geo.normal.y, geo.normal.z]}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_polyhedron(body):
    try:
        root = get_root()
        vertices_dict = body.get("vertices", {})
        faces_list = body.get("faces", [])
        name = body.get("name", "Polyhedron")
        if len(vertices_dict) < 4:
            return {"error": True, "message": "Need >= 4 vertices"}
        if len(faces_list) < 4:
            return {"error": True, "message": "Need >= 4 faces"}

        vp = {}
        for vid, c in vertices_dict.items():
            vp[vid] = adsk.core.Point3D.create(c[0]/10, c[1]/10, c[2]/10)

        temp_brep = adsk.fusion.TemporaryBRepManager.get()
        surface_bodies = []
        for face_verts in faces_list:
            if len(face_verts) < 3:
                continue
            try:
                p1, p2, p3 = vp[face_verts[0]], vp[face_verts[1]], vp[face_verts[2]]
            except KeyError as e:
                return {"error": True, "message": f"Unknown vertex: {e}"}
            lines = [adsk.core.Line3D.create(p1, p2),
                     adsk.core.Line3D.create(p2, p3),
                     adsk.core.Line3D.create(p3, p1)]
            wire_body, _ = temp_brep.createWireFromCurves(lines)
            if wire_body:
                try:
                    fb = temp_brep.createFaceFromPlanarWires([wire_body])
                    if fb:
                        surface_bodies.append(fb)
                except Exception:
                    pass
        if not surface_bodies:
            return {"error": True, "message": "Could not create any faces"}

        try:
            result_body = temp_brep.stitch(surface_bodies, 0.01)
        except Exception:
            result_body = surface_bodies[0]

        if not result_body:
            return {"error": True, "message": "Failed to stitch faces"}

        bf = root.features.baseFeatures.add()
        bf.startEdit()
        rb = root.bRepBodies.add(result_body, bf)
        rb.name = name
        bf.finishEdit()
        adsk.doEvents()
        return {"success": True, "body_id": name, "body_name": rb.name,
                "vertex_count": len(vertices_dict), "face_count": len(faces_list),
                "faces_created": len(surface_bodies)}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_triangular_prism(body):
    try:
        root = get_root()
        v1 = body.get("v1", [0, 0, 0])
        v2 = body.get("v2", [100, 0, 0])
        v3 = body.get("v3", [50, 100, 0])
        height = body.get("height", 50)
        name = body.get("name")

        p1 = adsk.core.Point3D.create(v1[0]/10, v1[1]/10, v1[2]/10)
        p2 = adsk.core.Point3D.create(v2[0]/10, v2[1]/10, v2[2]/10)
        p3 = adsk.core.Point3D.create(v3[0]/10, v3[1]/10, v3[2]/10)
        vec1 = adsk.core.Vector3D.create(p2.x-p1.x, p2.y-p1.y, p2.z-p1.z)
        vec2 = adsk.core.Vector3D.create(p3.x-p1.x, p3.y-p1.y, p3.z-p1.z)
        normal = vec1.crossProduct(vec2)
        normal.normalize()

        plane_geom = adsk.core.Plane.create(p1, normal)
        cp = root.constructionPlanes.add(root.constructionPlanes.createInput())
        cpi = root.constructionPlanes.createInput()
        cpi.setByPlane(plane_geom)
        cp = root.constructionPlanes.add(cpi)
        cp.name = "_temp_tri_plane"

        sketch = root.sketches.add(cp)
        sketch.name = "_temp_tri_sketch"
        st = sketch.transform
        st.invert()
        sp1, sp2, sp3 = p1.copy(), p2.copy(), p3.copy()
        sp1.transformBy(st); sp2.transformBy(st); sp3.transformBy(st)

        lines = sketch.sketchCurves.sketchLines
        lines.addByTwoPoints(adsk.core.Point3D.create(sp1.x, sp1.y, 0),
                             adsk.core.Point3D.create(sp2.x, sp2.y, 0))
        lines.addByTwoPoints(adsk.core.Point3D.create(sp2.x, sp2.y, 0),
                             adsk.core.Point3D.create(sp3.x, sp3.y, 0))
        lines.addByTwoPoints(adsk.core.Point3D.create(sp3.x, sp3.y, 0),
                             adsk.core.Point3D.create(sp1.x, sp1.y, 0))
        adsk.doEvents()
        if sketch.profiles.count == 0:
            return {"error": True, "message": "No closed profile created"}

        ei = root.features.extrudeFeatures.createInput(
            sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ei.setSymmetricExtent(adsk.core.ValueInput.createByReal(height/10/2), True)
        feat = root.features.extrudeFeatures.add(ei)
        adsk.doEvents()
        nb = feat.bodies.item(0)
        if name:
            nb.name = name
        return {"success": True, "body_id": nb.name, "body_name": nb.name}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── Body query ────────────────────────────────────────────────

def handle_list_bodies(body):
    root = get_root()
    design = get_design()
    component_name = body.get("component")
    include_all = body.get("include_all", True)
    bodies = []

    body_provenance = {}
    try:
        tl = design.timeline
        for i in range(tl.count):
            item = tl.item(i)
            try:
                entity = item.entity
                if hasattr(entity, 'bodies') and entity.bodies:
                    for b in entity.bodies:
                        src_sk = None
                        ft = entity.objectType.split('::')[-1]
                        if hasattr(entity, 'profile') and entity.profile:
                            try:
                                src_sk = entity.profile.parentSketch.name
                            except Exception:
                                pass
                        body_provenance[b.entityToken] = {
                            "feature_name": item.name, "feature_type": ft,
                            "source_sketch": src_sk, "timeline_index": i}
            except Exception:
                pass
    except Exception:
        pass

    def add_body_info(b, comp_name):
        bb = b.boundingBox
        w = (bb.maxPoint.x - bb.minPoint.x) * 10
        d = (bb.maxPoint.y - bb.minPoint.y) * 10
        h = (bb.maxPoint.z - bb.minPoint.z) * 10
        prov = body_provenance.get(b.entityToken, {})
        dims = sorted([(w, 'X'), (d, 'Y'), (h, 'Z')], key=lambda x: x[0], reverse=True)
        bodies.append({
            "body_id": b.name, "name": b.name, "component": comp_name,
            "provenance": prov or None, "is_solid": b.isSolid,
            "volume_mm3": round(b.volume * 1000, 2),
            "dimensions": {"x_extent": round(w, 2), "y_extent": round(d, 2), "z_extent": round(h, 2)},
            "bounding_box": {
                "min": [round(bb.minPoint.x*10, 2), round(bb.minPoint.y*10, 2), round(bb.minPoint.z*10, 2)],
                "max": [round(bb.maxPoint.x*10, 2), round(bb.maxPoint.y*10, 2), round(bb.maxPoint.z*10, 2)]},
            "center": [round((bb.minPoint.x+bb.maxPoint.x)*5, 2),
                        round((bb.minPoint.y+bb.maxPoint.y)*5, 2),
                        round((bb.minPoint.z+bb.maxPoint.z)*5, 2)]})

    if not component_name or component_name == "root":
        for b in root.bRepBodies:
            add_body_info(b, "root")
    if include_all:
        for occ in root.allOccurrences:
            for b in occ.component.bRepBodies:
                add_body_info(b, occ.component.name)
    return {"bodies": bodies, "count": len(bodies)}


def handle_list_edges(body):
    root = get_root()
    body_id = body.get("body_id")
    component_name = body.get("component")
    comp = get_component_by_name(component_name)[0] if component_name else root
    if not comp:
        raise Exception(f"Component not found: {component_name}")
    tb = None
    for b in comp.bRepBodies:
        if b.name == body_id:
            tb = b; break
    if not tb:
        raise Exception(f"Body not found: {body_id}")

    edges = []
    for idx, edge in enumerate(tb.edges):
        geo = edge.geometry
        etype = "linear"
        radius = None
        if hasattr(geo, 'curveType'):
            if geo.curveType in (adsk.core.Curve3DTypes.Circle3DCurveType, adsk.core.Curve3DTypes.Arc3DCurveType):
                etype = "circular"
                radius = geo.radius * 10
        mp = edge.pointOnEdge
        edges.append({"edge_id": f"{body_id}_edge_{idx}", "type": etype,
                       "length": edge.length * 10, "radius": radius,
                       "midpoint": [mp.x*10, mp.y*10, mp.z*10]})
    return {"edges": edges}


def handle_list_faces(body):
    root = get_root()
    body_id = body.get("body_id")
    component_name = body.get("component")
    comp = get_component_by_name(component_name)[0] if component_name else root
    if not comp:
        raise Exception(f"Component not found: {component_name}")
    tb = None
    for b in comp.bRepBodies:
        if b.name == body_id:
            tb = b; break
    if not tb:
        raise Exception(f"Body not found: {body_id}")

    faces = []
    for idx, face in enumerate(tb.faces):
        geo = face.geometry
        ftype = "unknown"
        normal = None
        if hasattr(geo, 'surfaceType'):
            if geo.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                ftype = "planar"
                normal = [geo.normal.x, geo.normal.y, geo.normal.z]
            elif geo.surfaceType == adsk.core.SurfaceTypes.CylinderSurfaceType:
                ftype = "cylindrical"
            elif geo.surfaceType == adsk.core.SurfaceTypes.SphereSurfaceType:
                ftype = "spherical"
        c = face.centroid
        faces.append({"face_id": f"{body_id}_face_{idx}", "type": ftype,
                       "area": face.area * 100, "normal": normal,
                       "centroid": [c.x*10, c.y*10, c.z*10]})
    return {"faces": faces}


def handle_get_face_info(body):
    root = get_root()
    body_id = body.get("body_id")
    face_id = body.get("face_id")
    component_name = body.get("component")
    comp = get_component_by_name(component_name)[0] if component_name else root
    if not comp:
        raise Exception(f"Component not found: {component_name}")
    tb = None
    for b in comp.bRepBodies:
        if b.name == body_id:
            tb = b; break
    if not tb:
        raise Exception(f"Body not found: {body_id}")

    tf = None
    if "_face_" in face_id:
        fi = int(face_id.split("_face_")[-1])
        if 0 <= fi < tb.faces.count:
            tf = tb.faces.item(fi)
    else:
        try:
            fi = int(face_id)
            if 0 <= fi < tb.faces.count:
                tf = tb.faces.item(fi)
        except ValueError:
            pass
    if not tf:
        raise Exception(f"Face not found: {face_id}")

    geo = tf.geometry
    ftype = "unknown"
    normal = None
    angles = {}
    if hasattr(geo, 'surfaceType') and geo.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
        ftype = "planar"
        normal = [geo.normal.x, geo.normal.y, geo.normal.z]
        angles = {
            "to_xy_plane": math.degrees(geo.normal.angleTo(adsk.core.Vector3D.create(0, 0, 1))),
            "to_xz_plane": math.degrees(geo.normal.angleTo(adsk.core.Vector3D.create(0, 1, 0))),
            "to_yz_plane": math.degrees(geo.normal.angleTo(adsk.core.Vector3D.create(1, 0, 0)))}
    c = tf.centroid
    bb = tf.boundingBox
    return {"face_id": face_id, "body_id": body_id, "type": ftype,
            "area_mm2": tf.area * 100, "normal": normal, "angles": angles,
            "centroid_mm": [c.x*10, c.y*10, c.z*10],
            "bounding_box": {
                "min": [bb.minPoint.x*10, bb.minPoint.y*10, bb.minPoint.z*10],
                "max": [bb.maxPoint.x*10, bb.maxPoint.y*10, bb.maxPoint.z*10]}}


def handle_find_body_intersections(body):
    root = get_root()
    b1n = body.get("body1")
    b2n = body.get("body2")
    component_name = body.get("component")
    tol = body.get("tolerance", 0.01) / 10.0
    comp = get_component_by_name(component_name)[0] if component_name else root
    if not comp:
        raise Exception(f"Component not found: {component_name}")
    b1 = b2 = None
    for b in comp.bRepBodies:
        if b.name == b1n: b1 = b
        if b.name == b2n: b2 = b
    if not b1:
        raise Exception(f"Body not found: {b1n}")
    if not b2:
        raise Exception(f"Body not found: {b2n}")

    ints = []
    for ei, e1 in enumerate(b1.edges):
        s1, e1e = e1.startVertex.geometry, e1.endVertex.geometry
        for ej, e2 in enumerate(b2.edges):
            s2, e2e = e2.startVertex.geometry, e2.endVertex.geometry
            ds = min(s1.distanceTo(s2), s1.distanceTo(e2e))
            de = min(e1e.distanceTo(s2), e1e.distanceTo(e2e))
            if ds < tol and de < tol:
                mx = (s1.x + e1e.x) / 2
                my = (s1.y + e1e.y) / 2
                mz = (s1.z + e1e.z) / 2
                ints.append({"type": "shared_edge",
                             "edge1_id": f"{b1n}_edge_{ei}", "edge2_id": f"{b2n}_edge_{ej}",
                             "position_mm": [mx*10, my*10, mz*10], "length_mm": e1.length*10})
                break
    return {"body1": b1n, "body2": b2n, "intersections": ints, "count": len(ints)}


def handle_select_by_position(body):
    root = get_root()
    pt = point3d([c / 10.0 for c in body["point"]])
    search_type = body.get("type", "edge")
    tol = body.get("tolerance", 1) / 10.0
    matches = []
    for b in root.bRepBodies:
        if search_type == "edge":
            for e in b.edges:
                if e.pointOnEdge.distanceTo(pt) <= tol:
                    matches.append({"id": e.entityToken[:8], "distance": e.pointOnEdge.distanceTo(pt)*10})
        elif search_type == "face":
            for f in b.faces:
                if f.centroid.distanceTo(pt) <= tol:
                    matches.append({"id": f.entityToken[:8], "distance": f.centroid.distanceTo(pt)*10})
        elif search_type == "body":
            bb = b.boundingBox
            if (bb.minPoint.x <= pt.x <= bb.maxPoint.x and
                bb.minPoint.y <= pt.y <= bb.maxPoint.y and
                bb.minPoint.z <= pt.z <= bb.maxPoint.z):
                matches.append({"id": b.name, "distance": 0})
    return {"matches": matches}


def handle_get_body_center(body):
    root = get_root()
    body_id = body.get("body_id")
    tb = _find_body(root, body_id)
    if not tb:
        raise Exception(f"Body not found: {body_id}")
    bb = tb.boundingBox
    return {"body_id": body_id,
            "center": [round((bb.minPoint.x+bb.maxPoint.x)/2*10, 2),
                        round((bb.minPoint.y+bb.maxPoint.y)/2*10, 2),
                        round((bb.minPoint.z+bb.maxPoint.z)/2*10, 2)],
            "bounding_box": {
                "min": [round(bb.minPoint.x*10, 2), round(bb.minPoint.y*10, 2), round(bb.minPoint.z*10, 2)],
                "max": [round(bb.maxPoint.x*10, 2), round(bb.maxPoint.y*10, 2), round(bb.maxPoint.z*10, 2)]},
            "dimensions": {"width": round((bb.maxPoint.x-bb.minPoint.x)*10, 2),
                           "depth": round((bb.maxPoint.y-bb.minPoint.y)*10, 2),
                           "height": round((bb.maxPoint.z-bb.minPoint.z)*10, 2)},
            "volume_mm3": round(tb.volume * 1000, 2)}


def handle_get_model_summary(body):
    root = get_root()
    design = get_design()
    world_min = [float('inf')]*3
    world_max = [float('-inf')]*3
    all_bodies = []

    def proc(b, cn):
        bb = b.boundingBox
        for i in range(3):
            mn = [bb.minPoint.x, bb.minPoint.y, bb.minPoint.z][i] * 10
            mx = [bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z][i] * 10
            world_min[i] = min(world_min[i], mn)
            world_max[i] = max(world_max[i], mx)
        w = (bb.maxPoint.x-bb.minPoint.x)*10
        d = (bb.maxPoint.y-bb.minPoint.y)*10
        h = (bb.maxPoint.z-bb.minPoint.z)*10
        dims = sorted([(w, 'X'), (d, 'Y'), (h, 'Z')], key=lambda x: x[0], reverse=True)
        return {"body": b.name, "component": cn,
                "dims_mm": f"{round(dims[0][0],1)}({dims[0][1]}) x {round(dims[1][0],1)}({dims[1][1]}) x {round(dims[2][0],1)}({dims[2][1]})",
                "z_range": [round(bb.minPoint.z*10, 2), round(bb.maxPoint.z*10, 2)]}

    for b in root.bRepBodies:
        all_bodies.append(proc(b, "root"))
    for occ in root.allOccurrences:
        for b in occ.component.bRepBodies:
            all_bodies.append(proc(b, occ.component.name))

    comps = [{"name": "root", "body_count": root.bRepBodies.count, "sketch_count": root.sketches.count}]
    for occ in root.allOccurrences:
        c = occ.component
        comps.append({"name": c.name, "body_count": c.bRepBodies.count, "sketch_count": c.sketches.count})

    params = []
    try:
        for p in design.userParameters:
            params.append({"name": p.name,
                           "value": round(p.value*10, 3) if p.unit == "cm" else p.value,
                           "unit": "mm" if p.unit == "cm" else p.unit})
    except Exception:
        pass

    inf = float('inf')
    return {
        "world_bounds": {
            "min": [round(world_min[i], 2) for i in range(3)] if world_min[0] != inf else None,
            "max": [round(world_max[i], 2) for i in range(3)] if world_max[0] != -inf else None,
            "size": [round(world_max[i]-world_min[i], 2) if world_min[i] != inf else 0 for i in range(3)]},
        "components": comps, "bodies_summary": all_bodies, "parameters": params}


# ── Body manipulation ─────────────────────────────────────────

def handle_delete_body(body):
    root = get_root()
    body_name = body.get("body_name")
    component_name = body.get("component")
    if not body_name:
        raise Exception("body_name is required")

    deleted = False
    if component_name:
        comp, _ = get_component_by_name(component_name)
        if comp:
            for b in comp.bRepBodies:
                if b.name == body_name:
                    b.deleteMe(); deleted = True; break
    else:
        for b in root.bRepBodies:
            if b.name == body_name:
                b.deleteMe(); deleted = True; break
        if not deleted:
            for occ in root.allOccurrences:
                for b in occ.component.bRepBodies:
                    if b.name == body_name:
                        b.deleteMe(); deleted = True; break
                if deleted: break
    if not deleted:
        raise Exception(f"Body not found: {body_name}")
    return {"success": True, "deleted_body": body_name}


def handle_copy_body(body):
    root = get_root()
    body_id = body.get("body_id")
    new_name = body.get("name")
    src = None
    for b in root.bRepBodies:
        if b.name == body_id:
            src = b; break
    if not src:
        raise Exception(f"Body not found: {body_id}")
    coll = adsk.core.ObjectCollection.create()
    coll.add(src)
    feat = root.features.copyPasteBodies.add(coll)
    nb = feat.bodies.item(0)
    if new_name:
        nb.name = new_name
    return {"body_id": nb.name, "name": nb.name}


def handle_move_body(body):
    root = get_root()
    body_id = body.get("body_id")
    translation = body.get("translation")
    rotation = body.get("rotation")
    tb = None
    for b in root.bRepBodies:
        if b.name == body_id:
            tb = b; break
    if not tb:
        raise Exception(f"Body not found: {body_id}")
    coll = adsk.core.ObjectCollection.create()
    coll.add(tb)
    mi = root.features.moveFeatures.createInput2(coll)
    t = adsk.core.Matrix3D.create()
    if translation:
        t.translation = adsk.core.Vector3D.create(translation[0]/10, translation[1]/10, translation[2]/10)
    if rotation:
        ax = vector3d(rotation.get("axis", [0, 0, 1]))
        ang = rotation.get("angle", 0) * math.pi / 180.0
        org = point3d([c/10.0 for c in rotation.get("origin", [0, 0, 0])])
        t.setToRotation(ang, ax, org)
    mi.defineAsFreeMove(t)
    root.features.moveFeatures.add(mi)
    return {"success": True}


def handle_mirror_body(body):
    root = get_root()
    body_id = body.get("body_id")
    plane_id = body.get("plane", "xy")
    tb = None
    for b in root.bRepBodies:
        if b.name == body_id:
            tb = b; break
    if not tb:
        raise Exception(f"Body not found: {body_id}")

    plane_map = {"xy": root.xYConstructionPlane, "xz": root.xZConstructionPlane,
                  "yz": root.yZConstructionPlane}
    plane = plane_map.get(plane_id)
    if not plane:
        plane = root.constructionPlanes.itemByName(plane_id)
    if not plane:
        raise Exception(f"Plane not found: {plane_id}")

    coll = adsk.core.ObjectCollection.create()
    coll.add(tb)
    feat = root.features.mirrorFeatures.add(root.features.mirrorFeatures.createInput(coll, plane))
    return {"body_id": feat.bodies.item(0).name, "name": feat.bodies.item(0).name}


def handle_pattern_rectangular(body):
    root = get_root()
    body_id = body.get("body_id")
    tb = None
    for b in root.bRepBodies:
        if b.name == body_id:
            tb = b; break
    if not tb:
        raise Exception(f"Body not found: {body_id}")

    dir1 = vector3d(body.get("direction1", [1, 0, 0]))
    count1 = body.get("count1", 2)
    spacing1 = body.get("spacing1", 10) / 10.0
    coll = adsk.core.ObjectCollection.create()
    coll.add(tb)

    if dir1.x == 1: axis1 = root.xConstructionAxis
    elif dir1.y == 1: axis1 = root.yConstructionAxis
    else: axis1 = root.zConstructionAxis

    pi = root.features.rectangularPatternFeatures.createInput(
        coll, axis1, adsk.core.ValueInput.createByReal(count1),
        adsk.core.ValueInput.createByReal(spacing1),
        adsk.fusion.PatternDistanceType.SpacingPatternDistanceType)

    dir2 = body.get("direction2")
    if dir2:
        count2 = body.get("count2", 1)
        spacing2 = body.get("spacing2", 10) / 10.0
        if dir2[0] == 1: axis2 = root.xConstructionAxis
        elif dir2[1] == 1: axis2 = root.yConstructionAxis
        else: axis2 = root.zConstructionAxis
        pi.setDirectionTwo(axis2, adsk.core.ValueInput.createByReal(count2),
                           adsk.core.ValueInput.createByReal(spacing2))

    feat = root.features.rectangularPatternFeatures.add(pi)
    return {"feature_id": feat.name, "body_ids": [b.name for b in feat.bodies]}


# ── Route table fragment ──────────────────────────────────────

SOLID_ROUTES = {
    "/extrude": handle_extrude,
    "/extrude_with_draft": handle_extrude_with_draft,
    "/fillet_edges": handle_fillet_edges,
    "/chamfer_edges": handle_chamfer_edges,
    "/boolean": handle_boolean,
    "/shell": handle_shell,
    "/split_body": handle_split_body,
    "/create_patch": handle_create_patch,
    "/stitch": handle_stitch,
    "/loft": handle_loft,
    "/sweep": handle_sweep,
    "/revolve": handle_revolve,
    "/create_sphere": handle_create_sphere,
    "/create_cylinder": handle_create_cylinder,
    "/create_box": handle_create_box,
    "/create_hole": handle_create_hole,
    "/create_box_joint": handle_create_box_joint,
    "/create_polyhedron": handle_create_polyhedron,
    "/create_triangular_prism": handle_create_triangular_prism,
    "/list_bodies": handle_list_bodies,
    "/list_edges": handle_list_edges,
    "/list_faces": handle_list_faces,
    "/get_face_info": handle_get_face_info,
    "/find_body_intersections": handle_find_body_intersections,
    "/select_by_position": handle_select_by_position,
    "/get_body_center": handle_get_body_center,
    "/get_model_summary": handle_get_model_summary,
    "/delete_body": handle_delete_body,
    "/copy_body": handle_copy_body,
    "/move_body": handle_move_body,
    "/mirror_body": handle_mirror_body,
    "/pattern_rectangular": handle_pattern_rectangular,
}
