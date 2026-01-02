# Stage 13: Bottom Corner Blocks

## Prerequisites
- Stage 12 complete (top corner blocks exist)

## Goals
1. **Create 4 corner blocks** for bottom corners
2. **Position**: 2 per bottom corner (front and rear)

## Success Criteria
- [ ] 4 triangular blocks at bottom corners
- [ ] Total of 8 corner blocks in model
- [ ] Blocks sit in interior corners at Z=19

## Positions
| Block | Corner | Y Center | Y Range |
|-------|--------|----------|---------|
| BL_front | Bottom-Left | 60 | 20 to 100 |
| BL_rear | Bottom-Left | 334 | 294 to 374 |
| BR_front | Bottom-Right | 60 | 20 to 100 |
| BR_rear | Bottom-Right | 334 | 294 to 374 |

## Fusion Steps

### Bottom-Left Front Block
1. **Create Sketch** on XZ plane at Y=20
2. **Draw Triangle**:
   - Point A: `(206, 19)` — corner at panel inner faces
   - Point B: `(206, 69)` — up 50mm
   - Point C: `(156, 19)` — left 50mm
3. **Finish Sketch**
4. **Extrude** 80mm (+Y)
5. Rename to `CornerBlock_BL_Front`

### Bottom-Left Rear Block
1. Copy and move to Y=294, or create new
2. Rename to `CornerBlock_BL_Rear`

### Bottom-Right Front Block
1. **Draw Triangle**:
   - Point A: `(-206, 19)`
   - Point B: `(-206, 69)`
   - Point C: `(-156, 19)`
2. **Extrude** 80mm
3. Rename to `CornerBlock_BR_Front`

### Bottom-Right Rear Block
1. Copy and move, or create new
2. Rename to `CornerBlock_BR_Rear`

## Verification
- 8 total corner blocks
- Bottom blocks sit on top of bottom panel inner face (Z=19)
- No interference with false floor (which is at Z=344)

## Checkpoint: Reinforcement Complete
All 8 corner blocks installed.


