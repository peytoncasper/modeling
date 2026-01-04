# Stage 14: Plinth Base

## Prerequisites
- Stage 13 complete (corner blocks installed)

## Goals
1. **Create plinth** - inset base platform
2. **Position below cabinet** at Z=-40 to Z=0

## Success Criteria
- [ ] Body named "Plinth" exists
- [ ] Plinth is inset 25mm from cabinet edges
- [ ] Dimensions: 400 × 350 × 40mm

## Plinth Dimensions
- **Width**: 400mm (cabinet width minus 2×25mm inset)
- **Depth**: 350mm (cabinet depth minus 2×25mm inset)
- **Height**: 40mm
- **Inset**: 25mm from all cabinet edges

## Position
- **X**: -200 to 200 (centered)
- **Y**: -175 to 175 (centered)
- **Z**: -40 to 0 (below cabinet)

## Fusion Steps

### Create Sketch
1. **Create Offset Plane** at Z=-40 (below origin)
2. **Create Sketch** on offset plane
3. **Draw Rectangle**
   - Corner 1: `(-200, -175)`
   - Corner 2: `(200, 175)`
4. **Finish Sketch**

### Extrude
1. **Create > Extrude**
2. Select rectangle profile
3. Distance: `40` mm
4. Direction: **Positive** (+Z, up to Z=0)
5. Operation: **New Body**
6. Click **OK**

### Rename
1. Rename body to `Plinth`

## Verification
- Plinth top surface meets cabinet bottom
- 25mm gap visible between plinth edge and cabinet edge (all sides)
- Plinth is centered under cabinet









