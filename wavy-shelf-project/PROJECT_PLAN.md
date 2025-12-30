# Curved Wall Shelf - Project Plan v20.0

## CRITICAL: Coordinate System (from Blueprint)

```
                    WALL (Y=0)
                      │
    ┌─────────────────┴─────────────────┐
    │         CURVED MOUNT              │  Y = 0 to 15
    │    (screws go INTO wall, -Y)      │
    ├───────────────────────────────────┤
    │                                   │
    │     SHELF BACK (thick)            │  Y = 15 to 50
    │                                   │
    │         BOWL CAVITY               │  Y = 50 to 150
    │                                   │
    │     FRONT LIP                     │  Y = 150 to 200
    │                                   │
    └───────────────────────────────────┘
              INTO ROOM (Y = 200)
              
X = left/right along wall (±400mm)
Y = depth into room from wall (0 to 200mm)  
Z = height (varies with curve, ~0 to 100mm)
```

## Overview
A curved floating wall shelf with a bowl/trough cavity. Organic, sculptural design with:
- Thick elevated back at wall
- Deep bowl cavity in center  
- Front lip with defined thickness (8-10mm, not knife-edge)
- Flat end planes extending almost to front lip
- **Curved mount** between wall and shelf - holes go INTO wall (negative Y direction)

### Design Intent - Based on Blueprint
The shelf has:
- **Top View**: Kidney/bean shape - straight back edge, curved front
- **Front Elevation**: Bowl shape - ends curve UP, center dips DOWN
- **Side View**: Raised back against wall, curves forward with front lip

```
FRONT ELEVATION (looking at shelf from front):

       ╭─────╮                     ╭─────╮
      ╱       ╲                   ╱       ╲
     │         ╲                 ╱         │
     │          ╲_______________╱          │  ← Bowl shape
     │                                     │    (ends HIGH, center LOW)
     └─────────────────────────────────────┘
     
     ◄──────────── 800mm ────────────────►

RIGHT SIDE VIEW:

     WALL
       │   ╭────╮ ← Raised back (wall side)
       │  ╱      ╲
       │ │        ╲
       │ │         ╲___╱ ← Front lip curves up
       │ │              │
       │  ╲____________╱
       │
       │ ◄── 200mm ──►

TOP VIEW:

     ╭───────────────────────────────────╮  ← Front edge (curved)
    ╱                                     ╲
   │                                       │
   │            SHELF SURFACE              │  ← 200mm depth at center
   │                                       │
    ╲_____________________________________╱  ← Back edge (at wall)
    
    ◄────────────── 800mm ────────────────►
```

---

## Dimensions (from Blueprint)

| Parameter | Metric | Imperial | Notes |
|-----------|--------|----------|-------|
| Overall Length | 800mm | 31.5" | End to end |
| Max Depth | 200mm | 7.9" | How far it projects from wall |
| Max Height | 100mm | 3.9" | At the raised ends |
| Center Height | ~30-50mm | ~1.5" | Dipped trough area |
| Wall Thickness | ~15-25mm | ~0.8" | Thin-walled bowl |

---

## Raw Materials

### Primary Stock
| Material | Dimensions | Qty | Notes |
|----------|------------|-----|-------|
| Solid Oak | 850mm × 220mm × 110mm | 1 | CNC carved or laminated |

### Mounting
| Item | Qty | Notes |
|------|-----|-------|
| Hidden keyhole brackets | 2 | Recessed in back |
| Wall screws | 2 | Into studs |

---

## Fusion 360 Build Steps (Exact MCP Commands Used)

### Step 1: Create Offset Planes

```
fusion_create_offset_plane(base_plane="yz", offset=-400)  → Plane6 (left end)
fusion_create_offset_plane(base_plane="yz", offset=400)   → Plane7 (right end)
# Center uses the standard YZ plane at X=0
```

### Step 2: Create Left End Profile

