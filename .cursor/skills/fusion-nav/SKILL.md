---
name: fusion-nav
description: Query and maintain spatial awareness in Fusion 360 — STATE snapshots, incremental PATCH diffs, LOCAL_GRAPH entity neighborhoods, reference frames, entity resolution, and structured ACTION execution. Use whenever you need to know what's happening in the Fusion model, where entities are, what changed, or you want to execute a high-level modeling operation.
---

# Fusion 360 Navigation & Indexing System

Spatial awareness and state tracking via `tools/fusion-nav`. This is the "frames + anchors + vector" system that gives you orientation inside the CAD model.

## Architecture overview

The nav system has six subsystems:

| Subsystem | Purpose | Key commands |
|-----------|---------|-------------|
| **STATE** | Full snapshot of current editing context | `state`, `nav-string` |
| **PATCH** | Incremental diffs since last check | `patches`, `drain` |
| **LOCAL_GRAPH** | Entity neighborhood around a focus | `graph` |
| **FRAMES** | Spatial reference frames for coordinate reasoning | `frames`, `frame`, `create-frame`, etc. |
| **ENTITY RESOLVER** | Stable dual-reference entity cache | `entities`, `resolve` |
| **ACTION** | Structured high-level operations | `actions`, `do` |

## STATE — "Where am I right now?"

Get a complete snapshot of the current Fusion editing context.

```bash
# Full snapshot (doc, context, focus, frame, selection, timeline, params)
tools/fusion-nav state

# Sparse — omit null/empty fields to save tokens
tools/fusion-nav state --sparse

# One-line compact string, ideal for context injection
tools/fusion-nav nav-string
# Output: {"nav_string": "S t5 doc=MyPart ctx=root focus=sketch:Sketch1 frame=XY_Frame tl=3/5"}
```

### STATE fields

| Field | Contents |
|-------|----------|
| `t` | Monotonic tick counter |
| `doc` | Active document name |
| `ctx` | Active component + occurrence |
| `focus` | What's being edited: `{kind, id, plane?}` |
| `frame` | Current reference frame: `{id, origin}` |
| `sel` | Selected entity ids (up to 20) |
| `timeline` | `{count, at, rolled_to}` |
| `params` | User-defined parameters (compact) |

### When to use STATE

- At the start of any modeling task — call `state --sparse` to orient yourself
- Before creating geometry — check `focus` to know if a sketch is active
- After user says "something changed" — call `state` to get full context

## PATCH — "What changed since I last checked?"

Poll for incremental state diffs. Each patch has a tick `t` and a list of `ops` (set/del operations on STATE paths).

```bash
# Get all patches since tick 0 (first call)
tools/fusion-nav patches

# Get patches since a known tick
tools/fusion-nav patches --since 42

# Return AND clear all queued patches
tools/fusion-nav drain
```

### Patch format

```json
{
  "patches": [
    {"t": 43, "ops": [{"set": "focus", "v": {"kind": "sketch", "id": "Sketch2"}}]},
    {"t": 44, "ops": [{"set": "sel", "v": ["Body1"]}]}
  ],
  "current_t": 44,
  "queued": 2
}
```

### When to use PATCH

- During multi-step operations — poll patches between steps to track what changed
- After applying an ACTION — patches in the response show side effects
- To detect user activity — selection changes, focus changes, timeline edits

## LOCAL_GRAPH — "What's around this entity?"

Extract the topological neighborhood of any entity.

