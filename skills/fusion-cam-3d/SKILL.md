---
name: fusion-cam-3d
description: Create 3D surface machining operations in Fusion 360 — adaptive clearing, pocket, parallel, scallop, pencil, contour (waterline), steep & shallow, horizontal, radial, spiral, morphed spiral, and flow. Use when the user asks to machine complex 3D surfaces, create finishing toolpaths, rough 3D geometry, use ball end mills, set scallop height, do rest machining, or create multi-axis style operations.
---

# Fusion 360 CAM 3D Milling Operations

Create 3D surface machining operations via `tools/fusion-cam-3d`. All dimensions are mm. Output is JSON.

## Orient yourself first

Before creating 3D operations, verify setup and available tools:

```bash
tools/fusion-cam-setup list                  # check for setups
tools/fusion-cam-setup operations            # existing operations
tools/fusion-cam-setup tools --type ball_end # check for ball end mills
```

If no setup exists, create one first with `tools/fusion-cam-setup create`.

## When to use 3D vs 2D

| Use 2D operations when... | Use 3D operations when... |
|---------------------------|--------------------------|
| Part is flat / prismatic | Part has curved surfaces |
| Vertical walls, flat floors | Sculpted / organic shapes |
| Pockets with flat bottoms | Mold cavities, dies |
| Simple profile cuts | Surface finishing quality matters |
| Drilling holes | Rest machining (remaining stock) |

## Operations at a glance

### Roughing (material removal)

| Operation | Best for |
|-----------|----------|
| `adaptive` | Heavy roughing — constant engagement, fastest |
| `pocket` | Roughing with parallel passes |

### Finishing (surface quality)

| Operation | Best for |
|-----------|----------|
| `parallel` | General finishing — raster pattern |
| `scallop` [Extension] | Constant scallop height — best surface quality |
| `pencil` [Extension] | Inside corners and fillets |
| `contour` [Extension] | Waterline / Z-level — steep walls |
| `steep-shallow` [Extension] | Combined strategy — auto picks steep vs. shallow |
| `horizontal` | Flat areas only |
| `radial` | Round parts — passes radiate from center |
| `spiral` | Round parts — continuous spiral |
| `morphed-spiral` [Extension] | Freeform surfaces with guided spirals |
| `flow` [Extension] | UV-aligned finishing (guided by surface flow) |

## License requirements

Operations marked [Extension] require the Fusion 360 Manufacturing Extension. If your license doesn't include it, the handler returns a clear error message suggesting alternatives. Stick to: `adaptive`, `pocket`, `parallel`, `horizontal`, `radial`, `spiral` on a basic license.

## 3D Roughing

### 3D Adaptive Clearing

The best roughing strategy — maintains constant tool engagement for maximum material removal with minimum tool stress. Always start here for 3D parts.

```bash
# Basic 3D adaptive
tools/fusion-cam-3d adaptive --name "Rough" --stepdown 3 --stock-to-leave 0.5

# With optimal load control
tools/fusion-cam-3d adaptive --name "Heavy Rough" --stepdown 4 --optimal-load 3

# Leave stock for finishing
tools/fusion-cam-3d adaptive --name "Rough" --stepdown 3 --stock-to-leave 0.5 --axial-stock 0.2

# Bi-directional for faster clearing
tools/fusion-cam-3d adaptive --name "Fast Rough" --optimal-load 3 --both-ways

# With flat area detection
tools/fusion-cam-3d adaptive --name "Rough" --stepdown 3 --flat-area-detection
```

### 3D Pocket Clearing

Traditional roughing with parallel passes at each Z-level.

```bash
tools/fusion-cam-3d pocket --name "Pocket Rough" --stepdown 2 --stock-to-leave 0.5
tools/fusion-cam-3d pocket --name "Pocket Rough" --stepdown 2 --direction climb
```

## 3D Finishing

### Parallel (raster)

General-purpose finishing. Passes are parallel lines across the model. Good starting point for most finishes.

```bash
# Basic parallel finish
tools/fusion-cam-3d parallel --name "Finish" --stepover 0.5

# At 45° angle
tools/fusion-cam-3d parallel --name "Finish 45" --stepover 0.3 --pass-angle 45

# Zero stock to leave (final pass)
tools/fusion-cam-3d parallel --name "Final" --stepover 0.3 --stock-to-leave 0

# Both directions
tools/fusion-cam-3d parallel --name "Cross Finish" --stepover 0.5 --direction both
```

### Scallop

