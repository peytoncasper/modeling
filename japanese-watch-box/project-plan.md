# Japanese Watch Box - CNC Project Plan

## Overview
A traditional Japanese-style watch box featuring:
- Light wood (Hinoki/Maple/Oak) carcass
- Dark wood (Walnut) accents
- Kumiko lattice panel in lid (Asanoha pattern)
- 4 watch compartments with cushions
- Decorative corner splines

---

## Reference Dimensions

| Component | Length | Width | Height/Thickness |
|-----------|--------|-------|------------------|
| Exterior | 220mm | 110mm | 55mm (box) + 18mm (lid) |
| Wall thickness | - | - | 10mm |
| Bottom panel | 200mm | 90mm | 6mm |
| Lid | 220mm | 110mm | 18mm |
| Kumiko recess | 190mm | 80mm | 10mm deep |
| Kumiko panel | 186mm | 76mm | 5mm |
| Interior frame | 200mm | 90mm | 5mm thick, 5mm tall |
| Dividers | 80mm | 5mm | 38mm |
| Corner splines | 10mm | 10mm | 4mm (12 total) |

---

## Component Breakdown by CNC Operation

### Group A: Contour Cuts (Oak 12-20mm stock)

#### A1. Box Walls (as assembled frame or 4 panels)
- Option 1: Cut as hollow frame from single piece
- Option 2: Cut 4 mitered panels, assemble with splines
- Exterior: 220×110mm, Interior: 200×90mm, Height: 55mm

#### A2. Bottom Panel
- 200×90×6mm
- Simple rectangular contour

#### A3. Lid Panel
- 220×110×18mm
- Contour cut + pocket for kumiko recess (190×80×10mm)

---

### Group B: Contour Cuts (Walnut 5-6mm stock)

#### B1. Interior Perimeter Frame
- Outer: 200×90mm, Inner: 190×80mm
- Height: 5mm
- Sits at top of compartments

#### B2. Cross Dividers (3x)
- 80×38×5mm each
- Run front-to-back (Y direction)
- Spacing: Creates 4 equal compartments

#### B3. Horizontal Rails (2x) 
- 190×38×5mm each
- Run left-to-right at front and back
- Connect to cross dividers

#### B4. Kumiko Lattice Panel ⭐ FOCUS PIECE
- 186×76×5mm
- Grid pattern with Asanoha-inspired design
- See detailed breakdown below

#### B5. Corner Spline Strips
- Cut strips 4mm × 15mm × 200mm
- Cross-cut into individual splines after

---

### Group C: Post-Assembly Operations

#### C1. Corner Spline Slots
- 45° fixture required
- 12 slots total (3 per corner × 4 corners)
- Slot dimensions: 4mm wide × 12mm deep

#### C2. Hinge Mortises
- 2 barrel hinges on back edge
- Pocket cut into lid and box back

---

## Kumiko Lattice Panel - Detailed Plan ⭐

### Dimensions
- Overall: 186mm × 76mm × 5mm
- Frame border: 3mm
- Grid bar width: 3mm

### Grid Layout
- 6 columns × 2 rows of cells
- Cell size: approximately 27mm × 33mm
- 5 vertical internal bars
- 1 horizontal internal bar

### Asanoha Pattern (Simplified for CNC)
Traditional Asanoha has diagonal divisions in each cell. For 2D router:
- Option A: Simple rectangular grid (CNC-friendly)
- Option B: Add diagonal bars in each cell (more complex)
- Option C: Laser cut the intricate pattern

### Modeling Strategy
1. Create panel as separate body (isolated from box)
2. Draw grid geometry as positive profiles (bars, not cells)
3. Extrude grid bars as single operation
4. Position into lid recess as final step

### Grid Bar Positions
```
X positions (vertical bars):
  Frame left:  -93 to -90
  Bar 1:       -62 to -59
  Bar 2:       -32 to -29
  Bar 3:       -1.5 to +1.5
  Bar 4:       +29 to +32
  Bar 5:       +59 to +62
  Frame right: +90 to +93

Y positions (horizontal bars):
  Frame top:    +35 to +38
  Middle bar:   -1.5 to +1.5
  Frame bottom: -38 to -35
```

---

## Materials

| Material | Appearance | Used For |
|----------|------------|----------|
| Hinoki/Maple/Oak | Light, fine grain | Box carcass, lid, bottom |
| Walnut | Dark, rich grain | Dividers, frame, kumiko, splines |

