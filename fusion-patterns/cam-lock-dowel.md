# Pattern: Cam Lock + Dowel (Flat-Pack / Knockdown Fittings)

## What Are Cam Lock Fittings?

A two-part mechanical fastener system (also called Minifix, Rafix, or KD fittings) that allows tool-free or single-tool assembly of panel furniture. The customer inserts a bolt into a cam housing and turns it to lock — the same system used by IKEA, Article, Floyd, and virtually all flat-pack furniture.

```
Cross-section of assembled joint:

    Panel A (side)
    ┌───────────────────────┐
    │                       │
    │    ╔═══╗              │
    │    ║ ◉ ║ ← cam       │   Cam grips bolt head,
    │    ╚═╤═╝   housing    │   pulls joint tight
    │      │                │
    ├──────┘                │
    │ ●────────── bolt ─────│── screwed into Panel B edge
    ├──────┐                │
    │      │                │
    │    ○ ○ ← alignment   │
    │      dowels           │
    └───────────────────────┘
         Panel B (shelf)
```

## Why Cam Locks for Customer-Assembled Products

| Criteria | Cam Lock | Confirmat Screw | Barrel Nut |
|----------|----------|-----------------|------------|
| Customer tool needed | Phillips or coin | Phillips driver | Allen key |
| Intuitive assembly | Very high | High | Medium |
| Repeatably demountable | Yes (50+ cycles) | No (strips) | Yes |
| Hidden from outside | Yes | No (cap visible) | No (bolt visible) |
| Pull-out strength | ~800N | ~1000N | ~1200N |
| Instruction clarity | Simple (insert + turn) | Simple (drive screw) | Moderate (align nut) |
| Premium perception | High | Low | Medium |

**Cam locks win on the combination of invisible joints, repeatability, and customer experience.**

## Hardware Specifications

### Standard Minifix 15 (for 18mm panels — recommended)

| Component | Dimension | Notes |
|-----------|-----------|-------|
| Cam housing diameter | 15mm | Forstner bore |
| Cam housing depth | 12.5mm | Blind bore on panel face |
| Cam bore setback | 34mm | Center of bore to joining edge |
| Edge access hole | 8mm diameter | Drilled from joining edge into cam pocket |
| Edge access depth | 34mm | Connects edge to cam bore |
| Connecting bolt length | 34mm | For 18mm mating panel |
| Bolt pilot hole | 5mm diameter × 13mm deep | In mating panel edge |
| Bolt center in edge | 9mm from face | Centered in 18mm panel |

### Minifix 12 (for 15mm panels)

| Component | Dimension |
|-----------|-----------|
| Cam housing diameter | 12mm |
| Cam housing depth | 10.5mm |
| Cam bore setback | 29mm |
| Edge access hole | 6mm diameter × 29mm deep |
| Connecting bolt length | 24mm |
| Bolt pilot hole | 5mm × 11mm |

### Alignment Dowels (both panel thicknesses)

| Component | Dimension |
|-----------|-----------|
| Dowel diameter | 8mm (fluted wooden) |
| Dowel length | 30mm |
| Hole diameter | 8mm |
| Hole depth per panel | 15mm |
| Typical spacing | 96mm apart, symmetric about cam |

## Panel Thickness Consideration

**18mm (3/4") is the industry standard for flat-pack panel furniture.** Most cam fittings are designed for it. If your current design uses 12.7mm (1/2") panels, strongly consider moving to 15mm or 18mm for a commercial flat-pack product:

| Thickness | Cam option | Edge screw holding | Suitability |
|-----------|------------|-------------------|-------------|
| 12.7mm | Marginal (Minifix 12 barely fits) | Weak | Not recommended |
| 15mm | Minifix 12 (good fit) | Acceptable | Viable |
| 18mm | Minifix 15 (standard) | Strong | Recommended |

## Joint Types in a Carcass

