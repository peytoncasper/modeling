"""Assembly / component / organization handlers for Fusion 360 MCP Bridge.

Manages the design hierarchy: components, occurrences, body ownership,
visibility, joints, and assembly-level transforms.

Every public function has the signature ``handle_*(body: dict) -> dict``
and is registered in ASSEMBLY_ROUTES.

Endpoints (20):
  COMPONENT MANAGEMENT
    /list_components        – tree of all components
    /get_component_info     – detailed info for one component
    /create_component       – new empty component (optionally nested)
    /delete_component       – remove a component occurrence
    /rename_component       – rename a component
    /duplicate_component    – deep-copy a component (new occurrence)
  BODY ORGANIZATION
    /rename_body            – rename a body
    /move_body_to_component – transfer a body between components
    /copy_body_to_component – copy a body into another component
  VISIBILITY
    /set_component_visibility – show/hide a component occurrence
    /set_body_visibility      – show/hide a body (light-bulb toggle)
  OCCURRENCE TRANSFORMS
    /move_occurrence        – translate/rotate a component occurrence
    /ground_component       – lock an occurrence in place
  JOINTS
    /create_joint           – rigid/revolute/slider/etc. between components
    /create_as_built_joint  – joint that preserves current positions
    /list_joints            – enumerate all joints
    /delete_joint           – remove a joint
  ASSEMBLY QUERY
    /get_assembly_context   – comprehensive assembly state snapshot
    /get_occurrence_transform – get the position/rotation of an occurrence
    /find_component_bodies  – list all bodies in a component (deep)
"""

import math
import traceback

import adsk.core
import adsk.fusion

try:
    from bridge_helpers import (
        get_design, get_root, get_component_by_name, find_body,
    )
except ImportError:
    from .bridge_helpers import (
        get_design, get_root, get_component_by_name, find_body,
    )


# ── Component Management ─────────────────────────────────────

def handle_list_components(body):
    root = get_root()
    components = []

    def gather_info(comp, parent_path="", occurrence=None):
        comp_name = comp.name
        comp_path = f"{parent_path}/{comp_name}" if parent_path else comp_name
        body_count = comp.bRepBodies.count
        sketch_count = comp.sketches.count

        children = []
        if occurrence:
            for child_occ in occurrence.childOccurrences:
                children.append({
                    "name": child_occ.component.name,
                    "occurrence_name": child_occ.name,
                    "path": f"{comp_path}/{child_occ.component.name}",
                })
        else:
            for child_occ in root.occurrences:
                children.append({
                    "name": child_occ.component.name,
                    "occurrence_name": child_occ.name,
                    "path": f"{comp_path}/{child_occ.component.name}",
                })

        info = {
            "name": comp_name,
            "path": comp_path,
            "body_count": body_count,
            "sketch_count": sketch_count,
            "children": children,
            "is_root": comp == root,
        }
        if occurrence:
            info["occurrence_name"] = occurrence.name
            info["is_visible"] = occurrence.isLightBulbOn
        return info

    components.append(gather_info(root, ""))
    for occ in root.allOccurrences:
        parent_path = ""
        if hasattr(occ, "assemblyContext") and occ.assemblyContext:
            parent_path = occ.assemblyContext.component.name
        components.append(gather_info(occ.component, parent_path, occ))

    return {
        "components": components,
        "total_components": len(components),
        "root_component": root.name,
        "total_occurrences": root.allOccurrences.count,
    }