```
fusion_create_sketch(plane="Plane6", name="LeftEndProfile")

# Top spline (positioned HIGH - ends curve up MORE)
fusion_draw_spline(sketch_id="LeftEndProfile", 
    points=[[0, 105], [15, 102], [30, 96], [40, 88]])

# Bottom spline
fusion_draw_spline(sketch_id="LeftEndProfile", 
    points=[[40, 88], [30, 80], [15, 77], [0, 75]])

# Close with back edge
fusion_draw_line(sketch_id="LeftEndProfile", start=[0, 75], end=[0, 105])

fusion_finish_sketch(sketch_id="LeftEndProfile")
```

Profile characteristics:
- Z range: 75-105mm (HIGHER position - ends curve up more)
- Y range: 0-40mm (shallow depth at tips)

### Step 3: Create Center Profile

```
fusion_create_sketch(plane="yz", name="CenterProfile")

# Top surface spline (dips DOWN into trough, rises to HIGHER front lip)
fusion_draw_spline(sketch_id="CenterProfile", 
    points=[[0, 80], [30, 70], [80, 35], [120, 30], [160, 50], [200, 75]])

# Front edge (lip) - TALLER lip
fusion_draw_line(sketch_id="CenterProfile", start=[200, 75], end=[200, 55])

# Bottom surface spline
fusion_draw_spline(sketch_id="CenterProfile", 
    points=[[200, 55], [160, 32], [120, 15], [80, 15], [30, 40], [0, 55]])

# Close with back edge
fusion_draw_line(sketch_id="CenterProfile", start=[0, 55], end=[0, 80])

fusion_finish_sketch(sketch_id="CenterProfile")
```

Profile characteristics:
- Z range: 15-80mm (LOWER position - creates the bowl dip)
- Y range: 0-200mm (full depth at center)
- The trough dips to Z=30 around Y=120 (the bowl cavity)
- Front lip raised to Z=75 (was 65)

### Step 4: Create Right End Profile

```
fusion_create_sketch(plane="Plane7", name="RightEndProfile")

# Same as left end profile (symmetric) - HIGHER ends
fusion_draw_spline(sketch_id="RightEndProfile", 
    points=[[0, 105], [15, 102], [30, 96], [40, 88]])

fusion_draw_spline(sketch_id="RightEndProfile", 
    points=[[40, 88], [30, 80], [15, 77], [0, 75]])

fusion_draw_line(sketch_id="RightEndProfile", start=[0, 75], end=[0, 105])

fusion_finish_sketch(sketch_id="RightEndProfile")
```

### Step 5: Loft Between All Three Profiles

```
fusion_loft(
    sketch_ids=["LeftEndProfile", "CenterProfile", "RightEndProfile"],
    operation="new_body",
    is_solid=true
)
```

Result: Creates Body6 with smooth transitions between profiles

### Step 6: Apply Appearance

```
fusion_apply_appearance(body_id="Body6", appearance="Oak")
```

### Step 7: Add Fillets

```
# Fillet top edges
fusion_fillet_edges(
    edge_ids=["Body6_edge_9", "Body6_edge_10"],
    radius=5,
    tangent_chain=true
)

# Fillet bottom edges  
fusion_fillet_edges(
    edge_ids=["Body6_edge_8", "Body6_edge_11"],
    radius=3,
    tangent_chain=true
)
```

### Step 8: Keyhole Slot Mounting System

#### Why Keyhole Slots Instead of French Cleat?

For curved organic shelves, a French cleat has fundamental problems:
1. The curved bottom of the shelf would hit the cleat before the channel can engage
2. The cleat geometry doesn't align with the shelf's curved profile
3. Requires flat surfaces that a sculptural shelf doesn't have

**Keyhole slots are ideal for curved shelves:**
- Hidden on the back surface
- No interference with curved bottom
- Simple installation with standard screws
- Completely invisible when mounted

```
KEYHOLE SLOT DIAGRAM:

     ┌───┐  ← Narrow slot (6mm wide)
     │   │     for screw shank
     │   │
     │   │  18mm tall
     │   │
     ├───┤
    /     \  ← Large hole (12mm diameter)
   (       )    for screw head to pass through
    \_____/

MOUNTING PROCESS:
1. Install 3 screws in wall (leave heads protruding ~5mm)
2. Align shelf's large holes over screw heads
3. Lower shelf - screw shanks slide into narrow slots
4. Shelf locks in place - lift to remove
```

