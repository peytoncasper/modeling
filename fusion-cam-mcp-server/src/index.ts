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
  // ============ CAM Operations ============
  {
    name: "fusion_cam_list_setups",
    description: "List all CAM setups in the document.",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
  {
    name: "fusion_cam_create_setup",
    description: "Create a new CAM setup for machining.",
    inputSchema: {
      type: "object" as const,
      properties: {
        name: { type: "string", description: "Setup name" },
        type: { type: "string", enum: ["milling", "turning", "cutting"], description: "Operation type" },
        bodies: { type: "array", items: { type: "string" }, description: "Body IDs to machine (empty = all)" },
        stock_mode: { type: "string", enum: ["relative_box", "fixed_size"], description: "Stock definition mode" },
        stock_offset: { type: "number", description: "Stock offset in mm (for relative_box)" },
      },
      required: [],
    },
  },
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
  {
    name: "fusion_cam_create_2d_contour",
    description: "Create a 2D contour toolpath to cut around edges.",
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
  // CAM
  fusion_cam_list_setups: "/cam_list_setups",
  fusion_cam_create_setup: "/cam_create_setup",
  fusion_cam_list_tools: "/cam_list_tools",
  fusion_cam_create_2d_contour: "/cam_create_2d_contour",
  fusion_cam_create_2d_pocket: "/cam_create_2d_pocket",
  fusion_cam_create_engrave: "/cam_create_engrave",
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