```bash
# Auto-detect focus (uses active sketch or selection)
tools/fusion-nav graph

# Sketch neighborhood (points, lines, arcs, constraints, dimensions, profiles)
tools/fusion-nav graph --kind sketch --id Sketch1

# Body neighborhood (faces, edges, bounds, volume)
tools/fusion-nav graph --kind body --id Body1

# Face neighborhood (adjacent faces, bounding edges, normal, centroid)
tools/fusion-nav graph --kind face --id Body1_face_0

# Edge neighborhood (adjacent faces, length, midpoint)
tools/fusion-nav graph --kind edge --id Body1_edge_3

# Feature neighborhood (upstream/downstream deps, affected bodies, params)
tools/fusion-nav graph --kind feature --id Extrude1

# Deeper traversal
tools/fusion-nav graph --kind body --id Body1 --depth 2

# Scoped to a component
tools/fusion-nav graph --kind sketch --id Sketch1 --component Carcass
```

### Graph structure

```json
{
  "around": {"kind": "sketch", "id": "Sketch1"},
  "entities": {
    "sketch": {
      "pts": [{"id": "P0", "p": [0, 0]}, ...],
      "lines": [{"id": "L0", "a": "P0", "b": "P1", "length_mm": 50.0}],
      "profiles": [{"id": "Prof0", "area_mm2": 1500.0}]
    }
  },
  "deps": {"upstream": [], "downstream": ["Extrude1"]},
  "nearby": {"bodies": [], "frames": []}
}
```

### When to use LOCAL_GRAPH

- Before modifying a sketch — get all points, lines, and constraints
- Before applying features — check which profiles are available
- To understand body topology — face normals, edge counts, adjacency
- To trace feature dependencies — what feeds into what

## FRAMES — "How do I reason about coordinates?"

Frames are spatial anchors that prevent coordinate drift. The system auto-creates frames for construction planes (XY, XZ, YZ) and you can create body/interface frames.

```bash
# List all frames
tools/fusion-nav frames

# Filter by type
tools/fusion-nav frames --type body
tools/fusion-nav frames --type plane
tools/fusion-nav frames --type interface

# Get specific frame with details
tools/fusion-nav frame WorldFrame
tools/fusion-nav frame Body1_Frame --children
tools/fusion-nav frame Joint1 --mates

# Auto-create frame from body bounding box
tools/fusion-nav body-frame Body1
tools/fusion-nav body-frame Body1 --component Carcass

# Create custom frame
tools/fusion-nav create-frame MyAnchor --type custom --origin 50,40,10
tools/fusion-nav create-frame MyAnchor --type custom --origin 50,40,10 --parent Body1_Frame

# Create interface/joint frame
tools/fusion-nav interface-frame --parent Body1_Frame --name TopJoint --origin 25,15,30 --normal 0,0,1
tools/fusion-nav interface-frame --parent Body1_Frame --name SideJoint --origin 50,15,15 --normal 1,0,0 --mates-with OtherJoint

# Delete a frame
tools/fusion-nav delete-frame MyAnchor

# Find frames near a point
tools/fusion-nav nearby --origin 50,40,10
tools/fusion-nav nearby --origin 50,40,10 --radius 100

# Transform a point between frames
tools/fusion-nav transform --point 10,20,30 --from WorldFrame --to Body1_Frame
```

### Frame types

| Type | Description |
|------|-------------|
| `world` | Root coordinate system (WorldFrame) — always exists |
| `plane` | Construction planes (XY_Frame, XZ_Frame, YZ_Frame) — always exist |
| `body` | Auto-created from body bounding box center |
| `interface` | Joint/connection point with normal and optional mating info |
| `custom` | User-defined reference point |

### When to use FRAMES

- When reasoning about where bodies are relative to each other
- Before creating joints — set up interface frames at connection points
- When placing geometry — transform coordinates between body-local and world frames
- To track body positions after transforms/moves

## ENTITY RESOLVER — "How do I refer to this entity later?"

The resolver maintains stable dual-references (native token + semantic key) that survive parametric timeline edits.

```bash
# List all cached entity refs
tools/fusion-nav entities

# Filter by type
tools/fusion-nav entities --type body
tools/fusion-nav entities --type face

# Look up a specific ref
tools/fusion-nav resolve myEntityToken
```

### Ref structure

