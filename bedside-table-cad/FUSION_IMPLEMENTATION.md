# Bedside Table - Fusion 360 Implementation

## Overall Dimensions
- **Width:** 450mm
- **Depth:** 400mm  
- **Height:** 579mm (carcass only)
- **Panel Thickness:** 19mm

---

## 1. MITERED CORNERS

All four corners use 45° miter joints for a clean, modern look.

### Construction
1. Create overlapping panels (side panels full height)
2. Cut 45° triangular sections at each corner overlap
3. Panels meet at diagonal miter line

### Miter Cut Locations
| Corner | Overlap Region | Miter Diagonal |
|--------|---------------|----------------|
| Top-Left | X: 206-225, Z: 560-579 | (206,560) → (225,579) |
| Top-Right | X: -225 to -206, Z: 560-579 | (-225,579) → (-206,560) |
| Bottom-Left | X: 206-225, Z: 0-19 | (206,19) → (225,0) |
| Bottom-Right | X: -225 to -206, Z: 0-19 | (-225,0) → (-206,19) |

---

## 2. SPLINES (Alignment)

Hidden inside miter joints for alignment during glue-up.

| Parameter | Value |
|-----------|-------|
| Material | 4mm plywood |
| Slot Depth | 16mm per panel |
| Spacing | 100mm |
| Edge Inset | 50mm |
| Per Joint | 3-4 splines |
| **Total** | **~16 splines** |

### Cutting Spline Slots
1. Set up router table with 4mm bit
2. Create 45° jig to hold mitered edge
3. Route 16mm deep slot centered on miter face

---

## 3. CORNER BLOCKS (Assembly)

Triangular hardwood braces that screw into both panels.

```
        ┌───────────┐ TOP PANEL
        │     ╲     │
        │  ┌───╲    │  ← 50mm × 50mm triangle
        │  │    ╲   │     with 6mm alignment rabbets
        │  └─────╲  │
        ├─────────┼─┤
        │  SIDE   │ │
```

| Parameter | Value |
|-----------|-------|
| Leg Length | 50mm |
| Block Length | 80mm |
| Alignment Rabbet | 6mm deep × 10mm wide |
| Screws | #8 × 32mm (2 per block) |
| Positions | Y = 60mm, 334mm from front |
| Per Corner | 2 blocks |
| **Total** | **8 blocks** |

---

## 4. BACK PANEL

Sits in rabbets on all four carcass panels.

| Parameter | Value |
|-----------|-------|
| Rabbet Depth | 9mm |
| Rabbet Width | 6mm |
| Panel Size | 432 × 561 × 6mm |

---

## 5. FALSE FLOOR

Divider shelf between drawers, sits in stopped dados.

| Parameter | Value |
|-----------|-------|
| Dado Depth | 6mm |
| Z Position | 344mm |
| Size | 424 × 347 × 12mm |
| Dado Stop | 25mm from front (blind) |

---

## 6. ASSEMBLY ORDER

1. **Cut all panels** with 45° miters on corners
2. **Route spline slots** into miter faces
3. **Cut dados** for false floor (side panels)
4. **Cut rabbets** for back panel (all panels)
5. **Make corner blocks** with alignment rabbets
6. **Dry fit** - test all joints
7. **Glue up:**
   - Apply glue to miters + spline slots
   - Insert splines
   - Assemble bottom → sides → top
   - Install corner blocks with screws
   - Slide in back panel (no glue)
   - Slide in false floor

---

## 7. PARTS LIST

| Part | Dimensions | Qty |
|------|-----------|-----|
| Bottom Panel | 450 × 400 × 19mm | 1 |
| Top Panel | 450 × 400 × 19mm | 1 |
| Side Panels | 19 × 400 × 579mm | 2 |
| Back Panel | 432 × 6 × 561mm | 1 |
| False Floor | 424 × 347 × 12mm | 1 |
| Corner Blocks | 50 × 50 × 80mm | 8 |
| Splines | 4 × 30 × ~394mm | 4 |
