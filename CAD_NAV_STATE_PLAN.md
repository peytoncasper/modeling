# Implementation Plan: CAD Navigation State System

## What This Is

A **STATE + PATCH + LOCAL_GRAPH** layer for the Fusion 360 MCP that gives the LLM a compact, streaming-friendly model of the current CAD context. Instead of the LLM reconstructing spatial understanding from scratch on every tool call, it maintains a tiny live state object and receives incremental patches.

This builds on top of the existing **frame system** (frame_manager.py, MCP frame tools) and adds three new capabilities:

1. **STATE** — A single, fixed-schema object representing "where I am and what I'm looking at" in the parametric model
2. **PATCH** — Atomic delta ops emitted when Fusion state changes (selection, timeline, parameters)
3. **LOCAL_GRAPH** — The entity neighborhood around the current focus (sketch topology, feature deps, nearby geometry)

## Why This Matters

| Without this | With this |
|---|---|
| LLM calls `list_bodies` + `get_body_center` + `list_faces` on every turn | LLM reads STATE once, receives PATCHes |
| Context grows linearly with conversation length | Context stays bounded (STATE + latest graph + N patches) |
| No tracking of "what am I editing" between tool calls | Explicit `focus` + `ctx` in STATE |
| Entity IDs brittle across timeline edits | Dual `id` + semantic `key` refs |
| LLM guesses extrude directions, sketch planes | Frame + focus give unambiguous local coordinate context |

## Architecture

```
┌─────────────────────────────────────────────┐
│  LLM (MCP Client)                           │
│  Reads: STATE, LOCAL_GRAPH                  │
│  Emits: ACTION                              │
│  Receives: PATCH (via tool responses)       │
└──────────────────┬──────────────────────────┘
                   │ MCP Protocol
┌──────────────────▼──────────────────────────┐
│  TypeScript MCP Server                      │
│  New tools:                                 │
│    fusion_get_state                         │
│    fusion_get_local_graph                   │
│    fusion_apply_action                      │
│    fusion_get_patches_since                 │
│  Existing tools: unchanged                  │
└──────────────────┬──────────────────────────┘
                   │ HTTP (localhost:8080)
┌──────────────────▼──────────────────────────┐
│  Python Fusion Bridge                       │
│  New modules:                               │
│    cad_state.py      — STATE builder        │
│    graph_extractor.py — LOCAL_GRAPH builder  │
│    entity_resolver.py — stable ref system   │
│    patch_emitter.py   — event → PATCH       │
│  Existing: frame_manager.py (feeds STATE)   │
└──────────────────┬──────────────────────────┘
                   │ Fusion API + Events
┌──────────────────▼──────────────────────────┐
│  Fusion 360                                 │
│  Events subscribed:                         │
│    selectionChanged                         │
│    activeDocumentChanged                    │
│    commandExecuted (timeline changes)       │
│    parameterChanged                         │
└─────────────────────────────────────────────┘
```

## Existing Infrastructure We Build On

| Exists | Role in new system |
|---|---|
| `frame_manager.py` (Frame, FrameManager) | Frame tree feeds `STATE.frame` and `STATE.anchors` |
| `/list_bodies`, `/get_body_center` | Feed into `LOCAL_GRAPH.entities` and STATE builder |
| `/list_faces`, `/list_edges`, `/get_face_info` | Feed into LOCAL_GRAPH when focus is a body/face |
| `/list_sketches`, `/get_sketch_profiles`, `/list_sketch_dimensions` | Feed into LOCAL_GRAPH when focus is a sketch |
| `/get_timeline` | Feeds `STATE.timeline` |
| `/list_parameters`, `/list_all_parameters` | Feed `STATE.params` |
| `/list_components`, `/get_component_info` | Feed `STATE.ctx` |
| Frame MCP tools (`fusion_create_frame`, etc.) | Still used directly; STATE reads from FrameManager |

---