Constant scallop height — produces the most uniform surface quality. Passes follow the surface contours. Best for organic shapes.

```bash
tools/fusion-cam-3d scallop --name "Scallop Finish" --scallop-height 0.1
tools/fusion-cam-3d scallop --name "Fine Scallop" --scallop-height 0.05 --tolerance 0.005
```

### Pencil

Cleans inside corners and fillets that larger tools can't reach. Run after parallel/scallop to clean up remaining material in tight areas.

```bash
tools/fusion-cam-3d pencil --name "Corners" --tool-number 5
tools/fusion-cam-3d pencil --name "Fillets" --stock-to-leave 0
```

### 3D Contour (waterline / Z-level)

Cuts at constant Z-heights. Excellent for steep walls where parallel leaves poor finish.

```bash
tools/fusion-cam-3d contour --name "Walls" --stepdown 0.5
tools/fusion-cam-3d contour --name "Fine Walls" --stepdown 0.2 --stock-to-leave 0
```

### Steep & Shallow

Automatically combines waterline (steep areas) and raster (shallow areas) into one operation. Best all-around strategy when you don't know the geometry well.

```bash
# Default threshold (45°)
tools/fusion-cam-3d steep-shallow --name "Combined" --stepover 0.5

# Custom threshold angle
tools/fusion-cam-3d steep-shallow --name "Combined" \
  --threshold-angle 40 --steep-stepdown 0.3 --shallow-stepover 0.5
```

### Horizontal

Finishes only flat/horizontal areas. Use after contour or parallel to clean up flats.

```bash
tools/fusion-cam-3d horizontal --name "Flats"
```

### Radial

Passes radiate from a center point. Good for round parts, bowls, domes.

```bash
tools/fusion-cam-3d radial --name "Radial Finish" --center 0,0 --stepover 0.5
```

### Spiral

Continuous spiral from outside in (or inside out). Good for round parts — no retract moves.

```bash
tools/fusion-cam-3d spiral --name "Spiral Finish" --stepover 0.5
```

### Morphed Spiral

Like spiral but guided by the surface shape. Good for freeform surfaces with complex boundaries.

```bash
tools/fusion-cam-3d morphed-spiral --name "Morphed" --stepover 0.3
```

### Flow

Follows the UV curves of the surface. Best when the surface has strong directional flow (like an airfoil or boat hull).

```bash
tools/fusion-cam-3d flow --name "Flow Finish" --stepover 0.3
```

## Common parameters (all 3D operations)

```bash
--setup "Setup Name"         # target setup (defaults to last)
--name "Operation Name"      # display name
--stock-to-leave 0.5         # radial stock to leave (mm)
--axial-stock 0.2            # axial stock to leave (mm)
--stepover 0.5               # lateral step between passes (mm)
--stepdown 3                 # vertical step between levels (mm)
--tolerance 0.01             # surface tolerance (mm)
--boundary silhouette        # auto-detect machining boundary
--tool-number 3              # select tool from library
--tool-type "ball end mill"  # find tool by type
--rest-machining             # only cut remaining stock
--clearance-height 30        # clearance from stock top (mm)
--retract-height 10          # retract from stock top (mm)
--top-height 0               # top height offset (mm)
--bottom-height 20           # bottom height (mm)
--top-from stock top         # top height reference: 'stock top', 'model top' (default: 'stock top')
--bottom-from stock bottom   # bottom height reference: 'stock bottom', 'model bottom' (default: 'stock bottom')
```

## Operation management

```bash
# Read current values of specific parameters
tools/fusion-cam-3d read-params --operation "Parallel" --params stockToLeave stepover topHeight_mode

# Duplicate an operation with all settings (tool, params, boundary)
tools/fusion-cam-3d duplicate --operation "Adaptive1" --new-name "Finish Pass"

# Edit an existing operation
tools/fusion-cam-3d edit --operation "Parallel" --stepover 0.3 --stock-to-leave 0

# Edit raw parameters
tools/fusion-cam-3d edit --operation "Adaptive" --params optimalLoad="2.5 mm"

# Rename
tools/fusion-cam-3d edit --operation "Parallel" --new-name "Final Finish"

# Suppress / unsuppress
tools/fusion-cam-3d suppress --operation "Scallop"
tools/fusion-cam-3d unsuppress --operation "Scallop"

# Delete
tools/fusion-cam-3d delete --operation "Old Rough"
```

## Decision guide