#### 8a: Create Keyhole Slots

Each keyhole consists of:
- Large hole: 12mm diameter (for screw head)
- Narrow slot: 6mm × 18mm (for screw shank)
- Depth: 15mm into shelf back

Position at X=-200, 0, +200 (evenly spaced across 800mm shelf)

```
# Create large holes for screw heads (12mm diameter = radius 6)
fusion_create_cylinder(center=[-200, 50, -5], radius=6, height=15, axis="z", name="KeyholeHead1")
fusion_create_cylinder(center=[0, 50, -5], radius=6, height=15, axis="z", name="KeyholeHead2")
fusion_create_cylinder(center=[200, 50, -5], radius=6, height=15, axis="z", name="KeyholeHead3")

# Create narrow slots extending upward (6mm wide × 18mm tall)
fusion_create_box(center=[-200, 62, 2], width=6, depth=18, height=15, name="KeyholeSlot1")
fusion_create_box(center=[0, 62, 2], width=6, depth=18, height=15, name="KeyholeSlot2")
fusion_create_box(center=[200, 62, 2], width=6, depth=18, height=15, name="KeyholeSlot3")

# Boolean subtract all keyhole geometry from shelf
fusion_boolean(
    operation="subtract",
    target_body="ShelfBody",
    tool_bodies=["KeyholeHead1", "KeyholeHead2", "KeyholeHead3", 
                 "KeyholeSlot1", "KeyholeSlot2", "KeyholeSlot3"],
    keep_tools=false
)
```

#### 8b: Installation Instructions

```
MOUNTING:
1. Mark wall at desired shelf height
2. Measure 200mm left of center, center, 200mm right of center
3. Install 3 × #8 or #10 screws into wall studs (or use anchors)
4. Leave screw heads protruding 5-6mm from wall
5. Align shelf's large keyhole holes over screw heads
6. Lower shelf ~20mm - screws slide into narrow slots
7. Shelf is secure - bowl faces up, back flush to wall

TO REMOVE:
1. Lift shelf straight up ~20mm
2. Pull shelf away from wall

HARDWARE RECOMMENDATIONS:
- Screws: #8 × 2" or #10 × 2.5" wood screws
- For drywall: Use toggle bolts or heavy-duty anchors
- Weight capacity: ~20-30 lbs with proper stud mounting
```

#### 8c: Apply Appearance

```
fusion_apply_appearance(body_id="ShelfBody", appearance="Oak")
```

---

## Key Design Insights

1. **Why loft instead of sweep?**
   - Sweep keeps the same profile throughout
   - Loft allows different profiles at each position
   - This creates the tapered ends AND the bowl cavity

2. **Why position end profiles HIGH and center LOW?**
   - Front elevation shows ends curving UP
   - Center dips DOWN to create the bowl
   - The Z-coordinate positioning achieves this

3. **Coordinate system on YZ planes:**
   - Y = depth from wall (0 = at wall, positive = away from wall)
   - Z = height (positive = up)

---

## Revision History

| Date | Version | Notes |
|------|---------|-------|
| 2024-12-29 | 1.0-6.0 | Initial attempts with sweep - wrong orientation |
| 2024-12-29 | 7.0-8.0 | Sweep corrections - still issues with ends and cavity |
| 2024-12-29 | 9.0 | Blueprint-based loft approach - correct bowl shape |
| 2024-12-29 | 9.1 | Added exact MCP commands - reproducible build steps |
| 2024-12-29 | 9.2-9.3 | French cleat attempts - coordinate issues |
| 2024-12-29 | 10.0 | Corrected French cleat - proper geometry analysis |
| 2024-12-29 | **10.1** | **Boolean-based cleat channel** - using copy + boolean subtract for reliable cuts |
| 2024-12-29 | **11.0** | **MCP Bridge optimizations** - New tools based on project learnings |
| 2024-12-29 | **12.0** | **Fixed French cleat** - Shallow 20mm channel using fusion_create_box + fusion_create_hole |
| 2024-12-29 | **14.0** | **Correct cleat orientation** - Bevel faces UP into room, triangular channel via copy+subtract |
| 2024-12-29 | **15.0** | **Z-direction mounting holes** - Holes go perpendicular to wall (Z-axis), not Y-axis |
| 2024-12-29 | **16.0** | **Keyhole slots** - Replaced French cleat with keyhole slots for curved shelf compatibility |
| 2024-12-29 | **17.0** | **Final Design** - Front lip thickness, flat end planes, steel wall bracket |
| 2024-12-29 | **18.0** | **Curved Mount Shell** - Elegant mounting that follows shelf's bottom curvature for seamless look |
| 2024-12-29 | **19.0** | **Correct Mount Orientation** - Mount at Y=0-20 (against wall), holes go INTO wall |
| 2024-12-29 | **20.0** | **Blueprint Re-review** - Fixed coordinate system. Y=into room (0-200mm), mount holes go -Y into wall |
| 2024-12-29 | **21.0** | **Curved Cradle Mount** - Slice of shelf bottom creates "hand" that cups the shelf |