## Phase 1: Entity Reference System

**Goal:** Stable entity references that survive timeline edits.

### 1.1 Create `fusion-addin/entity_resolver.py`

Every entity gets a dual reference:

```python
class EntityRef:
    id: str              # native Fusion entityToken or path
    key: SemanticKey     # deterministic fallback locator

class SemanticKey:
    type: str            # "face", "edge", "vertex", "sketch", "feature", "body", "component"
    of: dict             # parent context: {"feature": "Extrude7", "body": "B3"}
    where: dict          # disambiguation heuristics: {"normal": "~+Z", "area_rank": 1}
```

### 1.2 Resolver logic

```
resolve(ref) → Fusion entity:
  1. Try ref.id (fast path — entityToken lookup)
  2. If stale/missing, use ref.key:
     a. Find parent (feature/body) by name
     b. Enumerate candidates of ref.key.type
     c. Score by ref.key.where heuristics (normal direction, area rank, position)
     d. Return best match
  3. If resolved via key, update ref.id for next time
```

### 1.3 Key generation

When the system encounters an entity for the first time:
- Extract its `entityToken` → `ref.id`
- Walk up to owning feature/body → `ref.key.of`
- Compute distinguishing properties → `ref.key.where` (face normal, edge midpoint, area rank among siblings)

### Files

| File | What |
|---|---|
| `fusion-addin/entity_resolver.py` | `EntityRef`, `SemanticKey`, `EntityResolver` classes |
| Changes to `FusionMCPBridge.py` | `EntityResolver` instance; wrap entity lookups |

### Dependencies

- Fusion API: `entityToken`, `BRepFace.geometry.normal`, `BRepBody.faces`, timeline feature access
- No new MCP tools yet (internal plumbing)

---

## Phase 2: STATE Builder

**Goal:** Produce a compact, fixed-schema snapshot of the current CAD context.

### 2.1 STATE Schema

```yaml
STATE:
  t: 1842                            # monotonic tick (incremented on any change)
  doc: "MyDesign"                    # active document name
  ctx:
    comp: "C_root"                   # active component ref
    occ: null                        # active occurrence (if in assembly context)
  focus:
    kind: "sketch"                   # sketch | body | face | edge | feature | none
    id: "S45"                        # entity ref id
    key: {type: "sketch", of: {feature: "Sketch7"}}
    plane: {kind: "face", id: "F203"}  # sketch plane (when focus is sketch)
  frame:
    id: "FR_S45"                     # active reference frame id
    origin: {kind: "vertex", id: "V9"}
    axes: {x: "E12", y: "E13"}      # entity-derived directions
  sel: ["L102", "L103"]             # current selection set (entity ref ids)
  timeline:
    count: 14                        # total features
    at: 14                           # current position (end = latest)
    rolled_to: null                  # non-null if rolled back: "before:Fillet2"
  params:                            # user parameters only (compact)
    depth: {v: "30 mm"}
    slotWidth: {v: "6.35 mm"}
  measures: []                       # active measurements (populated on demand)
  intent: null                       # LLM's declared intent (set by ACTION)
```

### 2.2 Create `fusion-addin/cad_state.py`

```python
class CADState:
    """Builds and maintains the compact STATE object."""

    def __init__(self, app, frame_manager, entity_resolver):
        self.app = app
        self.fm = frame_manager
        self.er = entity_resolver
        self.tick = 0
        self._state = {}

    def snapshot(self) -> dict:
        """Build full STATE from current Fusion state."""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.tick += 1
        ...build and return state dict...

    def get_focus(self) -> dict:
        """Determine what the user/LLM is currently focused on."""
        # Check active edit target (sketch being edited, feature being edited)
        # Fall back to selection
        # Fall back to "none"
        ...

    def get_compact_params(self) -> dict:
        """Return only user-defined parameters (not auto-generated)."""
        ...
```

### 2.3 HTTP Endpoint

