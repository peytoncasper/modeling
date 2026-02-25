"""Navigation / indexing system handlers for Fusion 360 MCP Bridge.

Wraps the STATE + PATCH + LOCAL_GRAPH + FrameManager + EntityResolver +
ActionExecutor subsystems behind HTTP endpoints.  These are the handlers
that give the LLM spatial awareness and streaming state updates.

Endpoints (19):
  STATE
    /get_state          – full STATE snapshot
    /get_state_compact  – one-line nav string
  PATCH
    /get_patches_since  – incremental state diffs since tick t
    /drain_patches      – return + clear all queued patches
  LOCAL_GRAPH
    /get_local_graph    – entity neighborhood around a focus
  ACTION
    /apply_action       – high-level structured action execution
    /list_actions       – enumerate known ACTION ops
  FRAMES
    /create_frame       – generic frame
    /get_frame          – query a single frame
    /list_frames        – all frames, optionally filtered
    /delete_frame       – remove frame + children
    /transform_point    – re-project a point between frames
    /create_body_frame  – auto-frame from body bounding box
    /create_interface_frame – joint / connection frame
    /get_nearby_frames  – frames within radius of a point
  ENTITY RESOLVER
    /register_entity    – manually register an entity ref
    /resolve_entity     – look up an entity ref by id
    /list_entities      – dump the resolver cache
"""

import traceback

import adsk.core
import adsk.fusion

import bridge_helpers as _bh


# ── STATE ────────────────────────────────────────────────────

def handle_get_state(body):
    if not _bh.cad_state:
        return {"error": True, "message": "CAD state system not initialized"}
    try:
        return _bh.cad_state.snapshot(sparse=body.get("sparse", False))
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_get_state_compact(body):
    if not _bh.cad_state:
        return {"error": True, "message": "CAD state system not initialized"}
    try:
        return {"nav_string": _bh.cad_state.to_nav_string(), "t": _bh.cad_state.tick}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── PATCH ────────────────────────────────────────────────────

def handle_get_patches_since(body):
    if not _bh.patch_emitter:
        return {"error": True, "message": "Patch emitter not initialized"}
    try:
        return _bh.patch_emitter.get_patches_since(body.get("since_t", 0))
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_drain_patches(body):
    if not _bh.patch_emitter:
        return {"error": True, "message": "Patch emitter not initialized"}
    try:
        patches = _bh.patch_emitter.drain()
        return {"patches": patches, "count": len(patches), "current_t": _bh.cad_state.tick}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── LOCAL_GRAPH ──────────────────────────────────────────────

def handle_get_local_graph(body):
    if not _bh.graph_extractor:
        return {"error": True, "message": "Graph extractor not initialized"}
    try:
        return _bh.graph_extractor.extract(
            body.get("focus_kind", "auto"), body.get("focus_id"),
            body.get("depth", 1), body.get("component"))
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── ACTION ───────────────────────────────────────────────────

def handle_apply_action(body):
    if not _bh.action_executor:
        return {"error": True, "message": "Action executor not initialized"}
    try:
        action = body.get("action")
        if not action:
            return {"error": True, "message": "Missing 'action' field in request body"}
        return _bh.action_executor.execute(action)
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_list_actions(body):
    if not _bh.action_executor:
        return {"error": True, "message": "Action executor not initialized"}
    ops = list(_bh.action_executor._OP_MAP.keys())
    return {"actions": ops, "count": len(ops)}


# ── FRAMES ───────────────────────────────────────────────────

def handle_create_frame(body):
    try:
        frame = _bh.frame_manager.create_frame(
            name=body.get('name'), type=body.get('type'),
            origin=body.get('origin'),
            orientation=body.get('orientation', {"x": 0, "y": 0, "z": 0}),
            parent=body.get('parent'), metadata=body.get('metadata'))
        return {"success": True, "frame": frame.to_dict()}
    except Exception as e:
        return {"error": True, "message": str(e)}


def handle_get_frame(body):
    frame = _bh.frame_manager.get_frame(body.get('name'))
    if not frame:
        return {"error": True, "message": f"Frame {body.get('name')} not found"}
    result = frame.to_dict()
    if body.get('include_children'):
        result['children_details'] = [
            _bh.frame_manager.get_frame(c).to_dict()
            for c in frame.children if _bh.frame_manager.get_frame(c)]
    if body.get('include_mates'):
        result['mating_frames'] = _bh.frame_manager.get_mating_frames(body.get('name'))
    return result


def handle_list_frames(body):
    ft = body.get('filter', {}).get('type') if body.get('filter') else None
    frames = _bh.frame_manager.list_frames(ft)
    return {"frames": [f.to_dict() for f in frames], "count": len(frames)}


def handle_delete_frame(body):
    _bh.frame_manager.delete_frame(body.get('name'))
    return {"success": True}


