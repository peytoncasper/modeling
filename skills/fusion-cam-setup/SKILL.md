---
name: fusion-cam-setup
description: Manage Fusion 360 CAM setups, stock, WCS, cutting tools, post-processing, and simulation. Use when the user asks to create a CAM setup, configure stock dimensions, set work coordinate system, manage tool libraries, post-process G-code, simulate toolpaths, estimate cycle time, or switch to the Manufacturing workspace.
---

# Fusion 360 CAM Setup / Tools / Post-processing

Control Fusion 360 manufacturing infrastructure via `tools/fusion-cam-setup`. All dimensions are mm. Output is JSON.

## Orient yourself first

Before creating setups, understand the current manufacturing state:

```bash
tools/fusion-cam-setup info                            # are we in Manufacturing workspace?
tools/fusion-cam-setup switch                          # switch to Manufacturing workspace
tools/fusion-cam-setup list                            # list all setups
tools/fusion-cam-setup list --show-params              # with full parameter dump
tools/fusion-cam-setup operations                      # all operations across all setups
tools/fusion-cam-setup tools                           # available cutting tools
```

## Workflow overview

```
1. Switch to Manufacturing workspace     →  tools/fusion-cam-setup switch
2. Create a setup (stock, WCS, model)    →  tools/fusion-cam-setup create ...
3. Set machining model bodies            →  tools/fusion-cam-setup set-model ...
4. Create operations (use fusion-cam-2d / fusion-cam-3d)
5. Generate toolpaths                    →  tools/fusion-cam-setup generate
6. Simulate to verify                    →  tools/fusion-cam-setup simulate
7. Post-process to G-code               →  tools/fusion-cam-setup post ...
```

## Setup creation

### Relative stock (default — offsets from model bounding box)

```bash
# Basic setup with default offsets (2mm sides, 4mm top)
tools/fusion-cam-setup create --name "Main Setup"

# Custom offsets
tools/fusion-cam-setup create --name "Tight Setup" --stock-offset 1 --stock-top 2
```

### Fixed stock (explicit dimensions)

```bash
# Fixed stock size — use when you know your blank dimensions
tools/fusion-cam-setup create --name "Board" \
  --stock-mode fixed --stock-x 500 --stock-y 400 --stock-z 20

# With origin at top center (common for CNC routers)
tools/fusion-cam-setup create --name "Board" \
  --stock-mode fixed --stock-x 500 --stock-y 400 --stock-z 20 \
  --stock-point top-center
```

## WCS origin (stock point)

Set where the WCS origin sits on the stock:

```bash
fusion-cam-setup create --name Setup1 --stock-point corner          # stock box corner (most CNC-friendly)
fusion-cam-setup create --name Setup1 --stock-point center          # center of stock
fusion-cam-setup create --name Setup1 --stock-point top-center      # top face center
fusion-cam-setup create --name Setup1 --stock-point bottom-center   # bottom face center
```

Use `corner` for most CNC workflows — it matches typical machine datum at the front-left corner of the stock.

## Setup editing

```bash
# Edit stock dimensions
tools/fusion-cam-setup edit --setup "Main Setup" --stock-mode fixed --stock-x 600

# Fix WCS orientation (flip Z up)
tools/fusion-cam-setup fix --setup "Main Setup"

# Edit raw parameters directly
tools/fusion-cam-setup edit --setup "Main Setup" --params job_stockOffsetSides="3 mm"

# Discover available parameters
tools/fusion-cam-setup params --setup "Main Setup"
tools/fusion-cam-setup params --setup "Main Setup" --filter job_    # stock params only
tools/fusion-cam-setup params --setup "Main Setup" --filter wcs_    # WCS params only
```

## Setup management

```bash
tools/fusion-cam-setup duplicate --setup "Main Setup" --new-name "Flip Side"
tools/fusion-cam-setup delete --setup "Old Setup"
```

## Model and fixture bodies

