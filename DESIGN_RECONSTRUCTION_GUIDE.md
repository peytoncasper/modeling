# Table Base Design -- Full Reconstruction Guide

This document records exactly how every piece of the current Fusion 360 model was built, in the order it would need to be recreated. Use this as a reference when modifying the polyhedron shape.

---

## 1. Parameters

| Name | Value | Unit | Purpose |
|------|-------|------|---------|
| `panel_thickness` | 12.7 | mm | Wall thickness for all panels (1/2") |

Rib thickness: 6.35mm (1/4"), slot width: 6.85mm (6.35 + 0.5mm CNC tolerance), slot/tab depth: 4mm.

---

## 2. Construction Planes (Timeline 0-13)

These define the orientation of each face sketch. They come in pairs: the original plane at the origin, and a second version (`_v2` / `_2x`) positioned at the actual face location.

| Index | Name | Type | Notes |
|-------|------|------|-------|
| 0 | `Face1_Plane` | XY at origin | Horizontal reference |
| 1 | `Face2_Plane` | Custom at origin | normal=[0.771, 0, 0.637] |
| 2 | `Face3_Plane` | Custom at origin | normal=[0.263, 0.813, -0.519] |
| 3 | (Floor_Sketch) | Sketch | Placed before the v2 planes |
| 4 | `Face2_Plane_v2` | Custom | Positioned at face location |
| 5 | `Face3_Plane_v2` | Custom | Positioned at face location |
| 6 | `Face4_Plane_v2` | XZ at Y=75 | Vertical front plane |
| 7 | `Face_DEI_Plane_v2` | XZ at (806.82, 95, 216.18) | |
| 8 | `Face_DIH_Plane_v2` | YZ at (806.82, 95, 216.18) | |
| 9 | `Face_IHC_Plane_v2` | XZ at (191.33, -151.16, -140) | |
| 10-13 | `*_2x` variants | Duplicates | Face4, DEI, DIH, IHC second copies |

---

## 3. Face Sketches (Timeline 14-21)

Each sketch defines one face of the polyhedron as a closed polygon. These are the **foundational geometry** -- everything else derives from them.

| Index | Sketch | Plane | Normal (outward) | Profile | Coord Mapping |
|-------|--------|-------|-------------------|---------|---------------|
| 14 | `Face1_Sketch` | XY at origin | [-0.259, 0, 0.966] | 1 closed, 4 curves | x=World+X, y=World+Y |
| 15 | `Face2_Sketch` | Custom n=[0.771,0,0.637] | [0.771, 0, 0.637] | 1 closed, 4 curves | Custom plane |
| 16 | `Face3_Sketch` | Custom n=[0.263,0.813,-0.519] | [0.263, 0.813, -0.519] | 1 closed, 4 curves | Custom plane |
| 17 | `Face4_Sketch` | XZ at Y=75 | [0, -1, 0] | 1 closed, 3 curves | x=World+X, y=World-Z |
| 18 | `Face_DIH_Sketch` | YZ at (806.82, 95, 216.18) | ~[-1, 0, 0] direction | 1 closed, 4 curves | x=World-Z, y=World+Y |
| 19 | `Face_DEI_Sketch` | XZ at (806.82, 95, 216.18) | ~[0, -1, 0] direction | 1 closed, 3 curves | x=World+X, y=World-Z |
| 20 | `Face_IHC_Sketch` | XZ at (191.33, -151.16, -140) | ~[0, 1, 0] direction | 1 closed, 3 curves | x=World+X, y=World-Z |
| 21 | `Floor_Sketch` | XY (horizontal) | [0, 0, -1] | 1 closed | x=World+X, y=World+Y |

**Key gotcha:** On XZ planes, sketch +Y maps to World -Z. On YZ planes, sketch +X maps to World -Z.

### Face adjacency map (14 shared edges)

```
Face4 --- Face1 --- Face3 --- IHC
  |    \    |    /    |         |
  |     \   |   /     |         |
 DEI --- (Face2) --- Floor --- DIH
  |                    |         |
  +-------- Floor -----+---------+
```

Explicit pairs:
- Face4 <-> Face1, Face2, DEI
- Face1 <-> Face4, Face2, Face3, DIH
- Face2 <-> Face4, Face1, Face3, Floor
- Face3 <-> Face1, Face2, Floor, IHC
- DEI <-> Face4, DIH, Floor
- DIH <-> Face1, DEI, IHC, Floor
- IHC <-> Face3, DIH, Floor
- Floor <-> Face2, Face3, DEI, DIH, IHC

---

## 4. Surface Patches (Timeline 22-29)

Each face sketch was converted to a zero-thickness surface body using `fusion_create_patch`. The patches were then stitched together to form a watertight solid.

| Index | Feature | Source Sketch |
|-------|---------|---------------|
| 22 | SurfacePatch1 | Face1_Sketch |
| 23 | SurfacePatch2 | Face2_Sketch |
| 24 | SurfacePatch3 | Face3_Sketch |
| 25 | SurfacePatch4 | Face4_Sketch |
| 26 | SurfacePatch5 | Face_DIH_Sketch |
| 27 | SurfacePatch6 | Face_DEI_Sketch |
| 28 | SurfacePatch7 | Face_IHC_Sketch |
| 29 | SurfacePatch8 | Floor_Sketch (profile_index: 0, direct extrude workaround for broken reference plane) |

**To recreate patches:**
```
For each face sketch:
  fusion_create_patch(sketch_id=<sketch_name>)
```

**Note:** `Floor_Sketch` had a broken `referencePlane` -- use `profile_index: 0` explicitly and skip `get_sketch_profiles`.

---

## 5. Stitch into Solid (Timeline 30)

| Index | Feature | Bodies Stitched | Result |
|-------|---------|-----------------|--------|
| 30 | SurfaceStitch5 | All 8 patches | Watertight solid (~31.4M mm^3) |

```
fusion_stitch(body_ids=[all 8 patch body names], tolerance=0.1)
```

The stitch creates a **solid** body because the 8 patches form a closed (watertight) boundary. This is the foundation for everything that follows.

---

## 6. Bisector Planes (Timeline 31-135)

For each of the 14 shared edges between adjacent faces, a bisector construction plane was created. The bisector plane splits the dihedral angle between two neighboring faces exactly in half.

**Formula:** `bisector_normal = normalize(N1 + N2)` where N1, N2 are the outward normals of the two adjacent faces. The point is on the shared edge.

Each bisector plane is created via `fusion_create_angled_plane`, which internally creates 3 helper planes + 3 helper sketches (6 timeline items per bisector plane). This accounts for the large gap from index 31 to 135.

| Bisector Plane | Adjacent Faces | Timeline Index |
|----------------|----------------|----------------|
| BP_Face4_Face1 | Face4 <-> Face1 | 37 |
| BP_Face4_DEI | Face4 <-> DEI | 44 |
| BP_Face4_Face2 | Face4 <-> Face2 | 51 |
| BP_DEI_DIH | DEI <-> DIH | 58 |
| BP_DEI_Floor | DEI <-> Floor | 65 |
| BP_Face1_DIH | Face1 <-> DIH | 72 |
| BP_Face1_Face2 | Face1 <-> Face2 | 79 |
| BP_Face1_Face3 | Face1 <-> Face3 | 86 |
| BP_Face2_Floor | Face2 <-> Floor | 93 |
| BP_Face2_Face3 | Face2 <-> Face3 | 100 |
| BP_Face3_Floor | Face3 <-> Floor | 107 |
| BP_Face3_IHC | Face3 <-> IHC | 114 |
| BP_IHC_Floor | IHC <-> Floor | 121 |
| BP_IHC_DIH | IHC <-> DIH | 128 |
| BP_DIH_Floor | DIH <-> Floor | 135 |

---

## 7. Shell (Timeline 136)

The stitched solid was shelled at 12.7mm wall thickness with Face1 removed (to create the opening).

| Index | Feature | Thickness | Face Removed | Result |
|-------|---------|-----------|--------------|--------|
| 136 | Shell7 | 12.7mm | Face1 (largest face) | Hollow shell body "Polyhedron" (6.6M mm^3) |

```
fusion_shell(body_id="<stitched_solid>", thickness=12.7, remove_faces=["face_<id>"], direction="inside")
```

The shell automatically creates perfect miter joints at every internal corner where panels meet. The resulting `Polyhedron` body is a single hollow shell with one open face.

---

## 8. Panel Extraction (Timeline 137-220)

Each panel was extracted from the Polyhedron shell by:
1. **Copy** the Polyhedron shell body (`CopyPasteBodies`)
2. **Cut** the copy at each adjacent bisector plane to isolate just one panel

The cutting process for each panel:
1. Create a sketch on each relevant bisector plane (`Cut_<face1><face2>`)
2. Draw a large rectangle covering the cut area
3. Extrude-cut through the copy (30mm depth) to trim at the bisector

### Cut sketches (Timeline 139-156)

| Sketch | Bisector Plane | Panels It Separates |
|--------|----------------|---------------------|
| Cut_F4F1 | BP_Face4_Face1 | Face4 from Face1 |
| Cut_F4F2 | BP_Face4_Face2 | Face4 from Face2 |
| Cut_F4DEI | BP_Face4_DEI | Face4 from DEI |
| Cut_DEIDIH | BP_DEI_DIH | DEI from DIH |
| Cut_F1DIH | BP_Face1_DIH | Face1 from DIH |
| Cut_F1F2 | BP_Face1_Face2 | Face1 from Face2 |
| Cut_DEIFloor | BP_DEI_Floor | DEI from Floor |
| Cut_F1F3 | BP_Face1_Face3 | Face1 from Face3 |
| Cut_F2F3 | BP_Face2_Face3 | Face2 from Face3 |
| Cut_F3Floor | BP_Face3_Floor | Face3 from Floor |
| Cut_F2Floor | BP_Face2_Floor | Face2 from Floor |
| Cut_F3IHC | BP_Face3_IHC | Face3 from IHC |
| Cut_IHCDIH | BP_IHC_DIH | IHC from DIH |
| Cut_DIHFloor | BP_DIH_Floor | DIH from Floor |
| Cut_IHCFloor | BP_IHC_Floor | IHC from Floor |

### Panel bodies created

Each panel was created by copying the shell and trimming it with the relevant bisector cuts. The final panels were refined with boolean Combine operations (indices 215-220):

| Body | Provenance | Dimensions (mm) | Bounding Box |
|------|-----------|------------------|--------------|
| Panel_Face1 | Combine55 (idx 215) | 807 x 211 x 223 | X:[0, 807] Y:[-116, 95] Z:[-7, 216] |
| Panel_Face2 | Extrude194 (idx 168) | 122 x 222 x 140 | X:[0, 122] Y:[-127, 95] Z:[-140, 0] |
| Panel_Face3 | Combine56 (idx 216) | 764 x 155 x 345 | X:[0, 765] Y:[-151, 4] Z:[-140, 205] |
| Panel_Face4 | Combine57 (idx 217) | 807 x 31 x 356 | X:[0, 807] Y:[64, 95] Z:[-140, 216] |
| Panel_DEI | Combine58 (idx 218) | 691 x 31 x 356 | X:[116, 807] Y:[64, 95] Z:[-140, 216] |
| Panel_DIH | Extrude208 (idx 185) | 188 x 211 x 356 | X:[619, 807] Y:[-116, 95] Z:[-140, 216] |
| Panel_IHC | Combine59 (idx 219) | 573 x 50 x 345 | X:[191, 765] Y:[-151, -101] Z:[-140, 205] |
| Panel_Floor | Combine60 (idx 220) | 544 x 246 x 13 | X:[116, 660] Y:[-151, 95] Z:[-140, -127] |

---

## 9. Ribs (Timeline 201-213)

Two vertical partition ribs provide structural support inside the shell. They were created by **mathematically computing the interior cross-section polygon** at each X position from the panel face plane equations.

### Rib geometry approach

For each rib at X = x0:
1. For each panel face, compute the **inner surface** plane equation: offset the outer face 8.7mm inward (12.7mm - 4mm tab depth) along the inward normal
2. Substitute x = x0 into each plane equation to get a linear constraint in the YZ plane
3. Find the **polygon** formed by the intersection of all active half-plane constraints
4. The polygon vertices are where pairs of constraint lines meet (and all other constraints are satisfied)
5. Sketch the polygon on an offset YZ plane at x = x0
6. Extrude 6.35mm (symmetric or one-sided) to create the rib

### Construction planes for ribs

| Index | Name | Type | Position |
|-------|------|------|----------|
| 201 | Plane369 | Offset from YZ | X = 300mm (Rib 1 center minus half-thickness) |
| 202 | Plane370 | Offset from YZ | X = 480mm (Rib 2 center minus half-thickness) |

### Rib 1 (X = 300mm)

- **Sketch:** `Rib1_Sketch` (Timeline 203, on Plane369)
- **Extrude:** Extrude232 (Timeline 204), 6.35mm
- **Body:** `Rib_1` -- 6.35mm thick, 222mm deep, 203mm tall
- **Cross-section polygon (6 vertices in YZ):**
  - Computed from Face1, Face3, Face4, DEI, IHC, Floor inner surface intersections at X=300
  - The polygon extends 4mm past each panel's inner surface to form tabs

### Rib 2 (X = 480mm)

- **Sketch:** `Rib2_Sketch` (Timeline 205, on Plane370)
- **Extrude:** Extrude233 (Timeline 206), 6.35mm
- **Body:** `Rib_2` -- 6.35mm thick, 211mm deep, 251mm tall
- **Cross-section polygon:**
  - Computed from Face1, Face3, Face4, DEI, IHC, Floor, DIH inner surface intersections at X=480
  - Taller than Rib 1 because the top panel (Face1) is higher at X=480

### Slots

Slots were cut into the panels to accept the rib tabs:
- **Slot width:** 6.85mm (6.35mm rib + 0.5mm CNC tolerance)
- **Slot depth:** 4mm into each panel
- **Method:** Extrude slot bodies from the same rib sketches at 6.85mm width, then boolean subtract from each panel

| Feature | Type | Timeline | Target | Result |
|---------|------|----------|--------|--------|
| Extrude234 | Slot body for Rib 1 | 207 | -- | Slot_1 body |
| Combine49-54 | Boolean subtract | 208-213 | Various panels | Slots cut |
| Extrude235 | Slot body for Rib 2 | 214 | -- | Slot_2 body |
| Combine55-60 | Boolean subtract | 215-220 | Various panels | Slots cut |

**Note:** The Slot_1 and Slot_2 bodies remain in the model because the parametric Combine features depend on them. They can be hidden but not deleted without breaking the slot cuts.

---

## 10. Tabletop (Timeline 221-224)

The tabletop sits above the base at Z=220mm, centered over the base center at (403, -28).

| Index | Feature | Details |
|-------|---------|---------|
| 221 | Plane371 | (unused/earlier attempt) |
| 222 | Plane372 | Offset from XY at Z=220mm |
| 223 | TableTop_Sketch | On Plane372 |
| 224 | Extrude239 | 30mm, new body "TableTop" |

### TableTop shape

A **rounded rectangle** (stadium shape):
- **Total length:** 1220mm (48 inches) along X
- **Width:** 457mm (18 inches) along Y
- **Straight middle section:** 610mm (24 inches)
- **Rounded ends:** 305mm (12 inches) on each end, elliptical profile (semi-axes 305mm x 228.5mm)
- **Thickness:** 30mm
- **No fillet** -- will be refined during sanding

Sketch geometry:
- 2 straight lines for the long edges (Y=200.5 and Y=-256.5)
- 2 open splines for the rounded ends (7 points each, following elliptical path)

The spline points keep the curve **within the 18" width envelope** (not circular arcs, which would bulge wider).

---

## 11. Current Bodies Summary

| Body | Type | Volume (mm^3) | Role |
|------|------|---------------|------|
| Polyhedron | Shell | 6,627,075 | Original shelled solid (can be hidden) |
| Panel_Face1 | Panel | 1,350,109 | Top/sloped panel |
| Panel_Face2 | Panel | 291,703 | Left lower panel |
| Panel_Face3 | Panel | 1,132,486 | Front lower panel |
| Panel_Face4 | Panel | 797,480 | Back panel |
| Panel_DEI | Panel | 1,148,678 | Back-right upper panel |
| Panel_DIH | Panel | 878,690 | Right side panel |
| Panel_IHC | Panel | 874,747 | Front-right lower panel |
| Panel_Floor | Panel | 1,352,482 | Bottom floor panel |
| Rib_1 | Rib | 234,684 | Vertical rib at X=300 |
| Rib_2 | Rib | 308,777 | Vertical rib at X=480 |
| Slot_1 | Tool body | 253,163 | Slot cutter (keep for parametric refs) |
| Slot_2 | Tool body | 333,090 | Slot cutter (keep for parametric refs) |
| TableTop | Top | 14,930,691 | Rounded-rectangle tabletop |

---

## 12. Reconstruction Order (if rebuilding from scratch)

If you change the polyhedron shape (modify the face sketches), here is the order to rebuild:

1. **Modify face sketches** (Face1_Sketch through Floor_Sketch) to new geometry
2. **Recreate patches:** `fusion_create_patch` for each of the 8 sketches
3. **Stitch:** `fusion_stitch` all 8 patches (tolerance=0.1) -> watertight solid
4. **Recompute bisector planes:** For each of the 14 adjacent face pairs, `fusion_create_angled_plane` with `normal = normalize(N1 + N2)` and a point on the shared edge
5. **Shell:** `fusion_shell` the solid at `panel_thickness` (12.7mm), removing one face to open
6. **Extract panels:** For each of 8 faces: copy shell, then extrude-cut from each adjacent bisector plane (30mm cuts) to isolate the panel
7. **Ribs:** Compute interior cross-section polygons at rib X positions from panel inner-surface plane equations, sketch and extrude at 6.35mm
8. **Slots:** Extrude 6.85mm-wide slot bodies from rib sketches, boolean subtract from each panel
9. **Tabletop:** Offset plane at top Z + clearance, sketch rounded rectangle, extrude 30mm

### Critical lessons learned

- **Patch + Stitch is the only reliable method** for creating the solid polyhedron. Intersecting half-space prisms fails for non-convex shapes.
- **Shell automatically creates miter joints.** Don't try to compute miters manually.
- **Bisector normal = normalize(N1 + N2)**, NOT N1 - N2. The sum of outward normals gives the bisector.
- **Floor_Sketch has a broken referencePlane.** Always use `profile_index: 0` explicitly.
- **Slot/Combine tool bodies can't be deleted** without breaking parametric features. Hide them instead.
- **Circular 3-point arcs bulge wider** than the chord endpoints when sagitta > half-chord. Use elliptical splines for rounded-rectangle ends that stay within the width envelope.
- **On XZ planes**, sketch +Y maps to world -Z. Always verify with `suggest_sketch_coords` or `sketch_to_3d_coords`.