def handle_transform_point(body):
    try:
        result = _bh.frame_manager.transform_point_between_frames(
            body.get('point'), body.get('from_frame'), body.get('to_frame'))
        return {"point": result, "from_frame": body.get('from_frame'), "to_frame": body.get('to_frame')}
    except Exception as e:
        return {"error": True, "message": str(e)}


def handle_create_body_frame(body):
    try:
        design = adsk.fusion.Design.cast(_bh.app.activeProduct)
        if not design:
            return {"error": True, "message": "No active design"}
        target_body = None
        comp_name = body.get('component')
        if comp_name:
            comp, occ = _bh.get_component_by_name(comp_name)
            if comp:
                for b in comp.bRepBodies:
                    if b.name == body.get('body_name'):
                        target_body = b
                        break
        else:
            for b in design.rootComponent.bRepBodies:
                if b.name == body.get('body_name'):
                    target_body = b
                    break
        if not target_body:
            return {"error": True, "message": f"Body {body.get('body_name')} not found"}
        bbox = target_body.boundingBox
        frame = _bh.frame_manager.create_body_frame(
            body_name=body.get('body_name'),
            bounds_min=[bbox.minPoint.x * 10, bbox.minPoint.y * 10, bbox.minPoint.z * 10],
            bounds_max=[bbox.maxPoint.x * 10, bbox.maxPoint.y * 10, bbox.maxPoint.z * 10],
            volume=target_body.volume * 1000, component=comp_name)
        return {"success": True, "frame": frame.to_dict()}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_create_interface_frame(body):
    try:
        frame = _bh.frame_manager.create_interface_frame(
            parent_frame=body.get('parent_frame'), name=body.get('name'),
            origin=body.get('origin'), normal=body.get('normal'),
            mates_with=body.get('mates_with'), metadata=body.get('metadata'))
        return {"success": True, "frame": frame.to_dict()}
    except Exception as e:
        return {"error": True, "message": str(e)}


def handle_get_nearby_frames(body):
    try:
        origin = body.get('origin', [0, 0, 0])
        radius = body.get('radius', 50.0)
        frames = _bh.frame_manager.get_nearby_frames(origin, radius)
        return {"frames": [f.to_dict() for f in frames], "count": len(frames)}
    except Exception as e:
        return {"error": True, "message": str(e)}


# ── ENTITY RESOLVER ──────────────────────────────────────────

def handle_register_entity(body):
    if not _bh.entity_resolver:
        return {"error": True, "message": "Entity resolver not initialized"}
    try:
        from entity_resolver import EntityRef, SemanticKey
        key_data = body.get("key")
        key = SemanticKey.from_dict(key_data) if key_data else None
        ref = EntityRef(id=body.get("id", ""), key=key)
        _bh.entity_resolver.register(ref)
        return {"success": True, "ref": ref.to_dict()}
    except Exception as e:
        return {"error": True, "message": str(e)}


def handle_resolve_entity(body):
    if not _bh.entity_resolver:
        return {"error": True, "message": "Entity resolver not initialized"}
    try:
        ref = _bh.entity_resolver.get_ref(body.get("id", ""))
        if not ref:
            return {"error": True, "message": f"Entity {body.get('id')} not in cache"}
        return {"ref": ref.to_dict(), "stale": ref.is_stale}
    except Exception as e:
        return {"error": True, "message": str(e)}


def handle_list_entities(body):
    if not _bh.entity_resolver:
        return {"error": True, "message": "Entity resolver not initialized"}
    try:
        data = _bh.entity_resolver.to_dict()
        refs = data.get("refs", {})
        type_filter = body.get("type")
        if type_filter:
            refs = {k: v for k, v in refs.items()
                    if v.get("key", {}).get("type") == type_filter}
        return {"refs": refs, "count": len(refs)}
    except Exception as e:
        return {"error": True, "message": str(e)}


# ── Route table ──────────────────────────────────────────────

NAV_ROUTES = {
    # STATE
    "/get_state": handle_get_state,
    "/get_state_compact": handle_get_state_compact,
    # PATCH
    "/get_patches_since": handle_get_patches_since,
    "/drain_patches": handle_drain_patches,
    # LOCAL_GRAPH
    "/get_local_graph": handle_get_local_graph,
    # ACTION
    "/apply_action": handle_apply_action,
    "/list_actions": handle_list_actions,
    # FRAMES
    "/create_frame": handle_create_frame,
    "/get_frame": handle_get_frame,
    "/list_frames": handle_list_frames,
    "/delete_frame": handle_delete_frame,
    "/transform_point": handle_transform_point,
    "/create_body_frame": handle_create_body_frame,
    "/create_interface_frame": handle_create_interface_frame,
    "/get_nearby_frames": handle_get_nearby_frames,
    # ENTITY RESOLVER
    "/register_entity": handle_register_entity,
    "/resolve_entity": handle_resolve_entity,
    "/list_entities": handle_list_entities,
}
