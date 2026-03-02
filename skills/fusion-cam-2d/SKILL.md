---
name: fusion-cam-2d
description: Create 2D/2.5D milling operations in Fusion 360 — contour, pocket, adaptive, drilling, face, engrave, trace, slot, chamfer, and miter clearing. Use when the user asks to create CAM toolpaths for flat or prismatic parts, cut profiles, clear pockets, drill holes, engrave text, make V-bit miter cuts, or manage 2D operation parameters.
---

# Fusion 360 CAM 2D/2.5D Milling Operations

Create 2D toolpath operations via `tools/fusion-cam-2d`. All dimensions are mm. Output is JSON.

## Orient yourself first

Before creating operations, make sure a setup exists:

```bash
tools/fusion-cam-setup list                  # check for existing setups
tools/fusion-cam-setup operations            # see current operations
tools/fusion-cam-setup tools                 # available cutting tools
```

If no setup exists, create one first with `tools/fusion-cam-setup create`.

## Operations at a glance

| Operation | Strategy ID | Best for |
|-----------|------------|----------|
| `contour` | contour2d | Profile cuts, outside/inside edges |
| `pocket` | pocket2d | Clearing enclosed areas |
| `adaptive` | adaptive2d | Aggressive clearing (constant engagement) |
| `face` | face | Flattening top surface |
| `drill` | drill | Holes (standard, peck, deep peck) |
| `bore` | bore | Precision hole finishing |
| `engrave` | engrave | Following curves at shallow depth |
| `trace` | trace | V-bit cuts, miter joints (multi-depth) |
| `slot` | slot | Slot milling |
| `chamfer` | chamfer2d | Edge deburring / chamfering |
| `miter-clearing` | (multi-contour) | Terraced roughing for miter cuts |

## Contour (profile cutting)

The most common operation — follows the outside or inside edges of a part.

```bash
# Basic profile cut
tools/fusion-cam-2d contour --name "Profile Cut" --depth 19

# With tabs to hold parts
tools/fusion-cam-2d contour --name "Cutout" --depth 19 --tabs --tab-height 3 --tab-width 5

# With specific tool
tools/fusion-cam-2d contour --name "Finish Pass" --depth 19 --tool-number 3

# With stepdown and climb cutting
tools/fusion-cam-2d contour --name "Heavy Cut" --depth 25 --stepdown 5 --compensation left

# Advanced contour with tool diameter / V-bit angle control
tools/fusion-cam-2d contour-advanced --name "V-Cut" --depth 8 --tool-diameter 25 --tool-angle 90
```

## Pocket (area clearance)

Clears material from enclosed areas. Uses a back-and-forth raster pattern.

```bash
# Basic pocket
tools/fusion-cam-2d pocket --name "Dado" --depth 10

# With stepover control
tools/fusion-cam-2d pocket --name "Wide Pocket" --depth 10 --stepover 3

# Leave stock for finish pass
tools/fusion-cam-2d pocket --name "Rough Pocket" --depth 10 --stock-to-leave 0.5
```

## Adaptive clearing (constant engagement)

Fusion's killer 2D strategy — maintains constant tool engagement for faster, safer cutting. Better tool life and surface finish than pocket.

```bash
# Basic adaptive clearing
tools/fusion-cam-2d adaptive --name "Rough" --depth 19 --stepdown 4

# With optimal load (radial engagement)
tools/fusion-cam-2d adaptive --name "Aggressive Rough" --depth 19 --optimal-load 3

# Bi-directional for faster clearing
tools/fusion-cam-2d adaptive --name "Fast Clear" --depth 19 --optimal-load 3 --both-ways
```

## Facing

Flattens the top surface of stock. Run this first if your stock isn't perfectly flat.

```bash
tools/fusion-cam-2d face --name "Face Top" --stepover 15
tools/fusion-cam-2d face --name "Face Top" --depth 1 --stepover 10
```

## Drilling

Standard drilling cycles with peck and dwell support.

```bash
# Basic drill
tools/fusion-cam-2d drill --name "3mm Holes" --depth 20 --tool-number 5

# Peck drilling (chip breaking — for deep holes)
tools/fusion-cam-2d drill --name "Deep Holes" --depth 30 --peck-depth 5 --cycle peck

# Deep peck drilling (full retract between pecks)
tools/fusion-cam-2d drill --name "Very Deep" --depth 50 --peck-depth 5 --cycle deep_peck

# With dwell at bottom
tools/fusion-cam-2d drill --name "Precision" --depth 15 --dwell 0.5
```