```
POST /get_state → returns STATE dict
POST /get_state?sparse=true → returns only non-null fields
```

### 2.4 MCP Tool

```
fusion_get_state:
  description: "Get the current compact CAD navigation state. Returns focus, selection,
                timeline position, active frame, and user parameters."
  params: {sparse: boolean}
  returns: STATE object
```

### Files

| File | What |
|---|---|
| `fusion-addin/cad_state.py` | `CADState` class |
| Changes to `FusionMCPBridge.py` | Instantiate `CADState`, add `/get_state` endpoint |
| Changes to `fusion-design-mcp-server/src/index.ts` | Add `fusion_get_state` tool |

### Dependencies

- Phase 1 (entity resolver) for stable refs in STATE
- Existing frame_manager for `STATE.frame`

---

## Phase 3: LOCAL_GRAPH Extractor

**Goal:** Given the current focus entity, extract its local neighborhood graph.

### 3.1 Graph Types by Focus Kind

| Focus kind | LOCAL_GRAPH contains |
|---|---|
| **sketch** | Points, lines, arcs, constraints, dimensions, profiles, construction geometry |
| **body** | Faces (with normals, area), edges, vertices, neighboring bodies |
| **face** | Adjacent faces, bounding edges, owning body, face normal + centroid |
| **edge** | Adjacent faces, connected edges, start/end vertices |
| **feature** | Timeline deps (upstream/downstream), affected bodies, parameters |
| **none** | Top-level: all bodies with bounds, component tree summary |

### 3.2 LOCAL_GRAPH Schema

```yaml
LOCAL_GRAPH:
  around: {kind: "sketch", id: "S45"}     # what this graph describes
  entities:
    sketch:                                 # present when focus is sketch
      pts: [{id: "P1", p: [10, 20]}, ...]
      lines: [{id: "L102", a: "P1", b: "P2"}, ...]
      arcs: [{id: "A5", center: "P3", start: "P4", end: "P5", radius: 12.5}]
      constraints: [{id: "C7", type: "parallel", a: "L102", b: "L33"}]
      dims: [{id: "D4", type: "distance", a: "P1", b: "P2", v: 25, unit: "mm"}]
      profiles: [{id: "Prof0", area: 322.58, loops: ["L102", "L103", "L104", "L105"]}]
    body:                                   # present when focus is body
      faces: [{id: "F203", normal: [0,0,1], area: 500, centroid: [10,20,5]}]
      edges: [{id: "E12", type: "line", length: 25.4, midpoint: [5,0,12.7]}]
    refs:                                   # reference geometry near focus
      planes: [{id: "PL6", type: "offset", from: "F203", v: 10}]
      axes: [{id: "AX2", from: "E12"}]
  deps:
    upstream: ["Sketch12", "Plane3"]        # features this depends on
    downstream: ["Extrude7", "Fillet2"]     # features that depend on this
  nearby:                                   # bodies/entities close to focus
    bodies: [{id: "B3", name: "Shelf", distance: 0.0}]
    frames: [{id: "FR_shelf", type: "interface"}]
```

### 3.3 Create `fusion-addin/graph_extractor.py`

```python
class GraphExtractor:
    """Extracts local entity neighborhoods from Fusion."""

    def __init__(self, app, entity_resolver):
        self.app = app
        self.er = entity_resolver

    def extract(self, focus_kind: str, focus_id: str, depth: int = 1) -> dict:
        """Extract LOCAL_GRAPH around the given focus entity."""
        if focus_kind == "sketch":
            return self._extract_sketch_graph(focus_id)
        elif focus_kind == "body":
            return self._extract_body_graph(focus_id)
        elif focus_kind == "face":
            return self._extract_face_graph(focus_id)
        elif focus_kind == "feature":
            return self._extract_feature_graph(focus_id)
        else:
            return self._extract_toplevel_graph()

    def _extract_sketch_graph(self, sketch_id):
        """Walk sketch curves, constraints, dimensions."""
        ...

    def _extract_body_graph(self, body_id):
        """Enumerate faces, edges, find neighbors."""
        ...

    def _extract_feature_graph(self, feature_id):
        """Walk timeline dependencies."""
        ...
```