```json
{
  "ref": {
    "id": "native_token_abc123",
    "key": {
      "type": "face",
      "of": {"body": "Body1", "index": 3},
      "where": {"normal": [0, 0, 1], "centroid_mm": [25, 15, 30], "area_mm2": 750.0}
    }
  },
  "stale": false
}
```

When `stale` is true, the native token was invalid and the entity was re-resolved by scoring candidates against the semantic key. The new token is cached automatically.

### Resolution types

The resolver supports re-resolving these entity types when tokens go stale:

| Entity | Scoring method | Fallback keys |
|--------|---------------|---------------|
| **Body** | Name match | `name` |
| **Face** | Normal similarity (40) + centroid distance (30) + area ratio (30) | `normal`, `centroid_mm`, `area_mm2` |
| **Edge** | Midpoint distance (50) + length ratio (30) + adjacent faces (20) | `midpoint_mm`, `length_mm` |
| **Sketch** | Name match | `name` |

### Stable edge references across topology changes

Edge indices (`Body1_edge_3`) break after booleans and fillets. The resolver and the solid CLI both support spatial references:

```bash
# Spatial ref in solid commands — preferred for fillet/chamfer after booleans
tools/fusion-solid fillet --edges "Body1@170,0,542" --radius 10
```

## ACTION — "Execute a high-level operation"

Actions are structured commands that wrap primitive bridge endpoints. They return the operation result plus any state patches generated.

```bash
# List available action ops
tools/fusion-nav actions

# Create a sketch
tools/fusion-nav do sketch.create --args '{"plane":"xy","name":"Sketch1"}'

# Draw in a sketch
tools/fusion-nav do sketch.add_rectangle --ctx '{"sketch":"Sketch1"}' --args '{"corner1":[0,0],"corner2":[50,30]}'
tools/fusion-nav do sketch.add_line --ctx '{"sketch":"Sketch1"}' --args '{"start":[0,0],"end":[50,30]}'
tools/fusion-nav do sketch.add_circle --ctx '{"sketch":"Sketch1"}' --args '{"center":[25,15],"radius":10}'

# Finish sketch
tools/fusion-nav do sketch.finish --ctx '{"sketch":"Sketch1"}'

# Extrude
tools/fusion-nav do feature.extrude --ctx '{"sketch":"Sketch1"}' --args '{"distance":20,"operation":"new_body"}'

# Fillet/chamfer
tools/fusion-nav do feature.fillet --args '{"body":"Body1","edges":["Body1_edge_0"],"radius":2}'
tools/fusion-nav do feature.chamfer --args '{"body":"Body1","edges":["Body1_edge_0"],"distance":1}'

# Boolean
tools/fusion-nav do feature.boolean --args '{"target":"Body1","tool":"Body2","operation":"cut"}'

# Parameters
tools/fusion-nav do param.create --args '{"name":"width","value":50,"unit":"mm"}'
tools/fusion-nav do param.set --args '{"name":"width","value":"60 mm"}'

# Camera
tools/fusion-nav do view.set --args '{"preset":"isometric"}'
tools/fusion-nav do view.screenshot --args '{"width":1920,"height":1080"}'
```

### Action response format

```json
{
  "success": true,
  "result": { ... },
  "patches": [
    {"t": 15, "ops": [{"set": "timeline.count", "v": 4}]}
  ]
}
```

### Available ops

| Op | Required ctx | Required args |
|----|-------------|---------------|
| `sketch.create` | — | `plane`, `name?` |
| `sketch.add_rectangle` | `sketch` | `corner1, corner2` or `center, w, h` |
| `sketch.add_line` | `sketch` | `start, end` |
| `sketch.add_circle` | `sketch` | `center, radius` |
| `sketch.finish` | `sketch` | — |
| `feature.extrude` | `sketch` | `distance`, `operation?`, `profile_index?` |
| `feature.fillet` | — | `body, edges[], radius` |
| `feature.chamfer` | — | `body, edges[], distance` |
| `feature.boolean` | — | `target, tool, operation` |
| `param.set` | — | `name, value` |
| `param.create` | — | `name, value, unit?` |
| `body.move` | — | `body, transform` |
| `view.set` | — | `preset` |
| `view.screenshot` | — | `width?, height?` |