### Type 1: Right-Angle Joint (panel edge to panel face)

The most common joint. A shelf or top/bottom panel butts its edge against the inner face of a side panel.

```
                  Panel A (side)
                  ┌──────┐
    ──────────────┤      │
    Panel B       │  ◉   │ ← cam in face of A
    (shelf)       │      │
    ──────────────┤      │
                  └──────┘
```

**Panel A (receives cam):**
- Face bore: 15mm × 12.5mm deep
- Edge access hole from joining edge: 8mm × 34mm deep
- Both centered on panel thickness (9mm from outer face for 18mm panel)
- Cam center: 34mm from joining edge

**Panel B (receives bolt):**
- Edge bore: 5mm × 13mm deep, centered on panel thickness
- Bolt screws into this hole; head protrudes from edge

### Type 2: T-Joint (shelf between two sides)

A shelf is held by cam fittings on both ends. Each end is a Type 1 joint.

```
    ┌──────┐                     ┌──────┐
    │      ├─────────────────────┤      │
    │  ◉   │     Panel B         │  ◉   │
    │      ├─────────────────────┤      │
    │      │                     │      │
    └──────┘                     └──────┘
    Panel A (left)               Panel A (right)
```

### Type 3: Back Panel Attachment

For thin back panels (typically 6mm HDF), use separate fittings or a routed groove in the carcass panels instead of cam locks.

## Implementation: Right-Angle Joint

### Phase 1: Identify Joint Parameters

```python
# Known from carcass geometry
panel_thickness = 18       # mm, both panels
cam_diameter = 15          # mm, Minifix 15
cam_depth = 12.5           # mm
cam_setback = 34           # mm from joining edge to cam center
access_hole_diameter = 8   # mm
bolt_pilot_diameter = 5    # mm
bolt_pilot_depth = 13      # mm
dowel_diameter = 8         # mm
dowel_depth = 15           # mm
dowel_length = 30          # mm

# Cam center in panel thickness
cam_center_in_thickness = panel_thickness / 2  # 9mm
```

### Phase 2: Determine Fitting Positions Along Joint

For a joint edge of length `L`, place fittings to distribute load evenly:

```python
# Minimum 50mm from panel corners to avoid blowout
edge_margin = 50

if L <= 300:
    # Single cam + 2 dowels
    cam_positions = [L / 2]
    dowel_positions = [edge_margin, L - edge_margin]
elif L <= 600:
    # Two cams + 1 center dowel
    cam_positions = [L / 3, 2 * L / 3]
    dowel_positions = [L / 2]
elif L <= 900:
    # Two cams + 2 dowels
    cam_positions = [L / 3, 2 * L / 3]
    dowel_positions = [edge_margin, L - edge_margin]
else:
    # Three cams + 2 dowels
    cam_positions = [L / 4, L / 2, 3 * L / 4]
    dowel_positions = [edge_margin, L - edge_margin]
```

### Phase 3: Bore Cam Pockets in Panel A (Face)

Each cam pocket is a blind cylindrical bore on the inner face of Panel A.

```python
# Example: left side panel, shelf joins at height Z_shelf
# Panel A inner face is at X = panel_thickness (for left side panel)
# Cam pocket center: 34mm below the shelf position

inner_face_x = panel_thickness  # X coordinate of inner face

for i, pos in enumerate(cam_positions):
    # pos = position along the joint edge (maps to Y for a side panel)

    # 1. Create sketch on Panel A inner face
    fusion_create_offset_plane(base_plane="yz", offset=inner_face_x)
    fusion_create_sketch(plane=f"Plane_cam_{i}", name=f"CamPocket_{i}")

    # 2. Draw 15mm circle for cam bore
    # Center at: Y=pos along edge, Z=Z_shelf - cam_setback
    cam_z = Z_shelf - cam_setback  # 34mm below shelf bottom
    fusion_draw_circle(sketch_id=f"CamPocket_{i}",
        center=[pos, cam_z],
        radius=cam_diameter / 2)

    fusion_finish_sketch(sketch_id=f"CamPocket_{i}")

    # 3. Cut blind bore into panel (toward -X, into panel body)
    fusion_extrude(sketch_id=f"CamPocket_{i}",
        distance=cam_depth,
        direction="negative",
        operation="cut",
        target_body="Left Panel")
```