```bash
# Set which bodies to machine (by name)
tools/fusion-cam-setup set-model --setup "Main Setup" --bodies TopPanel,SidePanel

# Set fixture bodies (clamps — tool avoids these)
tools/fusion-cam-setup set-fixture --setup "Main Setup" --fixtures Clamp1,Clamp2

# Import a body from another Fusion design
tools/fusion-cam-setup derive-body --source /path/to/design.f3d --body BodyName --new-name ImportedPart

# Create corner keep-out zones (for clamp clearance)
tools/fusion-cam-setup keepout --setup "Main Setup" --corner-size 20
```

## Tool management

### List available tools

```bash
# All tools (from document operations + local libraries)
tools/fusion-cam-setup tools

# Filter by type
tools/fusion-cam-setup tools --type flat_end
tools/fusion-cam-setup tools --type ball_end
tools/fusion-cam-setup tools --type chamfer
tools/fusion-cam-setup tools --type drill
tools/fusion-cam-setup tools --type v_bit
```

### Create a new tool (auto-added to library)

```bash
# Flat end mill — automatically added to persistent Local library
tools/fusion-cam-setup create-tool --type "flat end mill" --diameter 6 --flutes 2

# Ball end mill
tools/fusion-cam-setup create-tool --type "ball end mill" --diameter 6 --flutes 2

# V-bit (chamfer mill)
tools/fusion-cam-setup create-tool --type "chamfer mill" --diameter 25 --tip-angle 90

# Drill
tools/fusion-cam-setup create-tool --type "drill" --diameter 5 --flutes 2

# With full specs
tools/fusion-cam-setup create-tool \
  --type "flat end mill" --diameter 6 --flutes 3 \
  --flute-length 20 --overall-length 50 \
  --tool-number 1 --description "6mm 3-flute upcut"

# Create tool WITHOUT adding to library (document-only)
tools/fusion-cam-setup create-tool --type "flat end mill" --diameter 6 --no-library
```

### Tool disambiguation

When multiple tools share the same tool number, use `--tool-description` on 2D/3D operations to pick the right one:

```bash
tools/fusion-cam-2d adaptive --setup S --name Rough --tool-number 2 --tool-description "1/2 inch"
tools/fusion-cam-3d parallel --setup S --name Finish --tool-number 2 --tool-description "ball"
```

## Library management (persistent across all documents)

The Local library persists across all Fusion 360 documents. Tools stored here are always available regardless of which document is open.

### List library tools

```bash
tools/fusion-cam-setup library list
```

### Add tools to library

```bash
# Add a tool definition directly
tools/fusion-cam-setup library add \
  --type "flat end mill" --diameter 12.7 --flutes 2 \
  --flute-length 25 --tool-number 3 --description "1/2in flat upcut"

# Copy a tool from a document operation into the library
tools/fusion-cam-setup library add-from-op --operation "Flat2"

# Bulk import all unique tools from the current document
tools/fusion-cam-setup library import-doc
```

### Remove a tool

```bash
tools/fusion-cam-setup library remove --index 0
```

### Export / Import (backup, sharing, migration)

```bash
# Export to JSON file
tools/fusion-cam-setup library export --output ~/my-tools.json

# Import from JSON file (deduplicates automatically)
tools/fusion-cam-setup library import-file --input ~/my-tools.json
```

### Recommended workflow for new documents

```bash
# 1. All your tools are already in the Local library — just reference by number
tools/fusion-cam-2d adaptive --setup S --name Rough --tool-number 3

# 2. Or import tools from another document first
tools/fusion-cam-setup library import-doc
```

## Operations query

```bash
# List all operations (all setups)
tools/fusion-cam-setup operations

# Operations in a specific setup
tools/fusion-cam-setup operations --setup "Main Setup"

# With full parameter dump (for debugging)
tools/fusion-cam-setup operations --setup "Main Setup" --show-params
# Note: --show-params filters out tool_* and holder_* params by default for cleaner output.
# To see ALL params including tool details, pass --operation NAME to filter to a specific operation.

# Set an operation to auto-detect geometry (silhouette)
tools/fusion-cam-setup silhouette --operation "2D Contour"
```

## Generate toolpaths