---

## Curved Cradle Mount (v21.0)

### Concept

The mount is a **curved slice of the shelf's bottom surface** that acts as a cradle:

```
SIDE VIEW:

WALL
  │
  │  ┌────────┐ ← Back plate (screwed to wall)
  │  │ ○  ○   │   
  │  └────┬───┘
  │       │
  │    ╭──┴──╮
  │   ╱      ╲  ← CURVED CRADLE (matches shelf bottom curve)
  │  │        │   Prevents shelf from sliding forward
  │   ╲______╱
  │      │
  │   ╭──┴────────────────────────╮
  │  ╱                             ╲
  │ │          SHELF                │ ← Shelf NESTS into cradle
  │  ╲___________________________╱
  │
  └──────────────────────────────────►  INTO ROOM
```

### Dimensions

| Component | Dimensions | Position |
|-----------|------------|----------|
| **Back Plate** | 600mm × 30mm × 15mm | Y: 0-15, Z: 50-80 (against wall) |
| **Curved Cradle** | 600mm × 50mm × 10mm thick | Y: 0-50, follows shelf bottom curve |
| **Mounting Holes** | 4 × Ø8mm | Spaced at X: -250, -80, 80, 250 |

### Build Steps (Tool Calls)

```python
# Step 1: Create the shelf (loft between 3 profiles)
fusion_loft(sketch_ids=["LeftEnd", "Center", "RightEnd"])

# Step 2: Copy the shelf to create cradle base
fusion_copy_body(body_id="Shelf", name="CradleBase")

# Step 3: Move copy backward to overlap with wall zone
fusion_move_body(body_id="CradleBase", translation=[0, -15, 0])

# Step 4: Create slicer box - keeps only bottom 10mm of the copy
# Slicer positioned to intersect with bottom surface of shelf
fusion_create_box(corner1=[-320, -5, 0], corner2=[320, 55, 50], name="BottomSlicer")

# Step 5: Intersect to get curved bottom slice
fusion_boolean(operation="intersect", target_body="CradleBase", tool_bodies=["BottomSlicer"])

# Step 6: Create back plate against wall
fusion_create_box(corner1=[-300, 0, 50], corner2=[300, 15, 80], name="BackPlate")

# Step 7: Add mounting holes (going into wall, -Y direction)
fusion_create_cylinder(center=[-250, -10, 65], radius=4, height=30, axis="y")
fusion_create_cylinder(center=[-80, -10, 65], radius=4, height=30, axis="y")
fusion_create_cylinder(center=[80, -10, 65], radius=4, height=30, axis="y")
fusion_create_cylinder(center=[250, -10, 65], radius=4, height=30, axis="y")
fusion_boolean(operation="subtract", target_body="BackPlate", tool_bodies=[holes])

# Step 8: Union back plate with curved cradle
fusion_boolean(operation="union", target_body="CradleBase", tool_bodies=["BackPlate"])

# Step 9: Apply Oak appearance to both
fusion_apply_appearance(body_id="Shelf", appearance="Oak")
fusion_apply_appearance(body_id="CradleMount", appearance="Oak")
```

### How It Works

