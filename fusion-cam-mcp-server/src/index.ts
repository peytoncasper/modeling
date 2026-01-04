import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const FUSION_URL = "http://localhost:8080";

// Helper to call Fusion 360 bridge
async function callFusion(
  endpoint: string,
  method: "GET" | "POST" = "POST",
  body?: Record<string, unknown>
): Promise<Record<string, unknown>> {
  const url = `${FUSION_URL}${endpoint}`;

  try {
    const options: RequestInit = {
      method,
      headers: { "Content-Type": "application/json" },
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    return (await response.json()) as Record<string, unknown>;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes("fetch")) {
      return {
        error: true,
        message: "Cannot connect to Fusion 360. Is the add-in running?",
      };
    }
    return {
      error: true,
      message: error instanceof Error ? error.message : String(error),
    };
  }
}

function formatResult(result: Record<string, unknown>): string {
  return JSON.stringify(result, null, 2);
}

// Create MCP server
const server = new Server(
  {
    name: "fusion-cam",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool definitions - CAM only
const TOOLS = [
  // ============ CAM Setup & Configuration ============
  {
    name: "fusion_cam_list_setups",
    description: "List all CAM setups in the document.",
    inputSchema: { type: "object" as const, properties: { show_params: { type: "boolean", description: "Include setup parameters for debugging" } }, required: [] },
  },
  {
    name: "fusion_cam_create_setup",
    description: `Create a new CAM setup with full control over stock dimensions and WCS orientation.

STOCK MODES:
- "fixed": Use exact stock dimensions (stock_x, stock_y, stock_z in mm)
- "relative": Use offsets from model bounding box (stock_offset, stock_top)

WCS ORIENTATION:
- flip_z: true (default) makes Z point up from top face
- x_axis: Set X to align with long dimension of stock
- stock_point: Origin location ("center", "top-center", "corner")

EXAMPLE for 19.5" x 18" x 18.5mm stock:
{
  "name": "TopPanel",
  "stock_mode": "fixed",
  "stock_x": 495.3,  // 19.5" in mm
  "stock_y": 457.2,  // 18" in mm
  "stock_z": 18.5,
  "flip_z": true,
  "stock_point": "top-center"
}`,
    inputSchema: {
      type: "object" as const,
      properties: {
        name: { type: "string", description: "Setup name" },
        stock_mode: { type: "string", enum: ["fixed", "relative"], description: "Stock definition mode: 'fixed' for exact dimensions, 'relative' for offsets" },
        // Fixed stock dimensions
        stock_x: { type: "number", description: "Stock width (X) in mm - for fixed mode" },
        stock_y: { type: "number", description: "Stock depth (Y) in mm - for fixed mode" },
        stock_z: { type: "number", description: "Stock height/thickness (Z) in mm - for fixed mode" },
        // Relative stock offsets
        stock_offset: { type: "number", description: "Stock side offset in mm - for relative mode (default: 2)" },
        stock_top: { type: "number", description: "Stock top offset in mm - for relative mode (default: 4)" },
        // WCS orientation
        flip_z: { type: "boolean", description: "Flip Z axis to point up (default: true)" },
        x_axis: { type: "string", description: "X axis direction alignment" },
        z_axis: { type: "string", description: "Z axis direction" },
        stock_point: { type: "string", enum: ["center", "top-center", "corner", "bottom-center"], description: "Stock origin point (default: center)" },
      },
      required: [],
    },
  },
  {
    name: "fusion_cam_fix_setup",
    description: "Fix WCS orientation and stock offsets on an existing setup.",
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name to fix" },
        stock_offset: { type: "number", description: "Stock side offset in mm" },
        stock_top: { type: "number", description: "Stock top offset in mm" },
      },
      required: ["setup"],
    },
  },
  {
    name: "fusion_cam_set_model",
    description: "Set specific bodies as the machining model for a setup.",
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name" },
        bodies: { type: "array", items: { type: "string" }, description: "List of body names to machine" },
      },
      required: ["bodies"],
    },
  },
  {
    name: "fusion_cam_get_setup_params",
    description: "Get all parameters from a setup for debugging. Use filter to narrow results (e.g., 'job_' for stock params, 'wcs_' for orientation).",
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name" },
        filter: { type: "string", description: "Filter prefix (e.g., 'job_', 'wcs_')" },
      },
      required: [],
    },
  },
  
  // ============ Model Import ============
  {
    name: "fusion_cam_derive_body",
    description: `Import/derive a body from an external Fusion 360 design file (.f3d).

Use this to bring a body from another design into the current CAM document.

EXAMPLE:
{
  "source_path": "/Users/me/Documents/bedside-table.f3d",
  "body_name": "Top Panel",
  "new_name": "TopPanel_CAM"
}`,
    inputSchema: {
      type: "object" as const,
      properties: {
        source_path: { type: "string", description: "Absolute path to the source .f3d file" },
        body_name: { type: "string", description: "Name of the body to derive from the source" },
        new_name: { type: "string", description: "Optional new name for the derived body" },
      },
      required: ["source_path", "body_name"],
    },
  },
  
  // ============ Keep-Out Zones ============
  {
    name: "fusion_cam_create_keepout",
    description: `Create keep-out zones to avoid fixtures/clamps during machining.

Creates a sketch with rectangular zones at stock corners for screw/clamp avoidance.

EXAMPLE for 20mm x 20mm corner zones:
{
  "setup": "TopPanel",
  "corner_size": 20
}`,
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name" },
        corner_size: { type: "number", description: "Size of square keep-out zones at each corner in mm (e.g., 20 for 20x20mm)" },
      },
      required: ["corner_size"],
    },
  },
  
  // ============ Tools ============
  {
    name: "fusion_cam_list_tools",
    description: "List available cutting tools from the tool library.",
    inputSchema: {
      type: "object" as const,
      properties: {
        type: { type: "string", enum: ["flat_end", "ball_end", "bull_nose", "v_bit", "drill"], description: "Filter by tool type" },
      },
      required: [],
    },
  },
  
  // ============ Operations ============
  {
    name: "fusion_cam_create_face",
    description: `Create a facing/surface operation for the top of stock.

EXAMPLE:
{
  "setup": "TopPanel",
  "name": "Face Top",
  "tool_diameter": 25,
  "stepover": 15,
  "stock_to_leave": 0
}`,
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name" },
        name: { type: "string", description: "Operation name" },
        tool_diameter: { type: "number", description: "Tool diameter in mm" },
        stepover: { type: "number", description: "Stepover distance in mm" },
        stock_to_leave: { type: "number", description: "Stock to leave in mm (default: 0)" },
        depth: { type: "number", description: "Facing depth in mm" },
      },
      required: [],
    },
  },
  {
    name: "fusion_cam_create_2d_contour",
    description: "Create a basic 2D contour toolpath to cut around edges.",
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name (uses active if not specified)" },
        name: { type: "string", description: "Operation name" },
        tool_diameter: { type: "number", description: "Tool diameter in mm" },
        depth: { type: "number", description: "Cut depth in mm" },
      },
      required: [],
    },
  },
  {
    name: "fusion_cam_create_contour_advanced",
    description: `Create a 2D contour with specific tool selection and advanced settings.

Supports flat end mills, ball end mills, and V-bits.

EXAMPLE for 90° V-bit contour:
{
  "setup": "TopPanel",
  "name": "V-Carve Edge",
  "tool_type": "v_bit",
  "tool_diameter": 6.35,
  "tool_angle": 90,
  "depth": 3,
  "compensation": "center"
}`,
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name" },
        name: { type: "string", description: "Operation name" },
        tool_type: { type: "string", enum: ["flat_end", "ball_end", "v_bit"], description: "Tool type" },
        tool_diameter: { type: "number", description: "Tool diameter in mm" },
        tool_angle: { type: "number", description: "V-bit tip angle in degrees (e.g., 90 for 90° V-bit)" },
        depth: { type: "number", description: "Cut depth in mm" },
        use_tabs: { type: "boolean", description: "Add holding tabs/bridges" },
        stock_to_leave: { type: "number", description: "Stock to leave in mm" },
        compensation: { type: "string", enum: ["left", "right", "center"], description: "Side compensation (default: center)" },
        boundary: { type: "string", enum: ["silhouette", "selection"], description: "Machining boundary mode (default: silhouette)" },
      },
      required: [],
    },
  },
  {
    name: "fusion_cam_create_2d_pocket",
    description: "Create a 2D pocket toolpath to clear an area.",
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name" },
        name: { type: "string", description: "Operation name" },
        depth: { type: "number", description: "Pocket depth in mm" },
      },
      required: [],
    },
  },
  {
    name: "fusion_cam_create_miter_clearing",
    description: `Create terraced clearing operations for 45-degree miter cuts.

Creates multiple 2D contour operations at progressively deeper levels,
each offset inward to approximate the miter angle. This prepares the
material for a V-bit finish pass that only needs to clean up ~1mm.

For a 45° miter at 18mm depth, creates 4 terrace levels:
- Terrace 1: 4.5mm deep, 5.5mm offset
- Terrace 2: 9mm deep, 10mm offset  
- Terrace 3: 13.5mm deep, 14.5mm offset
- Terrace 4: 18mm deep, 19mm offset

EXAMPLE:
{
  "setup": "Setup1",
  "depth": 18,
  "steps": 4,
  "tool_diameter": 6,
  "stock_for_finish": 1.0,
  "stepdown": 4
}`,
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name" },
        depth: { type: "number", description: "Total miter depth in mm (default: 18)" },
        steps: { type: "number", description: "Number of terrace levels (default: 4)" },
        tool_diameter: { type: "number", description: "Flat endmill diameter in mm (default: 6)" },
        stock_for_finish: { type: "number", description: "Stock to leave for V-bit finish in mm (default: 1.0)" },
        miter_angle: { type: "number", description: "Miter angle in degrees (default: 45)" },
        stepdown: { type: "number", description: "Max stepdown per pass within each terrace (default: 4mm)" },
      },
      required: [],
    },
  },
  {
    name: "fusion_cam_create_engrave",
    description: "Create an engrave toolpath for text or detail work.",
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name" },
        name: { type: "string", description: "Operation name" },
        depth: { type: "number", description: "Engrave depth in mm" },
      },
      required: [],
    },
  },
  {
    name: "fusion_cam_create_trace",
    description: `Create a Trace toolpath - ideal for V-bit miter cuts.

IMPORTANT: Fusion blocks multiple depths for V-bits, so create separate operations per depth.
Use axialOffset (via depth parameter) to control cut depth for each pass.

EXAMPLE for 45° miter with 90° V-bit at 4mm depth:
{
  "setup": "Setup1",
  "name": "V-Miter 4mm",
  "sketch_id": "Miter_Trace_Top",
  "depth": 4,
  "tool_type": "chamfer mill",
  "tool_angle": 90,
  "tool_diameter": 25.4
}`,
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name" },
        name: { type: "string", description: "Operation name" },
        sketch_id: { type: "string", description: "Sketch containing trace curves" },
        depth: { type: "number", description: "Cut depth in mm (sets axialOffset)" },
        tool_type: { type: "string", description: "Tool type (default: 'chamfer mill' for V-bits)" },
        tool_angle: { type: "number", description: "V-bit included angle in degrees (default: 90)" },
        tool_diameter: { type: "number", description: "Tool diameter in mm" },
        stepdown: { type: "number", description: "Stepdown per pass in mm (may not work with V-bits)" },
        passes: { type: "number", description: "Number of passes (alternative to stepdown)" },
        axial_offset: { type: "number", description: "Axial offset to shift cut depth (mm)" },
        compensation: { type: "string", enum: ["left", "right", "center", "off"], description: "Sideways compensation (default: center)" },
      },
      required: [],
    },
  },
  {
    name: "fusion_cam_select_silhouette",
    description: "Set an operation to use silhouette (auto) geometry selection mode.",
    inputSchema: {
      type: "object" as const,
      properties: {
        operation: { type: "string", description: "Operation name to configure" },
      },
      required: ["operation"],
    },
  },
  
  // ============ Generation & Output ============
  {
    name: "fusion_cam_generate_all",
    description: "Generate all toolpaths in a setup.",
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name (generates all if not specified)" },
      },
      required: [],
    },
  },
  {
    name: "fusion_cam_post_process",
    description: "Post process toolpaths to generate G-code.",
    inputSchema: {
      type: "object" as const,
      properties: {
        output_path: { type: "string", description: "Output file path for G-code" },
        setup: { type: "string", description: "Setup name" },
        post_processor: { type: "string", description: "Post processor name (default: fanuc)" },
      },
      required: ["output_path"],
    },
  },
  {
    name: "fusion_cam_list_operations",
    description: "List all operations in a CAM setup.",
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name" },
        show_params: { type: "boolean", description: "Include operation parameters" },
      },
      required: [],
    },
  },
  {
    name: "fusion_cam_simulate",
    description: "Start toolpath simulation for a setup.",
    inputSchema: {
      type: "object" as const,
      properties: {
        setup: { type: "string", description: "Setup name" },
      },
      required: [],
    },
  },
];