| I want to... | Command |
|--------------|---------|
| Rough a 3D part | `adaptive --stepdown 3 --stock-to-leave 0.5` |
| General finish | `parallel --stepover 0.5` |
| Best surface quality | `scallop --scallop-height 0.1` |
| Clean inside corners | `pencil` |
| Finish steep walls | `contour --stepdown 0.5` |
| Auto-pick strategy | `steep-shallow --stepover 0.5` |
| Finish flat areas | `horizontal` |
| Finish a dome/bowl | `spiral --stepover 0.5` or `radial --center x,y` |
| Follow surface flow | `flow --stepover 0.3` |
| Only cut remaining | `parallel --rest-machining --stock-to-leave 0` |
| Edit existing op | `edit --operation O --stepover S` |
| Skip an operation | `suppress --operation O` |

## Common patterns

### Duplicate-and-edit pattern (fastest, most reliable)

Instead of creating operations from scratch, duplicate an existing one that's close to what you want:

```bash
tools/fusion-cam-3d duplicate --operation "Adaptive1" --new-name "Finish Pass"
tools/fusion-cam-3d edit --operation "Finish Pass" --stock-to-leave 0 --stepover 0.5
```

This preserves tool, boundary selection, and heights from the source operation.

### Rough → semi-finish → finish

```bash
# 1. Heavy roughing with 3D adaptive (leave 0.5mm)
tools/fusion-cam-3d adaptive --name "Rough" --stepdown 3 --stock-to-leave 0.5 --tool-number 1

# 2. Semi-finish parallel (leave 0.1mm)
tools/fusion-cam-3d parallel --name "Semi-Finish" --stepover 1.0 --stock-to-leave 0.1 --tool-number 2

# 3. Final scallop finish (zero stock)
tools/fusion-cam-3d scallop --name "Finish" --scallop-height 0.05 --stock-to-leave 0 --tool-number 3

# 4. Clean corners
tools/fusion-cam-3d pencil --name "Corners" --stock-to-leave 0 --tool-number 3
```

### Steep & shallow single-pass

```bash
tools/fusion-cam-3d adaptive --name "Rough" --stepdown 3 --stock-to-leave 0.3
tools/fusion-cam-3d steep-shallow --name "Finish" --stepover 0.3 --stock-to-leave 0
```

### Rest machining (smaller tool cleans up)

```bash
# Large tool roughing
tools/fusion-cam-3d adaptive --name "Rough 12mm" --stepdown 3 --stock-to-leave 0.5 --tool-number 1

# Smaller tool cleans remaining stock
tools/fusion-cam-3d adaptive --name "Rest Rough 6mm" --stepdown 2 --stock-to-leave 0.5 --tool-number 2 --rest-machining
```

## Key parameter names

| What you want | Fusion parameter name | Example expression |
|---|---|---|
| Stock to leave | `stockToLeave` | `0.5 mm` |
| Top height mode | `topHeight_mode` | `'from stock top'` |
| Top height offset | `topHeight_offset` | `-0.5 mm` |
| Bottom height mode | `bottomHeight_mode` | `'from stock bottom'` |
| Bottom height offset | `bottomHeight_offset` | `0 mm` |
| Rest machining | `useRestMachining` | `true` |
| Rest source | `restMaterialSource` | `'previousOperations'` |
| Boundary mode | `boundaryMode` | `'selection'` or `'silhouette'` |
| Pass angle | `passAngle` | `45 deg` |
| Tolerance | `tolerance` | `0.01 mm` |

## Common mistakes

- **Setting height offset without mode** — always set `--top-from`/`--bottom-from` with `--top-height`/`--bottom-height` or use `read-params` first to check current mode
- **Using Extension-only operations without the license** — check your Fusion license tier first, stick to parallel/adaptive/pocket on basic
- **Using parallel on steep walls** — parallel leaves a poor finish on walls >~60°. Use `contour` or `steep-shallow` instead
- **Forgetting rest machining** — when switching to a smaller tool, enable `--rest-machining` to avoid re-cutting already-machined areas
- **Too large stepover** — for ball end mills, stepover should be much less than tool diameter (typically 10-30% of diameter for finishing)
- **No roughing before finishing** — finishing operations assume most material is already removed. Always rough first
- **Wrong tool type** — 3D finishing usually needs ball end mills (spherical tip). Flat end mills leave stair-stepping on curved surfaces
- **Stock to leave mismatch** — roughing should leave >= what the finishing pass expects. If rough leaves 0.5mm, finish should use stock_to_leave=0