1. **Mount screws to wall** via 4 holes in back plate
2. **Curved cradle extends forward** from wall (~50mm)
3. **Shelf slides in from above** and nests into the curved cradle
4. **Curvature prevents forward sliding** - the bowl shape locks the shelf in place
5. **Looks seamless** - same Oak material, cradle matches shelf bottom exactly

---

## MCP Bridge Improvements (v11.0)

Based on lessons learned from this project, the following improvements were made to the Fusion 360 MCP bridge:

### New Tools Added

| Tool | Description | Why It Was Needed |
|------|-------------|-------------------|
| `fusion_create_box` | Create box primitive by corners or center+dimensions | Much simpler than sketch+extrude for boolean operations |
| `fusion_create_hole` | Drill cylindrical holes through bodies | Simpler than cylinder + boolean subtract, common operation |
| `fusion_list_sketches` | List all sketches with plane info and profile counts | Helps understand what geometry exists in the design |
| `fusion_sketch_to_3d_coords` | Convert 2D sketch coords to 3D world coords | Essential for verifying where cuts will actually happen |
| `fusion_get_body_center` | Get body centroid and bounding box | Critical for positioning geometry relative to existing bodies |

### Bug Fixes

1. **Cylinder positioning** - Fixed issue where cylinders created at non-zero Z positions wouldn't intersect bodies correctly. Now uses offset planes instead of post-creation moves.

2. **Coordinate documentation** - Added clear notes to sketch drawing tools explaining how 2D sketch coordinates map to 3D space based on sketch plane orientation.

### Key Learnings

1. **Boolean operations are more reliable than extrude cuts** for complex geometry intersections
2. **Always use `get_body_center` first** when positioning cuts or holes to verify body bounds
3. **Use `sketch_to_3d_coords`** to verify sketch geometry position before extruding
4. **Primitive shapes** (box, cylinder) are more predictable than sketch-based approaches for boolean operations

---

## Final Design (v17.0) - Complete Build

### Shelf Body Specifications

| Dimension | Value |
|-----------|-------|
| Width | 800mm |
| Depth | ~95mm (varies with curve) |
| Height | ~210mm (back to front) |
| Volume | ~3,869,000 mm³ |
| Material | Oak |

### Profile Definitions

**Left/Right End Profiles** (at X = ±400mm):
```
Top spline:    [[0, 110], [20, 105], [50, 98], [90, 94], [140, 92], [190, 91]]
Bottom spline: [[0, 70], [20, 75], [50, 80], [90, 83], [140, 84], [190, 83]]
Back line:     [0, 70] → [0, 110]  (40mm thick at wall)
Front line:    [190, 83] → [190, 91]  (8mm thick at front lip)
```

**Center Profile** (at X = 0):
```
Top spline:    [[0, 90], [25, 82], [70, 55], [120, 45], [170, 52], [210, 62]]
Bottom spline: [[0, 55], [25, 48], [70, 25], [120, 15], [170, 28], [210, 52]]
Back line:     [0, 55] → [0, 90]  (35mm thick at wall)
Front line:    [210, 52] → [210, 62]  (10mm thick at front lip)
```

### Keyhole Slots

3 keyhole slots at X = -200, 0, +200:
- Large hole: 12mm diameter (screw head entry)
- Narrow slot: 6mm × 18mm (screw shank)
- Depth: 15mm into back surface

### Wall Bracket

| Dimension | Value |
|-----------|-------|
| Width | 500mm |
| Height | 40mm |
| Depth | 10mm (plate) + 8mm (pegs) |
| Material | Steel - Satin |

**Components:**
- Base plate: 500 × 40 × 10mm
- 3 mounting pegs: 10mm diameter × 8mm tall at X = -200, 0, +200
- 4 wall mounting holes: 6mm diameter at X = -225, -100, +100, +225

### Build Steps

