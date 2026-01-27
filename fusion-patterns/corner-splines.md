# Pattern: Corner Splines (Structural Corner Braces)

## What Are Corner Splines?

Triangular or rectangular blocks that sit in the internal corners of a box/carcass to:
1. **Align panels** during assembly (registration feature)
2. **Reinforce corners** with mechanical fasteners (screws)
3. **Hide screw heads** inside the corner where they won't be visible
4. **Distribute stress** across the corner joint

```
Top view of corner:
    
    ┌─────────────┐
    │             │
    │   ┌─────┐   │  ← Corner spline with dados
    │   │▓▓▓▓▓│   │     (shaded = spline body)
    │   └─────┘   │
    │             │
    └─────────────┘
    
Side panels      Triangular spline
                 (fits into 3mm dados)
```

## Types of Corner Splines

### 1. Triangular Spline (Most Common)
45° triangle in the corner, space-efficient:
```
Plan view:
    │ Panel
    │╲
    │ ╲ Spline
    │  ╲
    ────┴──
     Panel
```

### 2. Square Spline
Full square corner block, more material:
```
Plan view:
    │ Panel
    │▓▓
    │▓▓ Spline
    ────┴─
     Panel
```

### 3. Rounded Spline
Curved face for aesthetics or clearance:
```
Plan view:
    │ Panel
    │╭─
    ││  Spline
    │╰─
    ────┴─
     Panel
```

## Corner Identification in a Carcass

For a standard rectangular carcass with 4 vertical corners:

```
Top-down view (looking at -Z):

    Front (Y=0)
    
(0,0)   +X→    (X_max,0)
  ┌──────────────┐
  │ FL        FR │
 +Y              │
  │              │
  │ BL        BR │
  └──────────────┘
(0,Y_max)    (X_max,Y_max)

    Back (Y=Y_max)

FL = Front-Left corner
FR = Front-Right corner  
BR = Back-Right corner
BL = Back-Left corner
```

## Implementation: Triangular Corner Spline

### Phase 1: Get Carcass Information

**Goal:** Understand the carcass geometry before creating splines.

```python
# 1. Get model summary to understand overall structure
fusion_get_model_summary()

# 2. Get specific panel bodies
fusion_list_bodies(component="Carcass")

# 3. Get bounds of key panels
fusion_get_body_center(body_id="Left Panel")
fusion_get_body_center(body_id="Right Panel")
fusion_get_body_center(body_id="Bottom Panel")
fusion_get_body_center(body_id="Top Panel")
```

**Extract key dimensions:**
- `X_inner_min` = Left panel inner face (X_max of left panel)
- `X_inner_max` = Right panel inner face (X_min of right panel)
- `Y_inner_min` = Front panel inner face (Y_max of front panel, if exists)
- `Y_inner_max` = Back panel inner face (Y_min of back panel, if exists)
- `Z_bottom` = Top of bottom panel (Z_max)
- `Z_top` = Bottom of top panel (Z_min)

### Phase 2: Calculate Spline Dimensions

**Parameters:**
```python
dado_depth = 3        # How deep spline sits into panel (typically 3-6mm)
spline_size = 25      # Base size of triangle (e.g., 25mm × 25mm)
screw_hole_diameter = 3.5    # Pilot hole for #6 wood screw
screw_positions = []  # List of Z heights for screws
```

**Corner positions:**
```python
# Front-Left (FL) corner - touching both left and front panels
FL_corner = {
    "x": X_inner_min + dado_depth,
    "y": Y_inner_min + dado_depth,
    "z_range": [Z_bottom, Z_top]
}

# Front-Right (FR) corner
FR_corner = {
    "x": X_inner_max - dado_depth,
    "y": Y_inner_min + dado_depth,
    "z_range": [Z_bottom, Z_top]
}

# Back-Right (BR) corner
BR_corner = {
    "x": X_inner_max - dado_depth,
    "y": Y_inner_max - dado_depth,
    "z_range": [Z_bottom, Z_top]
}

# Back-Left (BL) corner
BL_corner = {
    "x": X_inner_min + dado_depth,
    "y": Y_inner_max - dado_depth,
    "z_range": [Z_bottom, Z_top]
}
```

### Phase 3: Create Spline Body

**Steps for Front-Left corner (repeat for all 4 corners):**

