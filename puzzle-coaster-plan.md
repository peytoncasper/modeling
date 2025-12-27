# Puzzle Piece Coasters - Build Plan

## Dimensions

| Element | Dimension |
|---------|-----------|
| Base square | 90mm × 90mm |
| Thickness | 8mm |
| Tab (knob) diameter | 24mm (radius 12mm) |
| Tab protrusion | 12mm beyond edge |
| Edge fillets | 2mm |
| Corner radius | 8mm |

## Puzzle Configuration (2×2 Grid)

```
┌─────────┬─────────┐
│  Piece1 ◄► Piece2 │
│    ▲         ▲    │
│    ▼         ▼    │
│  Piece3 ◄► Piece4 │
└─────────┴─────────┘
```

| Piece | Right | Bottom | Left | Top |
|-------|-------|--------|------|-----|
| 1 (top-left) | Tab ► | Tab ▼ | Flat | Flat |
| 2 (top-right) | Flat | Tab ▼ | Blank ◄ | Flat |
| 3 (bottom-left) | Tab ► | Flat | Flat | Blank ▲ |
| 4 (bottom-right) | Flat | Flat | Blank ◄ | Blank ▲ |

## Tool Call Sequence

### Phase 1: Setup
1. `fusion_new_document(name="PuzzleCoasters")`
2. `fusion_create_parameter(name="base_size", value=90, unit="mm")`
3. `fusion_create_parameter(name="thickness", value=8, unit="mm")`
4. `fusion_create_parameter(name="tab_diameter", value=24, unit="mm")`
5. `fusion_create_parameter(name="tab_offset", value=12, unit="mm")`
6. `fusion_create_parameter(name="corner_radius", value=8, unit="mm")`
7. `fusion_create_parameter(name="edge_fillet", value=2, unit="mm")`

### Phase 2: Create Piece 1 (Tabs on Right & Bottom)
8. `fusion_create_sketch(plane="xy", name="Piece1_Sketch")`
9. Draw base square: `fusion_draw_rectangle(corner1=[0,0], corner2=[90,90])`
10. Right tab circle: `fusion_draw_circle(center=[90, 45], radius=12)`
11. Bottom tab circle: `fusion_draw_circle(center=[45, 0], radius=12)`
12. `fusion_finish_sketch(sketch_id="Piece1_Sketch")`
13. `fusion_get_sketch_profiles(sketch_id="Piece1_Sketch")`
14. `fusion_extrude(sketch_id="Piece1_Sketch", distance=8, profile_index=<largest>)`
15. `fusion_list_edges(body_id="Piece1")`
16. `fusion_fillet_edges(edge_ids=[...], radius=2)`
17. `fusion_apply_appearance(body_id="Piece1", appearance="Walnut")`

### Phase 3: Create Piece 2 (Blank on Left, Tab on Bottom)
- Offset X by 110mm (90 + 20 gap)
- Base square with left side indented for blank
- Circle cut on left side (boolean subtract)
- Tab circle on bottom

### Phase 4: Create Piece 3 (Tab on Right, Blank on Top)
- Offset Y by -110mm
- Tab on right, blank on top

### Phase 5: Create Piece 4 (Blanks on Left & Top)
- Offset X by 110mm, Y by -110mm
- Blanks on left and top (no tabs)

### Phase 6: Final
- `fusion_set_view(preset="isometric", fit=true)`
- `fusion_take_screenshot()`
- `fusion_export(format="stl", path="puzzle_coasters.stl")`

## Sketch Geometry Detail

### Piece 1 (Top-Left Corner Piece)
```
              Tab
               ●
        ┌──────┴──────┐
        │             │
        │    BASE     ●── Tab
        │   90×90     │
        │             │
        └─────────────┘
```

### Key Coordinates for Each Piece

**Piece 1** (origin at 0,0):
- Square: (0,0) to (90,90)
- Right tab center: (90, 45)
- Bottom tab center: (45, 0)

**Piece 2** (origin at 110,0):
- Square: (110,0) to (200,90)
- Left blank center: (110, 45) - cut
- Bottom tab center: (155, 0)

**Piece 3** (origin at 0,-110):
- Square: (0,-110) to (90,-20)
- Right tab center: (90, -65)
- Top blank center: (45, -20) - cut

**Piece 4** (origin at 110,-110):
- Square: (110,-110) to (200,-20)
- Left blank center: (110, -65) - cut
- Top blank center: (155, -20) - cut


