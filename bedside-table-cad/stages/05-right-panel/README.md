# Stage 05: Right Panel

## Prerequisites
- Stage 04 complete (left panel exists)

## Goals
1. **Create right side panel** - vertical panel on -X side
2. **Mirror of left panel** position

## Success Criteria
- [ ] Body named "Right_Panel" exists
- [ ] Dimensions: 19 × 400 × 579mm
- [ ] X range: -225 to -206 (inner face at X=-206)

## Fusion Steps

### Option A: Copy Left Panel
1. **Modify > Move/Copy**
2. Select `Left_Panel` body
3. Check **Create Copy**
4. Move Type: **Translate**
5. X Distance: `-431` mm (from X=206 to X=-225)
6. Click **OK**
7. Rename copy to `Right_Panel`

### Option B: Create from Sketch
1. **Create Sketch** on YZ plane
2. **Draw Rectangle**
   - Corner 1: `(-200, 0)`
   - Corner 2: `(200, 579)`
3. **Finish Sketch**
4. **Extrude** 19mm
5. Start offset: `-225` mm (toward -X)
6. Rename to `Right_Panel`

## Verification
- 4 panels now form a rectangular tube
- Panels overlap at corners (will be mitered later)
- Internal width: 412mm (225-19 to -225+19 = 206 to -206)

## Checkpoint: Basic Box Complete
You should now have 4 bodies:
- Bottom_Panel
- Top_Panel
- Left_Panel
- Right_Panel