### 3.4 HTTP Endpoint

```
POST /get_local_graph
  body: {focus_kind: "sketch", focus_id: "S45", depth: 1}
  returns: LOCAL_GRAPH dict
```

### 3.5 MCP Tool

```
fusion_get_local_graph:
  description: "Get the entity neighborhood graph around the current focus or a specific entity.
                Returns topology (points, lines, constraints for sketches; faces, edges for bodies;
                timeline deps for features)."
  params:
    focus_kind: string (sketch|body|face|edge|feature|auto)
    focus_id: string (optional — defaults to STATE.focus)
    depth: integer (1 = immediate neighbors, 2 = neighbors of neighbors)
  returns: LOCAL_GRAPH object
```

### Files

| File | What |
|---|---|
| `fusion-addin/graph_extractor.py` | `GraphExtractor` class with per-kind extraction |
| Changes to `FusionMCPBridge.py` | Instantiate `GraphExtractor`, add `/get_local_graph` endpoint |
| Changes to `fusion-design-mcp-server/src/index.ts` | Add `fusion_get_local_graph` tool |

### Dependencies

- Phase 1 (entity resolver) for stable refs in graph nodes
- Fusion API: sketch curves/constraints/dimensions, BRep traversal, timeline features

---

## Phase 4: PATCH Emitter

**Goal:** Capture Fusion state changes as atomic PATCH ops and queue them for the LLM.

### 4.1 PATCH Schema

```yaml
PATCH:
  t: 1843                               # monotonic tick
  ops:
    - {set: "focus", v: {kind: "feature", id: "Extrude7"}}
    - {set: "sel", v: ["Profile9"]}
    - {set: "timeline.at", v: 13}
    - {set: "params.depth", v: {v: "35 mm"}}
    - {set: "intent", v: {op: "edit_feature", goal: "increase_depth"}}
```

### 4.2 Op types

| Op | Meaning | Example |
|---|---|---|
| `set` | Replace value at path | `{set: "focus.kind", v: "sketch"}` |
| `add` | Delta-add to numeric/array | `{add: "timeline.at", v: 1}` |
| `del` | Remove key | `{del: "measures.M1"}` |
| `replace_graph` | Swap LOCAL_GRAPH (focus changed cells) | `{replace_graph: {around: ...}}` |

### 4.3 Create `fusion-addin/patch_emitter.py`

```python
class PatchEmitter:
    """Listens to Fusion events and emits PATCH dicts."""

    def __init__(self, app, cad_state):
        self.app = app
        self.state = cad_state
        self.patch_queue = []
        self.max_queue = 50

    def subscribe(self):
        """Subscribe to Fusion events."""
        ui = self.app.userInterface
        ui.selectionEvent.add(self._on_selection_changed)
        # Fusion custom event or polling for:
        #   - active document change
        #   - timeline roll
        #   - parameter edits

    def _on_selection_changed(self, args):
        """Generate PATCH when selection changes."""
        new_sel = [self._ref(e) for e in args.selection]
        self._emit({set: "sel", v: new_sel})

    def _emit(self, op):
        self.state.tick += 1
        patch = {"t": self.state.tick, "ops": [op]}
        self.patch_queue.append(patch)
        if len(self.patch_queue) > self.max_queue:
            self.patch_queue.pop(0)

    def get_patches_since(self, since_t: int) -> list:
        """Return patches with t > since_t."""
        return [p for p in self.patch_queue if p["t"] > since_t]

    def drain(self) -> list:
        """Return all queued patches and clear."""
        patches = self.patch_queue[:]
        self.patch_queue.clear()
        return patches
```

### 4.4 Fusion Event Mapping