### Phase 4: Bore Edge Access Holes in Panel A

These connect the joining edge to each cam pocket so the bolt can reach the cam.

```python
for i, pos in enumerate(cam_positions):
    # Edge hole enters from the joining edge (top of side panel where shelf meets)
    # and goes inward (in -Z direction) to reach the cam pocket

    # 1. Create sketch on the joining edge face
    # For a side panel, the shelf sits on top edge or at a specific Z
    fusion_create_offset_plane(base_plane="xy", offset=Z_shelf)
    fusion_create_sketch(plane=f"Plane_access_{i}", name=f"AccessHole_{i}")

    # 2. Draw 8mm circle centered in panel thickness
    access_center_x = cam_center_in_thickness  # 9mm from outer face
    fusion_draw_circle(sketch_id=f"AccessHole_{i}",
        center=[access_center_x, pos],
        radius=access_hole_diameter / 2)

    fusion_finish_sketch(sketch_id=f"AccessHole_{i}")

    # 3. Cut hole from edge into panel, reaching cam pocket
    fusion_extrude(sketch_id=f"AccessHole_{i}",
        distance=cam_setback + cam_diameter / 2,  # reach past cam center
        direction="negative",  # into -Z (into panel body from shelf edge)
        operation="cut",
        target_body="Left Panel")
```

### Phase 5: Bore Bolt Holes in Panel B (Edge)

```python
for i, pos in enumerate(cam_positions):
    # Bolt pilot hole in shelf edge, centered on thickness

    # 1. Create sketch on shelf end face (the edge that meets Panel A)
    # For a shelf, the left end face is at X=panel_thickness
    fusion_create_sketch(plane="yz", name=f"BoltHole_{i}")

    # 2. Draw 5mm circle centered on shelf thickness
    bolt_center_z = Z_shelf + cam_center_in_thickness  # centered in shelf
    fusion_draw_circle(sketch_id=f"BoltHole_{i}",
        center=[pos, bolt_center_z],
        radius=bolt_pilot_diameter / 2)

    fusion_finish_sketch(sketch_id=f"BoltHole_{i}")

    # 3. Cut pilot hole into shelf edge
    fusion_extrude(sketch_id=f"BoltHole_{i}",
        distance=bolt_pilot_depth,
        direction="positive",  # into +X (into shelf body)
        operation="cut",
        target_body="Shelf")
```

### Phase 6: Bore Dowel Holes (Both Panels)

Alignment dowels prevent racking and make assembly foolproof for the customer.

```python
for i, pos in enumerate(dowel_positions):
    # --- Panel A face (same face as cam pockets) ---
    fusion_create_offset_plane(base_plane="yz", offset=inner_face_x)
    fusion_create_sketch(plane=f"Plane_dowelA_{i}", name=f"DowelA_{i}")

    dowel_z = Z_shelf  # at the joining edge
    fusion_draw_circle(sketch_id=f"DowelA_{i}",
        center=[pos, dowel_z],
        radius=dowel_diameter / 2)

    fusion_finish_sketch(sketch_id=f"DowelA_{i}")

    # Dowel hole goes from the joining edge INTO Panel A
    fusion_extrude(sketch_id=f"DowelA_{i}",
        distance=dowel_depth,
        direction="negative",  # into -Z (below shelf line, into panel)
        operation="cut",
        target_body="Left Panel")

    # --- Panel B edge (shelf end) ---
    fusion_create_sketch(plane="yz", name=f"DowelB_{i}")

    fusion_draw_circle(sketch_id=f"DowelB_{i}",
        center=[pos, Z_shelf + cam_center_in_thickness],
        radius=dowel_diameter / 2)

    fusion_finish_sketch(sketch_id=f"DowelB_{i}")

    fusion_extrude(sketch_id=f"DowelB_{i}",
        distance=dowel_depth,
        direction="positive",
        operation="cut",
        target_body="Shelf")
```

