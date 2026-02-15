# Sculptural Coffee Table Base - Design Plan

## Overview

This document defines the geometry and construction plan for a faceted, origami-like sculptural coffee table base. The form is a **polyhedron** with planar triangular faces creating a twisted, asymmetric appearance.

## Design Philosophy

Rather than using lofts or extrusions (which create curved or axis-aligned geometry), we define the form by:
1. **Vertices** - specific 3D points
2. **Faces** - triangular connections between vertices
3. **Solid** - the enclosed volume

This approach gives complete control over the faceted geometry.

---

## Geometry Definition

### Dimensions
- Base footprint: ~400mm x 350mm
- Height: 350mm
- Top surface: ~200mm x 180mm (smaller, offset from center)

### Vertices (8 total)

All coordinates in mm, origin at world center.

#### Floor Level (Z = 0)
| ID | X | Y | Z | Description |
|----|-----|-----|-----|-------------|
| V1 | -180 | -120 | 0 | Front-left base |
| V2 | 200 | -80 | 0 | Front-right base |
| V3 | 160 | 150 | 0 | Back-right base |
| V4 | -140 | 130 | 0 | Back-left base |

#### Mid Level (Z = 140) - Creates the "fold"
| ID | X | Y | Z | Description |
|----|-----|-----|-----|-------------|
| V5 | 40 | 20 | 140 | Central fold vertex |

#### Top Level (Z = 350)
| ID | X | Y | Z | Description |
|----|-----|-----|-----|-------------|
| V6 | -40 | 10 | 350 | Top front-left |
| V7 | 100 | 30 | 350 | Top front-right |
| V8 | 60 | 100 | 350 | Top back |

### Faces (10 total)

Each face is a triangle defined by 3 vertices (counter-clockwise winding for outward normal).

#### Bottom Face
| ID | Vertices | Description |
|----|----------|-------------|
| F1 | V1-V2-V3 | Bottom triangle 1 |
| F2 | V1-V3-V4 | Bottom triangle 2 |

*(Forms a quadrilateral base)*

#### Top Face
| ID | Vertices | Description |
|----|----------|-------------|
| F3 | V6-V8-V7 | Top triangle (table mount) |

#### Side Faces - Lower Section (floor to fold)
| ID | Vertices | Description |
|----|----------|-------------|
| F4 | V1-V5-V2 | Front face, lower |
| F5 | V2-V5-V3 | Right face, lower |
| F6 | V3-V5-V4 | Back face, lower |
| F7 | V4-V5-V1 | Left face, lower |

#### Side Faces - Upper Section (fold to top)
| ID | Vertices | Description |
|----|----------|-------------|
| F8 | V5-V6-V7 | Front face, upper |
| F9 | V5-V7-V8 | Right-back face, upper |
| F10 | V5-V8-V6 | Left-back face, upper |

---

## Visual Representation

```
Top View (looking down Z axis):

        V3(160,150)
          /\
         /  \
        /    \
  V4(-140,130)-------- V2(200,-80)
        \    /
         \  /
          \/
        V1(-180,-120)

              V8(60,100)
               /\
              /  \          (Top triangle, 
             /    \          smaller, offset)
        V6(-40,10)--V7(100,30)
        
               V5(40,20,140)  ← Fold vertex (mid-height)
```

```
Side View (looking down Y axis):

     Z
     |    V6----V7----V8  (Z=350)
     |        \ | /
     |         \|/
     |          V5        (Z=140, fold)
     |         /|\
     |        / | \
     |    V1----+----V2   (Z=0)
     +-------------------> X
```

---

## Construction Operations

### Phase 1: Create Vertices
```
for each vertex V1-V8:
    create_vertex(id, x, y, z)
```

### Phase 2: Create Faces
```
for each face F1-F10:
    create_triangular_face(face_id, vertex_a, vertex_b, vertex_c)
```

### Phase 3: Form Solid
```
create_solid_from_faces([F1, F2, F3, F4, F5, F6, F7, F8, F9, F10])
```

### Phase 4: Apply Material
```
apply_appearance(body_id, "Walnut")
```

---

## Required Tools

### New Tools Needed (not in current bridge)

| Tool | Purpose | Parameters |
|------|---------|------------|
| `create_vertex` | Define a 3D point | id, x, y, z |
| `create_triangular_face` | Create planar triangle from 3 vertices | face_id, v1, v2, v3 |
| `create_solid_from_faces` | Enclose faces into solid body | face_ids[], body_name |
| `create_angled_plane` | Construction plane from point + normal | point, normal |

### Existing Tools Needed

| Tool | Purpose |
|------|---------|
| `fusion_new_document` | Create design |
| `fusion_apply_appearance` | Material |
| `fusion_take_screenshot` | Visualization |
| `fusion_export` | Output |

---

## Alternative Implementation Strategy

If direct polyhedron creation is too complex, use **planar face extrusions**:

1. For each triangular face:
   - Create an angled construction plane through the 3 vertices
   - Sketch the triangle on that plane
   - Extrude with minimal thickness (0.1mm) as a "shell"
   
2. Boolean union all face shells

3. Apply shell/thicken operation to create solid walls

This is more indirect but uses existing Fusion operations with the addition of angled plane creation.

---

## Validation Criteria

- [ ] 8 vertices at correct positions
- [ ] 10 planar faces
- [ ] Closed solid (watertight)
- [ ] No self-intersections
- [ ] Stable on floor (V1-V4 coplanar at Z=0)
- [ ] Flat top surface (V6-V7-V8 coplanar at Z=350)

---

## File Outputs

| Format | Use |
|--------|-----|
| .f3d | Fusion native, parametric editing |
| .step | CAD interchange |
| .stl | 3D printing / CNC |
