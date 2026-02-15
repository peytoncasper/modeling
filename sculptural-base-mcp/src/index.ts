/**
 * Sculptural Base MCP Server
 * 
 * A minimal, purpose-built MCP server for creating a faceted sculptural
 * coffee table base. Only includes the tools needed for this specific object.
 * 
 * Design Philosophy:
 * - Plan-first: The geometry is defined in DESIGN_PLAN.md
 * - Minimal tools: Only what's needed, nothing more
 * - High-level operations: create_polyhedron instead of dozens of low-level calls
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const FUSION_URL = "http://localhost:8080";

// The design plan geometry - embedded for reference
const DESIGN_PLAN = {
  vertices: {
    // Floor level (Z = 0)
    V1: [-180, -120, 0],   // Front-left base
    V2: [200, -80, 0],     // Front-right base
    V3: [160, 150, 0],     // Back-right base
    V4: [-140, 130, 0],    // Back-left base
    // Mid level (Z = 140) - The fold
    V5: [40, 20, 140],     // Central fold vertex
    // Top level (Z = 350)
    V6: [-40, 10, 350],    // Top front-left
    V7: [100, 30, 350],    // Top front-right
    V8: [60, 100, 350],    // Top back
  },
  faces: [
    // Bottom (quadrilateral as 2 triangles)
    ["V1", "V2", "V3"],
    ["V1", "V3", "V4"],
    // Top
    ["V6", "V8", "V7"],
    // Lower side faces (floor to fold)
    ["V1", "V5", "V2"],
    ["V2", "V5", "V3"],
    ["V3", "V5", "V4"],
    ["V4", "V5", "V1"],
    // Upper side faces (fold to top)
    ["V5", "V6", "V7"],
    ["V5", "V7", "V8"],
    ["V5", "V8", "V6"],
  ]
};

// Helper to call Fusion 360 bridge
async function callFusion(
  endpoint: string,
  body?: Record<string, unknown>
): Promise<Record<string, unknown>> {
  const url = `${FUSION_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
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
    name: "sculptural-base",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// ============================================================================
// TOOL DEFINITIONS - Only what's needed for this object
// ============================================================================

const TOOLS = [
  // ===== Setup =====
  {
    name: "ping",
    description: "Check if Fusion 360 is connected.",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
  {
    name: "new_document",
    description: "Create a new Fusion 360 document for the sculptural base.",
    inputSchema: {
      type: "object" as const,
      properties: {
        name: { type: "string", description: "Document name", default: "Sculptural Coffee Table Base" },
      },
      required: [],
    },
  },

  // ===== Core Geometry - The main tools for this object =====
  {
    name: "create_polyhedron",
    description: `Create the sculptural base as a solid polyhedron from vertices and triangular faces.
    
This is the PRIMARY tool for creating the faceted base geometry.

Default geometry (from DESIGN_PLAN.md):
- 8 vertices defining the shape
- 10 triangular faces creating the faceted appearance
- Central "fold" vertex at Z=140 creates the origami-like quality

You can use the default geometry or provide custom vertices/faces.`,
    inputSchema: {
      type: "object" as const,
      properties: {
        vertices: {
          type: "object",
          description: `Dict of vertex_id -> [x, y, z] in mm. 
Default uses the planned geometry with V1-V8.
Example: {"V1": [-180, -120, 0], "V2": [200, -80, 0], ...}`,
        },
        faces: {
          type: "array",
          items: { type: "array", items: { type: "string" } },
          description: `List of [v1, v2, v3] triangular faces.
Default uses the planned 10-face configuration.
Example: [["V1", "V2", "V3"], ["V1", "V3", "V4"], ...]`,
        },
        name: { type: "string", description: "Body name", default: "SculpturalBase" },
        use_default_geometry: { 
          type: "boolean", 
          description: "If true, uses the pre-planned geometry from DESIGN_PLAN.md",
          default: true 
        },
      },
      required: [],
    },
  },
  {
    name: "create_angled_plane",
    description: "Create a construction plane at an arbitrary angle (point + normal vector). Useful for sketching on angled faces.",
    inputSchema: {
      type: "object" as const,
      properties: {
        point: { type: "array", items: { type: "number" }, description: "[x, y, z] point on plane in mm" },
        normal: { type: "array", items: { type: "number" }, description: "[x, y, z] normal vector" },
        name: { type: "string", description: "Plane name" },
      },
      required: ["point", "normal"],
    },
  },
  {
    name: "create_triangular_prism",
    description: "Create a simple triangular prism from 3 vertices and a height. Useful for testing or simpler geometry.",
    inputSchema: {
      type: "object" as const,
      properties: {
        v1: { type: "array", items: { type: "number" }, description: "[x, y, z] first vertex in mm" },
        v2: { type: "array", items: { type: "number" }, description: "[x, y, z] second vertex in mm" },
        v3: { type: "array", items: { type: "number" }, description: "[x, y, z] third vertex in mm" },
        height: { type: "number", description: "Extrusion height in mm" },
        name: { type: "string", description: "Body name" },
      },
      required: ["v1", "v2", "v3", "height"],
    },
  },

  // ===== Finishing =====
  {
    name: "apply_appearance",
    description: "Apply a wood appearance to the sculptural base.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_name: { type: "string", description: "Body to apply appearance to", default: "SculpturalBase" },
        appearance: { 
          type: "string", 
          enum: ["Walnut", "Oak", "Oak - Semigloss"],
          description: "Wood appearance to apply",
          default: "Walnut"
        },
      },
      required: [],
    },
  },

  // ===== Visualization =====
  {
    name: "take_screenshot",
    description: "Capture the current viewport.",
    inputSchema: {
      type: "object" as const,
      properties: {
        view: { 
          type: "string", 
          enum: ["current", "top", "front", "right", "isometric"],
          default: "isometric"
        },
      },
      required: [],
    },
  },
  {
    name: "set_view",
    description: "Set the camera view.",
    inputSchema: {
      type: "object" as const,
      properties: {
        preset: { 
          type: "string", 
          enum: ["top", "front", "right", "back", "left", "bottom", "isometric"],
        },
        fit: { type: "boolean", description: "Zoom to fit", default: true },
      },
      required: ["preset"],
    },
  },

  // ===== Export =====
  {
    name: "export",
    description: "Export the model.",
    inputSchema: {
      type: "object" as const,
      properties: {
        format: { type: "string", enum: ["stl", "step", "f3d"], description: "Export format" },
        path: { type: "string", description: "Output file path" },
      },
      required: ["format", "path"],
    },
  },

  // ===== Plan Reference =====
  {
    name: "get_design_plan",
    description: "Get the embedded design plan with vertex positions and face definitions. Use this to understand the intended geometry.",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
];

// Endpoint mapping
const ENDPOINTS: Record<string, string> = {
  ping: "/ping",
  new_document: "/new_document",
  create_polyhedron: "/create_polyhedron",
  create_angled_plane: "/create_angled_plane",
  create_triangular_prism: "/create_triangular_prism",
  apply_appearance: "/apply_appearance",
  take_screenshot: "/take_screenshot",
  set_view: "/set_view",
  export: "/export",
};

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: TOOLS };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  // Special case: get_design_plan returns embedded data
  if (name === "get_design_plan") {
    return {
      content: [{
        type: "text" as const,
        text: JSON.stringify({
          description: "Sculptural Coffee Table Base - Faceted Polyhedron",
          dimensions: {
            base_footprint: "~400mm x 350mm",
            height: "350mm",
            top_surface: "~200mm x 180mm"
          },
          vertices: DESIGN_PLAN.vertices,
          faces: DESIGN_PLAN.faces,
          notes: [
            "V5 is the 'fold' vertex that creates the origami-like quality",
            "Faces use counter-clockwise winding for outward normals",
            "Bottom is a quadrilateral split into 2 triangles",
            "Top is a single triangle for table mounting"
          ]
        }, null, 2)
      }],
    };
  }

  // Special case: create_polyhedron with default geometry
  if (name === "create_polyhedron") {
    const typedArgs = args as Record<string, unknown> | undefined;
    const useDefault = typedArgs?.use_default_geometry !== false;
    
    const polyhedronArgs: Record<string, unknown> = {
      name: typedArgs?.name || "SculpturalBase",
    };
    
    if (useDefault && !typedArgs?.vertices) {
      polyhedronArgs.vertices = DESIGN_PLAN.vertices;
      polyhedronArgs.faces = DESIGN_PLAN.faces;
    } else {
      polyhedronArgs.vertices = typedArgs?.vertices;
      polyhedronArgs.faces = typedArgs?.faces;
    }
    
    const result = await callFusion("/create_polyhedron", polyhedronArgs);
    return {
      content: [{ type: "text" as const, text: formatResult(result) }],
      isError: !!result.error,
    };
  }

  // Special case: apply_appearance needs body_id mapping
  if (name === "apply_appearance") {
    const typedArgs = args as Record<string, unknown> | undefined;
    const result = await callFusion("/apply_appearance", {
      body_id: typedArgs?.body_name || "SculpturalBase",
      appearance: typedArgs?.appearance || "Walnut",
    });
    return {
      content: [{ type: "text" as const, text: formatResult(result) }],
      isError: !!result.error,
    };
  }

  const endpoint = ENDPOINTS[name];
  if (!endpoint) {
    return {
      content: [{ type: "text" as const, text: `Unknown tool: ${name}` }],
      isError: true,
    };
  }

  const result = await callFusion(endpoint, args as Record<string, unknown>);

  // Handle screenshot specially
  if (name === "take_screenshot" && result.image_base64) {
    return {
      content: [
        {
          type: "image" as const,
          data: result.image_base64 as string,
          mimeType: "image/png",
        },
      ],
    };
  }

  return {
    content: [{ type: "text" as const, text: formatResult(result) }],
    isError: !!result.error,
  };
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Sculptural Base MCP server running on stdio");
  console.error("Tools available: " + TOOLS.map(t => t.name).join(", "));
}

main().catch(console.error);
