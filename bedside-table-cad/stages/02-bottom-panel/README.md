# Stage 02: Bottom Panel

## Prerequisites
- Stage 01 complete (parameters exist)

## Goals
1. **Create bottom panel** - horizontal slab at Z=0
2. **Verify dimensions** - 450 × 400 × 19mm

## Success Criteria
- [ ] Body named "Bottom_Panel" exists
- [ ] Dimensions match: 450 × 400 × 19mm
- [ ] Bottom face at Z=0, top face at Z=19

## Fusion Steps

### Create Sketch
1. **Create Sketch** on XY plane (Z=0)
2. **Draw Rectangle** (2-point)
   - Corner 1: `(-225, -200)`
   - Corner 2: `(225, 200)`
3. **Finish Sketch**

### Extrude
1. **Create > Extrude**
2. Select the rectangle profile
3. Distance: `19` mm (or `carcass_thickness`)
4. Direction: **Positive** (up)
5. Operation: **New Body**
6. Click **OK**

### Rename
1. In Browser, expand **Bodies**
2. Right-click the new body
3. Rename to `Bottom_Panel`

## Verification
- Measure tool: Width=450, Depth=400, Height=19