### Drill cycles

| Cycle | Description |
|-------|-------------|
| `drill` | Standard drilling (plunge to depth) |
| `peck` | Chip breaking (short retract between pecks) |
| `deep_peck` | Deep drilling (full retract between pecks) |
| `tap` | Tapping cycle |
| `bore` | Boring cycle |

## Bore

Precision hole finishing for already-drilled holes.

```bash
tools/fusion-cam-2d bore --name "Finish Bore" --depth 15 --diameter 10
```

## Engrave

Follows sketch curves at a shallow depth. Great for text, logos, decorative lines.

```bash
tools/fusion-cam-2d engrave --name "Logo" --depth 0.5
tools/fusion-cam-2d engrave --name "Text" --depth 0.3 --tolerance 0.005
```

## Trace (V-bit cuts)

Follows sketch curves with depth control and multi-pass support. Ideal for V-bit miter joints and decorative V-carving.

```bash
# Basic trace with V-bit
tools/fusion-cam-2d trace --name "V-Groove" --sketch GrooveLines --depth 5

# Multi-depth for heavy cuts
tools/fusion-cam-2d trace --name "Miter Cut" --sketch MiterLines --depth 8 --stepdown 2

# With specific number of passes
tools/fusion-cam-2d trace --name "Slow Miter" --sketch MiterLines --depth 8 --passes 4

# With tool from library
tools/fusion-cam-2d trace --name "V-Miter" --sketch MiterLines --depth 8 --tool-number 2
```

## Slot milling

Dedicated slot strategy — better chip evacuation than pocket for narrow features.

```bash
tools/fusion-cam-2d slot --name "T-Slot" --depth 12 --stepdown 4
```

## 2D Chamfer

Edge deburring — follows edges with an angled tool to create chamfers.

```bash
tools/fusion-cam-2d chamfer --name "Edge Break" --chamfer-width 1
tools/fusion-cam-2d chamfer --name "Chamfer" --chamfer-width 2 --tip-offset 0.5
```

## Miter clearing (terraced roughing)

Creates multiple contour operations at progressive depths for V-bit miter joint preparation. Each terrace is offset inward based on the miter angle.

```bash
# Standard 45° miter clearing (4 terraces)
tools/fusion-cam-2d miter-clearing --depth 18 --steps 4 --tool-diameter 6

# Custom angle and finish stock
tools/fusion-cam-2d miter-clearing --depth 12 --steps 3 --miter-angle 30 --stock-for-finish 0.5

# Fine terraces with small stepdown
tools/fusion-cam-2d miter-clearing --depth 18 --steps 6 --stepdown 2
```

## Common parameters (all operations)

These flags work on most operations:

```bash
--setup "Setup Name"         # target setup (defaults to last)
--name "Operation Name"      # operation display name
--depth 19                   # cut depth in mm
--stepdown 4                 # max depth per pass
--stock-to-leave 0.5         # radial stock for finish
--floor-stock 0.2            # floor stock for finish
--compensation left          # left (climb) / right (conventional) / center / off
--boundary silhouette        # auto-detect geometry
--tool-number 3              # tool from library by number
--tool-type "flat end mill"  # find tool by type
--ramp helix                 # entry strategy: helix / plunge / ramp / profile
--tabs                       # enable holding tabs
--tab-height 3               # tab height in mm
--tab-width 5                # tab width in mm
--tab-count 4                # number of tabs
--clearance-height 30        # clearance from stock top
--retract-height 10          # retract from stock top
--feed-height 5              # feed engage from stock top
```

## Operation management