| Fusion Event | PATCH ops generated |
|---|---|
| Selection changed | `set:sel`, possibly `set:focus` |
| Active edit target changed (enter/exit sketch) | `set:focus`, `set:frame`, `replace_graph` |
| Timeline marker moved | `set:timeline.at`, `set:timeline.rolled_to` |
| Parameter value changed | `set:params.<name>` |
| Feature created/deleted | `set:timeline.count`, `add:timeline.at` |
| Document switched | Full STATE reset (not a patch — re-snapshot) |
| Body created/renamed | Partial graph update |

### 4.5 Polling Fallback

Fusion 360's add-in event model is limited. For events without direct hooks, use a **polling loop** on a background timer (every 500ms):

```python
def _poll_state(self):
    """Detect state changes by diffing snapshots."""
    current = self.state.snapshot()
    diffs = self._diff(self._last_snapshot, current)
    for path, old_val, new_val in diffs:
        self._emit({"set": path, "v": new_val})
    self._last_snapshot = current
```

### 4.6 HTTP Endpoint

```
POST /get_patches_since
  body: {since_t: 1840}
  returns: {patches: [...], current_t: 1843}
```

### 4.7 MCP Tool

```
fusion_get_patches_since:
  description: "Get state patches since a given tick. Use to catch up on changes since
                your last STATE read. Returns empty array if no changes."
  params:
    since_t: integer
  returns: {patches: PATCH[], current_t: integer}
```

### Files

| File | What |
|---|---|
| `fusion-addin/patch_emitter.py` | `PatchEmitter` class |
| Changes to `FusionMCPBridge.py` | Instantiate `PatchEmitter`, subscribe to events, add endpoint |
| Changes to `fusion-design-mcp-server/src/index.ts` | Add `fusion_get_patches_since` tool |

### Dependencies

- Phase 2 (CADState) for snapshot diffing
- Fusion API event subscriptions

### Design Decision: Push vs Pull

MCP is request/response, so patches are **pulled** by the LLM:

```
LLM → fusion_get_state (first call)
LLM → ... does work, multiple tool calls ...
LLM → fusion_get_patches_since(since_t=1842)  (catch up)
```

If MCP gains server-sent events / notifications in the future, patches can be pushed. The PATCH format is the same either way.

---

## Phase 5: ACTION Contract

**Goal:** Define a structured output format for LLM commands that is timeline-safe and patchable.

### 5.1 ACTION Schema

```yaml
ACTION:
  op: "sketch.add_rectangle"
  ctx: {sketch: "S45"}
  args:
    center: {kind: "point", id: "P7"}
    w: "20 mm"
    h: "10 mm"
    constraints:
      - {type: "horizontal", entity: "L_new1"}
      - {type: "symmetry", a: "P_new1", b: "P_new2", about: "L102"}
  expect:
    adds: ["L_new1", "L_new2", "D_new1"]
    focus_after: {kind: "sketch", id: "S45"}
```

### 5.2 Action Executor

The action executor maps ACTION ops to sequences of existing MCP tool calls:

```python
class ActionExecutor:
    """Translates ACTION dicts into Fusion API calls."""

    OP_MAP = {
        "sketch.add_rectangle": "_do_sketch_add_rectangle",
        "sketch.add_line": "_do_sketch_add_line",
        "sketch.add_constraint": "_do_sketch_add_constraint",
        "feature.extrude": "_do_feature_extrude",
        "feature.fillet": "_do_feature_fillet",
        "param.set": "_do_param_set",
        "timeline.roll": "_do_timeline_roll",
        "body.move": "_do_body_move",
    }

    def execute(self, action: dict) -> dict:
        handler = self.OP_MAP.get(action["op"])
        if not handler:
            return {"error": f"Unknown op: {action['op']}"}
        return getattr(self, handler)(action)
```

### 5.3 MCP Tool