```python
# 1. Create sketch on XY plane at bottom of carcass
fusion_create_sketch(plane="xy", name="FL_Spline_Profile")

# 2. Draw right-triangle profile
# Triangle points counter-clockwise from origin
p1 = [FL_corner["x"], FL_corner["y"]]  # Corner point
p2 = [FL_corner["x"] + spline_size, FL_corner["y"]]  # Along X
p3 = [FL_corner["x"], FL_corner["y"] + spline_size]  # Along Y

fusion_draw_line(sketch_id="FL_Spline_Profile", 
    start=p1, end=p2)
fusion_draw_line(sketch_id="FL_Spline_Profile",
    start=p2, end=p3)
fusion_draw_line(sketch_id="FL_Spline_Profile",
    start=p3, end=p1)

fusion_finish_sketch(sketch_id="FL_Spline_Profile")

# 3. Extrude to create spline body
height = FL_corner["z_range"][1] - FL_corner["z_range"][0]
fusion_extrude(sketch_id="FL_Spline_Profile",
    distance=height,
    direction="positive",
    operation="new_body",
    body_name="FL_Corner_Spline")
```

### Phase 4: Add Dados (Insets for Panel Registration)

**Goal:** Cut 3mm channels on both faces so spline sits flush in panel dados.

```python
# Get the spline body bounds to find faces
fusion_get_body_center(body_id="FL_Corner_Spline")
# Returns min/max - we need the two flat faces

# Dado on X face (parallel to YZ plane, facing left panel)
# This face is at X = X_inner_min + dado_depth

# 1. Create offset plane at the face
fusion_create_offset_plane(base_plane="yz", 
    offset=FL_corner["x"])

fusion_create_sketch(plane="Plane1", name="FL_Dado_X")

# 2. Draw rectangle for dado on this face
# Use draw_rectangle_3d to avoid coordinate confusion
fusion_draw_rectangle_3d(sketch_id="FL_Dado_X",
    world_corner1=[FL_corner["x"], FL_corner["y"], Z_bottom],
    world_corner2=[FL_corner["x"], FL_corner["y"] + spline_size, Z_top])

fusion_finish_sketch(sketch_id="FL_Dado_X")

# 3. Cut dado into spline (direction toward panel)
fusion_extrude(sketch_id="FL_Dado_X",
    distance=dado_depth,
    direction="negative",  # Into -X (toward left panel)
    operation="cut",
    target_body="FL_Corner_Spline")

# Dado on Y face (parallel to XZ plane, facing front panel)
# This face is at Y = Y_inner_min + dado_depth

fusion_create_offset_plane(base_plane="xz",
    offset=FL_corner["y"])

fusion_create_sketch(plane="Plane2", name="FL_Dado_Y")

fusion_draw_rectangle_3d(sketch_id="FL_Dado_Y",
    world_corner1=[FL_corner["x"], FL_corner["y"], Z_bottom],
    world_corner2=[FL_corner["x"] + spline_size, FL_corner["y"], Z_top])

fusion_finish_sketch(sketch_id="FL_Dado_Y")

fusion_extrude(sketch_id="FL_Dado_Y",
    distance=dado_depth,
    direction="negative",  # Into -Y (toward front panel)
    operation="cut",
    target_body="FL_Corner_Spline")
```

### Phase 5: Add Screw Holes

**Goal:** Create pilot holes for screws at strategic heights.

```python
# Calculate screw positions (typically 1/3 and 2/3 height, or every 150-200mm)
height = Z_top - Z_bottom
if height <= 200:
    # Two screws
    screw_positions = [
        Z_bottom + height * 0.33,
        Z_bottom + height * 0.67
    ]
elif height <= 400:
    # Three screws  
    screw_positions = [
        Z_bottom + height * 0.25,
        Z_bottom + height * 0.50,
        Z_bottom + height * 0.75
    ]
else:
    # Four or more screws (every 150mm)
    num_screws = int(height / 150) + 1
    screw_positions = [Z_bottom + i * height / (num_screws - 1) 
                      for i in range(num_screws)]

# Calculate center point of spline for hole placement
center_x = FL_corner["x"] + spline_size / 2
center_y = FL_corner["y"] + spline_size / 2

# Create holes at each position
for i, z_pos in enumerate(screw_positions):
    # Create offset plane at this Z height
    fusion_create_offset_plane(base_plane="xy", offset=z_pos)
    
    fusion_create_sketch(plane=f"Plane{3+i}", 
        name=f"FL_Screw_{i}")
    
    # Draw circle at spline center
    fusion_draw_circle(sketch_id=f"FL_Screw_{i}",
        center=[center_x, center_y],
        radius=screw_hole_diameter / 2)
    
    fusion_finish_sketch(sketch_id=f"FL_Screw_{i}")
    
    # Cut hole through spline (goes both directions from center)
    fusion_extrude(sketch_id=f"FL_Screw_{i}",
        distance=spline_size * 1.5,  # Ensure it goes through
        direction="symmetric",       # Cut both +Z and -Z
        operation="cut",
        target_body="FL_Corner_Spline")
```

