# Stage 03: Top Panel

## Prerequisites
- Stage 02 complete (bottom panel exists)

## Goals
1. **Create offset plane** at Z=560
2. **Create top panel** - horizontal slab at top

## Success Criteria
- [ ] Body named "Top_Panel" exists
- [ ] Dimensions: 450 × 400 × 19mm
- [ ] Bottom face at Z=560, top face at Z=579

## Fusion Steps

### Create Offset Plane
1. **Construct > Offset Plane**
2. Select **XY plane** (origin)
3. Offset: `560` mm (or `overall_height - carcass_thickness`)
4. Click **OK**

### Create Sketch
1. **Create Sketch** on the new offset plane
2. **Draw Rectangle** (2-point)
   - Corner 1: `(-225, -200)`
   - Corner 2: `(225, 200)`
3. **Finish Sketch**

### Extrude
1. **Create > Extrude**
2. Select the rectangle profile
3. Distance: `19` mm
4. Direction: **Positive** (up)
5. Operation: **New Body**
6. Click **OK**

### Rename
1. Rename body to `Top_Panel`

## Verification
- Top panel Z range: 560 to 579
- Same XY footprint as bottom panel


