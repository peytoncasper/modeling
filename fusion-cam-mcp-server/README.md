# Fusion CAM MCP Server

MCP server for Fusion 360 CAM (Computer-Aided Manufacturing) workspace integration. Provides tools for creating toolpaths, managing setups, and generating G-code.

## Features

- CAM setup management
- Tool library access
- 2D contour toolpaths
- 2D pocket toolpaths
- Engraving toolpaths
- Toolpath generation
- G-code post-processing
- Toolpath simulation

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
    "fusion-cam": {
      "command": "node",
      "args": ["/path/to/fusion-cam-mcp-server/dist/index.js"]
    }
  }
}
```

## Tools

This server provides CAM-focused tools only. For design tools (sketches, features, components), use the `fusion-design-mcp-server`.