### Phase 6: Add Dados to Panels

**Goal:** Cut receiving dados in the panels themselves.

```python
# Left panel dado for FL corner
# This dado runs vertically on the inner face of left panel

# 1. Get left panel bounds
fusion_get_body_center(body_id="Left Panel")
# Let's say it returns max X = 19 (that's the inner face)

# 2. Create sketch on inner face of left panel
fusion_create_offset_plane(base_plane="yz", offset=19)
fusion_create_sketch(plane="PlaneN", name="Left_FL_Dado")

# 3. Draw dado rectangle (vertical channel)
fusion_draw_rectangle_3d(sketch_id="Left_FL_Dado",
    world_corner1=[19, FL_corner["y"] - dado_depth, Z_bottom],
    world_corner2=[19, FL_corner["y"] - dado_depth + spline_size, Z_top])

fusion_finish_sketch(sketch_id="Left_FL_Dado")

# 4. Cut dado into panel
fusion_extrude(sketch_id="Left_FL_Dado",
    distance=dado_depth,
    direction="positive",  # Into +X (into the panel)
    operation="cut",
    target_body="Left Panel")

# Front panel dado for FL corner (if front panel exists)
# Similar process but on XZ plane
```

## Corner Orientation Guide

Each corner has a different orientation for the triangle:

```python
# Front-Left (FL): Triangle opens toward back-right
points = [
    [x, y],              # Corner point
    [x + size, y],       # Right along X+
    [x, y + size]        # Back along Y+
]

# Front-Right (FR): Triangle opens toward back-left  
points = [
    [x, y],              # Corner point
    [x - size, y],       # Left along X-
    [x, y + size]        # Back along Y+
]

# Back-Right (BR): Triangle opens toward front-left
points = [
    [x, y],              # Corner point
    [x - size, y],       # Left along X-
    [x, y - size]        # Front along Y-
]

# Back-Left (BL): Triangle opens toward front-right
points = [
    [x, y],              # Corner point
    [x + size, y],       # Right along X+
    [x, y - size]        # Front along Y-
]
```

## Dado Direction Reference

When cutting dados on panels for spline insertion:

| Panel | Face | Plane | Dado Extrude Direction |
|-------|------|-------|------------------------|
| Left Panel | Inner (max X) | YZ offset | positive (+X into panel) |
| Right Panel | Inner (min X) | YZ offset | negative (-X into panel) |
| Front Panel | Inner (max Y) | XZ offset | positive (+Y into panel) |
| Back Panel | Inner (min Y) | XZ offset | negative (-Y into panel) |

## Verification Steps

After creating each spline:

```python
# 1. Check body was created
fusion_list_bodies(component="Carcass")
# Should see new spline body

# 2. Check spline dimensions
fusion_get_body_center(body_id="FL_Corner_Spline")
# Verify position and size are correct

# 3. Visual inspection
fusion_set_view(preset="isometric")
fusion_take_screenshot(view="current")

# 4. Check screw holes exist
fusion_list_faces(body_id="FL_Corner_Spline", 
    filter={"type": "cylindrical"})
# Should show cylindrical faces for holes
```

## Common Mistakes

### 1. Wrong Dado Depth
**Problem:** Spline doesn't fit or is too loose.
**Solution:** Use consistent `dado_depth` parameter (3-6mm typical). Too shallow = tight fit, too deep = weak joint.

### 2. Spline Outside Carcass Bounds
**Problem:** Spline extends beyond panel dimensions.
**Solution:** Always use `X_inner_min/max` and `Y_inner_min/max` from panel inner faces, not outer dimensions.

### 3. Screw Holes Don't Go Through
**Problem:** Holes are blind, can't insert screws.
**Solution:** Use `direction="symmetric"` with distance > spline thickness to ensure through-holes.

