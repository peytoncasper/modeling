---
name: fusion-sketch
description: Create and edit sketches in Fusion 360 using the fusion-sketch CLI. Use when the user asks to sketch, draw geometry, create profiles, add constraints, dimensions, patterns, or work with 2D geometry in Fusion 360.
---

# Fusion 360 Sketching

Control Fusion 360 sketches via `tools/fusion-sketch`. All coords are mm. Output is JSON.

## Orient yourself first

Before drawing anything, understand where you are:

```bash
tools/fusion-sketch state              # what's focused, selected, timeline position
tools/fusion-sketch list               # all sketches in the design
tools/fusion-sketch info --sketch S1   # curves, points, constraints detail
tools/fusion-sketch graph --sketch S1  # topology of a specific sketch
```

## Core workflow

```bash
# 1. Create sketch on a plane
tools/fusion-sketch create --plane xz --name SidePanel

# 2. Draw geometry (sketch coords — read the plane rules below)
tools/fusion-sketch rect --sketch SidePanel --c1 0,-50 --c2 100,0

# 3. Add constraints to lock geometry
tools/fusion-sketch constrain --sketch SidePanel --type horizontal --e1 SidePanel_curve_0

# 4. Add dimensions to make it parametric
tools/fusion-sketch add-dim --sketch SidePanel --type distance --e1 SidePanel_curve_0 --value 100

# 5. Verify profiles formed
tools/fusion-sketch finish --sketch SidePanel

# 6. If gaps exist, diagnose and fix
tools/fusion-sketch gaps --sketch SidePanel
tools/fusion-sketch close-gaps --sketch SidePanel
```

## Plane coordinate rules — MEMORIZE THESE

The sketch 2D coordinate system depends on which plane you drew on:

| Plane | Sketch X → | Sketch Y → | Gotcha |
|-------|-----------|-----------|--------|
| **XY** | World +X | World +Y | None — direct mapping |
| **XZ** | World +X | World **-Z** | **Y is inverted!** For +Z geometry, use negative sketch Y |
| **YZ** | World **-Z** | World +Y | **X is inverted!** For +Z geometry, use negative sketch X |

**The rule:** to place geometry at positive World Z, negate the corresponding sketch axis.

### Example: panel from Z=0 to Z=50 on XZ plane

```bash
# sketch Y = -50 → world Z = +50
# sketch Y = 0   → world Z = 0
tools/fusion-sketch rect --sketch S1 --c1 0,-50 --c2 100,0
```

### Bypass: use world coordinates directly

```bash
# rect3d auto-converts world coords to sketch coords for you
tools/fusion-sketch rect3d --sketch S1 --wc1 0,0,0 --wc2 100,50,0
```

**Prefer `rect3d` when placing geometry at known world positions.** Use `rect` only when you're thinking in sketch-local terms.

## Verify coordinates before trusting them

```bash
# Convert sketch 2D → world 3D to check your math
tools/fusion-sketch coords --sketch S1 --points 0,0 100,-50

# Get suggested sketch coords for world 3D targets
tools/fusion-sketch suggest --plane xz --wmin 0,0,0 --wmax 100,50,100
```

## Complete command reference

### Lifecycle

| Command | What it does |
|---------|-------------|
| `create --plane P [--name N] [--component C]` | New sketch on plane xy/xz/yz/custom |
| `create-on-face --body B --face F [--name N]` | New sketch on a body face |
| `finish --sketch S` | Validate: returns profile count + open curves |
| `delete --sketch S [--component C]` | Delete a sketch |
| `list` | All sketches with plane info + coordinate mappings |

### Drawing primitives

| Command | What it does |
|---------|-------------|
| `line --sketch S --start x,y --end x,y [--construction]` | Line segment (optionally construction) |
| `arc --sketch S --center x,y --radius R --start-angle D --sweep D` | Arc by center+radius+angles |
| `arc3 --sketch S --start x,y --mid x,y --end x,y` | Arc through 3 points |
| `circle --sketch S --center x,y --radius R` | Circle |
| `rect --sketch S --c1 x,y --c2 x,y` | Rectangle in sketch coords |
| `rect3d --sketch S --wc1 x,y,z --wc2 x,y,z` | Rectangle in world coords (auto-converts) |
| `spline --sketch S --points x,y x,y ... [--closed]` | Spline through points |
| `polygon --sketch S --center x,y --radius R [--sides N] [--rotation D]` | Regular polygon (default 6 sides) |
| `slot --sketch S --c1 x,y --c2 x,y --radius R` | Slot (oblong) shape |
| `centerline --sketch S --start x,y --end x,y` | Construction line |
| `point --sketch S --pos x,y` | Sketch point |

### Modifications

