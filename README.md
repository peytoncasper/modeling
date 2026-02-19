# Fusion 360 MCP Bridge

Control Fusion 360 programmatically through MCP (Model Context Protocol) servers, enabling AI-assisted CAD/CAM workflows.

## Architecture

```
fusion-addin/               Fusion 360 Python add-in (HTTP bridge)
fusion-design-mcp-server/   MCP server — Design workspace tools
fusion-cam-mcp-server/      MCP server — CAM workspace tools
sculptural-base-mcp/        MCP server — project-specific tools
fusion-patterns/            Design pattern reference library
bedside-table-cad/          Parametric CAD project (stages + validation)
```

## Setup

1. **Install the Fusion 360 add-in:**
   - Copy `fusion-addin/` to your Fusion 360 add-ins directory
   - Enable `FusionMCPBridge` in Fusion's Add-Ins panel

2. **Build the MCP servers:**
   ```bash
   cd fusion-design-mcp-server && npm install && npm run build
   cd fusion-cam-mcp-server && npm install && npm run build
   ```

3. **Configure Cursor** to use the MCP servers (see [SETUP.md](SETUP.md))

## MCP Servers

### Design Server (`fusion-design-mcp-server/`)
Sketches, extrusions, booleans, fillets, patterns, parameters, appearances, components, frames, and more.

### CAM Server (`fusion-cam-mcp-server/`)
Setups, toolpaths (face, contour, pocket, trace, engrave), tool libraries, simulation, and G-code post-processing.

## Resources

- [fusion-mcp-spec.md](fusion-mcp-spec.md) — Full MCP tool specification
- [fusion-patterns/](fusion-patterns/) — Coordinate systems, joinery, panel construction
- [SETUP.md](SETUP.md) — Detailed setup instructions
