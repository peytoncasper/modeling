"""Timeline handlers for Fusion 360 MCP Bridge.

The timeline is the parametric history — every sketch, feature, and operation
is an ordered item.  These handlers give full read/write/navigate access.

Endpoints (22):
  QUERY
    /timeline_list          – all items with rich details
    /timeline_item          – single item by name or index
    /timeline_marker        – current marker position + context
    /timeline_count         – quick count
    /timeline_search        – search by name/type substring
    /timeline_health        – health state of all features
    /timeline_feature_params – parameters for a specific feature
  NAVIGATE
    /timeline_roll_to       – move marker to index or feature name
    /timeline_roll_end      – marker → end
    /timeline_roll_beginning – marker → beginning
  MODIFY
    /timeline_suppress      – suppress one or more features
    /timeline_unsuppress    – unsuppress one or more features
    /timeline_delete        – delete a feature
    /timeline_move          – reorder feature to new position
    /timeline_edit_param    – edit a feature's parameter
    /timeline_rename        – rename a timeline item
    /timeline_undo          – delete last unsuppressed feature
    /timeline_redo          – unsuppress last suppressed feature
  GROUP
    /timeline_create_group  – create a group from index range
    /timeline_collapse_group – collapse a group
    /timeline_expand_group  – expand a group
  ANALYSIS
    /timeline_deps          – upstream/downstream dependencies
"""

import traceback

import adsk.core
import adsk.fusion

import bridge_helpers as _bh


# ── Helpers ──────────────────────────────────────────────────

def _get_timeline():
    design = adsk.fusion.Design.cast(_bh.app.activeProduct)
    if not design:
        return None, None
    return design, design.timeline


def _find_item(timeline, name=None, index=None):
    """Find a timeline item by name or index. Returns (item, index)."""
    if index is not None:
        if 0 <= index < timeline.count:
            return timeline.item(index), index
        return None, -1
    if name:
        for i in range(timeline.count):
            try:
                item = timeline.item(i)
                if item.name == name:
                    return item, i
            except Exception:
                pass
    return None, -1


def _item_to_dict(item, idx):
    """Rich dict representation of a timeline item."""
    d = {"index": idx, "name": "unknown", "type": "unknown", "suppressed": False}

    try:
        d["name"] = item.name
    except Exception:
        d["name"] = f"Item_{idx}"

    try:
        entity = item.entity
        d["type"] = entity.objectType.split("::")[-1] if entity else "unknown"
    except Exception:
        pass

    try:
        d["suppressed"] = item.isSuppressed
    except Exception:
        pass

    try:
        d["is_group"] = item.isGroup
    except Exception:
        d["is_group"] = False

    try:
        if hasattr(item, "isCollapsed"):
            d["is_collapsed"] = item.isCollapsed
    except Exception:
        pass

    try:
        if hasattr(item, "parentGroup") and item.parentGroup:
            d["parent_group"] = item.parentGroup.name
    except Exception:
        pass

    try:
        hs = item.healthState
        state_map = {0: "healthy", 1: "warning", 2: "error", 3: "suppressed"}
        d["health"] = state_map.get(hs, f"unknown({hs})")
    except Exception:
        d["health"] = "unknown"

    return d


def _item_detail(item, idx, design):
    """Extended details for a single item including params and affected bodies."""
    d = _item_to_dict(item, idx)

    try:
        entity = item.entity
        if entity:
            # Affected bodies
            if hasattr(entity, "bodies") and entity.bodies:
                d["affected_bodies"] = [b.name for b in entity.bodies]

            # Source sketch for sketch-based features
            if hasattr(entity, "profile") and entity.profile:
                try:
                    d["source_sketch"] = entity.profile.parentSketch.name
                except Exception:
                    pass

            # Parameters
            params = []
            if hasattr(entity, "extentOne"):
                try:
                    extent = entity.extentOne
                    if hasattr(extent, "distance"):
                        dp = extent.distance
                        params.append({
                            "name": "distance",
                            "value_mm": round(dp.value * 10, 4),
                            "expression": dp.expression if hasattr(dp, "expression") else None,
                        })
                except Exception:
                    pass

            if hasattr(entity, "parameters") and entity.parameters:
                try:
                    for p in entity.parameters:
                        params.append({
                            "name": p.name,
                            "value": round(p.value * 10, 4) if p.unit in ("cm", "") else round(p.value, 4),
                            "expression": p.expression,
                            "unit": p.unit or "mm",
                        })
                except Exception:
                    pass

            if params:
                d["parameters"] = params
    except Exception:
        pass

    # Related model parameters
    try:
        all_params = design.allParameters
        related = []
        feat_name = d["name"]
        for param in all_params:
            try:
                if feat_name in param.name or feat_name in (param.expression or ""):
                    related.append({
                        "name": param.name,
                        "value": round(param.value * 10, 4) if param.unit in ("cm", "mm", "") else round(param.value, 4),
                        "expression": param.expression,
                        "unit": param.unit or "mm",
                    })
            except Exception:
                pass
        if related:
            d["related_parameters"] = related
    except Exception:
        pass

    return d


