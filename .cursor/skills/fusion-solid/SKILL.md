---
name: fusion-solid
description: Create and modify 3D bodies in Fusion 360 using the fusion-solid CLI. Use when the user asks to extrude, revolve, loft, sweep, boolean, fillet, chamfer, shell, split, create primitives (box/cylinder/sphere/hole), query bodies/edges/faces, copy/move/mirror/pattern bodies, or work with construction planes.
---

# Fusion 360 Solid / Body Operations

Control Fusion 360 3D features and bodies via `tools/fusion-solid`. All dimensions are mm. Output is JSON.

## Orient yourself first

Before creating features, understand the current model:

```bash
tools/fusion-solid summary       # world bounds, all bodies, orientation
tools/fusion-solid list           # all bodies with dimensions + provenance
tools/fusion-solid planes         # all construction planes (xy, xz, yz + custom)
tools/fusion-solid center --body Body1   # center point + bounding box of a body
```

## Core workflow: sketch → extrude

```bash
# 1. Create a sketch (use fusion-sketch skill)
tools/fusion-sketch create --plane xy --name Base
tools/fusion-sketch rect --sketch Base --c1 0,0 --c2 100,80

# 2. Extrude the profile into a 3D body
tools/fusion-solid extrude --sketch Base --distance 20 --name BasePanel

# 3. Verify the result
tools/fusion-solid list
tools/fusion-solid center --body BasePanel
```

## Feature operations

All features that work from sketch profiles support `--op` for boolean behavior:
- `new_body` — creates a separate body (default)
- `join` — adds material to an existing body (must intersect)
- `cut` — removes material from an existing body
- `intersect` — keeps only the overlapping volume

### Extrude

```bash
# Basic extrude
tools/fusion-solid extrude --sketch S --distance 20

# Extrude as a cut into an existing body
tools/fusion-solid extrude --sketch SlotSketch --distance 15 --op cut --target Panel

# Symmetric extrude (both directions)
tools/fusion-solid extrude --sketch S --distance 10 --dir symmetric

# Extrude with draft/taper
tools/fusion-solid extrude-draft --sketch S --distance 20 --draft 5
```

### Revolve

```bash
# Full revolution around X axis
tools/fusion-solid revolve --sketch Profile --axis x

# Partial revolve (90°) around a sketch line
tools/fusion-solid revolve --sketch Profile --axis-sketch AxisSketch --axis-line 0 --angle 90
```

### Loft

```bash
# Loft between two sketches
tools/fusion-solid loft --sketches TopProfile BotProfile

# Loft with guide rails
tools/fusion-solid loft --sketches S1 S2 --rails RailSketch
```

### Sweep

```bash
# Sweep a profile along a path
tools/fusion-solid sweep --profile-sketch CrossSection --path-sketch SweepPath

# Sweep with twist
tools/fusion-solid sweep --profile-sketch CS --path-sketch P --twist 90
```

## Edge/face modifications

```bash
# Fillet edges (round them)
tools/fusion-solid fillet --edges Body1_edge_0 Body1_edge_3 --radius 2

# Chamfer edges (bevel them)
tools/fusion-solid chamfer --edges Body1_edge_0 --distance 1.5

# Boolean combine bodies
tools/fusion-solid boolean --op union --target Body1 --tools Body2 Body3
tools/fusion-solid boolean --op subtract --target Body1 --tools CutterBody

# Shell a body (hollow it out)
tools/fusion-solid shell --body Body1 --thickness 2 --faces 0

# Split a body with a plane
tools/fusion-solid split --body Body1 --tool xz --keep both
```

## Stable entity references

Edge indices (`Body1_edge_3`) **shift after every boolean, fillet, or chamfer**. Use spatial references instead — they survive topology changes.

### Three reference formats

| Format | Example | When to use |
|--------|---------|-------------|
| Index (legacy) | `Body1_edge_3` | Quick one-shot before any topology change |
| Spatial | `Body1@170,0,542` | **Preferred** — stable across booleans/fillets |
| Token | `token:abc123...` | EntityToken from resolver cache |

### Spatial reference workflow

```bash
# 1. List edges to find midpoints
tools/fusion-solid edges --body Body1
# Output includes midpoint for each edge, e.g.:
#   edge_3: midpoint [170.0, 0.0, 542.0]

# 2. Use the midpoint as a spatial ref — this survives topology changes
tools/fusion-solid fillet --edges "Body1@170,0,542" --radius 10

# 3. After a boolean, the same spatial ref still finds the right edge
tools/fusion-solid boolean --op subtract --target Body1 --tools Cutter
tools/fusion-solid fillet --edges "Body1@170,0,542" --radius 5
```

The spatial lookup finds the nearest edge within 10mm of the given point. Use midpoints from `edges --body` for best accuracy.

## Primitives — quick body creation

For simple shapes, skip the sketch step entirely:

```bash
# Box from two corners
tools/fusion-solid box --c1 0,0,0 --c2 100,80,20 --name Panel

# Box from center + dimensions
tools/fusion-solid box --center 50,40,10 --width 100 --depth 80 --height 20 --name Panel

# Cylinder
tools/fusion-solid cylinder --center 0,0,0 --radius 25 --height 50 --axis z --name Peg

# Sphere
tools/fusion-solid sphere --center 0,0,50 --radius 30 --name Ball

# Hole (cut into existing body)
tools/fusion-solid hole --body Panel --center 50,40,20 --diameter 10 --through

# Box joint helper
tools/fusion-solid box-joint --receiving SidePanel --mating BottomPanel --edge front
```

