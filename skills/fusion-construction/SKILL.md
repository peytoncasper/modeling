---
name: fusion-construction
description: Create and manage construction geometry in Fusion 360 — planes, axes, points, and measurements. Use when the user asks to create reference geometry, offset planes, angled planes, midplanes, construction axes, construction points, measure distances, measure angles, or query body properties.
---

# Fusion 360 Construction / Reference Geometry

Control Fusion 360 construction geometry via `tools/fusion-construction`. All dimensions are mm. Output is JSON.

## Orient yourself first

```bash
tools/fusion-construction planes     # all construction planes
tools/fusion-construction axes       # all construction axes
tools/fusion-construction points     # all construction points
tools/fusion-construction measure --body Body1   # body properties (volume, area, CoM)
tools/fusion-construction vertices --body Body1  # all vertex positions
```

## Construction Planes

Planes are the foundation for sketches. Fusion provides 3 built-in planes (XY, XZ, YZ) and you can create custom ones.

### Create offset plane

The most common operation — place a plane parallel to a base plane at a distance:

```bash
# 50mm above XY plane
tools/fusion-construction offset-plane --base xy --offset 50 --name ShelfPlane

# 25mm in front of XZ plane
tools/fusion-construction offset-plane --base xz --offset 25

# Offset from an existing custom plane
tools/fusion-construction offset-plane --base ShelfPlane --offset 19.05 --name NextShelf
```

### Create angled plane (arbitrary orientation)

Two input modes:

```bash
# Mode 1: Point + normal vector
tools/fusion-construction angled-plane --point 50,50,50 --normal 1,1,0 --name DiagonalCut

# Mode 2: Three points defining the plane
tools/fusion-construction angled-plane --p1 0,0,0 --p2 100,0,0 --p3 0,100,50 --name RampPlane
```

### Plane rotated around a line

Create a tilted plane by rotating a base plane around a sketch line:

```bash
tools/fusion-construction plane-by-angle --base xy --sketch AxisSketch --line 0 --angle 45 --name TiltedPlane
```

### Midplane

Create a plane halfway between two parallel planes or faces:

```bash
# Between two built-in planes
tools/fusion-construction midplane --p1 xy --p2 ShelfPlane --name MidShelf

# Between two faces of a body (use body:face syntax)
tools/fusion-construction midplane --p1 Panel1:Panel1_face_0 --p2 Panel1:Panel1_face_1
```

### Tangent plane

Create a plane tangent to a curved surface:

```bash
tools/fusion-construction tangent-plane --body Cylinder1 --face Cylinder1_face_2 --name TangentCut
```

### Delete a plane

```bash
tools/fusion-construction delete-plane --name MyOldPlane
```

## Construction Axes

Axes are used for revolves, patterns, and as references.

```bash
# List all axes
tools/fusion-construction axes

# Through two points
tools/fusion-construction axis-2pt --p1 0,0,0 --p2 100,100,0 --name DiagonalAxis

# Along a body edge
tools/fusion-construction axis-edge --body Body1 --edge Body1_edge_0 --name EdgeAxis

# Perpendicular to a face (through its center)
tools/fusion-construction axis-perp --body Body1 --face Body1_face_0 --name FaceNormal

# At the intersection of two planes
tools/fusion-construction axis-intersect --p1 xy --p2 xz --name OriginX

# Delete
tools/fusion-construction delete-axis --name MyAxis
```

## Construction Points

Reference points for snapping, dimensioning, and plane creation.

```bash
# List existing
tools/fusion-construction points

# At specific coordinates
tools/fusion-construction point --pos 50,30,20 --name CenterRef

# At a body vertex
tools/fusion-construction point-vertex --body Body1 --index 0 --name Corner

# At center of edge (midpoint) or face (centroid)
tools/fusion-construction point-center --body Body1 --entity Body1_edge_3 --name EdgeMid

# Delete
tools/fusion-construction delete-point --name CenterRef
```

## Measurements

### Distance between entities

The `--e1` and `--e2` flags use a `type:value` format:

| Entity spec | Meaning |
|-------------|---------|
| `body:BodyName` | Entire body |
| `face:Body:FaceID` | A specific face |
| `edge:Body:EdgeID` | A specific edge |
| `plane:xy` | A construction plane |
| `axis:z` | A construction axis |
| `point:x,y,z` | An arbitrary 3D point |

