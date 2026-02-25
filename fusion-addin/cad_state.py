"""Compact CAD state builder for Fusion 360.

Produces a fixed-schema STATE dict that gives the LLM a token-efficient
snapshot of the current editing context: what's focused, selected, where
in the timeline, active frame, and user parameters.
"""

import traceback
from typing import Dict, List, Optional, Any

try:
    import adsk.core
    import adsk.fusion
except ImportError:
    pass


class CADState:
    """Builds and maintains the compact STATE object."""

    def __init__(self, app, frame_manager, entity_resolver):
        self.app = app
        self.fm = frame_manager
        self.er = entity_resolver
        self.tick = 0
        self._last_snapshot = None

    def bump_tick(self) -> int:
        self.tick += 1
        return self.tick

    def snapshot(self, sparse: bool = False) -> dict:
        """Build full STATE from current Fusion context.

        Args:
            sparse: If True, omit null/empty fields to save tokens.
        """
        self.bump_tick()
        state = {"t": self.tick}

        try:
            state["doc"] = self._get_doc_name()
            state["ctx"] = self._get_context()
            state["focus"] = self._get_focus()
            state["frame"] = self._get_active_frame()
            state["sel"] = self._get_selection()
            state["timeline"] = self._get_timeline_summary()
            state["params"] = self._get_compact_params()
            state["measures"] = []
            state["intent"] = None
        except Exception:
            state["_error"] = traceback.format_exc()

        if sparse:
            state = {k: v for k, v in state.items()
                     if v is not None and v != [] and v != {}}

        self._last_snapshot = state
        return state

    def to_nav_string(self) -> str:
        """Single-line, token-minimal representation of state."""
        s = self._last_snapshot or self.snapshot(sparse=True)

        parts = [f"S t{s.get('t', 0)}"]

        doc = s.get("doc")
        if doc:
            parts.append(f"doc={doc}")

        ctx = s.get("ctx", {})
        if ctx.get("comp"):
            parts.append(f"ctx={ctx['comp']}")

        focus = s.get("focus", {})
        if focus.get("kind") and focus["kind"] != "none":
            parts.append(f"focus={focus['kind']}:{focus.get('id', '?')}")

        frame = s.get("frame", {})
        if frame.get("id"):
            parts.append(f"frame={frame['id']}")

        sel = s.get("sel", [])
        if sel:
            parts.append(f"sel=[{','.join(str(x) for x in sel[:5])}]")

        tl = s.get("timeline", {})
        if tl.get("count"):
            at = tl.get("at", tl["count"])
            parts.append(f"tl={at}/{tl['count']}")

        params = s.get("params", {})
        if params:
            param_strs = [f"{k}:{v.get('v', '?')}" for k, v in list(params.items())[:5]]
            parts.append(f"params={{{','.join(param_strs)}}}")

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Private builders
    # ------------------------------------------------------------------

    def _get_doc_name(self) -> Optional[str]:
        doc = self.app.activeDocument
        if doc:
            return doc.name
        return None

    def _get_context(self) -> dict:
        """Active component and occurrence."""
        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if not design:
                return {"comp": None, "occ": None}

            active_comp = design.activeComponent
            comp_name = active_comp.name if active_comp else None

            active_occ = design.activeOccurrence
            occ_name = active_occ.name if active_occ else None

            return {"comp": comp_name, "occ": occ_name}
        except Exception:
            return {"comp": None, "occ": None}

    def _get_focus(self) -> dict:
        """Determine what the user is currently focused on.

        Priority:
          1. Active sketch being edited
          2. Active edit target (feature editing)
          3. Current selection (first selected entity)
          4. "none"
        """
        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if not design:
                return {"kind": "none", "id": None}

            # Check for active sketch edit
            active_edit = design.activeEditObject
            if active_edit:
                obj_type = active_edit.objectType
                if "Sketch" in obj_type:
                    sketch = adsk.fusion.Sketch.cast(active_edit)
                    if sketch:
                        plane_info = self._get_sketch_plane_info(sketch)
                        return {
                            "kind": "sketch",
                            "id": sketch.name,
                            "plane": plane_info,
                        }

            # Check selection
            sel = self.app.userInterface.activeSelections
            if sel.count > 0:
                first = sel.item(0).entity
                return self._classify_entity(first)

            return {"kind": "none", "id": None}
        except Exception:
            return {"kind": "none", "id": None}

    def _classify_entity(self, entity) -> dict:
        """Classify a Fusion entity into focus kind + id."""
        obj_type = entity.objectType if entity else ""

        if "BRepBody" in obj_type:
            return {"kind": "body", "id": entity.name}
        elif "BRepFace" in obj_type:
            body = entity.body
            idx = self._face_index(entity, body)
            return {
                "kind": "face",
                "id": f"{body.name}_face_{idx}",
                "body": body.name,
            }
        elif "BRepEdge" in obj_type:
            body = entity.body
            idx = self._edge_index(entity, body)
            return {
                "kind": "edge",
                "id": f"{body.name}_edge_{idx}",
                "body": body.name,
            }
        elif "Sketch" in obj_type:
            sketch = adsk.fusion.Sketch.cast(entity)
            if sketch:
                return {"kind": "sketch", "id": sketch.name}
        elif "Feature" in obj_type or "Timeline" in obj_type:
            name = entity.name if hasattr(entity, "name") else str(entity)
            return {"kind": "feature", "id": name}

        return {"kind": "unknown", "id": str(entity.objectType)}

    def _face_index(self, face, body) -> int:
        for i, f in enumerate(body.faces):
            if f == face:
                return i
        return -1

    def _edge_index(self, edge, body) -> int:
        for i, e in enumerate(body.edges):
            if e == edge:
                return i
        return -1

    def _get_sketch_plane_info(self, sketch) -> Optional[dict]:
        """Compact plane info for a sketch."""
        try:
            plane = sketch.referencePlane
            if not plane or not hasattr(plane, "geometry"):
                return None
            geo = plane.geometry
            if not hasattr(geo, "normal"):
                return None
            n = geo.normal
            nx, ny, nz = abs(n.x), abs(n.y), abs(n.z)
            if nz > 0.9:
                plane_type = "XY"
            elif ny > 0.9:
                plane_type = "XZ"
            elif nx > 0.9:
                plane_type = "YZ"
            else:
                plane_type = "custom"

            origin = None
            if hasattr(geo, "origin"):
                o = geo.origin
                origin = [round(o.x * 10, 2), round(o.y * 10, 2), round(o.z * 10, 2)]

            return {"type": plane_type, "origin": origin}
        except Exception:
            return None

    def _get_active_frame(self) -> dict:
        """Return the frame most relevant to the current editing context."""
        if not self.fm:
            return {"id": None}

        focus = self._get_focus() if not self._last_snapshot else self._last_snapshot.get("focus", {})
        focus_kind = focus.get("kind", "none")
        focus_id = focus.get("id")

        if focus_kind == "body" and focus_id:
            frame_name = f"{focus_id}_Frame"
            frame = self.fm.get_frame(frame_name)
            if frame:
                return {"id": frame.name, "origin": frame.origin}

        if focus_kind == "sketch" and focus_id:
            frame_name = f"{focus_id}_Frame"
            frame = self.fm.get_frame(frame_name)
            if frame:
                return {"id": frame.name, "origin": frame.origin}

        return {"id": "WorldFrame", "origin": [0, 0, 0]}

    def _get_selection(self) -> List[str]:
        """Current selection as a list of short ids."""
        try:
            sel = self.app.userInterface.activeSelections
            ids = []
            for i in range(min(sel.count, 20)):
                entity = sel.item(i).entity
                obj_type = entity.objectType if entity else ""
                if "BRepBody" in obj_type:
                    ids.append(entity.name)
                elif "BRepFace" in obj_type:
                    ids.append(f"{entity.body.name}_face_{self._face_index(entity, entity.body)}")
                elif "BRepEdge" in obj_type:
                    ids.append(f"{entity.body.name}_edge_{self._edge_index(entity, entity.body)}")
                elif hasattr(entity, "name"):
                    ids.append(entity.name)
                else:
                    ids.append(str(i))
            return ids
        except Exception:
            return []

    def _get_timeline_summary(self) -> dict:
        """Compact timeline state."""
        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if not design:
                return {}
            timeline = design.timeline
            marker = timeline.markerPosition
            count = timeline.count

            rolled_to = None
            if marker < count:
                try:
                    item_at_marker = timeline.item(marker)
                    rolled_to = f"before:{item_at_marker.name}"
                except Exception:
                    rolled_to = f"at:{marker}"

            return {
                "count": count,
                "at": marker,
                "rolled_to": rolled_to,
            }
        except Exception:
            return {}

    def _get_compact_params(self) -> dict:
        """User-defined parameters only, compact representation."""
        try:
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if not design:
                return {}
            params = design.userParameters
            result = {}
            for param in params:
                val_mm = param.value * 10
                unit = param.unit or "mm"
                if unit == "mm":
                    result[param.name] = {"v": f"{round(val_mm, 3)} mm"}
                elif unit == "deg":
                    result[param.name] = {"v": f"{round(param.value, 3)} deg"}
                else:
                    result[param.name] = {"v": f"{round(val_mm, 3)} {unit}"}
            return result
        except Exception:
            return {}