## Corner Identification for a Carcass

A standard rectangular carcass has multiple cam lock joints:

```
Exploded view (looking at front):

         ┌──────────────────────┐
         │      Top Panel       │ ← bolts in both side edges
         └──┬────────────────┬──┘
            │                │
    ┌───────┤                ├───────┐
    │       │                │       │
    │ Left  │   (interior)   │ Right │ ← cam pockets on
    │ Panel │                │ Panel │   inner faces
    │       │                │       │
    └───────┤                ├───────┘
            │                │
         ┌──┴────────────────┴──┐
         │     Bottom Panel     │ ← bolts in both side edges
         └──────────────────────┘
```

| Joint | Panel with CAM (face bore) | Panel with BOLT (edge bore) |
|-------|----------------------------|----------------------------|
| Left ↔ Top | Left Panel (inner face) | Top Panel (left edge) |
| Left ↔ Bottom | Left Panel (inner face) | Bottom Panel (left edge) |
| Right ↔ Top | Right Panel (inner face) | Top Panel (right edge) |
| Right ↔ Bottom | Right Panel (inner face) | Bottom Panel (right edge) |
| Left ↔ Shelf | Left Panel (inner face) | Shelf (left edge) |
| Right ↔ Shelf | Right Panel (inner face) | Shelf (right edge) |

**Rule of thumb:** cams always go in the larger panel's face; bolts always go in the smaller panel's edge.

## Assembly Instructions Template (For Customer)

This is the experience your customer will have:

```
Step 1: Screw connecting bolts into shelf edges (pre-mark with ▲ stickers)
Step 2: Press wooden dowels into side panel holes (half-way)
Step 3: Align shelf dowels with side panel, press together
Step 4: Turn cam locks clockwise with a Phillips screwdriver or coin
Step 5: Repeat for all shelves, then attach top and bottom
```

**Design tips for customer experience:**
- Number each panel and mark "this side up" or "this side in"
- Pre-install bolts at the factory (saves a step)
- Use arrow stickers pointing to each cam access hole
- Include a coin-slot cam design so customers don't need tools
- Keep total fitting count under 20 for a simple carcass

## Verification

After boring each fitting:

```python
# 1. Confirm cam pocket dimensions
fusion_get_body_center(body_id="Left Panel")
# Volume should have decreased

# 2. Check that access hole connects to cam pocket
# Visual inspection from the joining edge
fusion_set_view(preset="front")
fusion_take_screenshot(view="current")

# 3. Verify bolt hole depth won't pierce shelf face
fusion_get_body_center(body_id="Shelf")
# Min/max bounds should be unchanged (blind hole)

# 4. Check dowel alignment
# Dowel positions in Panel A face should match Panel B edge
# within 0.1mm tolerance
```

## Parametric Integration

```python
# Fitting parameters (change these to switch hardware sizes)
fusion_create_parameter(name="cam_diameter", value=15, unit="mm")
fusion_create_parameter(name="cam_depth", value=12.5, unit="mm")
fusion_create_parameter(name="cam_setback", value=34, unit="mm")
fusion_create_parameter(name="bolt_pilot_dia", value=5, unit="mm")
fusion_create_parameter(name="bolt_pilot_depth", value=13, unit="mm")
fusion_create_parameter(name="access_hole_dia", value=8, unit="mm")
fusion_create_parameter(name="dowel_dia", value=8, unit="mm")
fusion_create_parameter(name="dowel_hole_depth", value=15, unit="mm")
fusion_create_parameter(name="edge_margin", value=50, unit="mm")
fusion_create_parameter(name="panel_thickness", value=18, unit="mm")
```