def handle_get_component_info(body):
    root = get_root()
    component_name = body.get("component")
    if not component_name:
        raise Exception("component name is required")

    target_component, target_occ = get_component_by_name(component_name)
    if not target_component:
        raise Exception(f"Component not found: {component_name}")

    bodies = []
    for b in target_component.bRepBodies:
        bbox = b.boundingBox
        bodies.append({
            "name": b.name, "is_solid": b.isSolid,
            "is_visible": b.isLightBulbOn,
            "volume_mm3": round(b.volume * 1000, 1),
            "bounding_box": {
                "min": [round(bbox.minPoint.x * 10, 2), round(bbox.minPoint.y * 10, 2),
                        round(bbox.minPoint.z * 10, 2)],
                "max": [round(bbox.maxPoint.x * 10, 2), round(bbox.maxPoint.y * 10, 2),
                        round(bbox.maxPoint.z * 10, 2)],
            },
        })

    sketches = []
    for sketch in target_component.sketches:
        sketches.append({
            "name": sketch.name,
            "is_visible": sketch.isVisible,
            "profiles_count": sketch.profiles.count if hasattr(sketch, "profiles") else 0,
        })

    planes = []
    for plane in target_component.constructionPlanes:
        planes.append({"name": plane.name, "is_visible": plane.isVisible})

    children = []
    if target_occ:
        for child_occ in target_occ.childOccurrences:
            children.append({
                "name": child_occ.component.name,
                "occurrence_name": child_occ.name,
            })

    return {
        "component": {
            "name": target_component.name,
            "is_root": target_component == root,
            "body_count": len(bodies),
            "sketch_count": len(sketches),
            "plane_count": len(planes),
            "bodies": bodies,
            "sketches": sketches,
            "construction_planes": planes,
            "children": children,
        },
        "occurrence": {
            "name": target_occ.name if target_occ else None,
            "is_visible": target_occ.isLightBulbOn if target_occ else None,
            "is_grounded": target_occ.isGrounded if target_occ else None,
        } if target_occ else None,
    }


def handle_create_component(body):
    root = get_root()
    name = body.get("name")
    parent_name = body.get("parent")
    if not name:
        raise Exception("Component name is required")

    existing_comp, _ = get_component_by_name(name)
    if existing_comp:
        raise Exception(f"Component '{name}' already exists")

    if parent_name:
        parent_comp, _ = get_component_by_name(parent_name)
        if not parent_comp:
            raise Exception(f"Parent component not found: {parent_name}")
        parent = parent_comp
    else:
        parent = root

    transform = adsk.core.Matrix3D.create()
    new_occ = parent.occurrences.addNewComponent(transform)
    new_comp = new_occ.component
    new_comp.name = name

    return {
        "success": True,
        "component": {
            "name": new_comp.name,
            "occurrence_name": new_occ.name,
            "parent": parent.name,
        },
    }


def handle_delete_component(body):
    root = get_root()
    component_name = body.get("component")
    if not component_name:
        raise Exception("Component name is required")
    if component_name.lower() == "root" or component_name == root.name:
        raise Exception("Cannot delete root component")

    target_component, target_occ = get_component_by_name(component_name)
    if not target_component:
        raise Exception(f"Component not found: {component_name}")
    if not target_occ:
        raise Exception(f"Component '{component_name}' has no occurrence to delete")

    comp_name = target_component.name
    occ_name = target_occ.name
    target_occ.deleteMe()

    return {"success": True, "deleted_component": comp_name, "deleted_occurrence": occ_name}


def handle_rename_component(body):
    component_name = body.get("component")
    new_name = body.get("new_name")
    if not component_name or not new_name:
        raise Exception("component and new_name are required")

    root = get_root()
    if component_name.lower() == "root" or component_name == root.name:
        root.name = new_name
        return {"success": True, "old_name": component_name, "new_name": root.name, "is_root": True}

    target_component, _ = get_component_by_name(component_name)
    if not target_component:
        raise Exception(f"Component not found: {component_name}")

    old_name = target_component.name
    target_component.name = new_name
    return {"success": True, "old_name": old_name, "new_name": target_component.name}


def handle_duplicate_component(body):
    root = get_root()
    component_name = body.get("component")
    new_name = body.get("new_name")
    if not component_name:
        raise Exception("component is required")

    target_component, target_occ = get_component_by_name(component_name)
    if not target_component or not target_occ:
        raise Exception(f"Component not found: {component_name}")

    parent = target_occ.assemblyContext.component if target_occ.assemblyContext else root
    transform = target_occ.transform if target_occ else adsk.core.Matrix3D.create()
    new_occ = parent.occurrences.addExistingComponent(target_component, transform)
    if new_name:
        new_occ.component.name = new_name

    return {
        "success": True,
        "component": new_occ.component.name,
        "occurrence_name": new_occ.name,
    }


# ── Body Organization ────────────────────────────────────────

def handle_rename_body(body):
    body_name = body.get("body_name")
    new_name = body.get("new_name")
    component_name = body.get("component")
    if not body_name or not new_name:
        raise Exception("body_name and new_name are required")

    target_body = find_body(body_name, component_name)
    if not target_body:
        raise Exception(f"Body not found: {body_name}")

    old_name = target_body.name
    target_body.name = new_name
    return {"success": True, "old_name": old_name, "new_name": target_body.name}


