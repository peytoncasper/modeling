# Stage 12: Top Corner Blocks

## Prerequisites
- Stage 11 complete (all miters cut)

## Goals
1. **Create 4 corner blocks** for top corners
2. **Position**: 2 per top corner (front and rear)

## Success Criteria
- [ ] 4 triangular blocks at top corners
- [ ] Blocks sit flush against both panels
- [ ] Front blocks at Y=60, rear blocks at Y=334

## Corner Block Dimensions
- **Leg length**: 50mm (right-angle triangle)
- **Extrusion**: 80mm along Y
- **Material**: Hardwood

## Positions
| Block | Corner | Y Center | Y Range |
|-------|--------|----------|---------|
| TL_front | Top-Left | 60 | 20 to 100 |
| TL_rear | Top-Left | 334 | 294 to 374 |
| TR_front | Top-Right | 60 | 20 to 100 |
| TR_rear | Top-Right | 334 | 294 to 374 |

## Fusion Steps

### Top-Left Front Block
1. **Create Sketch** on XZ plane at Y=20
2. **Draw Triangle**:
   - Point A: `(206, 560)` — corner (inner faces meet)
   - Point B: `(206, 510)` — down 50mm
   - Point C: `(156, 560)` — left 50mm
3. **Finish Sketch**
4. **Extrude** as **New Body**
   - Distance: `80` mm (+Y direction)
5. Rename to `CornerBlock_TL_Front`

### Top-Left Rear Block
1. **Copy** TL_front block
2. **Move** to Y=294 (or create new at that position)
3. Rename to `CornerBlock_TL_Rear`

### Top-Right Front Block
1. **Create Sketch** on XZ plane at Y=20
2. **Draw Triangle**:
   - Point A: `(-206, 560)`
   - Point B: `(-206, 510)`
   - Point C: `(-156, 560)`
3. **Extrude** 80mm, rename to `CornerBlock_TR_Front`

### Top-Right Rear Block
1. **Copy** and move, or create new
2. Rename to `CornerBlock_TR_Rear`

## Verification
- 4 blocks visible at top corners
- Blocks don't interfere with back panel (rear blocks end before Y=394)








