# Stage 09: False Floor

## Prerequisites
- Stage 08 complete (dados cut)

## Goals
1. **Create false floor** that sits in the dados
2. **Divides cabinet** into upper and lower sections

## Success Criteria
- [ ] Body named "False_Floor" exists
- [ ] Panel sits in both dados
- [ ] Top surface at Z=356, bottom at Z=344

## False Floor Dimensions
- **Width**: 424mm (extends 6mm into each dado)
- **Depth**: 369mm (from front to dado stop)
- **Thickness**: 12mm

## Position
- **X**: -212 to 212 (into dados on each side)
- **Y**: -200 to 169 (front to dado stop)
- **Z**: 344 to 356

## Fusion Steps

### Create Sketch
1. **Create Sketch** on XY plane
2. Create offset plane at Z=344, or sketch on XY and extrude with offset
3. **Draw Rectangle**
   - Corner 1: `(-212, -200)`
   - Corner 2: `(212, 169)`
4. **Finish Sketch**

### Extrude
1. **Create > Extrude**
2. Select rectangle profile
3. Distance: `12` mm
4. Direction: **Positive** (+Z, up)
5. Start: **From Object** or **Offset** = 344mm from XY plane
6. Operation: **New Body**
7. Click **OK**

### Rename
1. Rename body to `False_Floor`

## Verification
- False floor edges extend into dados
- Top surface at Z=356
- Doesn't interfere with back panel

## Checkpoint: Enclosure Complete
You should now have 6 bodies:
- Bottom_Panel, Top_Panel, Left_Panel, Right_Panel
- Back_Panel
- False_Floor