### 4. Dados on Wrong Panel Face
**Problem:** Dado cut on outer face instead of inner face.
**Solution:** Always work from panel inner face (the max or min coordinate that faces the interior).

### 5. Triangle Pointing Wrong Direction
**Problem:** Hypotenuse faces inward instead of corner faces outward.
**Solution:** Use the corner orientation guide above - corner point should be at the actual corner coordinate.

### 6. Coordinate Confusion on Vertical Sketches
**Problem:** Dados positioned incorrectly in Z dimension.
**Solution:** Use `fusion_draw_rectangle_3d` with world coordinates to avoid XZ/YZ plane inversions.

## Alternative: Using Primitive Box and Boolean Operations

For simpler square splines:

```python
# 1. Create square spline body
fusion_create_box(
    corner1=[FL_corner["x"] - dado_depth, 
             FL_corner["y"] - dado_depth, 
             Z_bottom],
    corner2=[FL_corner["x"] + spline_size,
             FL_corner["y"] + spline_size,
             Z_top],
    name="FL_Square_Spline")

# 2. Create dado cutters as boxes
fusion_create_box(
    corner1=[FL_corner["x"] - dado_depth,
             FL_corner["y"],
             Z_bottom],
    corner2=[FL_corner["x"],
             FL_corner["y"] + spline_size,
             Z_top],
    name="FL_Dado_Cutter_X")

# 3. Boolean subtract
fusion_boolean(operation="subtract",
    target_body="FL_Square_Spline",
    tool_bodies=["FL_Dado_Cutter_X"],
    keep_tools=False)
```

This approach is faster but less precise for complex shapes.

## Design Variations

### Variation 1: Countersunk Screw Holes
Add countersink for flat-head screws:

```python
# After creating pilot hole, add countersink
fusion_draw_circle(sketch_id=f"FL_Countersink_{i}",
    center=[center_x, center_y],
    radius=countersink_diameter / 2)

fusion_extrude(sketch_id=f"FL_Countersink_{i}",
    distance=countersink_depth,
    direction="negative",  # From top surface
    operation="cut",
    target_body="FL_Corner_Spline")
```

### Variation 2: Rounded Front Face
For aesthetic or clearance reasons:

```python
# Instead of straight triangle hypotenuse, use arc
fusion_draw_arc_3point(sketch_id="FL_Spline_Profile",
    start=[FL_corner["x"] + spline_size, FL_corner["y"]],
    mid=[FL_corner["x"] + spline_size*0.7, FL_corner["y"] + spline_size*0.7],
    end=[FL_corner["x"], FL_corner["y"] + spline_size])
```

### Variation 3: Tapered Spline
Smaller at top for easier assembly:

```python
# Create two profiles at top and bottom, then loft between them
# Bottom profile: full size triangle
# Top profile: 90% size triangle (offset inward)
fusion_loft(sketch_ids=["Bottom_Profile", "Top_Profile"])
```

## Integration with Parametric Design

If your carcass uses parameters:

```python
# Add spline-specific parameters
fusion_create_parameter(name="corner_spline_size", value=25, unit="mm")
fusion_create_parameter(name="corner_dado_depth", value=3, unit="mm")
fusion_create_parameter(name="corner_screw_diameter", value=3.5, unit="mm")

# Reference in dimensions
# When creating spline, use parameter expressions:
# spline_size = "corner_spline_size"
# dado_depth = "corner_dado_depth"
```

## Quick Reference: Process Summary

```
1. Get carcass panel bounds (get_body_center for all panels)
2. Calculate inner dimensions (X_inner, Y_inner, Z_bottom, Z_top)
3. Calculate corner positions with dado offset
4. For each of 4 corners:
   a. Create triangle profile sketch on XY plane
   b. Extrude to full height (new_body)
   c. Cut dados on both faces (2 cuts per spline)
   d. Cut screw holes at calculated heights
5. Cut receiving dados in panels (1 dado per adjacent panel)
6. Verify dimensions and visual appearance
```

## Manufacturing Notes

When actually building:
- Cut panel dados BEFORE assembly (table saw or router)
- Dry-fit splines to test fit (should slide in with light pressure)
- Apply glue to dado faces during assembly
- Insert splines and secure with screws
- Screws pull panels tight against spline dados for perfect alignment

The 3mm dado depth provides strong registration without weakening panels significantly.





