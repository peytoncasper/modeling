# Sculptural Base MCP Server

A minimal, purpose-built MCP server for creating a faceted sculptural coffee table base in Fusion 360.

## Philosophy

This demonstrates a **plan-first, scoped-tools** approach to CAD automation:

1. **Design Plan** (`DESIGN_PLAN.md`) - Define the geometry before writing code
2. **Minimal Tools** - Only 9 tools instead of 100+
3. **High-Level Operations** - `create_polyhedron` instead of dozens of low-level calls
4. **Embedded Defaults** - The planned geometry is built into the server

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  This MCP Server (9 tools)                                  │
│  - create_polyhedron (with embedded geometry)               │
│  - create_angled_plane                                      │
│  - create_triangular_prism                                  │
│  - apply_appearance, take_screenshot, export, etc.          │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP localhost:8080
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Enhanced Fusion Add-in                                     │
│  - Existing endpoints                                       │
│  + NEW: /create_polyhedron                                  │
│  + NEW: /create_angled_plane                                │
│  + NEW: /create_triangular_prism                            │
└─────────────────────────────────────────────────────────────┘
```

## Tools

| Tool | Purpose |
|------|---------|
| `ping` | Check Fusion connection |
| `new_document` | Create new design |
| `create_polyhedron` | **Core tool** - creates the faceted base from vertices/faces |
| `create_angled_plane` | Construction plane at arbitrary angle |
| `create_triangular_prism` | Simple triangular extrusion |
| `apply_appearance` | Apply wood material |
| `take_screenshot` | Capture viewport |
| `set_view` | Set camera |
| `export` | Export model |
| `get_design_plan` | View embedded geometry plan |

## Usage

### Setup

```bash
cd sculptural-base-mcp
npm install
npm run build
```

### Add to Cursor MCP config

```json
{
  "mcpServers": {
    "sculptural-base": {
      "command": "node",
      "args": ["/path/to/sculptural-base-mcp/dist/index.js"]
    }
  }
}
```

### Create the Base

The simplest usage - creates the base using the pre-planned geometry:

```
1. ping                           → Verify Fusion connection
2. new_document                   → Create new design  
3. create_polyhedron              → Creates the sculptural base (uses defaults)
4. apply_appearance               → Apply walnut finish
5. take_screenshot view=isometric → See the result
```

### Custom Geometry

You can also provide custom vertices and faces:

```javascript
create_polyhedron({
  vertices: {
    "A": [0, 0, 0],
    "B": [100, 0, 0],
    "C": [50, 100, 0],
    "D": [50, 50, 100]
  },
  faces: [
    ["A", "C", "B"],  // Bottom
    ["A", "B", "D"],  // Front
    ["B", "C", "D"],  // Right
    ["C", "A", "D"]   // Left
  ],
  name: "Tetrahedron",
  use_default_geometry: false
})
```

## The Design Plan

See `DESIGN_PLAN.md` for the complete geometry specification:

- **8 vertices** defining the shape
- **10 triangular faces** creating the faceted appearance
- **Central fold vertex** (V5) at Z=140 creates the origami-like quality

## Bridge Requirements

The Fusion add-in (`FusionMCPBridge.py`) must have these endpoints:
- `/create_polyhedron` - Create solid from vertices + faces
- `/create_angled_plane` - Construction plane from point + normal
- `/create_triangular_prism` - Simple triangle extrusion

These were added to the main bridge file.
