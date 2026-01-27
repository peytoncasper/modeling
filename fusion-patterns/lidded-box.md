# Pattern: Lidded Box with Overhang

## Overview

A classic box construction where the lid sits ON TOP of the box walls and overhangs on all sides. This creates a clean, elegant look suitable for keepsake boxes, jewelry boxes, and decorative storage.

## When to Use This Pattern

- Decorative/keepsake boxes where aesthetics matter more than mechanical strength
- Boxes with hinges and latches
- When you want a lid that "caps" the box
- Rustic or traditional woodworking styles

## When NOT to Use This Pattern

- High-stress applications (use box joints instead)
- Drawers or sliding components
- When maximum glue surface is needed

## Anatomy of a Lidded Box

```
        ┌─────────────────────────┐  ← Lid (overhangs all sides)
        │                         │
    ┌───┴─────────────────────┴───┐
    │                             │  ← Box walls
    │                             │
    │                             │
    └─────────────────────────────┘
              ↑ Bottom panel
```

## Key Dimensions

For a box with:
- Outer dimensions: Length × Width × Height
- Wall thickness: T
- Lid thickness: T_lid
- Lid overhang: O (typically 3-6mm per side)

**Lid dimensions:**
- Lid Length = Box Length + (2 × O)
- Lid Width = Box Width + (2 × O)

**Wall heights:**
- Front/Back/Left/Right walls: Height - T (bottom thickness)
- Walls sit ON TOP of the bottom panel

## Construction Order

### Phase 1: Bottom Panel
```
Sketch on XY plane at Z=0
Rectangle: [0, 0] to [Length, Width]
Extrude +Z by thickness
```

### Phase 2: Walls (sitting on bottom)

**Front Wall:**
```
Sketch on XZ plane at Y=0
World bounds: X=[0, Length], Z=[T, Height]
Extrude +Y by thickness
```

**Back Wall:**
```
Sketch on XZ offset plane at Y=Width-T
World bounds: X=[0, Length], Z=[T, Height]
Extrude +Y by thickness
```

**Left Wall:**
```
Sketch on YZ plane at X=0
World bounds: Y=[T, Width-T], Z=[T, Height]  ← Note: between front/back
Extrude +X by thickness
```

**Right Wall:**
```
Sketch on YZ offset plane at X=Length-T
World bounds: Y=[T, Width-T], Z=[T, Height]
Extrude +X by thickness
```

### Phase 3: Lid (separate body, overhanging)

```
Sketch on XY offset plane at Z=Height
Rectangle: [-O, -O] to [Length+O, Width+O]
Extrude +Z by lid thickness
Name body: "Lid"
```

## Corner Joint Options

### Option A: Butt Joints (Simplest)
Front/back walls span full length, left/right fit between them.
- Pros: Simple, clean look
- Cons: End grain visible on sides

### Option B: Mitered Corners
45° cuts at all corners.
- Pros: No end grain visible, elegant
- Cons: Requires precise cuts, weaker without splines

### Option C: Rabbeted Joints
Stepped cuts that interlock.
- Pros: Stronger than butt joints, hides end grain
- Cons: More complex

## Hardware Mortises

### Hinge Mortises (Back Edge)
```
Location: Back panel top edge, or lid bottom back edge
Typical hinge: 25-40mm wide, 1.5-2mm deep
Create sketch on top face of back panel
Rectangle at hinge positions
Extrude cut DOWN by mortise depth
```

### Latch Mortise (Front)
```
Location: Front panel, centered
Hasp catch typically needs:
- Plate recess: ~2mm deep
- Staple hole: through or partial depth
```

## Lid Attachment Options

### Piano Hinge (Full Width)
- Single long hinge across entire back edge
- Very strong, even weight distribution

### Butt Hinges (2-3 Hinges)
- Individual hinges at specific positions
- Typical positions: 20% and 80% from ends, or add center hinge

### Wooden Hinge (Traditional)
- Integral wooden hinge carved from lid/back
- Requires advanced techniques

## Example: 254mm × 178mm × 89mm Keepsake Box

```
Parameters:
- Length: 254mm
- Width: 178mm  
- Height: 89mm (box) + 12.7mm (lid) = 101.7mm total
- Thickness: 12.7mm
- Lid overhang: 6mm per side

Bottom: [0,0,0] to [254, 178, 12.7]

Front: X=[0, 254], Y=[0, 12.7], Z=[12.7, 89]
Back:  X=[0, 254], Y=[165.3, 178], Z=[12.7, 89]
Left:  X=[0, 12.7], Y=[12.7, 165.3], Z=[12.7, 89]
Right: X=[241.3, 254], Y=[12.7, 165.3], Z=[12.7, 89]

Lid: X=[-6, 260], Y=[-6, 184], Z=[89, 101.7]
```

## Common Mistakes

1. **Walls not sitting on bottom** - Walls should start at Z=thickness, not Z=0
2. **Side walls too long** - Left/right should fit BETWEEN front/back
3. **Lid not overhanging** - Lid should extend beyond box on all sides
4. **Forgetting hinge clearance** - Lid needs to rotate without hitting back wall

## Verification Checklist

- [ ] Bottom panel at Z=0
- [ ] All walls start at Z=thickness
- [ ] Front/back span full length
- [ ] Left/right fit between front/back
- [ ] Lid overhangs evenly on all sides
- [ ] Lid is separate body (not joined)
- [ ] Hinge mortises aligned between lid and back