def handle_move_body_to_component(body):
    root = get_root()
    body_name = body.get("body_name")
    target_component_name = body.get("target_component")
    source_component_name = body.get("source_component")
    if not body_name or not target_component_name:
        raise Exception("body_name and target_component are required")

    target_comp, target_occ = get_component_by_name(target_component_name)
    if not target_comp:
        raise Exception(f"Target component not found: {target_component_name}")

    src_body = find_body(body_name, source_component_name)
    if not src_body:
        raise Exception(f"Body not found: {body_name}")

    bodies = adsk.core.ObjectCollection.create()
    bodies.add(src_body)
    move_input = root.features.moveFeatures.createInput2(bodies)
    move_input.defineAsMoveBodies(target_comp)
    root.features.moveFeatures.add(move_input)
    adsk.doEvents()

    return {
        "success": True,
        "body": body_name,
        "target_component": target_comp.name,
    }


def handle_copy_body_to_component(body):
    root = get_root()
    body_name = body.get("body_name")
    target_component_name = body.get("target_component")
    new_name = body.get("new_name")
    if not body_name or not target_component_name:
        raise Exception("body_name and target_component are required")

    target_comp, _ = get_component_by_name(target_component_name)
    if not target_comp:
        raise Exception(f"Target component not found: {target_component_name}")

    src_body = find_body(body_name)
    if not src_body:
        raise Exception(f"Body not found: {body_name}")

    coll = adsk.core.ObjectCollection.create()
    coll.add(src_body)
    feat = target_comp.features.copyPasteBodies.add(coll)
    new_body = feat.bodies.item(0)
    if new_name:
        new_body.name = new_name

    return {
        "success": True,
        "body": new_body.name,
        "target_component": target_comp.name,
    }


# ── Visibility ────────────────────────────────────────────────

def handle_set_component_visibility(body):
    component_name = body.get("component")
    visible = body.get("visible", True)
    if not component_name:
        raise Exception("component is required")

    _, target_occ = get_component_by_name(component_name)
    if not target_occ:
        raise Exception(f"Component occurrence not found: {component_name}")

    target_occ.isLightBulbOn = visible
    return {"success": True, "component": component_name, "visible": visible}


def handle_set_body_visibility(body):
    body_name = body.get("body_name")
    visible = body.get("visible", True)
    component_name = body.get("component")
    if not body_name:
        raise Exception("body_name is required")

    target_body = find_body(body_name, component_name)
    if not target_body:
        raise Exception(f"Body not found: {body_name}")

    target_body.isLightBulbOn = visible
    return {"success": True, "body": body_name, "visible": visible}


# ── Occurrence Transforms ─────────────────────────────────────

def handle_move_occurrence(body):
    component_name = body.get("component")
    translation = body.get("translation")
    rotation = body.get("rotation")
    if not component_name:
        raise Exception("component is required")

    _, target_occ = get_component_by_name(component_name)
    if not target_occ:
        raise Exception(f"Component occurrence not found: {component_name}")

    transform = target_occ.transform
    if translation:
        t = adsk.core.Vector3D.create(
            translation[0] / 10.0, translation[1] / 10.0, translation[2] / 10.0)
        transform.translation = adsk.core.Vector3D.create(
            transform.translation.x + t.x,
            transform.translation.y + t.y,
            transform.translation.z + t.z)
    if rotation:
        axis = adsk.core.Vector3D.create(*rotation.get("axis", [0, 0, 1]))
        angle = rotation.get("angle", 0) * math.pi / 180.0
        origin_coords = rotation.get("origin", [0, 0, 0])
        origin = adsk.core.Point3D.create(
            origin_coords[0] / 10.0, origin_coords[1] / 10.0, origin_coords[2] / 10.0)
        rot_matrix = adsk.core.Matrix3D.create()
        rot_matrix.setToRotation(angle, axis, origin)
        transform.transformBy(rot_matrix)

    target_occ.transform = transform
    adsk.doEvents()

    final_t = target_occ.transform.translation
    return {
        "success": True,
        "component": component_name,
        "position_mm": [round(final_t.x * 10, 2), round(final_t.y * 10, 2),
                        round(final_t.z * 10, 2)],
    }


