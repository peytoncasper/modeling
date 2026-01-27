# Pattern: Coordinate Systems

## The Core Problem

Fusion 360 uses different coordinate systems for sketches vs 3D world space. Getting this wrong causes geometry to appear in wrong positions (often negative Z space).

## World Coordinate System

Standard right-hand coordinate system:
```
        +Z (up)
         │
         │
         │────── +Y (back)
        /
       /
      +X (right)
```

## Sketch Coordinate Systems by Plane

### XY Plane (horizontal, looking down)
```
Sketch X → World +X (right)
Sketch Y → World +Y (back)
```
✅ **No conversion needed** - sketch coords = world coords (for X,Y)

### XZ Plane (vertical, front view)
```
Sketch X → World +X (right)
Sketch Y → World -Z (DOWN!) ⚠️
```
⚠️ **INVERTED Y AXIS** - positive sketch Y goes DOWN in world

### YZ Plane (vertical, side view)  
```
Sketch X → World -Z (DOWN!) ⚠️
Sketch Y → World +Y (back)
```
⚠️ **INVERTED X AXIS** - positive sketch X goes DOWN in world

## Practical Examples

### Example 1: Draw panel from Z=0 to Z=50 on XZ plane

**WRONG (intuitive but incorrect):**
```
corner1 = [0, 0]      # Seems like Z=0
corner2 = [100, 50]   # Seems like Z=50
```
Result: Panel goes from Z=0 to Z=-50 (negative!)

**CORRECT:**
```
corner1 = [0, -50]    # Sketch Y=-50 → World Z=+50
corner2 = [100, 0]    # Sketch Y=0 → World Z=0
```
Result: Panel goes from Z=0 to Z=+50 ✓

### Example 2: Draw panel from Z=0 to Z=50 on YZ plane

**WRONG:**
```
corner1 = [0, 0]      
corner2 = [50, 100]   
```
Result: Panel goes from Z=0 to Z=-50 (negative!)

**CORRECT:**
```
corner1 = [-50, 0]    # Sketch X=-50 → World Z=+50
corner2 = [0, 100]    # Sketch X=0 → World Z=0
```

## The Easy Solution: Use `fusion_draw_rectangle_3d`

This tool accepts **world coordinates** and automatically converts to sketch coordinates:

```json
{
  "sketch_id": "MySketch",
  "world_corner1": [0, 0, 0],
  "world_corner2": [100, 50, 50]
}
```

The tool figures out what plane the sketch is on and converts appropriately.

## Verification

After drawing, verify position:

1. **Before extrusion:** Use `fusion_sketch_to_3d_coords` to see where sketch points will end up
2. **After extrusion:** Use `fusion_get_body_center` to verify body bounds

## Quick Reference

| I want geometry at World Z | On XZ plane, use Sketch Y | On YZ plane, use Sketch X |
|---------------------------|--------------------------|--------------------------|
| Z = 0                     | Y = 0                    | X = 0                    |
| Z = +50                   | Y = -50                  | X = -50                  |
| Z = +100                  | Y = -100                 | X = -100                 |
| Z = -50                   | Y = +50                  | X = +50                  |

**Rule of thumb:** Negate the Z value for the corresponding sketch axis.






