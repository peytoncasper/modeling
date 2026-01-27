# Pattern: Box Joints (Finger Joints)

## What Are Box Joints?

Interlocking rectangular fingers that connect two panels at a corner. One panel has "fingers" (protruding material), the mating panel has "slots" (removed material) that receive those fingers.

```
Panel A:  ████    ████    ████    ████
              ↘  ↙    ↘  ↙    ↘  ↙
Panel B:      ████    ████    ████
```

## The Core Concept

**Two panels, opposite patterns:**
- Panel A: Finger-Slot-Finger-Slot-Finger...
- Panel B: Slot-Finger-Slot-Finger-Slot...

When assembled, Panel A's fingers fill Panel B's slots and vice versa.

## Implementation Using Primitive Tools

### Step 1: Create Both Panels First (No Joints)

Build simple rectangular panels in correct positions:

```
Panel A: Base panel at Z=[0, 12.7]
Panel B: Front panel at Y=[0, 12.7], Z=[12.7, 88.9]
```

Use `fusion_draw_rectangle_3d` + `fusion_extrude` with `operation: "new_body"`.

### Step 2: Cut Slots in ONE Panel

Choose which panel receives slots. Create a sketch, draw slot rectangles, extrude cut.

**Example: Cut slots in Panel A (base) for Panel B's (front) fingers:**

```python
# 1. Create sketch on top of Panel A
fusion_create_offset_plane(base_plane="xy", offset=12.7)
fusion_create_sketch(plane="Plane1", name="BaseSlots")

# 2. Draw slot rectangles at alternating positions
# For a 254mm edge with 12.7mm fingers = 20 positions
# Slots at even positions: 0, 2, 4, 6, ...
fusion_draw_rectangle(sketch_id="BaseSlots", corner1=[0, 0], corner2=[12.7, 12.7])
fusion_draw_rectangle(sketch_id="BaseSlots", corner1=[25.4, 0], corner2=[38.1, 12.7])
# ... continue pattern

# 3. Finish and cut
fusion_finish_sketch(sketch_id="BaseSlots")
fusion_extrude(
    sketch_id="BaseSlots",
    distance=12.7,
    direction="negative",  # Cut down through panel
    operation="cut",
    target_body="BasePanel"
)
```

### Step 3: Add Fingers to OTHER Panel

The mating panel needs fingers that fill those slots. 

**CRITICAL: Fingers must TOUCH the existing panel body for JOIN to work!**

```python
# 1. Create sketch on same plane as panel's edge
fusion_create_sketch(plane="xz", name="FrontFingers")

# 2. Draw finger rectangles at SAME X positions as slots
# Fingers go from Z=0 to Z=12.7 (filling the slots)
fusion_draw_rectangle_3d(
    sketch_id="FrontFingers",
    world_corner1=[0, 0, 0],
    world_corner2=[12.7, 0, 12.7]
)
# ... continue pattern

# 3. Finish and JOIN to front panel
fusion_finish_sketch(sketch_id="FrontFingers")
fusion_extrude(
    sketch_id="FrontFingers",
    distance=12.7,
    direction="positive",  # Extrude into +Y where FrontPanel is
    operation="join",
    target_body="FrontPanel"
)
```

## Why JOIN Fails (Orphan Bodies)

The `join` operation ONLY works when new geometry **physically touches** the target body.

```
Target Body:     ████████████
                           ↑ Bottom at Z=12.7
                           
New Extrusion:            ████  ← Top must reach Z=12.7!
                           ↓ Z=0

✅ If top of finger reaches Z=12.7 → Joins to target
❌ If top of finger at Z=12.6 (gap!) → Creates orphan body
```

### Verification

After every JOIN operation:
1. Check response for `"warning": "JOIN_CREATED_ORPHAN_BODY"` 
2. Run `fusion_list_bodies` - count should NOT have increased
3. Run `fusion_get_body_center` on target body - bounds should have expanded

## Pattern Assignment Table

For a typical box with Base, Front, Back, Left, Right panels:

| Joint | Panel with SLOTS | Panel with FINGERS | Why |
|-------|------------------|-------------------|-----|
| Base↔Front | Base (front edge) | Front (bottom) | Front fingers go down into base |
| Base↔Back | Base (back edge) | Back (bottom) | Back fingers go down into base |
| Base↔Left | Base (left edge) | Left (bottom) | Left fingers go down into base |
| Base↔Right | Base (right edge) | Right (bottom) | Right fingers go down into base |
| Front↔Left | Front (left edge) | Left (front edge) | Left fingers go into front |
| Front↔Right | Front (right edge) | Right (front edge) | Right fingers go into front |
| Back↔Left | Back (left edge) | Left (back edge) | Left fingers go into back |
| Back↔Right | Back (right edge) | Right (back edge) | Right fingers go into back |

## Calculating Finger Positions

```
edge_length = 254mm
finger_width = 12.7mm
num_positions = edge_length / finger_width = 20

Slot positions (even indices): 0, 2, 4, 6, 8, 10, 12, 14, 16, 18
  → X = [0, 12.7], [25.4, 38.1], [50.8, 63.5], ...

Finger positions (same as slots - they interlock):
  → Same X positions, but on the MATING panel
```

## Complete Checklist

Before starting:
- [ ] Both panels exist and are positioned correctly
- [ ] Know which panel gets slots vs fingers
- [ ] Calculated finger positions along edge

For slot cutting:
- [ ] Sketch plane at top surface of receiving panel
- [ ] Rectangles at correct positions
- [ ] Extrude direction goes INTO the panel (usually negative)
- [ ] Operation is "cut"
- [ ] target_body is the receiving panel

For finger joining:
- [ ] Sketch plane where fingers will start (touching mating panel)
- [ ] Rectangles at SAME positions as slots
- [ ] Finger height matches slot depth
- [ ] Extrude direction goes TOWARD the mating panel body
- [ ] Operation is "join" 
- [ ] target_body is the mating panel

After completion:
- [ ] Body count unchanged
- [ ] No orphan body warning
- [ ] Visual verification