---

## Assembly Order

1. Glue box walls (if separate panels)
2. Glue bottom panel into rabbet
3. Cut corner spline slots (45° fixture)
4. Glue corner splines, trim flush
5. Glue interior frame to top of box
6. Glue cross dividers and horizontal rails
7. Mortise hinges
8. Glue kumiko panel into lid recess
9. Attach lid with hinges
10. Finish (oil/wax)

---

## Files

| File | Description |
|------|-------------|
| `kumiko-lattice.f3d` | Fusion 360 model of kumiko panel |
| `full-box.f3d` | Complete watch box assembly |
| `cam-setup.f3d` | CAM operations by material group |

---

## Lessons Learned

### Fusion 360 MCP Tips
1. **Build in place** - Don't move bodies during construction
2. **Use XY offset planes** - More predictable than XZ/YZ for horizontal features
3. **Avoid overlapping sketch rectangles** - Creates fragmented profiles
4. **Draw positive geometry** - Draw what you want to extrude, not what you want to remove
5. **Separate complex parts** - Build isolated, position later
6. **Use symmetric extrusion for cuts** - `direction: negative` fails to find target body; `direction: symmetric` works reliably

### Kumiko Modeling - SOLVED ✅
**Problem:** Overlapping rectangles create 40+ fragmented profiles (unusable)

**Solution: Negative Space Approach**
1. Create solid panel first (186 × 76 × 5mm)
2. Draw cell openings as NON-overlapping rectangles on offset plane at top of panel
3. Cut each cell individually using `symmetric` extrusion direction
4. Result: Clean 6×2 grid with 3mm frame and 3mm bars

**Grid Dimensions:**
- Panel: 186 × 76mm (centered on origin: -93 to 93, -38 to 38)
- Frame border: 3mm on all sides
- Inner area: 180 × 70mm (-90 to 90, -35 to 35)
- Vertical bars: 5 bars × 3mm = 15mm → 6 cells × 27.5mm = 165mm
- Horizontal bar: 1 bar × 3mm → 2 rows × 33.5mm = 67mm

**Cell Positions (12 total):**
```
Top Row (y: 1.5 to 35):
  Cell 1: x -90 to -62.5
  Cell 2: x -59.5 to -32
  Cell 3: x -29 to -1.5
  Cell 4: x 1.5 to 29
  Cell 5: x 32 to 59.5
  Cell 6: x 62.5 to 90

Bottom Row (y: -35 to -1.5):
  Same X positions as top row
```

### Corner Splines
- Must be embedded IN the corner, not outside
- Use XY planes at specific Z heights for consistent placement
- Span both wall directions (10mm × 10mm footprint)

---

## Completed Models

| Model | File | Status |
|-------|------|--------|
| Kumiko Simple Grid | `Kumiko Lattice Panel.f3d` | ✅ Complete (6×2 rectangular grid) |
| Kumiko X-Pattern | `Kumiko Asanoha Final.f3d` | ✅ Complete (6×2 cells with X-diagonals) |
| Watch Box Carcass | `Japanese Watch Box.f3d` | ✅ Complete (4 mitered walls + bottom + 12 splines) |
| Interior Dividers | `Japanese Watch Box.f3d` | ✅ Complete (frame + 3 dividers = 4 compartments) |
| Full Assembly | - | Pending |

---

## Watch Box Carcass - Build Notes ✅

### Approach: Trapezoid Profiles with Built-in Miters

Each wall was drawn as a trapezoid profile on the XY plane with the 45° miter already included, then extruded upward to 55mm height.

### Wall Profiles
- **Front/Back walls**: Trapezoid from outer edge (220mm) to inner edge (200mm)
- **Left/Right walls**: Trapezoid from outer edge (110mm) to inner edge (90mm)
- Walls meet perfectly at 45° mitered corners

### Bodies Created
| Body | Description | Dimensions | Material |
|------|-------------|------------|----------|
| Body2 | Front Wall | 220 × 10 × 55mm | Oak |
| Body3 | Back Wall | 220 × 10 × 55mm | Oak |
| Body4 | Left Wall | 10 × 110 × 55mm | Oak |
| Body5 | Right Wall | 10 × 110 × 55mm | Oak |
| Body6 | Bottom Panel | 200 × 90 × 6mm | Oak |
| Body7-18 | 12 Corner Splines | 10 × 10 × 4mm each | Walnut |