### When to use ACTIONs vs direct CLI calls

Use ACTIONs when you want:
- Automatic state patch tracking (each action returns resulting patches)
- Validation before execution
- A single round-trip for the operation + its side effects

Use direct CLIs (`fusion-sketch`, `fusion-solid`, etc.) when you need:
- Fine-grained control over specific parameters
- Endpoints not covered by the ACTION system
- Simple queries that don't need patch tracking

## Common workflows

### "Orient yourself in the model"

```bash
tools/fusion-nav state --sparse
tools/fusion-nav frames
```

### "Understand what the user is working on"

```bash
tools/fusion-nav nav-string
tools/fusion-nav graph
```

### "Track changes during a multi-step operation"

```bash
# Get current tick
tools/fusion-nav state --sparse   # note the "t" field

# Do some work...
tools/fusion-sketch draw-line Sketch1 --start 0,0 --end 50,0

# Check what changed
tools/fusion-nav patches --since 5
```

### "Build spatial awareness for assembly"

```bash
# Frame each body
tools/fusion-nav body-frame Body1
tools/fusion-nav body-frame Body2

# Check relative positions
tools/fusion-nav transform --point 0,0,0 --from Body1_Frame --to Body2_Frame

# Set up joints
tools/fusion-nav interface-frame --parent Body1_Frame --name Slot --origin 25,15,0 --normal 0,0,1
tools/fusion-nav interface-frame --parent Body2_Frame --name Tab --origin 0,0,15 --normal 0,0,-1 --mates-with Slot
```

### "Execute a parametric modeling sequence"

```bash
tools/fusion-nav do sketch.create --args '{"plane":"xy","name":"Base"}'
tools/fusion-nav do sketch.add_rectangle --ctx '{"sketch":"Base"}' --args '{"corner1":[0,0],"corner2":[100,60]}'
tools/fusion-nav do sketch.finish --ctx '{"sketch":"Base"}'
tools/fusion-nav do feature.extrude --ctx '{"sketch":"Base"}' --args '{"distance":18,"operation":"new_body"}'
tools/fusion-nav body-frame Body1
tools/fusion-nav state --sparse
```

## Complete command reference

### State & patches

| Command | What it does |
|---------|-------------|
| `state [--sparse]` | Full STATE snapshot |
| `nav-string` | One-line compact state |
| `patches [--since T]` | Incremental diffs since tick T |
| `drain` | Return + clear all queued patches |

### Local graph

| Command | What it does |
|---------|-------------|
| `graph [--kind K] [--id ID] [--depth D] [--component C]` | Entity neighborhood |

### Actions

| Command | What it does |
|---------|-------------|
| `actions` | List available ACTION ops |
| `do OP [--ctx JSON] [--args JSON]` | Execute structured action |

### Frames

| Command | What it does |
|---------|-------------|
| `frames [--type T]` | List all frames |
| `frame NAME [--children] [--mates]` | Get specific frame |
| `create-frame NAME --type T --origin x,y,z [--parent P] [--orientation x,y,z]` | Create frame |
| `delete-frame NAME` | Delete frame + children |
| `body-frame BODY [--component C]` | Auto-frame from body bbox |
| `interface-frame --parent P --name N --origin x,y,z --normal x,y,z [--mates-with M]` | Create joint frame |
| `nearby --origin x,y,z [--radius R]` | Find frames near point |
| `transform --point x,y,z --from F1 --to F2` | Re-project point between frames |

### Entity resolver

| Command | What it does |
|---------|-------------|
| `entities [--type T]` | List cached entity refs |
| `resolve ID` | Look up cached ref by id |
