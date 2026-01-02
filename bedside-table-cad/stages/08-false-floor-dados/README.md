# Stage 08: False Floor Dados

## Prerequisites
- Stage 07 complete (back panel installed)

## Goals
1. **Cut dados** in left and right panels for false floor
2. **Dado position**: Z=344mm (top of dado)

## Success Criteria
- [ ] Left_Panel has horizontal groove at Z=344
- [ ] Right_Panel has matching groove
- [ ] Dados are 6mm deep × 12mm tall

## Dado Dimensions
- **Depth**: 6mm (into panel from inner face)
- **Width/Height**: 12mm (matches false floor thickness)
- **Z position**: 344 to 356 (false floor sits here)
- **Y extent**: -200 to ~169 (stopped dado, doesn't go to back)

## Fusion Steps

### Left Panel Dado
1. **Create Sketch** on inner face of Left_Panel (X=206)
2. **Draw Rectangle** (in YZ plane, where Y is horizontal, Z is vertical)
   - Corner 1: `(-200, 344)` — front edge, bottom of dado
   - Corner 2: `(169, 356)` — stopped before back, top of dado
3. **Finish Sketch**
4. **Extrude** as **Cut**
   - Distance: `6` mm (toward +X, into panel)
   - Select Body: `Left_Panel`

### Right Panel Dado
1. **Create Sketch** on inner face of Right_Panel (X=-206)
2. **Draw Rectangle**
   - Corner 1: `(-200, 344)`
   - Corner 2: `(169, 356)`
3. **Finish Sketch**
4. **Extrude** as **Cut**
   - Distance: `6` mm (toward -X, into panel)
   - Select Body: `Right_Panel`

## Verification
- Section view shows horizontal grooves in side panels
- Dados align at same Z height
- Dados stop before reaching back panel


