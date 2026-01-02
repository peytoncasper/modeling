# Pattern: Join Operations (Boolean Operations)

## Overview

Fusion 360's extrude operation supports four modes:
- `new_body` - Creates a separate body
- `join` - Merges new geometry INTO an existing body
- `cut` - Removes geometry FROM an existing body
- `intersect` - Keeps only the overlapping volume

## The Critical Rule

**JOIN and CUT only work when geometry TOUCHES the target body.**

```
✅ Touching (works):
Target:  ████████████
New:              ████  ← Shares boundary

❌ Gap (creates orphan):
Target:  ████████████
                      (gap)
New:                  ████  ← No contact
```

## Operation: JOIN

**Purpose:** Add material to an existing body.

**Requirements:**
1. New geometry must touch OR intersect target body
2. Both must be in the same component

**Example - Adding a finger to a panel:**
```
Panel at Y=[0, 12.7], Z=[12.7, 88.9]

Finger sketch at Y=0, Z=[0, 12.7]
Finger extrudes in +Y direction by 12.7mm

The finger's top (Z=12.7) touches panel's bottom (Z=12.7) ✓
The finger extrudes INTO the panel's Y range ✓
```

**Failure Detection:**
The MCP returns `"warning": "JOIN_CREATED_ORPHAN_BODY"` if join fails.

## Operation: CUT

**Purpose:** Remove material from an existing body.

**Requirements:**
1. Cut geometry must intersect target body
2. Extrude direction must go THROUGH the target

**Example - Cutting a slot:**
```
Panel at Z=[0, 12.7]

Slot sketch at Z=12.7 (top surface of panel)
Slot extrudes in -Z direction by 12.7mm

Cut goes from Z=12.7 down to Z=0 (through entire panel) ✓
```

**Common Mistake:** Cutting in wrong direction
```
Sketch at Z=12.7
Extrude +Z by 12.7mm  ← Goes UP, misses the panel!
```

## Operation: INTERSECT

**Purpose:** Keep only the volume where bodies overlap.

Less commonly used for woodworking. Mainly for complex geometric operations.

## Diagnosing Failures

### Symptom: Body count increased after JOIN

**Cause:** New geometry didn't touch target body.

**Debug steps:**
1. Get target body bounds: `fusion_get_body_center(body_id="TargetPanel")`
2. Check new body bounds from response
3. Look for gap between them

**Example failure:**
```json
{
  "orphan_body_bounds": {"min": [0, 0, 0], "max": [12.7, 12.7, 12.6]},
  "target_body_bounds": {"min": [0, 0, 12.7], "max": [254, 12.7, 88.9]}
}
```
Gap: Orphan max Z=12.6, Target min Z=12.7 → 0.1mm gap!

### Symptom: Cut didn't remove anything

**Cause:** Cut geometry missed the target body.

**Debug steps:**
1. Verify sketch is on correct plane (touching target surface)
2. Verify extrude direction goes INTO target
3. Verify distance is sufficient to pass through

## Best Practices

### 1. Always know your bounds first

Before any join/cut:
```
fusion_get_body_center(body_id="TargetPanel")
```
Returns `min` and `max` coordinates - use these to position your sketch.

### 2. Position sketch on contact surface

For JOIN: Sketch should be ON the face where you want to add material.
For CUT: Sketch should be ON the face you're cutting into.

### 3. Use the right direction

| Target surface | Extrude direction |
|---------------|-------------------|
| Top of panel (max Z) | negative (into -Z) |
| Bottom of panel (min Z) | positive (into +Z) |
| Front of panel (min Y) | positive (into +Y) |
| Back of panel (max Y) | negative (into -Y) |
| Left of panel (min X) | positive (into +X) |
| Right of panel (max X) | negative (into -X) |

### 4. Verify after operation

```
# Check body count didn't increase
fusion_list_bodies(component="MyComponent")

# Check target body expanded correctly  
fusion_get_body_center(body_id="TargetPanel")
```

## Quick Reference

| I want to... | Operation | Sketch location | Extrude into |
|-------------|-----------|-----------------|--------------|
| Add material on top | join | target's max Z face | -Z |
| Add material on bottom | join | target's min Z face | +Z |
| Add material on front | join | target's min Y face | +Y |
| Remove from top | cut | target's max Z face | -Z |
| Remove from bottom | cut | target's min Z face | +Z |
| Remove from front | cut | target's min Y face | +Y |