```
fusion_apply_action:
  description: "Execute a structured CAD action. Translates high-level intents into
                Fusion operations. Returns the resulting state patches."
  params:
    action: ACTION object
  returns: {success: boolean, patches: PATCH[], new_entities: EntityRef[]}
```

### 5.4 Why a separate ACTION tool

- Existing tools (`fusion_extrude`, `fusion_draw_rectangle`) still work — ACTION is optional
- ACTION gives the LLM a **single-call high-level interface** when it wants to express intent compactly
- ACTION returns patches, so the LLM can update its STATE in one round-trip
- ACTION validates before executing (checks refs, expected outcomes)

### Files

| File | What |
|---|---|
| `fusion-addin/action_executor.py` | `ActionExecutor` class |
| Changes to `FusionMCPBridge.py` | Instantiate `ActionExecutor`, add `/apply_action` endpoint |
| Changes to `fusion-design-mcp-server/src/index.ts` | Add `fusion_apply_action` tool |

### Dependencies

- Phase 1-4 (everything above)

---

## Phase 6: Integration & Token-Efficient Mode

**Goal:** Wire everything together and provide a super-compact nav string mode.

### 6.1 Compact "Nav String" Format

For contexts where tokens are precious, STATE can be serialized to a single line:

```
S t1842 doc=MyDesign ctx=C_root focus=sketch:S45 frame=FR_S45 sel=[L102,L103] tl=14/14 params={depth:30mm,slotW:6.35mm}
```

Patches:
```
P t1843 set(focus=feature:Extrude7) set(sel=[Profile9])
```

### 6.2 MCP Tool

```
fusion_get_state_compact:
  description: "Get the nav string — a single-line, token-minimal representation
                of current CAD state. Use for tight context windows."
  params: {}
  returns: {nav_string: string, t: integer}
```

### 6.3 System Prompt Fragment

For the LLM to use this effectively, include in system prompt:

```
You have access to a CAD navigation state system. At the start of each turn:
1. Call fusion_get_state to get current context (or fusion_get_patches_since if continuing)
2. Use STATE.focus to understand what you're editing
3. Call fusion_get_local_graph if you need entity-level detail
4. Express edits via fusion_apply_action or existing primitive tools
5. After actions, read returned patches to update your understanding
```

### Files

| File | What |
|---|---|
| Changes to `cad_state.py` | Add `to_nav_string()` method |
| Changes to `FusionMCPBridge.py` | Add `/get_state_compact` endpoint |
| Changes to `fusion-design-mcp-server/src/index.ts` | Add `fusion_get_state_compact` tool |
| New: `fusion-patterns/cad-nav-state.md` | Pattern doc explaining the system |

---

## Phase 7: Update frame_manager.py

**Goal:** Integrate the existing frame system with STATE so frames are first-class state citizens.

### 7.1 Changes

The existing `FrameManager` is already functional. Integration points:

1. `CADState.snapshot()` reads from `FrameManager` to populate `STATE.frame` and frame-based anchors
2. `GraphExtractor` uses frames to determine "nearby" entities
3. `PatchEmitter` tracks frame creation/deletion as patches
4. `ActionExecutor` can accept frame-based coordinates in ACTION args

### 7.2 New FrameManager methods needed

```python
def get_active_frame(self) -> Optional[Frame]:
    """Return the frame most relevant to the current editing context."""
    # If editing sketch S45, return S45's sketch frame
    # If looking at body B3, return B3's body frame
    # If no specific context, return WorldFrame

def get_nearby_frames(self, origin: List[float], radius: float) -> List[Frame]:
    """Return frames within radius of a point."""
    # Used by LOCAL_GRAPH to populate nearby.frames

def get_frame_for_entity(self, entity_ref: EntityRef) -> Optional[Frame]:
    """Find frame associated with an entity."""
    # Body → body frame
    # Sketch → sketch frame
    # Face → parent body frame
```

---

## Implementation Order & Dependencies

