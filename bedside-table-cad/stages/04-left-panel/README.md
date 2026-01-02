# Stage 04: Left Panel

## Prerequisites
- Stage 03 complete (top panel exists)

## Goals
1. **Create left side panel** - vertical panel on +X side
2. **Full height** from Z=0 to Z=579

## Success Criteria
- [ ] Body named "Left_Panel" exists
- [ ] Dimensions: 19 × 400 × 579mm
- [ ] X range: 206 to 225 (inner face at X=206)

## Fusion Steps

### Create Sketch
1. **Create Sketch** on YZ plane
2. **Draw Rectangle** (2-point)
   - Corner 1: `(-200, 0)` — that's (Y, Z)
   - Corner 2: `(200, 579)`
3. **Finish Sketch**

### Extrude
1. **Create > Extrude**
2. Select the rectangle profile
3. Distance: `19` mm
4. Direction: **One Side**
5. Start: **Offset** = `206` mm (from YZ plane toward +X)
6. Operation: **New Body**
7. Click **OK**

### Alternative Method (if offset start is tricky)
1. Extrude 19mm in +X direction
2. **Move/Copy** body to X=206

### Rename
1. Rename body to `Left_Panel`

## Verification
- Panel spans full depth (Y: -200 to 200)
- Panel spans full height (Z: 0 to 579)
- Panel is 19mm thick in X