```bash
# Distance between two bodies
tools/fusion-construction distance --e1 body:Panel1 --e2 body:Panel2

# Distance from a point to a plane
tools/fusion-construction distance --e1 point:50,30,20 --e2 plane:xy

# Distance between a face and a body
tools/fusion-construction distance --e1 face:Body1:Body1_face_0 --e2 body:Body2

# Distance between two points
tools/fusion-construction distance --e1 point:0,0,0 --e2 point:100,100,100
```

### Angle between planes/faces

```bash
# Angle between two built-in planes
tools/fusion-construction angle --e1 plane:xy --e2 plane:xz

# Angle between a face and a plane
tools/fusion-construction angle --e1 face:Wedge:Wedge_face_0 --e2 plane:xy

# Angle between two faces
tools/fusion-construction angle --e1 face:Body1:Body1_face_0 --e2 face:Body1:Body1_face_2
```

### Body physical properties

```bash
tools/fusion-construction measure --body Body1
```

Returns: volume, surface area, center of mass, bounding box, dimensions, face/edge/vertex counts.

### Vertex listing

```bash
tools/fusion-construction vertices --body Body1
```

Returns all vertex positions — useful for polyhedron workflows and verifying geometry.

## Complete command reference

### Planes

| Command | What it does |
|---------|-------------|
| `planes` | List all planes (3 built-in + user-created) |
| `offset-plane --base P --offset D [--name N] [--component C]` | Plane parallel to base at distance |
| `angled-plane --point x,y,z --normal x,y,z [--name N]` | Plane at arbitrary orientation (point+normal) |
| `angled-plane --p1 x,y,z --p2 x,y,z --p3 x,y,z [--name N]` | Plane through three points |
| `plane-by-angle --base P --sketch S --line I --angle D [--name N]` | Plane rotated around sketch line |
| `midplane --p1 ID --p2 ID [--name N]` | Midplane between two planes/faces |
| `tangent-plane --body B --face F [--point x,y,z] [--name N]` | Plane tangent to curved surface |
| `delete-plane --name N` | Delete a construction plane |

### Axes

| Command | What it does |
|---------|-------------|
| `axes` | List all axes (3 built-in + user-created) |
| `axis-2pt --p1 x,y,z --p2 x,y,z [--name N]` | Axis through two points |
| `axis-edge --body B --edge E [--name N]` | Axis along a body edge |
| `axis-perp --body B --face F [--name N]` | Axis perpendicular to face |
| `axis-intersect --p1 PLANE --p2 PLANE [--name N]` | Axis at intersection of two planes |
| `delete-axis --name N` | Delete a construction axis |

### Points

| Command | What it does |
|---------|-------------|
| `points` | List all construction points |
| `point --pos x,y,z [--name N]` | Point at coordinates |
| `point-vertex --body B --index I [--name N]` | Point at body vertex |
| `point-center --body B --entity E [--name N]` | Point at center of edge/face |
| `delete-point --name N` | Delete a construction point |

### Measurements

| Command | What it does |
|---------|-------------|
| `distance --e1 SPEC --e2 SPEC` | Minimum distance between entities |
| `angle --e1 SPEC --e2 SPEC` | Angle between planes/faces |
| `measure --body B` | Body properties (volume, area, CoM, counts) |
| `vertices --body B` | All vertex positions of a body |

## Decision guide

| I want to... | Command |
|--------------|---------|
| Sketch at a specific height | `offset-plane` then sketch on it |
| Create a miter cut plane | `angled-plane` with the bisector normal |
| Find the middle of a panel | `midplane` between its two faces |
| Place a hole at a body's center | `measure` to get center of mass |
| Check if two panels are parallel | `angle` between their faces (0° = parallel) |
| Revolve around a diagonal | `axis-2pt` then use in fusion-solid revolve |
| Pattern along an edge | `axis-edge` then use for pattern direction |
| Verify body dimensions | `measure` for exact volume/area/bounds |
| Find exact corner positions | `vertices` to list all vertex coordinates |

## Common mistakes

1. **Offset direction confusion.** Positive offset goes in the plane's normal direction. For XY: +Z (up). For XZ: +Y (into model). For YZ: +X (right).

2. **Forgetting to name planes.** Auto-generated names like "Plane1" are hard to reference later. Always use `--name`.

3. **Deleting helper geometry.** Angled planes in parametric mode create helper sketches/planes. Deleting them breaks the construction plane.

4. **Measuring with wrong entity type.** The `distance` command needs explicit `type:value` format. `body:Body1` not just `Body1`.
