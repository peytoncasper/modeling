# Fusion Design MCP Server

MCP server for Fusion 360 Design workspace integration. Provides tools for creating and modifying 3D designs, sketches, features, and components.

## Features

- Document lifecycle management
- Sketch operations (lines, arcs, circles, rectangles, splines)
- 3D features (extrude, fillet, chamfer, boolean operations)
- Organic modeling (loft, sweep, revolve)
- Component management
- Parameter management
- Appearance/material application
- Export capabilities

## Installation

```bash
npm install
npm run build
```

## Usage

Run the server:

```bash
npm start
```

Or in development mode:

```bash
npm run dev
```

## MCP Configuration

Add to your MCP settings:

```json
{
  "mcpServers": {
    "fusion-design": {
      "command": "node",
      "args": ["/path/to/fusion-design-mcp-server/dist/index.js"]
    }
  }
}
```

## Tools

This server provides design-focused tools only. For CAM (Computer-Aided Manufacturing) tools, use the `fusion-cam-mcp-server`.