```
Phase 1: Entity Resolver          (no deps, pure Python)
   ↓
Phase 2: STATE Builder            (depends on Phase 1 + existing frame_manager)
   ↓
Phase 3: LOCAL_GRAPH Extractor    (depends on Phase 1)
   ↓
Phase 4: PATCH Emitter            (depends on Phase 2)
   ↓
Phase 5: ACTION Contract          (depends on Phase 1-4)
   ↓
Phase 6: Integration & Compact    (depends on Phase 2, 4)
   ↓
Phase 7: Frame Integration        (depends on Phase 2, 3)
```

Phases 1-3 can be developed somewhat in parallel since they share only the entity resolver.

## New Files Summary

| File | Lines (est.) | Purpose |
|---|---|---|
| `fusion-addin/entity_resolver.py` | ~200 | Stable entity references |
| `fusion-addin/cad_state.py` | ~250 | STATE snapshot builder |
| `fusion-addin/graph_extractor.py` | ~350 | LOCAL_GRAPH extraction per focus kind |
| `fusion-addin/patch_emitter.py` | ~200 | Event → PATCH queue |
| `fusion-addin/action_executor.py` | ~300 | ACTION → Fusion API calls |
| `fusion-patterns/cad-nav-state.md` | ~200 | Pattern doc for the system |

## Modified Files Summary

| File | Changes |
|---|---|
| `fusion-addin/FusionMCPBridge.py` | Import new modules, instantiate classes, add 5 new HTTP endpoints |
| `fusion-addin/frame_manager.py` | Add 3 new methods (get_active_frame, get_nearby_frames, get_frame_for_entity) |
| `fusion-design-mcp-server/src/index.ts` | Add 5 new MCP tool definitions + endpoint mappings |

## New MCP Tools Summary

| Tool | Purpose |
|---|---|
| `fusion_get_state` | Full STATE snapshot |
| `fusion_get_state_compact` | Single-line nav string |
| `fusion_get_local_graph` | Entity neighborhood around focus |
| `fusion_get_patches_since` | Incremental state updates |
| `fusion_apply_action` | Execute structured high-level command |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Fusion event model too limited for real-time patches | Patches lag behind reality | Polling fallback (500ms) + always allow full STATE refresh |
| Entity tokens invalidated by undo/redo | Refs go stale | Semantic key fallback resolves by structure, not token |
| LOCAL_GRAPH too large for complex models | Token bloat | Depth parameter + entity count cap + focus-scoped extraction |
| ACTION executor doesn't cover all ops | LLM falls back to primitive tools | ACTION is optional; primitive tools always available |
| Numpy dependency in Fusion add-in | Import failures | Use math stdlib only (no numpy); frame_manager already needs refactoring for this |

## Open Design Decisions

1. **Polling interval** — 500ms default, configurable. Too fast wastes CPU in Fusion; too slow misses transient states.
2. **Patch queue depth** — 50 patches max. Older patches discarded; LLM can always do full STATE refresh.
3. **Graph depth default** — 1 (immediate neighbors). Depth 2 for sketch graphs (include constraint targets).
4. **Nav string format** — Fixed key order for parseability. Use `=` separators, `[]` for arrays, `{}` for maps.
5. **ACTION op vocabulary** — Start with ~15 ops covering sketch/feature/param/timeline. Expand as needed.

## Success Criteria

1. `fusion_get_state` returns a well-formed STATE in < 100ms
2. `fusion_get_local_graph` for a sketch with 20 entities returns in < 200ms
3. Patch queue captures selection and timeline changes within 1 second
4. Entity refs survive a timeline roll-back and re-roll-forward
5. LLM can navigate from "open document" to "edit a specific sketch dimension" using only STATE + LOCAL_GRAPH + ACTION, without calling `list_bodies` / `get_body_center` manually
6. Total STATE + LOCAL_GRAPH < 2000 tokens for a typical single-body document
