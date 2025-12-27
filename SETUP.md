# Fusion 360 MCP Bridge - Setup Guide

## Architecture

```
┌─────────────────┐      MCP Protocol      ┌─────────────────┐      HTTP       ┌─────────────────┐
│                 │  ◄──────────────────►  │                 │  ◄───────────►  │                 │
│  Cursor/Claude  │                        │  MCP Server     │                 │  Fusion 360     │
│                 │                        │  (Python)       │   localhost:8080│  Add-in         │
└─────────────────┘                        └─────────────────┘                 └─────────────────┘
```

---

## Step 1: Install the Fusion 360 Add-in

### Locate your Fusion 360 Add-ins folder

**macOS:**
```
~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/
```

**Windows:**
```
%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\
```

### Copy the add-in

```bash
# macOS
cp -r fusion-addin ~/Library/Application\ Support/Autodesk/Autodesk\ Fusion\ 360/API/AddIns/FusionMCPBridge

# Windows (PowerShell)
Copy-Item -Recurse fusion-addin "$env:APPDATA\Autodesk\Autodesk Fusion 360\API\AddIns\FusionMCPBridge"
```

### Enable the add-in in Fusion 360

1. Open Fusion 360
2. Press `Shift + S` to open Scripts and Add-Ins
3. Click the **Add-Ins** tab
4. Find **FusionMCPBridge** in the list
5. Click **Run**
6. You should see: "MCP Bridge running on localhost:8080"

### Test the add-in

Open a terminal and run:
```bash
curl http://localhost:8080/ping
```

Expected response:
```json
{"status": "ok", "message": "Fusion 360 MCP Bridge is running", "port": 8080}
```

---

## Step 2: Set up the MCP Server

### Install dependencies

```bash
cd fusion-mcp-server
npm install
npm run build
```

### Test the server manually (optional)

```bash
npm run dev
```

The server communicates via stdio (MCP protocol), so you won't see output.  
Press `Ctrl+C` to stop.

---

## Step 3: Configure Cursor

Add the MCP server to your Cursor settings.

### Open MCP settings

1. Open Cursor Settings (`Cmd/Ctrl + ,`)
2. Search for "MCP" or navigate to the MCP configuration
3. Edit your `mcp.json` or settings file

### Add this configuration

```json
{
  "mcpServers": {
    "fusion360": {
      "command": "node",
      "args": ["/Users/peytoncas/Documents/modeling/fusion-mcp-server/dist/index.js"]
    }
  }
}
```

> **Note:** Adjust the path if your workspace is in a different location.

### Restart Cursor

After saving, restart Cursor to load the new MCP server.

---

## Step 4: Test the Integration

In Cursor chat, try:

> "Ping Fusion 360 to see if it's connected"

If everything is working, I should be able to call `fusion_ping` and get a response confirming the connection.

---

## Troubleshooting

### "Cannot connect to Fusion 360"

- Is Fusion 360 running?
- Is the FusionMCPBridge add-in running? (Check Scripts & Add-Ins panel)
- Test with `curl http://localhost:8080/ping`

### Add-in won't start

- Check the Fusion 360 Text Commands window for errors (`View > Text Commands`)
- Make sure the manifest file is valid JSON

### MCP server not appearing in Cursor

- Check your MCP configuration path
- Make sure the Python path is correct
- Restart Cursor completely

---

## Current Tools

| Tool | Description |
|------|-------------|
| `fusion_ping` | Health check - verify connection |
| `fusion_get_document_info` | Get active document details |

More tools coming as we expand!

