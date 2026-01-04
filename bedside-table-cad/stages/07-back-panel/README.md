# Stage 07: Back Panel

## Prerequisites
- Stage 06 complete (rabbets cut)

## Goals
1. **Create back panel** that sits in the rabbets
2. **Verify fit** - panel should be flush with cabinet back

## Success Criteria
- [ ] Body named "Back_Panel" exists
- [ ] Panel sits in rabbets, back face flush at Y=200
- [ ] Dimensions: ~430 × 559 × 6mm

## Back Panel Dimensions
- **Width**: 430mm (fits between rabbet shoulders)
- **Height**: 559mm (fits between rabbet shoulders)
- **Thickness**: 6mm

## Position
- **X center**: 0 (centered)
- **Y**: 194 to 200 (in rabbet)
- **Z**: 10 to 569 (in rabbet)

## Fusion Steps

### Create Sketch
1. **Create Sketch** on XZ plane
2. Move sketch plane to Y=194 (or create offset plane first)
3. **Draw Rectangle**
   - Corner 1: `(-215, 10)`
   - Corner 2: `(215, 569)`
4. **Finish Sketch**

### Extrude
1. **Create > Extrude**
2. Select rectangle profile
3. Distance: `6` mm
4. Direction: **Positive** (+Y, toward back)
5. Operation: **New Body**
6. Click **OK**

### Rename
1. Rename body to `Back_Panel`

## Verification
- Back panel sits in all 4 rabbets
- Back face is flush with cabinet back (Y=200)
- No interference with carcass panels









