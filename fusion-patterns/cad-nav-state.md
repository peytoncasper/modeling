# Pattern: CAD Navigation State (STATE + PATCH + LOCAL_GRAPH)

## What This Is

A streaming-friendly context system that gives you a compact, live model of the current Fusion 360 editing state. Instead of calling `list_bodies` and `get_body_center` on every turn, you read a tiny STATE object and receive incremental patches.

## When to Use

- **Start of every turn:** call `fusion_get_state` to know what's focused, selected, and where in the timeline you are
- **Continuing work:** call `fusion_get_patches_since(t)` to catch up on changes since your last STATE read
- **Need entity detail:** call `fusion_get_local_graph` to see sketch topology, body faces, or timeline deps
- **Expressing intent:** call `fusion_apply_action` for high-level ops that return patches in one round-trip
- **Tight context:** call `fusion_get_state_compact` for a single-line nav string

## Tools

| Tool | Purpose | When |
|------|---------|------|
| `fusion_get_state` | Full STATE snapshot | Start of turn |
| `fusion_get_state_compact` | Single-line nav string | Tight context windows |
| `fusion_get_local_graph` | Entity neighborhood | Need sketch/body/feature detail |
| `fusion_get_patches_since` | Incremental updates | Continuing after previous turn |
| `fusion_apply_action` | High-level command | Expressing intent compactly |

## STATE Schema

```yaml
STATE:
  t: 1842                   # monotonic tick
  doc: "MyDesign"            # active document
  ctx:
    comp: "root"             # active component
    occ: null                # active occurrence
  focus:
    kind: "sketch"           # sketch | body | face | edge | feature | none
    id: "Sketch7"            # entity identifier
    plane: {type: "XZ", origin: [0, 0, 0]}
  frame:
    id: "WorldFrame"         # active reference frame
    origin: [0, 0, 0]
  sel: ["L3", "L5"]         # current selection ids
  timeline:
    count: 14                # total features
    at: 14                   # marker position
    rolled_to: null          # non-null if rolled back
  params:                    # user parameters only
    depth: {v: "30 mm"}
    slotWidth: {v: "6.35 mm"}
  measures: []
  intent: null
```

## LOCAL_GRAPH Schema (sketch focus)

```yaml
LOCAL_GRAPH:
  around: {kind: "sketch", id: "Sketch7"}
  entities:
    sketch:
      pts: [{id: "P0", p: [0, 0]}, {id: "P1", p: [20, 0]}, ...]
      lines: [{id: "L0", a: "P0", b: "P1", construction: false, length_mm: 20}]
      arcs: []
      constraints: [{id: "GC0", type: "horizontal"}, ...]
      dims: [{id: "D0", type: "linear", v: 20, unit: "mm", expr: "depth"}]
      profiles: [{id: "Prof0", area_mm2: 400}]
  deps:
    upstream: []
    downstream: ["Extrude1"]
  nearby:
    bodies: []
    frames: []
```

## PATCH Schema

```yaml
PATCH:
  t: 1843
  ops:
    - {set: "focus", v: {kind: "feature", id: "Extrude1"}}
    - {set: "sel", v: ["Profile0"]}
    - {set: "timeline.at", v: 13}
```

## ACTION Schema

```yaml
ACTION:
  op: "feature.extrude"
  ctx: {sketch: "Sketch7"}
  args:
    profile_index: 0
    distance: "30 mm"
    direction: "positive"
    operation: "new_body"
    body_name: "Panel"
  expect:
    focus_after: {kind: "body", id: "Panel"}
```

### Available Ops

| Op | Required args |
|----|---------------|
| `sketch.create` | `plane`, `name` |
| `sketch.add_rectangle` | ctx.sketch + `corner1`/`corner2` or `center`/`w`/`h` |
| `sketch.add_line` | ctx.sketch + `start`, `end` |
| `sketch.add_circle` | ctx.sketch + `center`, `radius` |
| `sketch.finish` | ctx.sketch |
| `feature.extrude` | ctx.sketch + `distance`, `direction`, `operation` |
| `feature.fillet` | `body`, `edges`, `radius` |
| `feature.chamfer` | `body`, `edges`, `distance` |
| `feature.boolean` | `target`, `tool`, `operation` |
| `param.set` | `name`, `value` |
| `param.create` | `name`, `value`, `unit` |
| `body.move` | `body`, `transform` |
| `view.set` | `preset` |
| `view.screenshot` | (optional `width`, `height`) |

## Workflow Pattern

### First turn — orient yourself

```
1. fusion_get_state → understand what's open, focused, selected
2. fusion_get_local_graph → see entity detail if needed
3. Plan your operations based on STATE + LOCAL_GRAPH
4. Execute via fusion_apply_action or primitive tools
```

### Continuing turns — catch up and proceed

```
1. fusion_get_patches_since(t=<your last tick>) → see what changed
2. If patches are stale or many, fall back to fusion_get_state
3. Continue work
```

### Token-minimal turns

```
1. fusion_get_state_compact → single line like:
   S t42 doc=MyDesign ctx=root focus=sketch:Sketch7 frame=WorldFrame sel=[L3,L5] tl=14/14 params={depth:30mm}
2. Work from that
```

## Relationship to Other Patterns

| Pattern | How NAV STATE helps |
|---------|-------------------|
| **Coordinate Systems** | `STATE.focus.plane` tells you which plane you're on, no guessing |
| **Join Operations** | `LOCAL_GRAPH.nearby.bodies` shows what's adjacent before you extrude |
| **Box Joints** | `STATE.frame` + `LOCAL_GRAPH.deps` track joint progress |
| **Frame System** | Frames are first-class in STATE; `STATE.frame.id` always current |
| **Panel Construction** | `STATE.params` shows all user parameters without extra calls |

## Entity References

Entities are referenced by short ids that follow existing conventions:
- Bodies: `"Panel"` (by name)
- Faces: `"Panel_face_3"` (body name + index)
- Edges: `"Panel_edge_7"` (body name + index)
- Sketches: `"Sketch7"` (by name)
- Features: `"Extrude1"` (timeline name)

Under the hood, the entity resolver maintains dual references (native token + semantic key) that survive timeline edits. You don't need to manage this — it's automatic.
