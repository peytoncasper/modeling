---
name: fusion-camera
description: Control the Fusion 360 viewport camera, take screenshots, and export designs. Use when the user asks to change the view, orbit, zoom, pan, take a screenshot, capture an image, save a render, or export to STL/STEP/IGES/F3D.
---

# Fusion 360 Camera & Viewport

Control the Fusion 360 camera and capture images via `tools/fusion-camera`. All coordinates are mm. Output is JSON.

## Quick reference

```bash
tools/fusion-camera get              # current camera state (eye, target, up, FOV)
tools/fusion-camera view isometric   # jump to a preset view
tools/fusion-camera fit              # fit all geometry in view
tools/fusion-camera screenshot       # capture the viewport as PNG
```

## Preset views

Jump to standard orientations. All presets auto-fit geometry unless `--no-fit` is used.

```bash
tools/fusion-camera view top
tools/fusion-camera view bottom
tools/fusion-camera view front
tools/fusion-camera view back
tools/fusion-camera view left
tools/fusion-camera view right
tools/fusion-camera view isometric          # default iso (top-right)
tools/fusion-camera view iso_top_left
tools/fusion-camera view iso_bottom_right
tools/fusion-camera view iso_bottom_left
```

## Camera movements

### Orbit (rotate around target)

```bash
# Rotate 45° right
tools/fusion-camera orbit --yaw 45

# Rotate 20° up
tools/fusion-camera orbit --pitch 20

# Combine
tools/fusion-camera orbit --yaw 30 --pitch 15
```

Positive yaw = clockwise (looking down). Positive pitch = tilt up.

### Zoom

```bash
# Zoom in 2x
tools/fusion-camera zoom --factor 2

# Zoom out to half
tools/fusion-camera zoom --factor 0.5
```

### Pan (move the whole view)

```bash
# Shift the view 100mm to the right
tools/fusion-camera pan --offset 100,0,0

# Shift the view 50mm up
tools/fusion-camera pan --offset 0,0,50
```

### Look at a specific point

```bash
# Point camera at the center of a body
tools/fusion-camera look-at --target 50,40,10

# Same but from a specific distance and angle
tools/fusion-camera look-at --target 50,40,10 --distance 500 --elevation 30 --azimuth 45
```

- `elevation`: angle above the XY plane in degrees (0 = eye level, 90 = directly above)
- `azimuth`: angle around the Z axis in degrees (0 = looking along +X, 90 = looking along +Y)

## Direct camera control

For precise camera placement:

```bash
# Get current state
tools/fusion-camera get

# Set exact position
tools/fusion-camera set --eye 500,300,400 --target 50,40,10

# With custom up vector
tools/fusion-camera set --eye 500,300,400 --target 50,40,10 --up 0,0,1

# Set orthographic with specific extents
tools/fusion-camera set --target 50,40,10 --extents 200

# Set perspective with specific FOV
tools/fusion-camera set --eye 500,300,400 --target 50,40,10 --fov 60
```

## Projection mode

```bash
# Switch to orthographic (no perspective distortion)
tools/fusion-camera projection orthographic

# Switch to perspective with 45° FOV
tools/fusion-camera projection perspective --fov 45
```

## Visual style

```bash
tools/fusion-camera style shaded              # solid shading
tools/fusion-camera style wireframe           # wireframe only
tools/fusion-camera style shaded_wireframe    # shaded + visible edges
tools/fusion-camera style hidden_edges        # shaded + all edges (including hidden)
```

## Screenshots

### Capture to terminal (base64)

```bash
# Default 1920x1080
tools/fusion-camera screenshot

# Custom resolution
tools/fusion-camera screenshot --width 3840 --height 2160

# Set view first, then capture
tools/fusion-camera screenshot --view front
tools/fusion-camera screenshot --view isometric --width 2560 --height 1440
```

### Save to file

```bash
tools/fusion-camera save ~/Desktop/model.png
tools/fusion-camera save ~/Desktop/top_view.png --view top
tools/fusion-camera save ~/Desktop/render.png --view isometric --width 3840 --height 2160
```

### Workflow: capture from multiple angles

```bash
tools/fusion-camera save ~/Desktop/front.png --view front
tools/fusion-camera save ~/Desktop/top.png --view top
tools/fusion-camera save ~/Desktop/iso.png --view isometric
tools/fusion-camera save ~/Desktop/right.png --view right
```

## Export

Export the full design to different file formats:

```bash
# STL (for 3D printing / CNC)
tools/fusion-camera export stl ~/Desktop/model.stl
tools/fusion-camera export stl ~/Desktop/model.stl --refinement high

# STEP (industry standard CAD interchange)
tools/fusion-camera export step ~/Desktop/model.step

# IGES (older CAD interchange format)
tools/fusion-camera export iges ~/Desktop/model.iges

# F3D (Fusion 360 archive)
tools/fusion-camera export f3d ~/Desktop/model.f3d
```

STL refinement options: `low` (fast, rough), `medium` (default), `high` (slow, smooth)

## Complete command reference

### Camera state

| Command | What it does |
|---------|-------------|
| `get` | Current camera eye, target, up, FOV, projection |
| `set --eye x,y,z --target x,y,z [--up x,y,z] [--fov D] [--extents D]` | Set camera directly |

### Views

| Command | What it does |
|---------|-------------|
| `view PRESET [--no-fit] [--no-smooth]` | Jump to preset orientation |
| `fit` | Fit view to all geometry |

### Movements

| Command | What it does |
|---------|-------------|
| `orbit --yaw D --pitch D` | Rotate around target |
| `zoom --factor F` | Zoom in (>1) or out (<1) |
| `pan --offset x,y,z` | Shift view in world coords |
| `look-at --target x,y,z [--distance D] [--elevation D] [--azimuth D]` | Point camera at target |

### Projection & Style

| Command | What it does |
|---------|-------------|
| `projection perspective/orthographic [--fov D]` | Switch projection mode |
| `style shaded/wireframe/shaded_wireframe/hidden_edges` | Visual rendering style |

### Capture & Export

| Command | What it does |
|---------|-------------|
| `screenshot [--view V] [--width W] [--height H] [--path P]` | Capture viewport |
| `save PATH [--view V] [--width W] [--height H]` | Save screenshot to file |
| `export FORMAT PATH [--refinement low/medium/high]` | Export design (stl/step/iges/f3d) |

## Common patterns

### "Show me the model from the front"

```bash
tools/fusion-camera view front
tools/fusion-camera save ~/Desktop/front.png --view front
```

### "Zoom into this area"

```bash
tools/fusion-camera look-at --target 50,40,10 --distance 200
```

### "Give me an isometric render at high resolution"

```bash
tools/fusion-camera view isometric
tools/fusion-camera style shaded_wireframe
tools/fusion-camera save ~/Desktop/render.png --width 3840 --height 2160
```

### "Export for 3D printing"

```bash
tools/fusion-camera export stl ~/Desktop/print.stl --refinement high
```