## Common Mistakes

### 1. Cam Pocket Too Deep
**Problem:** Bore goes through the outer face of Panel A.
**Solution:** `cam_depth` (12.5mm) must be less than `panel_thickness` (18mm). Leave at least 5mm of material. For 15mm panels, use Minifix 12 (10.5mm depth).

### 2. Access Hole Misses Cam Pocket
**Problem:** The 8mm edge hole doesn't intersect the 15mm cam bore.
**Solution:** Both must be centered on the same line: `panel_thickness / 2` from the outer face. The access hole depth must reach at least `cam_setback - cam_diameter / 2`.

### 3. Bolt Hole Pierces Panel Face
**Problem:** 5mm pilot hole drilled too deep, exits through shelf face.
**Solution:** `bolt_pilot_depth` (13mm) must be less than `panel_thickness / 2` for centered bolts. For 18mm panels, max safe depth is ~14mm.

### 4. Dowels Too Tight / Too Loose
**Problem:** Customer can't assemble, or joint is sloppy.
**Solution:** Use exactly 8mm holes for 8mm dowels. Fluted dowels compress slightly for a press fit. Don't oversize holes.

### 5. Fittings Too Close to Panel Edge
**Problem:** Panel splits during assembly.
**Solution:** Maintain minimum 50mm from any panel corner to the nearest fitting center. For edges, minimum 37mm from the parallel edge.

### 6. Wrong Panel Gets the Cam
**Problem:** Cam and bolt on the same panel, or cams on both.
**Solution:** Follow the rule: **cam in the face, bolt in the edge.** The larger panel always receives the cam on its face.

## Bill of Materials Per Joint

| Qty | Part | Specification | Typical Cost |
|-----|------|---------------|-------------|
| 1 | Cam housing | Minifix 15, zinc alloy | $0.30-0.60 |
| 1 | Connecting bolt | M6 × 34mm, steel | $0.10-0.20 |
| 2 | Wooden dowels | 8mm × 30mm, fluted | $0.02-0.05 |

For a basic 4-panel carcass (no shelves): 4 joints × ~$0.50 = **~$2.00 in hardware**.

## Quick Reference: Process Summary

```
1. Choose panel thickness (18mm recommended for flat-pack)
2. Identify all right-angle joints in the carcass
3. Assign cam vs bolt to each panel (cam in face, bolt in edge)
4. Calculate fitting positions along each joint edge
5. For each joint:
   a. Bore 15mm cam pockets on Panel A face (blind, 12.5mm deep)
   b. Bore 8mm access holes from Panel A joining edge to cam pockets
   c. Bore 5mm bolt pilot holes in Panel B edge
   d. Bore 8mm dowel holes in both panels (15mm deep each)
6. Verify alignment and depths
7. Test-assemble with actual hardware before production
```

## Manufacturing Notes

**CNC boring (production):**
- All holes are simple cylindrical bores on faces or edges
- Can be done on a single CNC boring machine (like a Blum Minipress)
- Cam pockets and dowel holes are typically bored in one setup (face boring)
- Edge holes (access + bolt pilot) in a second setup
- Cycle time per panel: ~15-30 seconds

**Shop tools (prototype):**
- 15mm Forstner bit for cam pockets
- 8mm brad-point bit for access holes and dowel holes
- 5mm brad-point bit for bolt pilots
- Drill press with depth stop is essential
- A 32mm system drilling jig speeds layout significantly

**Tolerances:**
- Cam pocket diameter: 15mm +0.1/-0 (slight oversize OK, undersize jams)
- Hole positions: ±0.5mm (cam is self-centering within this range)
- Depth: ±0.3mm (too shallow = hardware proud; too deep = weak)
