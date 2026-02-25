"""Local entity neighborhood extractor for Fusion 360.

Given a focus entity (sketch, body, face, feature), extracts the surrounding
topology graph: points/lines/constraints for sketches, faces/edges for bodies,
timeline deps for features.  Keeps output bounded by depth and entity caps.
"""

import traceback
from typing import Dict, List, Optional, Any

try:
    import adsk.core
    import adsk.fusion
except ImportError:
    pass

MAX_ENTITIES_PER_KIND = 60


class GraphExtractor:
    """Extracts LOCAL_GRAPH dicts from live Fusion state."""

    def __init__(self, app, entity_resolver):
        self.app = app
        self.er = entity_resolver

    def extract(self, focus_kind: str, focus_id: str,
                depth: int = 1, component: str = None) -> dict:
        """Extract LOCAL_GRAPH around the given focus entity.

        Args:
            focus_kind: "sketch" | "body" | "face" | "edge" | "feature" | "auto" | "none"
            focus_id: Entity identifier (name or ref id).
            depth: 1 = immediate neighbors, 2 = neighbors of neighbors.
            component: Optional component name scope.

        Returns:
            LOCAL_GRAPH dict.
        """
        if focus_kind == "auto":
            focus_kind, focus_id = self._auto_detect_focus()

        graph = {"around": {"kind": focus_kind, "id": focus_id}}

        try:
            if focus_kind == "sketch":
                graph["entities"] = {"sketch": self._extract_sketch(focus_id, component)}
            elif focus_kind == "body":
                graph["entities"] = {"body": self._extract_body(focus_id, component)}
            elif focus_kind == "face":
                graph["entities"] = {"face": self._extract_face(focus_id, component)}
            elif focus_kind == "edge":
                graph["entities"] = {"edge": self._extract_edge(focus_id, component)}
            elif focus_kind == "feature":
                graph["entities"] = {"feature": self._extract_feature(focus_id)}
            else:
                graph["entities"] = {"toplevel": self._extract_toplevel()}

            graph["deps"] = self._extract_deps(focus_kind, focus_id)
            graph["nearby"] = self._extract_nearby(focus_kind, focus_id, component)
        except Exception:
            graph["_error"] = traceback.format_exc()

        return graph

    # ------------------------------------------------------------------
    # Sketch graph
    # ------------------------------------------------------------------

    def _extract_sketch(self, sketch_id: str, component: str = None) -> dict:
        sketch = self._find_sketch(sketch_id, component)
        if not sketch:
            return {"error": f"Sketch {sketch_id} not found"}

        pts = []
        lines = []
        arcs = []
        circles = []
        constraints = []
        dims = []
        profiles = []

        # Points
        for i, pt in enumerate(sketch.sketchPoints):
            if i >= MAX_ENTITIES_PER_KIND:
                break
            geo = pt.geometry
            pts.append({
                "id": f"P{i}",
                "p": [round(geo.x * 10, 3), round(geo.y * 10, 3)],
            })

        # Curves
        for i, curve in enumerate(sketch.sketchCurves.sketchLines):
            if i >= MAX_ENTITIES_PER_KIND:
                break
            sp = curve.startSketchPoint
            ep = curve.endSketchPoint
            lines.append({
                "id": f"L{i}",
                "a": self._point_id(sp, sketch),
                "b": self._point_id(ep, sketch),
                "construction": curve.isConstruction,
                "length_mm": round(curve.length * 10, 3),
            })

        for i, curve in enumerate(sketch.sketchCurves.sketchArcs):
            if i >= MAX_ENTITIES_PER_KIND:
                break
            center = curve.centerSketchPoint
            arcs.append({
                "id": f"A{i}",
                "center": self._point_id(center, sketch),
                "radius_mm": round(curve.radius * 10, 3),
                "start_angle": round(curve.startAngle, 4),
                "end_angle": round(curve.endAngle, 4),
            })

        for i, curve in enumerate(sketch.sketchCurves.sketchCircles):
            if i >= MAX_ENTITIES_PER_KIND:
                break
            circles.append({
                "id": f"C{i}",
                "center_mm": [
                    round(curve.centerSketchPoint.geometry.x * 10, 3),
                    round(curve.centerSketchPoint.geometry.y * 10, 3),
                ],
                "radius_mm": round(curve.radius * 10, 3),
            })

        # Constraints
        for i, con in enumerate(sketch.geometricConstraints):
            if i >= MAX_ENTITIES_PER_KIND:
                break
            con_info = self._parse_constraint(con)
            if con_info:
                con_info["id"] = f"GC{i}"
                constraints.append(con_info)

        # Dimensions
        for i, dim in enumerate(sketch.sketchDimensions):
            if i >= MAX_ENTITIES_PER_KIND:
                break
            dim_info = self._parse_dimension(dim)
            if dim_info:
                dim_info["id"] = f"D{i}"
                dims.append(dim_info)

        # Profiles
        for i in range(min(sketch.profiles.count, 20)):
            profile = sketch.profiles.item(i)
            try:
                area = profile.areaProperties().area * 100
            except Exception:
                area = 0
            profiles.append({
                "id": f"Prof{i}",
                "area_mm2": round(area, 2),
            })

        result = {"pts": pts, "lines": lines}
        if arcs:
            result["arcs"] = arcs
        if circles:
            result["circles"] = circles
        if constraints:
            result["constraints"] = constraints
        if dims:
            result["dims"] = dims
        if profiles:
            result["profiles"] = profiles

        return result

    def _point_id(self, sketch_point, sketch) -> str:
        """Get a stable short id for a sketch point."""
        for i, pt in enumerate(sketch.sketchPoints):
            if pt == sketch_point:
                return f"P{i}"
        return "P?"

    def _parse_constraint(self, con) -> Optional[dict]:
        """Parse a geometric constraint to a compact dict."""
        try:
            obj_type = con.objectType.split("::")[-1]
            type_map = {
                "HorizontalConstraint": "horizontal",
                "VerticalConstraint": "vertical",
                "PerpendicularConstraint": "perpendicular",
                "ParallelConstraint": "parallel",
                "CoincidentConstraint": "coincident",
                "TangentConstraint": "tangent",
                "EqualConstraint": "equal",
                "CollinearConstraint": "collinear",
                "ConcentricConstraint": "concentric",
                "MidPointConstraint": "midpoint",
                "SymmetryConstraint": "symmetry",
                "FixConstraint": "fix",
                "SmoothConstraint": "smooth",
            }
            ctype = type_map.get(obj_type, obj_type)
            return {"type": ctype}
        except Exception:
            return None

    def _parse_dimension(self, dim) -> Optional[dict]:
        """Parse a sketch dimension to a compact dict."""
        try:
            obj_type = dim.objectType.split("::")[-1]
            value = dim.parameter.value if dim.parameter else 0

            type_map = {
                "SketchLinearDimension": "linear",
                "SketchAngularDimension": "angular",
                "SketchDiameterDimension": "diameter",
                "SketchRadialDimension": "radial",
                "SketchDistanceDimension": "distance",
                "SketchOffsetDimension": "offset",
            }
            dtype = type_map.get(obj_type, obj_type)

            unit = "mm"
            if dtype == "angular":
                unit = "deg"
            else:
                value = value * 10

            return {
                "type": dtype,
                "v": round(value, 4),
                "unit": unit,
                "expr": dim.parameter.expression if dim.parameter else None,
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Body graph
    # ------------------------------------------------------------------

    def _extract_body(self, body_id: str, component: str = None) -> dict:
        body = self._find_body(body_id, component)
        if not body:
            return {"error": f"Body {body_id} not found"}

        faces = []
        for i, face in enumerate(body.faces):
            if i >= MAX_ENTITIES_PER_KIND:
                break
            geo = face.geometry
            normal = None
            face_type = "unknown"
            if hasattr(geo, "surfaceType"):
                if geo.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                    face_type = "planar"
                    normal = [round(geo.normal.x, 4), round(geo.normal.y, 4), round(geo.normal.z, 4)]
                elif geo.surfaceType == adsk.core.SurfaceTypes.CylinderSurfaceType:
                    face_type = "cylindrical"
                elif geo.surfaceType == adsk.core.SurfaceTypes.SphereSurfaceType:
                    face_type = "spherical"

            centroid = face.centroid
            faces.append({
                "id": f"{body_id}_face_{i}",
                "type": face_type,
                "normal": normal,
                "area_mm2": round(face.area * 100, 2),
                "centroid_mm": [
                    round(centroid.x * 10, 2),
                    round(centroid.y * 10, 2),
                    round(centroid.z * 10, 2),
                ],
            })

        edges = []
        for i, edge in enumerate(body.edges):
            if i >= MAX_ENTITIES_PER_KIND:
                break
            midpoint = edge.pointOnEdge
            edge_type = "line"
            geo = edge.geometry
            if hasattr(geo, "curveType"):
                if geo.curveType in (adsk.core.Curve3DTypes.Circle3DCurveType,
                                     adsk.core.Curve3DTypes.Arc3DCurveType):
                    edge_type = "arc"

            edges.append({
                "id": f"{body_id}_edge_{i}",
                "type": edge_type,
                "length_mm": round(edge.length * 10, 2),
                "midpoint_mm": [
                    round(midpoint.x * 10, 2),
                    round(midpoint.y * 10, 2),
                    round(midpoint.z * 10, 2),
                ],
            })

        bbox = body.boundingBox
        bounds = {
            "min": [round(bbox.minPoint.x * 10, 2), round(bbox.minPoint.y * 10, 2), round(bbox.minPoint.z * 10, 2)],
            "max": [round(bbox.maxPoint.x * 10, 2), round(bbox.maxPoint.y * 10, 2), round(bbox.maxPoint.z * 10, 2)],
        }

        return {
            "name": body.name,
            "faces": faces,
            "edges": edges,
            "bounds_mm": bounds,
            "volume_mm3": round(body.volume * 1000, 2),
            "face_count": body.faces.count,
            "edge_count": body.edges.count,
        }

    # ------------------------------------------------------------------
    # Face / edge graph
    # ------------------------------------------------------------------

    def _extract_face(self, face_id: str, component: str = None) -> dict:
        """Extract neighborhood of a specific face."""
        body_name, _, idx_str = face_id.rpartition("_face_")
        if not body_name:
            return {"error": f"Cannot parse face id: {face_id}"}

        body = self._find_body(body_name, component)
        if not body:
            return {"error": f"Body {body_name} not found"}

        try:
            idx = int(idx_str)
            face = body.faces.item(idx) if idx < body.faces.count else None
        except (ValueError, RuntimeError):
            face = None

        if not face:
            return {"error": f"Face index {idx_str} out of range"}

        geo = face.geometry
        normal = None
        if hasattr(geo, "normal"):
            normal = [round(geo.normal.x, 4), round(geo.normal.y, 4), round(geo.normal.z, 4)]

        centroid = face.centroid
        adj_faces = []
        for edge in face.edges:
            for adj_face in edge.faces:
                if adj_face != face:
                    adj_idx = self._entity_index(adj_face, body.faces)
                    if adj_idx >= 0 and len(adj_faces) < 20:
                        adj_faces.append(f"{body_name}_face_{adj_idx}")

        bounding_edges = []
        for i, edge in enumerate(face.edges):
            edge_idx = self._entity_index(edge, body.edges)
            midpoint = edge.pointOnEdge
            bounding_edges.append({
                "id": f"{body_name}_edge_{edge_idx}",
                "length_mm": round(edge.length * 10, 2),
                "midpoint_mm": [
                    round(midpoint.x * 10, 2),
                    round(midpoint.y * 10, 2),
                    round(midpoint.z * 10, 2),
                ],
            })

        return {
            "id": face_id,
            "body": body_name,
            "normal": normal,
            "area_mm2": round(face.area * 100, 2),
            "centroid_mm": [
                round(centroid.x * 10, 2),
                round(centroid.y * 10, 2),
                round(centroid.z * 10, 2),
            ],
            "adjacent_faces": list(set(adj_faces)),
            "bounding_edges": bounding_edges,
        }

    def _extract_edge(self, edge_id: str, component: str = None) -> dict:
        """Extract neighborhood of a specific edge."""
        body_name, _, idx_str = edge_id.rpartition("_edge_")
        if not body_name:
            return {"error": f"Cannot parse edge id: {edge_id}"}

        body = self._find_body(body_name, component)
        if not body:
            return {"error": f"Body {body_name} not found"}

        try:
            idx = int(idx_str)
            edge = body.edges.item(idx) if idx < body.edges.count else None
        except (ValueError, RuntimeError):
            edge = None

        if not edge:
            return {"error": f"Edge index {idx_str} out of range"}

        midpoint = edge.pointOnEdge
        adj_faces = []
        for face in edge.faces:
            fidx = self._entity_index(face, body.faces)
            if fidx >= 0:
                adj_faces.append(f"{body_name}_face_{fidx}")

        return {
            "id": edge_id,
            "body": body_name,
            "length_mm": round(edge.length * 10, 2),
            "midpoint_mm": [
                round(midpoint.x * 10, 2),
                round(midpoint.y * 10, 2),
                round(midpoint.z * 10, 2),
            ],
            "adjacent_faces": adj_faces,
        }

    # ------------------------------------------------------------------
    # Feature graph
    # ------------------------------------------------------------------

    def _extract_feature(self, feature_id: str) -> dict:
        """Extract timeline dependencies for a feature."""
        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if not design:
                return {"error": "No active design"}

            timeline = design.timeline
            target_item = None
            target_index = -1

            for i in range(timeline.count):
                item = timeline.item(i)
                try:
                    if item.name == feature_id:
                        target_item = item
                        target_index = i
                        break
                except Exception:
                    pass

            if not target_item:
                return {"error": f"Feature {feature_id} not found in timeline"}

            entity = target_item.entity
            entity_type = "unknown"
            try:
                entity_type = entity.objectType.split("::")[-1]
            except Exception:
                pass

            affected_bodies = []
            try:
                if hasattr(entity, "bodies"):
                    for b in entity.bodies:
                        affected_bodies.append(b.name)
            except Exception:
                pass

            params = []
            try:
                if hasattr(entity, "parameters") and entity.parameters:
                    for p in entity.parameters:
                        params.append({
                            "name": p.name,
                            "v": round(p.value * 10, 4),
                            "unit": p.unit or "mm",
                            "expr": p.expression,
                        })
            except Exception:
                pass

            upstream = []
            downstream = []
            for i in range(timeline.count):
                if i == target_index:
                    continue
                try:
                    other = timeline.item(i)
                    other_entity = other.entity
                    if i < target_index:
                        if self._features_related(other_entity, entity):
                            upstream.append(other.name)
                    else:
                        if self._features_related(entity, other_entity):
                            downstream.append(other.name)
                except Exception:
                    pass

            return {
                "name": feature_id,
                "type": entity_type,
                "index": target_index,
                "affected_bodies": affected_bodies,
                "params": params,
                "upstream": upstream[:10],
                "downstream": downstream[:10],
            }
        except Exception:
            return {"error": traceback.format_exc()}

    def _features_related(self, earlier, later) -> bool:
        """Heuristic: do two features share any body?"""
        try:
            if hasattr(earlier, "bodies") and hasattr(later, "bodies"):
                early_names = {b.name for b in earlier.bodies}
                late_names = {b.name for b in later.bodies}
                return bool(early_names & late_names)
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Top-level overview
    # ------------------------------------------------------------------

    def _extract_toplevel(self) -> dict:
        """Overview when nothing specific is focused."""
        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if not design:
                return {"error": "No active design"}

            root = design.rootComponent
            bodies = []
            for b in root.bRepBodies:
                bbox = b.boundingBox
                bodies.append({
                    "name": b.name,
                    "bounds_mm": {
                        "min": [round(bbox.minPoint.x * 10, 2), round(bbox.minPoint.y * 10, 2), round(bbox.minPoint.z * 10, 2)],
                        "max": [round(bbox.maxPoint.x * 10, 2), round(bbox.maxPoint.y * 10, 2), round(bbox.maxPoint.z * 10, 2)],
                    },
                    "face_count": b.faces.count,
                })

            components = []
            for occ in root.allOccurrences:
                comp = occ.component
                components.append({
                    "name": occ.name,
                    "component": comp.name,
                    "body_count": comp.bRepBodies.count,
                })

            return {
                "bodies": bodies,
                "components": components,
                "sketch_count": root.sketches.count,
                "timeline_count": design.timeline.count,
            }
        except Exception:
            return {"error": traceback.format_exc()}

    # ------------------------------------------------------------------
    # Dependencies & nearby
    # ------------------------------------------------------------------

    def _extract_deps(self, focus_kind: str, focus_id: str) -> dict:
        """Extract upstream/downstream dependencies for any focus."""
        if focus_kind == "feature":
            return {}

        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if not design:
                return {}

            timeline = design.timeline
            upstream = []
            downstream = []

            if focus_kind == "sketch":
                for i in range(timeline.count):
                    try:
                        item = timeline.item(i)
                        if item.name == focus_id:
                            for j in range(i + 1, min(timeline.count, i + 10)):
                                later = timeline.item(j)
                                entity = later.entity
                                if hasattr(entity, "profile") and entity.profile:
                                    try:
                                        if entity.profile.parentSketch.name == focus_id:
                                            downstream.append(later.name)
                                    except Exception:
                                        pass
                            break
                    except Exception:
                        pass

            elif focus_kind in ("body", "face", "edge"):
                body_name = focus_id.split("_face_")[0].split("_edge_")[0]
                for i in range(timeline.count):
                    try:
                        item = timeline.item(i)
                        entity = item.entity
                        if hasattr(entity, "bodies"):
                            for b in entity.bodies:
                                if b.name == body_name:
                                    upstream.append(item.name)
                                    break
                    except Exception:
                        pass

            return {"upstream": upstream[:10], "downstream": downstream[:10]}
        except Exception:
            return {}

    def _extract_nearby(self, focus_kind: str, focus_id: str, component: str = None) -> dict:
        """Find bodies/frames near the focused entity."""
        nearby_bodies = []
        nearby_frames = []

        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if not design:
                return {}

            root = design.rootComponent

            if focus_kind == "body":
                target = self._find_body(focus_id, component)
                if target:
                    target_bbox = target.boundingBox
                    for b in root.bRepBodies:
                        if b.name == focus_id:
                            continue
                        if self._bboxes_close(target_bbox, b.boundingBox, tolerance_cm=0.5):
                            nearby_bodies.append({"name": b.name, "distance_mm": 0.0})
        except Exception:
            pass

        return {"bodies": nearby_bodies, "frames": nearby_frames}

    def _bboxes_close(self, a, b, tolerance_cm: float = 0.5) -> bool:
        """Check if two bounding boxes are within tolerance (overlap or gap < tol)."""
        for axis in ("x", "y", "z"):
            a_min = getattr(a.minPoint, axis)
            a_max = getattr(a.maxPoint, axis)
            b_min = getattr(b.minPoint, axis)
            b_max = getattr(b.maxPoint, axis)
            if a_max + tolerance_cm < b_min or b_max + tolerance_cm < a_min:
                return False
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _auto_detect_focus(self):
        """Detect focus from active edit or selection."""
        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if design:
                active = design.activeEditObject
                if active and "Sketch" in active.objectType:
                    sketch = adsk.fusion.Sketch.cast(active)
                    if sketch:
                        return "sketch", sketch.name

            sel = self.app.userInterface.activeSelections
            if sel.count > 0:
                entity = sel.item(0).entity
                obj_type = entity.objectType if entity else ""
                if "BRepBody" in obj_type:
                    return "body", entity.name
                elif "BRepFace" in obj_type:
                    body = entity.body
                    idx = self._entity_index(entity, body.faces)
                    return "face", f"{body.name}_face_{idx}"
                elif "BRepEdge" in obj_type:
                    body = entity.body
                    idx = self._entity_index(entity, body.edges)
                    return "edge", f"{body.name}_edge_{idx}"
        except Exception:
            pass

        return "none", None

    def _find_sketch(self, sketch_id: str, component: str = None):
        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if not design:
                return None
            root = design.rootComponent

            if component:
                for occ in root.allOccurrences:
                    if occ.component.name == component:
                        for sk in occ.component.sketches:
                            if sk.name == sketch_id:
                                return sk

            for sk in root.sketches:
                if sk.name == sketch_id:
                    return sk

            for occ in root.allOccurrences:
                for sk in occ.component.sketches:
                    if sk.name == sketch_id:
                        return sk
        except Exception:
            pass
        return None

    def _find_body(self, body_id: str, component: str = None):
        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if not design:
                return None
            root = design.rootComponent

            if component:
                for occ in root.allOccurrences:
                    if occ.component.name == component:
                        for b in occ.component.bRepBodies:
                            if b.name == body_id:
                                return b

            for b in root.bRepBodies:
                if b.name == body_id:
                    return b

            for occ in root.allOccurrences:
                for b in occ.component.bRepBodies:
                    if b.name == body_id:
                        return b
        except Exception:
            pass
        return None

    def _entity_index(self, entity, collection) -> int:
        for i in range(collection.count):
            if collection.item(i) == entity:
                return i
        return -1