// Endpoint mapping
const ENDPOINTS: Record<string, string> = {
  // CAM Setup & Configuration
  fusion_cam_list_setups: "/cam_list_setups",
  fusion_cam_create_setup: "/cam_create_setup",
  fusion_cam_fix_setup: "/cam_fix_setup",
  fusion_cam_set_model: "/cam_set_model",
  fusion_cam_get_setup_params: "/cam_get_setup_params",
  
  // Model Import
  fusion_cam_derive_body: "/cam_derive_body",
  
  // Keep-Out Zones
  fusion_cam_create_keepout: "/cam_create_keepout",
  
  // Tools
  fusion_cam_list_tools: "/cam_list_tools",
  
  // Operations
  fusion_cam_create_face: "/cam_create_face",
  fusion_cam_create_2d_contour: "/cam_create_2d_contour",
  fusion_cam_create_contour_advanced: "/cam_create_contour_advanced",
  fusion_cam_create_2d_pocket: "/cam_create_2d_pocket",
  fusion_cam_create_miter_clearing: "/cam_create_miter_clearing",
  fusion_cam_create_engrave: "/cam_create_engrave",
  fusion_cam_create_trace: "/cam_create_trace",
  fusion_cam_select_silhouette: "/cam_select_silhouette",
  
  // Generation & Output
  fusion_cam_generate_all: "/cam_generate_all",
  fusion_cam_post_process: "/cam_post_process",
  fusion_cam_list_operations: "/cam_list_operations",
  fusion_cam_simulate: "/cam_simulate",
};

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: TOOLS };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  const endpoint = ENDPOINTS[name];
  if (!endpoint) {
    return {
      content: [{ type: "text" as const, text: `Unknown tool: ${name}` }],
      isError: true,
    };
  }

  const result = await callFusion(endpoint, "POST", args as Record<string, unknown>);

  return {
    content: [{ type: "text" as const, text: formatResult(result) }],
    isError: !!result.error,
  };
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Fusion CAM MCP server running on stdio");
}

main().catch(console.error);