## Surfaces and stitching

For creating complex geometry from surface patches:

```bash
# Create a surface patch from a sketch profile
tools/fusion-solid patch --sketch FaceSketch --name Face1

# Stitch multiple surfaces into a solid (if watertight)
tools/fusion-solid stitch --bodies Face1 Face2 Face3 Face4 --name SolidResult
```

## Polyhedron / faceted geometry

```bash
# Arbitrary polyhedron from vertices + triangular faces
tools/fusion-solid polyhedron \
  --vertex V1=0,0,0 V2=100,0,0 V3=50,86.6,0 V4=50,28.9,81.6 \
  --face V1,V2,V3 V1,V2,V4 V2,V3,V4 V1,V3,V4 \
  --name Tetrahedron

# Triangular prism (simpler)
tools/fusion-solid tri-prism --v1 0,0,0 --v2 100,0,0 --v3 50,86.6,0 --height 50 --name Prism
```

## Construction planes

```bash
# List all planes
tools/fusion-solid planes

# Offset from a base plane
tools/fusion-solid offset-plane --base xy --offset 50

# Angled plane from point + normal
tools/fusion-solid angled-plane --point 50,50,50 --normal 1,1,0 --name DiagonalPlane

# Angled plane from three points
tools/fusion-solid angled-plane --p1 0,0,0 --p2 100,0,0 --p3 0,100,50

# Plane by rotating around a sketch line
tools/fusion-solid plane-by-angle --base xy --sketch AxisSketch --angle 45 --name Tilted
```

## Body query — understand the model

```bash
# List all bodies with dimensions and provenance
tools/fusion-solid list
tools/fusion-solid list --component Carcass

# Edges and faces of a specific body
tools/fusion-solid edges --body Body1
tools/fusion-solid faces --body Body1

# Detailed face geometry (normal, area, angles to world planes)
tools/fusion-solid face-info --body Body1 --face Body1_face_0

# Body center and bounding box
tools/fusion-solid center --body Body1

# Find shared edges between two bodies (miter joints, etc.)
tools/fusion-solid intersections --b1 Panel1 --b2 Panel2

# Select geometry by 3D position
tools/fusion-solid select --point 50,40,10 --type face --tolerance 2

# Full model summary
tools/fusion-solid summary
```

## Body transforms

```bash
# Copy a body
tools/fusion-solid copy --body Body1 --name Body1_Copy

# Translate a body
tools/fusion-solid move --body Body1 --translate 100,0,0

# Rotate a body
tools/fusion-solid move --body Body1 --rotate-axis 0,0,1 --rotate-angle 90

# Mirror across a plane
tools/fusion-solid mirror --body Body1 --plane yz

# Rectangular pattern
tools/fusion-solid pattern --body Body1 --dir 1,0,0 --count 4 --spacing 25

# Delete a body
tools/fusion-solid delete --body Body1
```

## Entity ID format

Bodies, edges, and faces support multiple reference formats:
- Body names: whatever Fusion auto-assigns or you specify with `--name`
- Edges: `BodyName_edge_0` (index) or `BodyName@x,y,z` (spatial — preferred)
- Faces: `BodyName_face_0` (index) or `BodyName@x,y,z` (spatial — preferred)

Use `edges --body B` or `faces --body B` to discover IDs and midpoints. **Prefer spatial refs (`Body@x,y,z`) whenever you plan to modify topology afterward.**

## Unit conversions

All inputs and outputs are mm. Fusion internally uses cm, but the bridge handles conversion.

| You give | Fusion gets | Meaning |
|----------|-----------|---------|
| 25.4 mm | 2.54 cm | 1 inch |
| 12.7 mm | 1.27 cm | 1/2 inch |
| 19.05 mm | 1.905 cm | 3/4 inch (standard plywood) |

## Common mistakes

1. **Extrude join that creates an orphan body.** The extruded geometry must physically touch the target body. If not, Fusion silently creates a new body. Watch for `warning: JOIN_CREATED_ORPHAN_BODY` in the output.

2. **Wrong extrude direction.** On XZ or YZ plane sketches, positive extrude may not go where you expect. Use `summary` to check body positions after extruding.

3. **Edge IDs change after modifying the body.** If you fillet/chamfer/boolean a body, the edge indices shift. **Use spatial refs (`Body@x,y,z`) instead of index-based IDs to avoid this problem entirely.**

4. **Shell without specifying faces to remove.** If `--faces` is empty, you get a fully enclosed shell (no opening). Usually you want to remove at least one face.

5. **Boolean with wrong body scope.** Bodies in different components may need assembly-context proxies. The bridge handles this, but verify with `list` if results seem wrong.

## Decision guide

| I want to... | Command |
|--------------|---------|
| Turn a sketch into a 3D shape | `extrude` |
| Create a round shape from a profile | `revolve` |
| Blend between two profiles | `loft` |
| Extrude along a curved path | `sweep` |
| Add material to an existing body | `extrude --op join --target B` |
| Cut material from a body | `extrude --op cut --target B` |
| Combine two separate bodies | `boolean --op union` |
| Subtract one body from another | `boolean --op subtract` |
| Round sharp edges | `fillet` |
| Bevel sharp edges | `chamfer` |
| Hollow out a solid | `shell` |
| Cut a body in half | `split` |
| Quick box without sketching | `box` |
| Quick cylinder without sketching | `cylinder` |
| Drill a hole | `hole` |
