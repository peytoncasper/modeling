"""Structured action executor for Fusion 360.

Translates high-level ACTION dicts into sequences of Fusion API operations.
Returns resulting state patches so the LLM can update its context in one
round-trip.

ACTIONs are optional — the LLM can always fall back to primitive MCP tools.
The executor validates before running and wraps results in patches.
"""

import traceback
from typing import Dict, List, Optional, Any, Callable


class ActionExecutor:
    """Translates ACTION dicts into Fusion API calls.

    The `routes` dict maps handler names from FusionMCPBridge (the ROUTES
    table) so we can reuse existing handlers without reimplementing them.
    """

    def __init__(self, app, cad_state, patch_emitter, routes: Dict[str, Callable]):
        self.app = app
        self.state = cad_state
        self.emitter = patch_emitter
        self.routes = routes

    def execute(self, action: dict) -> dict:
        """Execute a structured ACTION and return result + patches.

        Args:
            action: {
                "op": "sketch.add_rectangle",
                "ctx": {"sketch": "Sketch1"},
                "args": {...},
                "expect": {...}  # optional
            }

        Returns: {
            "success": bool,
            "result": <handler result>,
            "patches": [PATCH, ...],
            "error": <if failed>
        }
        """
        op = action.get("op")
        if not op:
            return {"success": False, "error": "Missing 'op' field"}

        handler = self._OP_MAP.get(op)
        if not handler:
            return {"success": False, "error": f"Unknown op: {op}. Known: {list(self._OP_MAP.keys())}"}

        before_t = self.state.tick

        try:
            result = handler(self, action)
            patches = self.emitter.get_patches_since(before_t).get("patches", [])
            return {
                "success": not result.get("error"),
                "result": result,
                "patches": patches,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------------
    # Op implementations
    # ------------------------------------------------------------------

    def _do_sketch_add_rectangle(self, action: dict) -> dict:
        ctx = action.get("ctx", {})
        args = action.get("args", {})
        sketch_id = ctx.get("sketch")
        if not sketch_id:
            return {"error": "ctx.sketch required"}

        body = {
            "sketch_id": sketch_id,
            "corner1": args.get("corner1"),
            "corner2": args.get("corner2"),
        }
        if args.get("center") and args.get("w") and args.get("h"):
            cx, cy = args["center"]
            w = _parse_mm(args["w"])
            h = _parse_mm(args["h"])
            body["corner1"] = [cx - w / 2, cy - h / 2]
            body["corner2"] = [cx + w / 2, cy + h / 2]

        handler = self.routes.get("/draw_rectangle")
        if not handler:
            return {"error": "draw_rectangle route not available"}
        return handler(body)

    def _do_sketch_add_line(self, action: dict) -> dict:
        ctx = action.get("ctx", {})
        args = action.get("args", {})
        body = {
            "sketch_id": ctx.get("sketch"),
            "start": args.get("start"),
            "end": args.get("end"),
        }
        handler = self.routes.get("/draw_line")
        if not handler:
            return {"error": "draw_line route not available"}
        return handler(body)

    def _do_sketch_add_circle(self, action: dict) -> dict:
        ctx = action.get("ctx", {})
        args = action.get("args", {})
        body = {
            "sketch_id": ctx.get("sketch"),
            "center": args.get("center"),
            "radius": _parse_mm(args.get("radius", 0)),
        }
        handler = self.routes.get("/draw_circle")
        if not handler:
            return {"error": "draw_circle route not available"}
        return handler(body)

    def _do_sketch_finish(self, action: dict) -> dict:
        ctx = action.get("ctx", {})
        body = {"sketch_id": ctx.get("sketch")}
        handler = self.routes.get("/finish_sketch")
        if not handler:
            return {"error": "finish_sketch route not available"}
        return handler(body)

    def _do_feature_extrude(self, action: dict) -> dict:
        ctx = action.get("ctx", {})
        args = action.get("args", {})
        body = {
            "sketch_id": ctx.get("sketch"),
            "profile_index": args.get("profile_index", 0),
            "distance": _parse_mm(args.get("distance", 0)),
            "direction": args.get("direction", "positive"),
            "operation": args.get("operation", "new_body"),
        }
        if args.get("target_body"):
            body["target_body"] = args["target_body"]
        if args.get("body_name"):
            body["body_name"] = args["body_name"]

        handler = self.routes.get("/extrude")
        if not handler:
            return {"error": "extrude route not available"}
        return handler(body)

    def _do_feature_fillet(self, action: dict) -> dict:
        args = action.get("args", {})
        body = {
            "body_id": args.get("body"),
            "edge_ids": args.get("edges", []),
            "radius": _parse_mm(args.get("radius", 0)),
        }
        handler = self.routes.get("/fillet_edges")
        if not handler:
            return {"error": "fillet_edges route not available"}
        return handler(body)

    def _do_feature_chamfer(self, action: dict) -> dict:
        args = action.get("args", {})
        body = {
            "body_id": args.get("body"),
            "edge_ids": args.get("edges", []),
            "distance": _parse_mm(args.get("distance", 0)),
        }
        handler = self.routes.get("/chamfer_edges")
        if not handler:
            return {"error": "chamfer_edges route not available"}
        return handler(body)

    def _do_feature_boolean(self, action: dict) -> dict:
        args = action.get("args", {})
        body = {
            "target_body": args.get("target"),
            "tool_body": args.get("tool"),
            "operation": args.get("operation", "join"),
        }
        handler = self.routes.get("/boolean")
        if not handler:
            return {"error": "boolean route not available"}
        return handler(body)

    def _do_param_set(self, action: dict) -> dict:
        args = action.get("args", {})
        name = args.get("name")
        value = args.get("value")
        if not name or value is None:
            return {"error": "args.name and args.value required"}

        handler = self.routes.get("/modify_parameter")
        if not handler:
            return {"error": "modify_parameter route not available"}
        return handler({"name": name, "value": value})

    def _do_param_create(self, action: dict) -> dict:
        args = action.get("args", {})
        body = {
            "name": args.get("name"),
            "value": _parse_mm(args.get("value", 0)),
            "unit": args.get("unit", "mm"),
            "comment": args.get("comment", ""),
        }
        handler = self.routes.get("/create_parameter")
        if not handler:
            return {"error": "create_parameter route not available"}
        return handler(body)

    def _do_timeline_roll(self, action: dict) -> dict:
        """Roll the timeline to a specific position.

        Not directly supported by current bridge — returns guidance.
        """
        args = action.get("args", {})
        target = args.get("to")
        return {
            "warning": "Timeline roll not yet implemented as a direct bridge endpoint.",
            "suggestion": f"Use Fusion UI or undo/redo to reach timeline position: {target}",
        }

    def _do_sketch_create(self, action: dict) -> dict:
        args = action.get("args", {})
        body = {
            "plane": args.get("plane", "xy"),
            "name": args.get("name"),
        }
        if args.get("offset"):
            body["offset"] = _parse_mm(args["offset"])
        handler = self.routes.get("/create_sketch")
        if not handler:
            return {"error": "create_sketch route not available"}
        return handler(body)

    def _do_body_move(self, action: dict) -> dict:
        args = action.get("args", {})
        body = {
            "body_id": args.get("body"),
            "transform": args.get("transform", {}),
        }
        handler = self.routes.get("/move_body")
        if not handler:
            return {"error": "move_body route not available"}
        return handler(body)

    def _do_view_set(self, action: dict) -> dict:
        args = action.get("args", {})
        body = {"preset": args.get("preset", "isometric")}
        handler = self.routes.get("/set_view")
        if not handler:
            return {"error": "set_view route not available"}
        return handler(body)

    def _do_screenshot(self, action: dict) -> dict:
        args = action.get("args", {})
        body = {
            "width": args.get("width", 800),
            "height": args.get("height", 600),
        }
        handler = self.routes.get("/take_screenshot")
        if not handler:
            return {"error": "take_screenshot route not available"}
        return handler(body)

    # ------------------------------------------------------------------
    # Op table
    # ------------------------------------------------------------------

    _OP_MAP: Dict[str, Callable] = {
        "sketch.create": _do_sketch_create,
        "sketch.add_rectangle": _do_sketch_add_rectangle,
        "sketch.add_line": _do_sketch_add_line,
        "sketch.add_circle": _do_sketch_add_circle,
        "sketch.finish": _do_sketch_finish,
        "feature.extrude": _do_feature_extrude,
        "feature.fillet": _do_feature_fillet,
        "feature.chamfer": _do_feature_chamfer,
        "feature.boolean": _do_feature_boolean,
        "param.set": _do_param_set,
        "param.create": _do_param_create,
        "timeline.roll": _do_timeline_roll,
        "body.move": _do_body_move,
        "view.set": _do_view_set,
        "view.screenshot": _do_screenshot,
    }


def _parse_mm(val) -> float:
    """Parse a value that may be a string like '20 mm' or a number."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip().lower().replace("mm", "").replace("deg", "").strip()
        try:
            return float(s)
        except ValueError:
            return 0.0
    return 0.0
