# Stage 10: Top Corner Miters

## Prerequisites
- Stage 09 complete (all enclosure parts exist)

## Goals
1. **Cut 45° miters** at top-left corner
2. **Cut 45° miters** at top-right corner

## Success Criteria
- [ ] Top-left corner shows diagonal miter line
- [ ] Top-right corner shows diagonal miter line
- [ ] No overlap between top panel and side panels at top

## Miter Geometry
Each corner has a 19×19mm overlap zone. We cut triangular prisms to create the miter.

### Top-Left Corner (X=206-225, Z=560-579)
```
Before:        After:
┌────┬──┐     ┌────╲──┐
│TOP │L │     │TOP  ╲ │
├────┤E │  →  │      ╲│
│    │FT│     │       │
```

### Top-Right Corner (X=-225 to -206, Z=560-579)
Mirror of top-left.

## Fusion Steps

### Top-Left: Cut Top Panel
1. **Create Sketch** on XZ plane (or front face)
2. **Draw Triangle** with 3 lines:
   - Point A: `(206, 579)` — inner top
   - Point B: `(225, 579)` — outer top
   - Point C: `(225, 560)` — outer bottom
3. **Finish Sketch**
4. **Extrude** as **Cut**
   - Distance: `400` mm (full depth, symmetric or one-side)
   - Select Body: `Top_Panel`

### Top-Left: Cut Left Panel
1. **Create Sketch** on XZ plane
2. **Draw Triangle**:
   - Point A: `(206, 579)`
   - Point B: `(206, 560)`
   - Point C: `(225, 560)`
3. **Extrude Cut** through `Left_Panel`

### Top-Right: Cut Top Panel
1. **Create Sketch** on XZ plane
2. **Draw Triangle**:
   - Point A: `(-206, 579)`
   - Point B: `(-225, 579)`
   - Point C: `(-225, 560)`
3. **Extrude Cut** through `Top_Panel`

### Top-Right: Cut Right Panel
1. **Create Sketch** on XZ plane
2. **Draw Triangle**:
   - Point A: `(-206, 579)`
   - Point B: `(-206, 560)`
   - Point C: `(-225, 560)`
3. **Extrude Cut** through `Right_Panel`

## Verification
- View from front: diagonal lines at top corners
- Section view: clean 45° meeting faces