### Corner Splines
- 3 per corner at Z heights: 10-14mm, 25-29mm, 40-44mm
- Total: 12 splines (4 corners × 3 heights)
- Dark walnut for contrast against light oak

---

## X-Pattern Kumiko - SUCCESSFUL APPROACH ✅

### The Solution: Draw Inset Triangles

**Key Insight:** Instead of drawing grid lines (zero-width), draw each triangular opening as an individual closed triangle with vertices inset from the grid boundaries.

### Geometry
- **6 columns × 2 rows** of cells (30mm × 35mm each)
- **4 triangular openings per cell** (48 total)
- Each triangle connects cell center to two adjacent corners
- Triangles are **inset ~2mm** from the grid lines to leave material for bars

### Successful Approach
1. Create solid panel (186 × 76 × 5mm)
2. Create offset plane at top of panel (z = 5mm)
3. For each cell, draw 4 closed triangles:
   - Top triangle: (cx, cy+2) → (left+3, top-2) → (right-3, top-2)
   - Right triangle: (cx+2, cy) → (right-2, top-3) → (right-2, bottom+3)
   - Bottom triangle: (cx, cy-2) → (right-3, bottom+2) → (left+3, bottom+2)
   - Left triangle: (cx-2, cy) → (left+2, bottom+3) → (left+2, top-3)
4. Each triangle becomes a separate closed profile
5. Cut each profile individually with symmetric extrusion

### Result
- 48 non-overlapping triangular profiles
- All cuts succeed without fragmenting the body
- Beautiful X-pattern lattice with ~3mm bars between openings
- CNC-friendly geometry

---

## Asanoha Pattern - Complexity Notes

### Why Asanoha is Difficult to Model with MCP

The true Asanoha (hemp leaf) pattern requires:
1. **Hexagonal base grid** - not rectangular
2. **60° angles** - lines radiating from each intersection at exact 60° intervals
3. **Staggered rows** - odd rows offset by half the horizontal spacing
4. **Consistent cell sizes** - all triangular cells must be equilateral

### Attempts Made

**Attempt 1: X diagonals in rectangular cells**
- Result: 4 triangular cells per rectangle, but stars are at cell centers not intersections
- Problem: Creates sawtooth edge pattern, not interior lattice

**Attempt 2: Full diagonal lines across panel**
- Result: Triangle grid with mixed cell sizes (87.5, 175, 262.5 mm²)
- Problem: Diagonals don't intersect at grid points, creating inconsistent cells

**Attempt 3: SVG Import with proper hexagonal geometry**
- Created SVG with staggered grid (even/odd row offsets) and 60° diagonal lines
- SVG file: `asanoha-kumiko.svg` 
- Import successful: 183 curves, 119 profiles
- Problem: SVG strokes import as zero-width lines, not filled bars
- Profiles represent triangular OPENINGS, not the lattice bars
- Profile 0 is just the outer frame ring, not the interior lattice
- Cutting profiles 1-118 individually is possible but creates scattered cuts due to profile ordering

### Core Issue with SVG Approach

**Why SVG lines don't work for Fusion extrusion:**
1. SVG strokes have `stroke-width` for display, but Fusion imports them as zero-width curves
2. The REGIONS between curves become profiles, not the curves themselves
3. For a lattice, we need the BARS to be solid, but we get the OPENINGS as profiles
4. Would need to draw bars as filled rectangles/polygons in SVG, not stroked lines

### Recommended Solutions

1. **For true Asanoha:** Use external CAD (Illustrator/Inkscape) to create filled bar geometry, export DXF, import to Fusion
2. **Laser Cutting**: The thin bars and intricate angles are better suited to laser cutting than CNC routing
3. **Use the simple grid**: The 6×2 rectangular grid (`Kumiko Lattice Panel.f3d`) is complete and CNC-friendly
4. **Accept triangle grid**: Continue cutting all 118 profiles systematically (time-consuming but viable)

### Files Created

| File | Description |
|------|-------------|
| `asanoha-kumiko.svg` | SVG with hexagonal Asanoha geometry (horizontal + diagonal lines at 60°) |
| `Kumiko Lattice Panel.f3d` | ✅ Working simple 6×2 rectangular grid |
| `Kumiko Asanoha SVG.f3d` | Partial - frame only, triangle profiles not cut |