def handle_ground_component(body):
    component_name = body.get("component")
    grounded = body.get("grounded", True)
    if not component_name:
        raise Exception("component is required")

    _, target_occ = get_component_by_name(component_name)
    if not target_occ:
        raise Exception(f"Component occurrence not found: {component_name}")

    target_occ.isGrounded = grounded
    return {"success": True, "component": component_name, "grounded": grounded}


# ── Joints ────────────────────────────────────────────────────

def _resolve_joint_geometry(root, comp, geo_spec):
    """Resolve a joint geometry spec like {type: 'origin', component: 'Leg'} into
    a JointGeometry object.

    Supported types:
      - origin: component origin point
      - body_center: center of a named body bounding box
      - point: explicit [x,y,z] in mm
      - edge: edge midpoint
    """
    geo_type = geo_spec.get("type", "origin")
    comp_name = geo_spec.get("component")
    target_comp = comp
    target_occ = None
    if comp_name:
        target_comp, target_occ = get_component_by_name(comp_name)
        if not target_comp:
            raise Exception(f"Component not found: {comp_name}")

    if geo_type == "origin":
        if target_occ:
            return adsk.fusion.JointGeometry.createByPoint(target_occ)
        origin = target_comp.originConstructionPoint
        return adsk.fusion.JointGeometry.createByPoint(origin)

    elif geo_type == "body_center":
        body_name = geo_spec.get("body")
        if not body_name:
            raise Exception("body is required for body_center geometry")
        for b in target_comp.bRepBodies:
            if b.name == body_name:
                bb = b.boundingBox
                mid_face = None
                for f in b.faces:
                    mid_face = f
                    break
                if mid_face:
                    return adsk.fusion.JointGeometry.createByPlanarFace(
                        mid_face, None, adsk.fusion.JointKeyPointTypes.MiddleKeyPoint)
        raise Exception(f"Body not found: {body_name}")

    elif geo_type == "point":
        coords = geo_spec.get("point", [0, 0, 0])
        cp = target_comp.constructionPoints
        cpi = cp.createInput()
        cpi.setByPoint(adsk.core.Point3D.create(
            coords[0] / 10.0, coords[1] / 10.0, coords[2] / 10.0))
        pt = cp.add(cpi)
        return adsk.fusion.JointGeometry.createByPoint(pt)

    raise Exception(f"Unsupported joint geometry type: {geo_type}")


