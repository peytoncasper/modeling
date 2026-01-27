# Pattern: Panel Construction

## Overview

Building boxes, furniture, and enclosures from flat panels. This pattern covers positioning panels in 3D space correctly.

## Coordinate Convention

For a box sitting on the ground:
```
Origin [0,0,0] = Front-Left-Bottom corner
+X = Right (length)
+Y = Back (depth/width)  
+Z = Up (height)
```

## The Six Panel Types

### 1. Bottom Panel (XY plane)
```
Sits at Z=0, extends in X and Y
Sketch on: XY plane
Extrude: +Z by thickness
```

### 2. Top Panel (XY plane)
```
Sits at Z=height-thickness
Sketch on: XY offset plane at Z=height-thickness
Extrude: +Z by thickness
```

### 3. Front Panel (XZ plane)
```
Sits at Y=0, extends in X and Z
Sketch on: XZ plane at Y=0
Extrude: +Y by thickness
```

### 4. Back Panel (XZ plane)
```
Sits at Y=depth-thickness
Sketch on: XZ offset plane at Y=depth-thickness  
Extrude: +Y by thickness
```

### 5. Left Panel (YZ plane)
```
Sits at X=0, extends in Y and Z
Sketch on: YZ plane at X=0
Extrude: +X by thickness
```

### 6. Right Panel (YZ plane)
```
Sits at X=width-thickness
Sketch on: YZ offset plane at X=width-thickness
Extrude: +X by thickness
```

## Example: Building a Box

Parameters:
- Length (X): 200mm
- Depth (Y): 150mm
- Height (Z): 100mm
- Thickness: 12mm

### Bottom Panel
```python
# Sketch on XY at Z=0, draw full footprint
fusion_create_sketch(plane="xy", name="BottomPanel")
fusion_draw_rectangle(sketch_id="BottomPanel", 
    corner1=[0, 0], corner2=[200, 150])
fusion_finish_sketch(sketch_id="BottomPanel")
fusion_extrude(sketch_id="BottomPanel", distance=12, 
    direction="positive", operation="new_body", body_name="Bottom")
```
**Result:** Body at X=[0,200], Y=[0,150], Z=[0,12]

### Front Panel
```python
# Sketch on XZ at Y=0
# IMPORTANT: Use draw_rectangle_3d to avoid coordinate confusion!
fusion_create_sketch(plane="xz", name="FrontPanel")
fusion_draw_rectangle_3d(sketch_id="FrontPanel",
    world_corner1=[0, 0, 12],    # Start above bottom panel
    world_corner2=[200, 0, 100]) # Go to full height
fusion_finish_sketch(sketch_id="FrontPanel")
fusion_extrude(sketch_id="FrontPanel", distance=12,
    direction="positive", operation="new_body", body_name="Front")
```
**Result:** Body at X=[0,200], Y=[0,12], Z=[12,100]

### Back Panel
```python
# Sketch on XZ offset plane at Y=150-12=138
fusion_create_offset_plane(base_plane="xz", offset=138)
fusion_create_sketch(plane="Plane1", name="BackPanel")
fusion_draw_rectangle_3d(sketch_id="BackPanel",
    world_corner1=[0, 138, 12],
    world_corner2=[200, 138, 100])
fusion_finish_sketch(sketch_id="BackPanel")
fusion_extrude(sketch_id="BackPanel", distance=12,
    direction="positive", operation="new_body", body_name="Back")
```
**Result:** Body at X=[0,200], Y=[138,150], Z=[12,100]

### Left Panel
```python
# Sketch on YZ at X=0
# Left panel sits BETWEEN front and back panels
fusion_create_sketch(plane="yz", name="LeftPanel")
fusion_draw_rectangle_3d(sketch_id="LeftPanel",
    world_corner1=[0, 12, 12],     # Inset from front
    world_corner2=[0, 138, 100])   # Inset from back
fusion_finish_sketch(sketch_id="LeftPanel")
fusion_extrude(sketch_id="LeftPanel", distance=12,
    direction="positive", operation="new_body", body_name="Left")
```
**Result:** Body at X=[0,12], Y=[12,138], Z=[12,100]

### Right Panel
```python
fusion_create_offset_plane(base_plane="yz", offset=188)  # 200-12
fusion_create_sketch(plane="Plane2", name="RightPanel")
fusion_draw_rectangle_3d(sketch_id="RightPanel",
    world_corner1=[188, 12, 12],
    world_corner2=[188, 138, 100])
fusion_finish_sketch(sketch_id="RightPanel")
fusion_extrude(sketch_id="RightPanel", distance=12,
    direction="positive", operation="new_body", body_name="Right")
```
**Result:** Body at X=[188,200], Y=[12,138], Z=[12,100]

## Panel Overlap Strategies

### Strategy 1: Front/Back Full Width (Common for boxes)
```
Front/Back: Full X extent (0 to length)
Left/Right: Inset by thickness (thickness to length-thickness)
```

### Strategy 2: Left/Right Full Depth (Common for cabinets)
```
Left/Right: Full Y extent (0 to depth)
Front/Back: Inset by thickness
```

### Strategy 3: All Panels Inset (For mitered/rabbeted joints)
```
All panels: Inset from edges
Requires additional joinery
```

## Verification

After each panel:
```python
fusion_get_body_center(body_id="PanelName")
```

Check that:
- All coordinates are in expected ranges
- No overlap conflicts between panels
- Gaps are intentional (for joinery) or absent (for butt joints)

## Common Mistakes

1. **Forgetting thickness offset** - Side panels should start at Z=thickness, not Z=0
2. **Wrong plane** - Using XY when you need XZ
3. **Coordinate inversion** - Not accounting for XZ/YZ coordinate flips
4. **Overlapping panels** - Front/back overlapping with left/right at corners

## Quick Reference

| Panel | Plane | Sketch Bounds (XY) | Extrude |
|-------|-------|-------------------|---------|
| Bottom | XY | Full footprint | +Z |
| Top | XY offset | Full footprint | +Z |
| Front | XZ | Full width, wall height | +Y |
| Back | XZ offset | Full width, wall height | +Y |
| Left | YZ | Inset depth, wall height | +X |
| Right | YZ offset | Inset depth, wall height | +X |