```bash
# Generate all toolpaths in all setups
tools/fusion-cam-setup generate

# Generate for one setup only
tools/fusion-cam-setup generate --setup "Main Setup"

# With extended timeout (for complex models)
tools/fusion-cam-setup generate --setup "Main Setup" --timeout 300
```

## Simulation

```bash
tools/fusion-cam-setup simulate --setup "Main Setup"
```

## Post-processing (G-code)

```bash
# Post-process to file
tools/fusion-cam-setup post --output /Users/me/gcode/part.nc --setup "Main Setup"

# With specific post-processor
tools/fusion-cam-setup post --output /path/output.nc --setup "Main Setup" --post-processor grbl

# Open in editor after post
tools/fusion-cam-setup post --output /path/output.nc --setup "Main Setup" --open-editor
```

## Cycle time estimation

```bash
tools/fusion-cam-setup cycle-time --setup "Main Setup"
# Returns: total_seconds, total_minutes, per-operation breakdown
```

## Decision guide

| I want to... | Command |
|--------------|---------|
| Start CAM work | `switch` then `create --name ...` |
| See what's set up | `list` or `info` |
| Set my blank size | `create --stock-mode fixed --stock-x W --stock-y D --stock-z H` |
| Fix upside-down WCS | `fix --setup S` |
| Choose bodies to cut | `set-model --bodies B1,B2` |
| See available tools | `tools` |
| Add a tool | `create-tool --type T --diameter D` (auto-added to library) |
| See library tools | `library list` |
| Import doc tools to library | `library import-doc` |
| Backup my tool library | `library export --output ~/tools.json` |
| Make G-code | `generate --setup S` then `post --output /path --setup S` |
| Check machining time | `cycle-time --setup S` |
| Verify before cutting | `simulate --setup S` |
| Debug a parameter | `params --setup S --filter prefix_` |

## Common patterns

### CNC router setup (flat stock, top-center origin)

```bash
tools/fusion-cam-setup switch
tools/fusion-cam-setup create --name "Router Job" \
  --stock-mode fixed --stock-x 610 --stock-y 305 --stock-z 19 \
  --stock-point top-center
tools/fusion-cam-setup set-model --setup "Router Job" --bodies Part1
tools/fusion-cam-setup keepout --setup "Router Job" --corner-size 25
```

### Full workflow (setup → operations → G-code)

```bash
# 1. Setup
tools/fusion-cam-setup switch
tools/fusion-cam-setup create --name "Job1" --stock-mode fixed --stock-x 300 --stock-y 200 --stock-z 25

# 2. Create operations (via fusion-cam-2d)
tools/fusion-cam-2d adaptive --setup "Job1" --name "Rough" --depth 19 --stepdown 4
tools/fusion-cam-2d contour --setup "Job1" --name "Profile" --depth 19 --tabs

# 3. Generate + verify + post
tools/fusion-cam-setup generate --setup "Job1"
tools/fusion-cam-setup cycle-time --setup "Job1"
tools/fusion-cam-setup simulate --setup "Job1"
tools/fusion-cam-setup post --output ~/gcode/job1.nc --setup "Job1" --post-processor grbl
```

## Common mistakes

- **Not switching to Manufacturing workspace first** — run `switch` before any CAM commands
- **Forgetting to generate** — operations must have toolpaths before post-processing
- **Wrong stock point** — CNC routers typically use `top-center`; mills use `center`
- **Stock point defaulting to center** — always specify `--stock-point corner` if your CNC expects origin at stock corner
- **Param listing only showing tool params** — the 100-param cap has been removed, tool_* params are filtered by default
- **Missing model selection** — if operations show no geometry, run `set-model` to specify which bodies to machine
- **Wrong tool picked (duplicate tool numbers)** — use `--tool-description` to disambiguate when multiple tools share the same number
- **Tools lost when operations deleted** — always import important tools into the Local library first with `library import-doc` or `library add-from-op`
- **Tools not available in new document** — use the persistent Local library (`library list`) instead of relying on document-embedded tools

## Deploying addin changes

After editing handler files in the workspace, run `./deploy-addin.sh` to copy them to the Fusion AddIns directory, then restart the addin.
