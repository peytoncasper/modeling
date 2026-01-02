# Stage 11: Bottom Corner Miters

## Prerequisites
- Stage 10 complete (top miters cut)

## Goals
1. **Cut 45° miters** at bottom-left corner
2. **Cut 45° miters** at bottom-right corner

## Success Criteria
- [ ] Bottom-left corner shows diagonal miter line
- [ ] Bottom-right corner shows diagonal miter line
- [ ] All 4 corners now have clean miter joints

## Miter Geometry

### Bottom-Left Corner (X=206-225, Z=0-19)
### Bottom-Right Corner (X=-225 to -206, Z=0-19)

## Fusion Steps

### Bottom-Left: Cut Bottom Panel
1. **Create Sketch** on XZ plane
2. **Draw Triangle**:
   - Point A: `(206, 0)` — inner bottom
   - Point B: `(225, 0)` — outer bottom
   - Point C: `(225, 19)` — outer top
3. **Finish Sketch**
4. **Extrude Cut** through `Bottom_Panel` (400mm depth)

### Bottom-Left: Cut Left Panel
1. **Create Sketch** on XZ plane
2. **Draw Triangle**:
   - Point A: `(206, 0)`
   - Point B: `(206, 19)`
   - Point C: `(225, 19)`
3. **Extrude Cut** through `Left_Panel`

### Bottom-Right: Cut Bottom Panel
1. **Create Sketch** on XZ plane
2. **Draw Triangle**:
   - Point A: `(-206, 0)`
   - Point B: `(-225, 0)`
   - Point C: `(-225, 19)`
3. **Extrude Cut** through `Bottom_Panel`

### Bottom-Right: Cut Right Panel
1. **Create Sketch** on XZ plane
2. **Draw Triangle**:
   - Point A: `(-206, 0)`
   - Point B: `(-206, 19)`
   - Point C: `(-225, 19)`
3. **Extrude Cut** through `Right_Panel`

## Verification
- All 4 corners show clean diagonal miter lines
- No overlapping geometry between panels
- Carcass still forms closed box

## Checkpoint: Miters Complete
All corner joints are now 45° miters.