def handle_create_joint(body):
    try:
        root = get_root()
        design = get_design()
        joint_type_str = body.get("joint_type", "rigid")
        name = body.get("name")
        geo1_spec = body.get("geometry1")
        geo2_spec = body.get("geometry2")

        if not geo1_spec or not geo2_spec:
            raise Exception("geometry1 and geometry2 are required")

        type_map = {
            "rigid": adsk.fusion.JointTypes.RigidJointType,
            "revolute": adsk.fusion.JointTypes.RevoluteJointType,
            "slider": adsk.fusion.JointTypes.SliderJointType,
            "cylindrical": adsk.fusion.JointTypes.CylindricalJointType,
            "pin_slot": adsk.fusion.JointTypes.PinSlotJointType,
            "planar": adsk.fusion.JointTypes.PlanarJointType,
            "ball": adsk.fusion.JointTypes.BallJointType,
        }
        joint_type = type_map.get(joint_type_str)
        if joint_type is None:
            raise Exception(f"Unknown joint type: {joint_type_str}. Valid: {list(type_map.keys())}")

        geo1 = _resolve_joint_geometry(root, root, geo1_spec)
        geo2 = _resolve_joint_geometry(root, root, geo2_spec)

        joints = root.joints
        joint_input = joints.createInput(geo1, geo2)
        joint_input.setAsRigidJointMotion() if joint_type_str == "rigid" else None
        if joint_type_str == "revolute":
            joint_input.setAsRevoluteJointMotion(
                adsk.fusion.JointDirections.ZAxisJointDirection)
        elif joint_type_str == "slider":
            joint_input.setAsSliderJointMotion(
                adsk.fusion.JointDirections.ZAxisJointDirection)

        joint = joints.add(joint_input)
        if name:
            joint.name = name
        adsk.doEvents()

        return {
            "success": True,
            "joint_name": joint.name,
            "joint_type": joint_type_str,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_as_built_joint(body):
    try:
        root = get_root()
        component1_name = body.get("component1")
        component2_name = body.get("component2")
        joint_type_str = body.get("joint_type", "rigid")
        name = body.get("name")

        if not component1_name or not component2_name:
            raise Exception("component1 and component2 are required")

        _, occ1 = get_component_by_name(component1_name)
        _, occ2 = get_component_by_name(component2_name)
        if not occ1:
            raise Exception(f"Component occurrence not found: {component1_name}")
        if not occ2:
            raise Exception(f"Component occurrence not found: {component2_name}")

        type_map = {
            "rigid": adsk.fusion.JointTypes.RigidJointType,
            "revolute": adsk.fusion.JointTypes.RevoluteJointType,
            "slider": adsk.fusion.JointTypes.SliderJointType,
            "cylindrical": adsk.fusion.JointTypes.CylindricalJointType,
            "pin_slot": adsk.fusion.JointTypes.PinSlotJointType,
            "planar": adsk.fusion.JointTypes.PlanarJointType,
            "ball": adsk.fusion.JointTypes.BallJointType,
        }
        joint_type = type_map.get(joint_type_str)
        if joint_type is None:
            raise Exception(f"Unknown joint type: {joint_type_str}")

        as_built = root.asBuiltJoints
        abi = as_built.createInput(occ1, occ2, joint_type)
        joint = as_built.add(abi)
        if name:
            joint.name = name
        adsk.doEvents()

        return {
            "success": True,
            "joint_name": joint.name,
            "joint_type": joint_type_str,
            "component1": component1_name,
            "component2": component2_name,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_list_joints(body):
    try:
        root = get_root()
        joints = []

        for j in root.joints:
            info = {
                "name": j.name,
                "type": "joint",
                "is_suppressed": j.isSuppressed,
            }
            try:
                if j.occurrenceOne:
                    info["component1"] = j.occurrenceOne.component.name
                if j.occurrenceTwo:
                    info["component2"] = j.occurrenceTwo.component.name
            except Exception:
                pass
            try:
                jm = j.jointMotion
                if jm:
                    info["joint_type"] = jm.jointType
            except Exception:
                pass
            joints.append(info)

        for j in root.asBuiltJoints:
            info = {
                "name": j.name,
                "type": "as_built_joint",
                "is_suppressed": j.isSuppressed,
            }
            try:
                if j.occurrenceOne:
                    info["component1"] = j.occurrenceOne.component.name
                if j.occurrenceTwo:
                    info["component2"] = j.occurrenceTwo.component.name
            except Exception:
                pass
            joints.append(info)

        return {"joints": joints, "count": len(joints)}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_delete_joint(body):
    try:
        root = get_root()
        joint_name = body.get("joint_name")
        if not joint_name:
            raise Exception("joint_name is required")

        for j in root.joints:
            if j.name == joint_name:
                j.deleteMe()
                return {"success": True, "deleted": joint_name}
        for j in root.asBuiltJoints:
            if j.name == joint_name:
                j.deleteMe()
                return {"success": True, "deleted": joint_name}

        raise Exception(f"Joint not found: {joint_name}")
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── Assembly Query ────────────────────────────────────────────

def handle_get_assembly_context(body):
    try:
        root = get_root()
        design = get_design()

        components = []
        for occ in root.allOccurrences:
            t = occ.transform.translation
            comp = occ.component
            bodies = [b.name for b in comp.bRepBodies]
            components.append({
                "name": comp.name,
                "occurrence_name": occ.name,
                "is_visible": occ.isLightBulbOn,
                "is_grounded": occ.isGrounded,
                "position_mm": [round(t.x * 10, 2), round(t.y * 10, 2), round(t.z * 10, 2)],
                "body_count": comp.bRepBodies.count,
                "bodies": bodies,
            })

        root_bodies = [b.name for b in root.bRepBodies]

        joints = []
        for j in root.joints:
            info = {"name": j.name, "type": "joint", "suppressed": j.isSuppressed}
            try:
                if j.occurrenceOne:
                    info["comp1"] = j.occurrenceOne.component.name
                if j.occurrenceTwo:
                    info["comp2"] = j.occurrenceTwo.component.name
            except Exception:
                pass
            joints.append(info)
        for j in root.asBuiltJoints:
            info = {"name": j.name, "type": "as_built", "suppressed": j.isSuppressed}
            try:
                if j.occurrenceOne:
                    info["comp1"] = j.occurrenceOne.component.name
                if j.occurrenceTwo:
                    info["comp2"] = j.occurrenceTwo.component.name
            except Exception:
                pass
            joints.append(info)

        return {
            "root_component": root.name,
            "root_bodies": root_bodies,
            "root_body_count": len(root_bodies),
            "components": components,
            "component_count": len(components),
            "joints": joints,
            "joint_count": len(joints),
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_get_occurrence_transform(body):
    component_name = body.get("component")
    if not component_name:
        raise Exception("component is required")

    _, target_occ = get_component_by_name(component_name)
    if not target_occ:
        raise Exception(f"Component occurrence not found: {component_name}")

    t = target_occ.transform
    translation = t.translation
    cells = []
    for r in range(4):
        for c in range(4):
            cells.append(t.getCell(r, c))

    return {
        "component": component_name,
        "translation_mm": [round(translation.x * 10, 2), round(translation.y * 10, 2),
                           round(translation.z * 10, 2)],
        "matrix_4x4": cells,
        "is_grounded": target_occ.isGrounded,
    }


def handle_find_component_bodies(body):
    component_name = body.get("component")
    include_children = body.get("include_children", True)
    if not component_name:
        raise Exception("component is required")

    target_comp, target_occ = get_component_by_name(component_name)
    if not target_comp:
        raise Exception(f"Component not found: {component_name}")

    bodies = []
    for b in target_comp.bRepBodies:
        bbox = b.boundingBox
        bodies.append({
            "name": b.name,
            "component": target_comp.name,
            "is_solid": b.isSolid,
            "is_visible": b.isLightBulbOn,
            "volume_mm3": round(b.volume * 1000, 2),
            "bounding_box": {
                "min": [round(bbox.minPoint.x * 10, 2), round(bbox.minPoint.y * 10, 2),
                        round(bbox.minPoint.z * 10, 2)],
                "max": [round(bbox.maxPoint.x * 10, 2), round(bbox.maxPoint.y * 10, 2),
                        round(bbox.maxPoint.z * 10, 2)],
            },
        })

    if include_children and target_occ:
        for child_occ in target_occ.childOccurrences:
            for b in child_occ.component.bRepBodies:
                bbox = b.boundingBox
                bodies.append({
                    "name": b.name,
                    "component": child_occ.component.name,
                    "is_solid": b.isSolid,
                    "is_visible": b.isLightBulbOn,
                    "volume_mm3": round(b.volume * 1000, 2),
                    "bounding_box": {
                        "min": [round(bbox.minPoint.x * 10, 2), round(bbox.minPoint.y * 10, 2),
                                round(bbox.minPoint.z * 10, 2)],
                        "max": [round(bbox.maxPoint.x * 10, 2), round(bbox.maxPoint.y * 10, 2),
                                round(bbox.maxPoint.z * 10, 2)],
                    },
                })

    return {"bodies": bodies, "count": len(bodies)}


# ── Route table ──────────────────────────────────────────────

ASSEMBLY_ROUTES = {
    # Component Management
    "/list_components": handle_list_components,
    "/get_component_info": handle_get_component_info,
    "/create_component": handle_create_component,
    "/delete_component": handle_delete_component,
    "/rename_component": handle_rename_component,
    "/duplicate_component": handle_duplicate_component,
    # Body Organization
    "/rename_body": handle_rename_body,
    "/move_body_to_component": handle_move_body_to_component,
    "/copy_body_to_component": handle_copy_body_to_component,
    # Visibility
    "/set_component_visibility": handle_set_component_visibility,
    "/set_body_visibility": handle_set_body_visibility,
    # Occurrence Transforms
    "/move_occurrence": handle_move_occurrence,
    "/ground_component": handle_ground_component,
    # Joints
    "/create_joint": handle_create_joint,
    "/create_as_built_joint": handle_create_as_built_joint,
    "/list_joints": handle_list_joints,
    "/delete_joint": handle_delete_joint,
    # Assembly Query
    "/get_assembly_context": handle_get_assembly_context,
    "/get_occurrence_transform": handle_get_occurrence_transform,
    "/find_component_bodies": handle_find_component_bodies,
}
