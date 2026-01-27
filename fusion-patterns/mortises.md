# Pattern: Mortises (Recessed Pockets)

## What Are Mortises?

Rectangular or shaped pockets cut into wood to receive hardware (hinges, latches) or other parts (tenons). The hardware sits flush with or below the surface.

## Types of Mortises

### 1. Surface Mortise (Hinge Pocket)
Shallow rectangular recess on a face for hardware like hinges.
```
Surface:  ─────────────
         │░░░░░░░░░░░│   ← Shallow pocket
         ─────────────
```

### 2. Through Mortise
Cuts completely through the material.
```
         ─────────────
         │           │
         │    [ ]    │   ← Hole through entire thickness
         │           │
         ─────────────
```

### 3. Blind Mortise
Pocket that doesn't go all the way through.
```
         ─────────────
         │▓▓▓▓▓▓▓▓▓▓▓│   ← Solid back
         │           │   ← Open pocket
         ─────────────
```

## Implementation Using Primitive Tools

### Surface Mortise (Hinge Pocket)

**Goal:** Cut a rectangular pocket in a panel face.

**Steps:**

1. **Get target body bounds:**
```python
fusion_get_body_center(body_id="BackPanel")
# Returns: min=[0, 165.1, 0], max=[254, 177.8, 88.9]
```

2. **Create sketch on the target face:**
```python
# For a pocket on top face (max Z)
fusion_create_offset_plane(base_plane="xy", offset=88.9)
fusion_create_sketch(plane="Plane1", name="HingeMortise")
```

3. **Draw mortise outline:**
```python
# Hinge at 50mm from left edge, 25.4mm wide, 19mm deep (into Y)
fusion_draw_rectangle(sketch_id="HingeMortise",
    corner1=[50, 165.1],      # At back edge of panel
    corner2=[75.4, 184.1])    # Extends into panel
# Wait - that goes outside the panel! Need to cut INTO it.

# Correct: mortise on TOP of panel (XY plane at Z=max)
# Drawing hinge pocket that goes INTO the panel from back edge
fusion_draw_rectangle(sketch_id="HingeMortise",
    corner1=[50, 165.1],        # Back edge of panel
    corner2=[75.4, 177.8])      # To front of panel (full depth)
```

4. **Extrude cut:**
```python
fusion_finish_sketch(sketch_id="HingeMortise")
fusion_extrude(sketch_id="HingeMortise", 
    distance=3,           # Depth of hinge leaf (e.g., 3mm)
    direction="negative", # Cut down into -Z
    operation="cut",
    target_body="BackPanel")
```

### Through Mortise

Same process but distance equals or exceeds panel thickness:
```python
fusion_extrude(sketch_id="ThroughMortise",
    distance=12.7,         # Full panel thickness
    direction="negative",
    operation="cut",
    target_body="Panel")
```

### Blind Mortise

Partial depth cut:
```python
fusion_extrude(sketch_id="BlindMortise",
    distance=8,            # Less than panel thickness
    direction="negative",
    operation="cut",
    target_body="Panel")
```

## Mortise on Different Faces

### Top Face (XY plane at max Z)
```python
fusion_create_offset_plane(base_plane="xy", offset=body_max_z)
# Extrude: negative (into -Z)
```

### Bottom Face (XY plane at min Z)
```python
fusion_create_sketch(plane="xy", name="BottomMortise")
# Sketch at Z=0
# Extrude: positive (into +Z)
```

### Front Face (XZ plane at min Y)
```python
fusion_create_sketch(plane="xz", name="FrontMortise")
# Draw using negative Y for positive Z!
# Extrude: positive (into +Y)
```

### Back Face (XZ plane at max Y)
```python
fusion_create_offset_plane(base_plane="xz", offset=body_max_y)
# Extrude: negative (into -Y)
```

### Side Faces (YZ planes)
```python
# Left face at X=0
fusion_create_sketch(plane="yz", name="LeftMortise")
# Extrude: positive (into +X)

# Right face at X=max
fusion_create_offset_plane(base_plane="yz", offset=body_max_x)
# Extrude: negative (into -X)
```

## Example: Hinge Mortises for a Box Lid

**Setup:**
- Back panel at Y=[165.1, 177.8], Z=[12.7, 88.9]
- Need two hinge mortises, 50mm from each end
- Hinge dimensions: 25.4mm wide × 19mm deep × 3mm thick

**Steps:**

```python
# 1. Create sketch on top of back panel
fusion_create_offset_plane(base_plane="xy", offset=88.9)
fusion_create_sketch(plane="Plane1", name="HingeMortises")

# 2. Draw two mortise rectangles
# Left hinge: X=[50, 75.4], Y extends into panel
fusion_draw_rectangle(sketch_id="HingeMortises",
    corner1=[50, 158.8],       # 177.8 - 19 = 158.8 (front of mortise)
    corner2=[75.4, 177.8])     # Back edge

# Right hinge: X=[178.6, 204], same Y
fusion_draw_rectangle(sketch_id="HingeMortises",
    corner1=[178.6, 158.8],    # 254 - 50 - 25.4 = 178.6
    corner2=[204, 177.8])

# 3. Cut mortises
fusion_finish_sketch(sketch_id="HingeMortises")
fusion_extrude(sketch_id="HingeMortises",
    distance=3,
    direction="negative",
    operation="cut",
    target_body="BackPanel")
```

## Verification

After cutting mortise:
1. Body should still exist (cut didn't go through)
2. Volume should have decreased slightly
3. Visual inspection shows pocket

```python
fusion_get_body_center(body_id="Panel")
# Bounds unchanged (mortise is internal)
# Volume will be slightly less

fusion_take_screenshot(view="isometric")
# Visual check for pocket
```

## Common Mistakes

1. **Wrong face selection** - Creating sketch on wrong plane
2. **Wrong direction** - Extruding away from panel instead of into it
3. **Too deep** - Cutting through entire panel when blind mortise intended
4. **Coordinate confusion** - On XZ/YZ planes, remember coordinate inversions

## Quick Reference

| Mortise Location | Sketch Plane | Extrude Direction |
|-----------------|--------------|-------------------|
| Top face | XY at max Z | negative (-Z) |
| Bottom face | XY at min Z | positive (+Z) |
| Front face | XZ at min Y | positive (+Y) |
| Back face | XZ at max Y | negative (-Y) |
| Left face | YZ at min X | positive (+X) |
| Right face | YZ at max X | negative (-X) |