```
# Step 1: Create offset planes
fusion_create_offset_plane(base_plane="yz", offset=-400)  # Left end
fusion_create_offset_plane(base_plane="yz", offset=0)     # Center
fusion_create_offset_plane(base_plane="yz", offset=400)   # Right end

# Step 2: Draw profiles with THICKNESS at front lip
# (Top and bottom splines end at different Z values, connected by line)

# Step 3: Loft between all three profiles
fusion_loft(sketch_ids=["LeftEnd", "Center", "RightEnd"])

# Step 4: Create keyhole slots
# Large holes + narrow slots, boolean subtract from shelf

# Step 5: Apply Oak appearance to shelf

# Step 6: Create wall bracket
fusion_create_box(center=[0, 5, 60], width=500, depth=10, height=40)

# Step 7: Add mounting pegs
fusion_create_cylinder(center=[-200, 10, 60], radius=5, height=8, axis="y")
fusion_create_cylinder(center=[0, 10, 60], radius=5, height=8, axis="y")
fusion_create_cylinder(center=[200, 10, 60], radius=5, height=8, axis="y")
# Boolean union pegs to bracket

# Step 8: Add wall mounting holes
# 4 holes at X = -225, -100, +100, +225
# Boolean subtract from bracket

# Step 9: Apply Steel appearance to bracket
```

### Installation

```
1. Mark wall at desired shelf height
2. Position curved mount shell against wall
3. Mark 4 mounting hole locations
4. Drill pilot holes into studs (or use wall anchors)  
5. Screw curved shell to wall using 4 × #10 screws
6. Place shelf on top of curved shell - they mate together seamlessly
7. Optional: add hidden screws or dowels from underneath to secure shelf to shell
```

---

## Curved Mount Shell (v18.0)

### Concept
The curved mounting shell replaces keyholes/French cleats with an elegant solution that:
- **Matches the shelf's bottom curvature exactly**
- **Fills in the "missing" section** of the shelf's underside
- **When assembled, looks like one continuous piece** of wood

### Curved Mount Shell Specifications

| Dimension | Value |
|-----------|-------|
| Width | 700mm |
| Depth | 45mm (extends from wall halfway into shelf) |
| Height | 45mm (follows bowl curvature) |
| Thickness | 5mm |
| Volume | ~157,500 mm³ |

### Profile Design

The mount shell uses lofted profiles that follow the shelf's bottom curve:

**Left/Right End Profiles** (at X = ±350mm):
```
Top (matching shelf bottom): [[0, 100], [15, 88], [30, 82], [45, 80]]
Bottom (5mm offset):         [[0, 95], [15, 83], [30, 77], [45, 75]]
```

**Center Profile** (at X = 0mm):
```
Top (matching shelf bottom): [[0, 60], [15, 35], [30, 22], [45, 18]]
Bottom (5mm offset):         [[0, 55], [15, 30], [30, 17], [45, 13]]
```

### Build Steps

```
# Step 1: Create offset planes at X = -350, 0, +350
fusion_create_offset_plane(base_plane="yz", offset=-350)
fusion_create_offset_plane(base_plane="yz", offset=0)
fusion_create_offset_plane(base_plane="yz", offset=350)

# Step 2: Create sketches on each plane
# Draw curved profiles matching shelf bottom, 5mm thick

# Step 3: Loft between profiles
fusion_loft(sketch_ids=["CMount_Left", "CMount_Center", "CMount_Right"])

# Step 4: Position shell at shelf bottom
fusion_move_body(body_id="CurvedMount", translation=[0, 0, -165])

# Step 5: Add 4 wall mounting holes
fusion_create_cylinder(center=[-280, 10, -185], radius=4, height=20, axis="y")
fusion_create_cylinder(center=[-100, 10, -185], radius=4, height=20, axis="y")
fusion_create_cylinder(center=[100, 10, -185], radius=4, height=20, axis="y")
fusion_create_cylinder(center=[280, 10, -185], radius=4, height=20, axis="y")
fusion_boolean(operation="subtract", target_body="CurvedMount", tool_bodies=[...])

# Step 6: Apply Oak appearance
```

### Assembly

```
     WALL
       │   ┌──────────────┐  ← Shelf (sits on shell)
       │  ╱                ╲
       │ │     CAVITY       │
       │  ╲________________╱
       │  ╔════════════════╗  ← Curved Mount Shell (screwed to wall)
       │  ║  ○    ○    ○   ║  ← Mounting holes
       └──╚════════════════╝

When assembled, shell fills underside → looks like ONE solid piece
```
