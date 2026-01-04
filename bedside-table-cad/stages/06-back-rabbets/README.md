# Stage 06: Back Panel Rabbets

## Prerequisites
- Stage 05 complete (4 carcass panels exist)

## Goals
1. **Cut rabbets** into all 4 panels for back panel
2. **Rabbet size**: 9mm deep × 6mm wide

## Success Criteria
- [ ] All 4 panels have step-cut along back edge
- [ ] Rabbet creates continuous groove around back opening

## Rabbet Dimensions
- **Depth**: 9mm (into panel thickness)
- **Width**: 6mm (matches back panel thickness)
- **Location**: Back edge (Y = +200 side)

## Fusion Steps

### Method: Sketch + Cut Extrude (per panel)

#### Bottom Panel Rabbet
1. **Create Sketch** on top face of Bottom_Panel (Z=19)
2. **Draw Rectangle**
   - Corner 1: `(-206, 194)` — inside corner
   - Corner 2: `(206, 200)` — back edge
3. **Finish Sketch**
4. **Extrude** as **Cut**
   - Distance: `9` mm (negative/down)
   - Select Body: `Bottom_Panel`

#### Top Panel Rabbet
1. **Create Sketch** on bottom face of Top_Panel (Z=560)
2. **Draw Rectangle**
   - Corner 1: `(-206, 194)`
   - Corner 2: `(206, 200)`
3. **Extrude Cut**: 9mm upward into Top_Panel

#### Left Panel Rabbet
1. **Create Sketch** on inner face of Left_Panel (X=206)
2. **Draw Rectangle** (in YZ plane)
   - Corner 1: `(194, 19)` — (Y, Z)
   - Corner 2: `(200, 560)`
3. **Extrude Cut**: 9mm toward +X into Left_Panel

#### Right Panel Rabbet
1. **Create Sketch** on inner face of Right_Panel (X=-206)
2. **Draw Rectangle**
   - Corner 1: `(194, 19)`
   - Corner 2: `(200, 560)`
3. **Extrude Cut**: 9mm toward -X into Right_Panel

## Verification
- Section view from side shows step at back
- Rabbets align to form continuous channel