```bash
# Edit an existing operation
tools/fusion-cam-2d edit --operation "2D Contour" --depth 20 --stock-to-leave 0.5

# Edit raw parameters
tools/fusion-cam-2d edit --operation "2D Contour" --params bottomHeight_offset="-20 mm"

# Read current values of specific parameters
tools/fusion-cam-2d read-params --operation "2D Contour" --params bottomHeight_offset stockToLeave maximumStepdown

# Duplicate an operation with all settings
tools/fusion-cam-2d duplicate --operation "2D Contour" --new-name "Final Profile"
tools/fusion-cam-2d duplicate --operation "2D Contour"   # keeps auto-generated name

# Rename
tools/fusion-cam-2d edit --operation "2D Contour" --new-name "Final Profile"

# Suppress / unsuppress (skip without deleting)
tools/fusion-cam-2d suppress --operation "Rough Pass"
tools/fusion-cam-2d unsuppress --operation "Rough Pass"

# Reorder in the setup
tools/fusion-cam-2d reorder --operation "Face" --direction up

# Delete
tools/fusion-cam-2d delete --operation "Old Pocket"
```

## Decision guide

| I want to... | Command |
|--------------|---------|
| Cut out a part | `contour --depth D --tabs` |
| Clear a pocket | `pocket --depth D --stepover S` or `adaptive --depth D` |
| Flatten the top | `face --stepover S` |
| Drill holes | `drill --depth D --tool-number N` |
| Engrave text/logo | `engrave --depth 0.5` |
| V-bit miter cut | `trace --sketch S --depth D --stepdown S` |
| Prep for V-bit | `miter-clearing --depth D --steps N` |
| Break edges | `chamfer --chamfer-width W` |
| Heavy roughing | `adaptive --depth D --optimal-load L --stepdown S` |
| Edit a parameter | `edit --operation O --depth D` |
| Skip an operation | `suppress --operation O` |

## Common patterns

### Profile cut with tabs

```bash
tools/fusion-cam-2d adaptive --name "Rough" --depth 19 --stepdown 4 --stock-to-leave 1
tools/fusion-cam-2d contour --name "Finish Profile" --depth 19 --tabs --tab-height 3
```

### Pocket with roughing + finishing

```bash
tools/fusion-cam-2d adaptive --name "Rough Pocket" --depth 10 --stock-to-leave 0.5
tools/fusion-cam-2d pocket --name "Finish Pocket" --depth 10 --stepover 1
```

### V-bit miter workflow

```bash
tools/fusion-cam-2d miter-clearing --depth 18 --steps 4 --tool-diameter 6
tools/fusion-cam-2d trace --name "V-Miter Finish" --sketch MiterLines --depth 18 --stepdown 3 --tool-number 2
```

### Face → rough → finish → cutout

```bash
tools/fusion-cam-2d face --name "Face" --stepover 15
tools/fusion-cam-2d adaptive --name "Rough" --depth 19 --stepdown 4 --stock-to-leave 1
tools/fusion-cam-2d contour --name "Finish Walls" --depth 19 --stock-to-leave 0
tools/fusion-cam-2d contour --name "Cutout" --depth 20 --tabs --tab-height 3
```

## Recommended workflow

### Duplicate-and-edit pattern

Instead of creating operations from scratch, duplicate an existing one:

```bash
tools/fusion-cam-2d duplicate --operation "2D Contour" --new-name "Final Profile"
tools/fusion-cam-2d edit --operation "Final Profile" --stock-to-leave 0
```

This preserves tool, boundary, and heights from the source.

## Key parameter names

| What you want | Fusion parameter name | Example expression |
|---|---|---|
| Depth (bottom height) | `bottomHeight_offset` | `-19 mm` |
| Stock to leave | `stockToLeave` | `0.5 mm` |
| Floor stock | `stockToLeaveFloor` | `0.2 mm` |
| Boundary mode | `machiningBoundary` | `'silhouette'` |
| Stepdown | `maximumStepdown` | `3 mm` |
| Multiple depths | `useMultipleDepths` | `true` |
| Tab height | `tabHeight` | `3 mm` |
| Compensation | `sidewaysCompensation` | `'left (climb)'` |

## Common mistakes

- **No setup exists** — create one with `tools/fusion-cam-setup create` first
- **Operations show no geometry** — run `tools/fusion-cam-setup set-model` or `silhouette`
- **Forgot to generate** — after creating operations, run `tools/fusion-cam-setup generate`
- **Tabs on pocket** — tabs only work on contour operations (profile cuts)
- **Adaptive vs pocket** — use adaptive for heavy roughing (constant engagement = less tool stress), pocket for lighter finishing
- **Depth is stock-relative** — depth 19 means 19mm from the stock top face, not from WCS origin
- **Setting depth with negative values** — pass positive depth values, the handler negates automatically