| Command | What it does |
|---------|-------------|
| `fillet --sketch S --c1 CURVE_ID --c2 CURVE_ID --radius R` | Fillet between two curves |
| `trim --sketch S --curve CURVE_ID --point x,y` | Trim curve at point |
| `extend --sketch S --curve CURVE_ID --point x,y [--from-start]` | Extend curve toward point |
| `offset --sketch S --curves ID ... --dist D --dir x,y` | Offset curves by distance |
| `mirror --sketch S --curves ID ... --line LINE_ID` | Mirror curves about a line |
| `pattern-rect --sketch S --curves ID ... [--xn N --yn N --xs D --ys D]` | Rectangular pattern |
| `pattern-circ --sketch S --curves ID ... --center x,y [--count N --angle D]` | Circular pattern |

### Constraints

| Command | What it does |
|---------|-------------|
| `constrain --sketch S --type TYPE --e1 ID [--e2 ID]` | Add geometric constraint |
| `coincident --sketch S [--tolerance T]` | Auto-apply coincident constraints at close endpoints |
| `list-constraints --sketch S` | List all constraints |

**Constraint types:** `coincident`, `horizontal`, `vertical`, `perpendicular`, `parallel`, `tangent`, `equal`, `concentric`, `midpoint`, `fix`, `collinear`

Single-entity types (no `--e2`): `horizontal`, `vertical`, `fix`

### Dimensions

| Command | What it does |
|---------|-------------|
| `dims --sketch S` | List all dimensions with values + expressions |
| `dim-edit --sketch S --dim INDEX [--value V] [--expr E]` | Edit dimension value or expression |
| `add-dim --sketch S --type TYPE --e1 ID [--e2 ID] [--value V] [--pos x,y]` | Add dimension |

**Dimension types:** `distance`, `diameter`, `radius`, `angular`

### Analysis & repair

| Command | What it does |
|---------|-------------|
| `gaps --sketch S [--tolerance T]` | Find unclosed gaps between curves |
| `close-gaps --sketch S [--tolerance T] [--max-gap M] [--dry-run]` | Auto-close small gaps |
| `recreate --sketch S [--new-name N] [--delete-orig]` | Recreate as proper closed polygon |

### Query & coordinate helpers

| Command | What it does |
|---------|-------------|
| `profiles --sketch S` | Profile list with areas and world bounds |
| `info --sketch S` | Detailed sketch: all curves, points, constraints |
| `coords --sketch S --points x,y ...` | Sketch 2D → world 3D conversion |
| `suggest --plane P --wmin x,y,z --wmax x,y,z` | World 3D → sketch 2D suggestion |
| `graph [--sketch S]` | Topology graph (LOCAL_GRAPH) |
| `state [--compact]` | Navigation state snapshot |

### Import & text

| Command | What it does |
|---------|-------------|
| `import-svg --path FILE [--plane P] [--body B] [--name N] [--scale S]` | Import SVG into sketch |
| `text --text T [--sketch S] [--plane P] [--font F] [--height H] [--pos x,y]` | Add text to sketch |

## Entity ID format

Curves and points use a predictable naming scheme:
- `SketchName_curve_0`, `SketchName_curve_1`, ... (index-based)
- `SketchName_point_0`, `SketchName_point_1`, ...
- `SketchName_dim_0`, `SketchName_dim_1`, ...

Use `info --sketch S` to see all entity IDs.

## Reading the output

Every command returns JSON. Key fields to watch:

**`finish`** — the most important check:
```json
{"success": true, "is_valid": true, "profile_count": 1, "open_curves": 0}
```
- `is_valid: false` means no closed profiles → can't extrude
- `open_curves > 0` means geometry doesn't close → run `gaps`

**`profiles`** — what you'll extrude:
```json
{"profiles": [{"profile_index": 0, "area_mm2": 5000, "sketch_bounds": {...}}]}
```
- `profile_index` is what you pass to extrude later

**`info`** — full detail for planning:
```json
{"curves": [{"curve_id": "S_curve_0", "type": "SketchLine", "start": [0,0], "end": [100,0], "length_mm": 100}]}
```

## Common mistakes

1. **Forgetting the Y inversion on XZ plane.** Geometry ends up at -Z. Use `rect3d` to avoid this entirely.

2. **Drawing open geometry then trying to extrude.** Always `finish` and check `profile_count > 0` before moving on.

3. **Sketch coords in mm but thinking in inches.** Everything is mm. A 1" panel is 25.4mm.

4. **Not naming sketches.** Always use `--name` on create. Unnamed sketches get auto-names that are hard to reference later.

5. **Drawing on the wrong plane.** XY = horizontal (floor). XZ = vertical front-facing. YZ = vertical side-facing.

6. **Not adding constraints.** Unconstrained sketches drift when you edit dimensions. Use `constrain` to lock geometry relationships, then `add-dim` to make it parametric.

## Decision guide: which plane?

| I want to make... | Plane | Extrude direction |
|-------------------|-------|-------------------|
| A horizontal panel (floor/shelf) | XY | +Z (up) or -Z (down) |
| A vertical front panel | XZ | +Y (into model) or -Y (toward viewer) |
| A vertical side panel | YZ | +X (right) or -X (left) |
| A panel at an offset | Create offset plane first, then sketch on it |
| A shape on an existing body face | Use `create-on-face` instead of a plane |