# ── QUERY ────────────────────────────────────────────────────

def handle_timeline_list(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        include_suppressed = body.get("include_suppressed", True)
        start = body.get("start", 0)
        limit = body.get("limit", timeline.count)

        items = []
        for i in range(start, min(start + limit, timeline.count)):
            try:
                item = timeline.item(i)
                d = _item_to_dict(item, i)
                if not include_suppressed and d.get("suppressed"):
                    continue
                items.append(d)
            except Exception:
                items.append({"index": i, "name": f"Item_{i}", "type": "unknown", "suppressed": False})

        return {
            "items": items,
            "count": timeline.count,
            "marker": timeline.markerPosition,
            "shown": len(items),
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_item(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        item, idx = _find_item(timeline, body.get("name"), body.get("index"))
        if not item:
            return {"error": True, "message": f"Item not found: name={body.get('name')}, index={body.get('index')}"}
        return _item_detail(item, idx, design)
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_marker(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        pos = timeline.markerPosition
        result = {
            "marker": pos,
            "count": timeline.count,
            "at_end": pos == timeline.count,
            "at_beginning": pos == 0,
        }
        if 0 < pos <= timeline.count:
            try:
                prev = timeline.item(pos - 1)
                result["last_feature"] = prev.name
            except Exception:
                pass
        if pos < timeline.count:
            try:
                nxt = timeline.item(pos)
                result["next_feature"] = nxt.name
            except Exception:
                pass
            result["rolled_back_features"] = timeline.count - pos
        return result
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_count(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        suppressed = 0
        for i in range(timeline.count):
            try:
                if timeline.item(i).isSuppressed:
                    suppressed += 1
            except Exception:
                pass
        return {
            "count": timeline.count,
            "active": timeline.count - suppressed,
            "suppressed": suppressed,
            "marker": timeline.markerPosition,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_search(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        query = (body.get("query") or "").lower()
        type_filter = (body.get("type") or "").lower()
        if not query and not type_filter:
            return {"error": True, "message": "Provide 'query' (name substring) and/or 'type' (type substring)"}

        matches = []
        for i in range(timeline.count):
            try:
                item = timeline.item(i)
                d = _item_to_dict(item, i)
                name_match = query and query in d["name"].lower()
                type_match = type_filter and type_filter in d["type"].lower()
                if (query and type_filter and name_match and type_match) or \
                   (query and not type_filter and name_match) or \
                   (type_filter and not query and type_match):
                    matches.append(d)
            except Exception:
                pass
        return {"matches": matches, "count": len(matches)}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_health(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        healthy, warning, error, suppressed = 0, 0, 0, 0
        issues = []
        for i in range(timeline.count):
            try:
                item = timeline.item(i)
                hs = item.healthState
                if hs == 0:
                    healthy += 1
                elif hs == 1:
                    warning += 1
                    issues.append({"index": i, "name": item.name, "state": "warning"})
                elif hs == 2:
                    error += 1
                    issues.append({"index": i, "name": item.name, "state": "error"})
                elif hs == 3:
                    suppressed += 1
            except Exception:
                pass
        return {
            "healthy": healthy,
            "warning": warning,
            "error": error,
            "suppressed": suppressed,
            "total": timeline.count,
            "issues": issues,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_feature_params(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        item, idx = _find_item(timeline, body.get("name"), body.get("index"))
        if not item:
            return {"error": True, "message": f"Feature not found: name={body.get('name')}, index={body.get('index')}"}
        detail = _item_detail(item, idx, design)
        return {
            "name": detail.get("name"),
            "type": detail.get("type"),
            "parameters": detail.get("parameters", []),
            "related_parameters": detail.get("related_parameters", []),
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── NAVIGATE ─────────────────────────────────────────────────

def handle_timeline_roll_to(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        target_name = body.get("name")
        target_index = body.get("index")
        before = body.get("before", True)

        if target_name:
            item, idx = _find_item(timeline, name=target_name)
            if not item:
                return {"error": True, "message": f"Feature '{target_name}' not found"}
            target_index = idx

        if target_index is None:
            return {"error": True, "message": "Provide 'name' or 'index'"}

        old_pos = timeline.markerPosition
        if before:
            timeline.markerPosition = target_index
        else:
            timeline.markerPosition = target_index + 1
        adsk.doEvents()

        return {
            "success": True,
            "old_marker": old_pos,
            "new_marker": timeline.markerPosition,
            "count": timeline.count,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_roll_end(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        old_pos = timeline.markerPosition
        timeline.markerPosition = timeline.count
        adsk.doEvents()
        return {
            "success": True,
            "old_marker": old_pos,
            "new_marker": timeline.markerPosition,
            "count": timeline.count,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_roll_beginning(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        old_pos = timeline.markerPosition
        timeline.markerPosition = 0
        adsk.doEvents()
        return {
            "success": True,
            "old_marker": old_pos,
            "new_marker": 0,
            "count": timeline.count,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── MODIFY ───────────────────────────────────────────────────

def handle_timeline_suppress(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        names = body.get("names", [])
        indices = body.get("indices", [])
        name = body.get("name")
        index = body.get("index")
        if name:
            names.append(name)
        if index is not None:
            indices.append(index)

        results = []
        for n in names:
            item, idx = _find_item(timeline, name=n)
            if item:
                try:
                    item.isSuppressed = True
                    results.append({"name": n, "index": idx, "suppressed": True})
                except Exception as e:
                    results.append({"name": n, "error": str(e)})
            else:
                results.append({"name": n, "error": "not found"})
        for idx in indices:
            item, real_idx = _find_item(timeline, index=idx)
            if item:
                try:
                    item.isSuppressed = True
                    results.append({"name": item.name, "index": real_idx, "suppressed": True})
                except Exception as e:
                    results.append({"index": idx, "error": str(e)})
            else:
                results.append({"index": idx, "error": "not found"})

        adsk.doEvents()
        return {"success": True, "results": results}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_unsuppress(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        names = body.get("names", [])
        indices = body.get("indices", [])
        name = body.get("name")
        index = body.get("index")
        if name:
            names.append(name)
        if index is not None:
            indices.append(index)

        results = []
        for n in names:
            item, idx = _find_item(timeline, name=n)
            if item:
                try:
                    item.isSuppressed = False
                    results.append({"name": n, "index": idx, "unsuppressed": True})
                except Exception as e:
                    results.append({"name": n, "error": str(e)})
            else:
                results.append({"name": n, "error": "not found"})
        for idx in indices:
            item, real_idx = _find_item(timeline, index=idx)
            if item:
                try:
                    item.isSuppressed = False
                    results.append({"name": item.name, "index": real_idx, "unsuppressed": True})
                except Exception as e:
                    results.append({"index": idx, "error": str(e)})
            else:
                results.append({"index": idx, "error": "not found"})

        adsk.doEvents()
        return {"success": True, "results": results}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_delete(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        item, idx = _find_item(timeline, body.get("name"), body.get("index"))
        if not item:
            return {"error": True, "message": f"Feature not found: name={body.get('name')}, index={body.get('index')}"}

        feat_name = item.name
        entity = item.entity if hasattr(item, "entity") else None
        feat_type = entity.objectType.split("::")[-1] if entity else "unknown"
        count_before = timeline.count

        if entity and hasattr(entity, "deleteMe"):
            entity.deleteMe()
        else:
            item.deleteMe()
        adsk.doEvents()

        return {
            "success": True,
            "deleted_feature": feat_name,
            "feature_type": feat_type,
            "timeline_index": idx,
            "count_before": count_before,
            "count_after": timeline.count,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_move(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        item, old_idx = _find_item(timeline, body.get("name"), body.get("index"))
        if not item:
            return {"error": True, "message": f"Feature not found: name={body.get('name')}, index={body.get('index')}"}

        new_index = body.get("to_index")
        if new_index is None:
            return {"error": True, "message": "Provide 'to_index'"}

        item.move(new_index)
        adsk.doEvents()

        return {
            "success": True,
            "feature": item.name,
            "old_index": old_idx,
            "new_index": new_index,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_edit_param(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        item, idx = _find_item(timeline, body.get("name"), body.get("index"))
        if not item:
            return {"error": True, "message": f"Feature not found: name={body.get('name')}, index={body.get('index')}"}

        entity = item.entity
        if not entity:
            return {"error": True, "message": f"Feature '{item.name}' has no editable entity"}

        param_name = body.get("parameter_name", "distance")
        expression = body.get("expression")
        value = body.get("value")

        if expression is None and value is None:
            return {"error": True, "message": "Provide 'expression' or 'value'"}

        old_expression = None
        old_value = None
        target_param = None

        # Try direct parameter access
        if hasattr(entity, "parameters") and entity.parameters:
            for p in entity.parameters:
                if p.name == param_name or param_name in p.name:
                    target_param = p
                    break

        # Try extent distance (common for extrudes)
        if not target_param and param_name == "distance" and hasattr(entity, "extentOne"):
            extent = entity.extentOne
            if hasattr(extent, "distance"):
                target_param = extent.distance

        # Fallback: search all design parameters
        if not target_param:
            for p in design.allParameters:
                if p.name == param_name:
                    target_param = p
                    break

        if not target_param:
            return {"error": True, "message": f"Parameter '{param_name}' not found on feature '{item.name}'"}

        old_expression = target_param.expression
        old_value = round(target_param.value * 10, 4) if target_param.unit in ("cm", "") else round(target_param.value, 4)

        if expression is not None:
            target_param.expression = str(expression)
        elif value is not None:
            if isinstance(value, str):
                target_param.expression = value
            else:
                target_param.value = value / 10.0 if target_param.unit in ("cm", "") else value

        adsk.doEvents()
        new_value = round(target_param.value * 10, 4) if target_param.unit in ("cm", "") else round(target_param.value, 4)

        return {
            "success": True,
            "feature": item.name,
            "parameter": param_name,
            "old_expression": old_expression,
            "old_value": old_value,
            "new_expression": target_param.expression,
            "new_value": new_value,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_rename(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        item, idx = _find_item(timeline, body.get("name"), body.get("index"))
        if not item:
            return {"error": True, "message": f"Feature not found: name={body.get('name')}, index={body.get('index')}"}

        new_name = body.get("new_name")
        if not new_name:
            return {"error": True, "message": "Provide 'new_name'"}

        old_name = item.name
        entity = item.entity
        if entity and hasattr(entity, "name"):
            entity.name = new_name
        else:
            return {"error": True, "message": f"Cannot rename '{old_name}' — entity does not support renaming"}

        adsk.doEvents()
        return {"success": True, "old_name": old_name, "new_name": new_name, "index": idx}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_undo(body):
    """Delete the last unsuppressed feature."""
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        if timeline.count == 0:
            return {"error": True, "message": "Timeline is empty"}

        target_item = None
        target_index = -1
        for i in range(timeline.count - 1, -1, -1):
            item = timeline.item(i)
            if not item.isSuppressed:
                target_item = item
                target_index = i
                break

        if not target_item:
            return {"error": True, "message": "No unsuppressed features to undo"}

        feat_name = target_item.name
        entity = target_item.entity if hasattr(target_item, "entity") else None
        feat_type = entity.objectType.split("::")[-1] if entity else "unknown"
        count_before = timeline.count

        if entity and hasattr(entity, "deleteMe"):
            entity.deleteMe()
        else:
            target_item.deleteMe()
        adsk.doEvents()

        return {
            "success": True,
            "undone_feature": feat_name,
            "feature_type": feat_type,
            "timeline_index": target_index,
            "count_before": count_before,
            "count_after": timeline.count,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_redo(body):
    """Unsuppress the last suppressed feature."""
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        for i in range(timeline.count - 1, -1, -1):
            item = timeline.item(i)
            if item.isSuppressed:
                feat_name = item.name
                item.isSuppressed = False
                adsk.doEvents()
                return {
                    "success": True,
                    "restored_feature": feat_name,
                    "timeline_index": i,
                }
        return {"error": True, "message": "No suppressed features to redo"}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── GROUP ────────────────────────────────────────────────────

def handle_timeline_create_group(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        start = body.get("start_index")
        end = body.get("end_index")
        if start is None or end is None:
            return {"error": True, "message": "Provide 'start_index' and 'end_index'"}
        if start < 0 or end >= timeline.count or start > end:
            return {"error": True, "message": f"Invalid range [{start}, {end}] for timeline with {timeline.count} items"}

        group = timeline.timelineGroups.add(start, end)
        adsk.doEvents()

        return {
            "success": True,
            "group_name": group.name if hasattr(group, "name") else "Group",
            "start_index": start,
            "end_index": end,
            "items_in_group": end - start + 1,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_collapse_group(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        item, idx = _find_item(timeline, body.get("name"), body.get("index"))
        if not item:
            return {"error": True, "message": f"Group not found: name={body.get('name')}, index={body.get('index')}"}

        if not hasattr(item, "isCollapsed"):
            return {"error": True, "message": f"'{item.name}' is not a group"}

        item.isCollapsed = True
        adsk.doEvents()
        return {"success": True, "group": item.name, "collapsed": True}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


def handle_timeline_expand_group(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        item, idx = _find_item(timeline, body.get("name"), body.get("index"))
        if not item:
            return {"error": True, "message": f"Group not found: name={body.get('name')}, index={body.get('index')}"}

        if not hasattr(item, "isCollapsed"):
            return {"error": True, "message": f"'{item.name}' is not a group"}

        item.isCollapsed = False
        adsk.doEvents()
        return {"success": True, "group": item.name, "expanded": True}
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── ANALYSIS ─────────────────────────────────────────────────

def handle_timeline_deps(body):
    design, timeline = _get_timeline()
    if not timeline:
        return {"error": True, "message": "No active design"}
    try:
        item, idx = _find_item(timeline, body.get("name"), body.get("index"))
        if not item:
            return {"error": True, "message": f"Feature not found: name={body.get('name')}, index={body.get('index')}"}

        entity = item.entity
        feat_bodies = set()
        try:
            if hasattr(entity, "bodies") and entity.bodies:
                for b in entity.bodies:
                    feat_bodies.add(b.name)
        except Exception:
            pass

        # Also capture source sketch for downstream matching
        source_sketch = None
        try:
            if hasattr(entity, "profile") and entity.profile:
                source_sketch = entity.profile.parentSketch.name
        except Exception:
            pass

        upstream = []
        downstream = []
        for i in range(timeline.count):
            if i == idx:
                continue
            try:
                other = timeline.item(i)
                other_entity = other.entity

                other_bodies = set()
                if hasattr(other_entity, "bodies") and other_entity.bodies:
                    for b in other_entity.bodies:
                        other_bodies.add(b.name)

                shared = feat_bodies & other_bodies

                if i < idx and shared:
                    upstream.append({"index": i, "name": other.name, "shared_bodies": list(shared)})
                elif i > idx and shared:
                    downstream.append({"index": i, "name": other.name, "shared_bodies": list(shared)})

                # Sketch → feature dependency
                if i < idx and source_sketch:
                    try:
                        if other.name == source_sketch:
                            upstream.append({"index": i, "name": other.name, "relation": "source_sketch"})
                    except Exception:
                        pass

                if i > idx:
                    try:
                        if hasattr(other_entity, "profile") and other_entity.profile:
                            if other_entity.profile.parentSketch.name == item.name:
                                downstream.append({"index": i, "name": other.name, "relation": "uses_sketch"})
                    except Exception:
                        pass

            except Exception:
                pass

        return {
            "feature": item.name,
            "index": idx,
            "upstream": upstream[:20],
            "downstream": downstream[:20],
            "affected_bodies": list(feat_bodies),
            "source_sketch": source_sketch,
        }
    except Exception as e:
        return {"error": True, "message": str(e), "traceback": traceback.format_exc()}


# ── Route table ──────────────────────────────────────────────

TIMELINE_ROUTES = {
    # Query
    "/timeline_list": handle_timeline_list,
    "/timeline_item": handle_timeline_item,
    "/timeline_marker": handle_timeline_marker,
    "/timeline_count": handle_timeline_count,
    "/timeline_search": handle_timeline_search,
    "/timeline_health": handle_timeline_health,
    "/timeline_feature_params": handle_timeline_feature_params,
    # Navigate
    "/timeline_roll_to": handle_timeline_roll_to,
    "/timeline_roll_end": handle_timeline_roll_end,
    "/timeline_roll_beginning": handle_timeline_roll_beginning,
    # Modify
    "/timeline_suppress": handle_timeline_suppress,
    "/timeline_unsuppress": handle_timeline_unsuppress,
    "/timeline_delete": handle_timeline_delete,
    "/timeline_move": handle_timeline_move,
    "/timeline_edit_param": handle_timeline_edit_param,
    "/timeline_rename": handle_timeline_rename,
    "/timeline_undo": handle_timeline_undo,
    "/timeline_redo": handle_timeline_redo,
    # Group
    "/timeline_create_group": handle_timeline_create_group,
    "/timeline_collapse_group": handle_timeline_collapse_group,
    "/timeline_expand_group": handle_timeline_expand_group,
    # Analysis
    "/timeline_deps": handle_timeline_deps,
}
