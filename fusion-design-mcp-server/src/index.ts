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
    name: "fusion-design",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool definitions - Design only (no CAM)
const TOOLS = [
  // ============ Document Lifecycle ============
  {
    name: "fusion_ping",
    description: "Check if Fusion 360 is connected and the MCP bridge is running.",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
  {
    name: "fusion_get_document_info",
    description: "Get information about the currently active Fusion 360 document.",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
  {
    name: "fusion_new_document",
    description: "Create a new Fusion 360 design document.",
    inputSchema: {
      type: "object" as const,
      properties: {
        name: { type: "string", description: "Document name" },
      },
      required: [],
    },
  },
  {
    name: "fusion_save",
    description: "Save the active document.",
    inputSchema: {
      type: "object" as const,
      properties: {
        path: { type: "string", description: "Local path for offline save" },
      },
      required: [],
    },
  },
  {
    name: "fusion_open_document",
    description: "Open a local .f3d file in Fusion 360.",
    inputSchema: {
      type: "object" as const,
      properties: {
        path: { type: "string", description: "Absolute path to the .f3d file" },
      },
      required: ["path"],
    },
  },

  // ============ Reference Geometry ============
  {
    name: "fusion_list_planes",
    description: "Get available construction planes.",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
  {
    name: "fusion_create_offset_plane",
    description: "Create an offset construction plane. Can optionally target a specific component.",
    inputSchema: {
      type: "object" as const,
      properties: {
        base_plane: { type: "string", description: "Plane ID to offset from (xy, xz, yz, or custom name)" },
        offset: { type: "number", description: "Distance in mm" },
        component: { type: "string", description: "Optional component name to create plane in" },
      },
      required: ["base_plane", "offset"],
    },
  },

  // ============ Sketch Operations ============
  {
    name: "fusion_create_sketch",
    description: "Start a new sketch on a plane. Can optionally target a specific component.",
    inputSchema: {
      type: "object" as const,
      properties: {
        plane: { type: "string", description: "Plane ID (xy, xz, yz, or custom)" },
        name: { type: "string", description: "Optional sketch name" },
        component: { type: "string", description: "Optional component name (e.g., 'Carcass' or 'Carcass:1') to create sketch in" },
      },
      required: ["plane"],
    },
  },
  {
    name: "fusion_create_sketch_on_face",
    description: "Start a new sketch directly on a body face (including angled faces like 45° miters). Much easier than creating construction planes!",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_id: { type: "string", description: "Body name containing the face" },
        face_id: { type: "string", description: "Face ID or index (use list_faces or get_face_info to find faces)" },
        name: { type: "string", description: "Optional sketch name" },
        component: { type: "string", description: "Optional component name to create sketch in" },
      },
      required: ["body_id", "face_id"],
    },
  },
  {
    name: "fusion_draw_line",
    description: "Draw a line in a sketch. COORDINATE NOTE: [x, y] are local to the sketch plane. On XY plane: x=right, y=forward. On YZ plane: x=forward(Y), y=up(Z). On XZ plane: x=right(X), y=up(Z). Use sketch_to_3d_coords to verify positions.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        start: { type: "array", items: { type: "number" }, description: "[x, y] start point in mm (local sketch coordinates)" },
        end: { type: "array", items: { type: "number" }, description: "[x, y] end point in mm (local sketch coordinates)" },
        construction: { type: "boolean", description: "Make it a construction line" },
      },
      required: ["sketch_id", "start", "end"],
    },
  },
  {
    name: "fusion_draw_arc",
    description: "Draw an arc by center, radius, start angle, and sweep angle.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        center: { type: "array", items: { type: "number" }, description: "[x, y] center in mm" },
        radius: { type: "number", description: "Radius in mm" },
        start_angle: { type: "number", description: "Start angle in degrees" },
        sweep_angle: { type: "number", description: "Sweep angle in degrees (positive = CCW)" },
      },
      required: ["sketch_id", "center", "radius", "start_angle", "sweep_angle"],
    },
  },
  {
    name: "fusion_draw_arc_3point",
    description: "Draw an arc through three points.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        start: { type: "array", items: { type: "number" }, description: "[x, y] start point" },
        mid: { type: "array", items: { type: "number" }, description: "[x, y] point on arc" },
        end: { type: "array", items: { type: "number" }, description: "[x, y] end point" },
      },
      required: ["sketch_id", "start", "mid", "end"],
    },
  },
  {
    name: "fusion_draw_circle",
    description: "Draw a circle.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        center: { type: "array", items: { type: "number" }, description: "[x, y] center in mm" },
        radius: { type: "number", description: "Radius in mm" },
      },
      required: ["sketch_id", "center", "radius"],
    },
  },
  {
    name: "fusion_draw_rectangle",
    description: "Draw a rectangle using sketch-local coordinates.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        corner1: { type: "array", items: { type: "number" }, description: "[x, y] first corner in sketch coords" },
        corner2: { type: "array", items: { type: "number" }, description: "[x, y] opposite corner in sketch coords" },
      },
      required: ["sketch_id", "corner1", "corner2"],
    },
  },
  {
    name: "fusion_draw_rectangle_3d",
    description: "Draw a rectangle using WORLD 3D coordinates. Automatically converts to sketch coordinates based on plane. Much easier than manual coordinate conversion!",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        world_corner1: { type: "array", items: { type: "number" }, description: "[x, y, z] first corner in world mm coordinates" },
        world_corner2: { type: "array", items: { type: "number" }, description: "[x, y, z] opposite corner in world mm coordinates" },
      },
      required: ["sketch_id", "world_corner1", "world_corner2"],
    },
  },
  {
    name: "fusion_draw_spline",
    description: "Draw a spline through control points.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        points: { type: "array", items: { type: "array", items: { type: "number" } }, description: "Array of [x, y] points" },
        closed: { type: "boolean", description: "Close the spline" },
      },
      required: ["sketch_id", "points"],
    },
  },
  {
    name: "fusion_sketch_fillet",
    description: "Add a fillet between two sketch curves at their intersection.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        curve1_id: { type: "string", description: "First curve ID" },
        curve2_id: { type: "string", description: "Second curve ID" },
        radius: { type: "number", description: "Fillet radius in mm" },
      },
      required: ["sketch_id", "curve1_id", "curve2_id", "radius"],
    },
  },
  {
    name: "fusion_finish_sketch",
    description: "Exit sketch editing mode and validate the sketch.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Sketch to finish" },
      },
      required: ["sketch_id"],
    },
  },
  {
    name: "fusion_get_sketch_profiles",
    description: "Get all closed profiles in a sketch with their indices, areas, and bounding boxes. ESSENTIAL for multi-profile sketches - use this to identify which profile_index to use in fusion_extrude. Returns profile_index (0-based), area_mm2, sketch_bounds (2D), and world_bounds_3d (3D coordinates).",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
      },
      required: ["sketch_id"],
    },
  },
  {
    name: "fusion_list_sketches",
    description: "List all sketches in the design with their plane information, profile counts, and 3D position hints.",
    inputSchema: {
      type: "object" as const,
      properties: {},
      required: [],
    },
  },
  {
    name: "fusion_sketch_to_3d_coords",
    description: "Convert 2D sketch coordinates to 3D world coordinates. Essential for understanding where sketch geometry will end up when extruded. Use this BEFORE creating cuts to verify positioning.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        points: { type: "array", items: { type: "array", items: { type: "number" } }, description: "Array of [x, y] 2D points to convert" },
      },
      required: ["sketch_id", "points"],
    },
  },
  {
    name: "fusion_suggest_sketch_coords",
    description: "Given desired world 3D bounds, returns the sketch 2D coordinates needed. ESSENTIAL for avoiding coordinate flip errors on XZ/YZ planes! Call this BEFORE drawing to get correct coordinates.",
    inputSchema: {
      type: "object" as const,
      properties: {
        plane: { type: "string", description: "Plane type: xy, xz, or yz" },
        world_min: { type: "array", items: { type: "number" }, description: "[x, y, z] minimum corner in world mm" },
        world_max: { type: "array", items: { type: "number" }, description: "[x, y, z] maximum corner in world mm" },
      },
      required: ["plane", "world_min", "world_max"],
    },
  },
  {
    name: "fusion_list_sketch_dimensions",
    description: "List all dimensions in a sketch with their values and expressions.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
      },
      required: ["sketch_id"],
    },
  },
  {
    name: "fusion_edit_sketch_dimension",
    description: "Edit a sketch dimension by setting a value or parameter expression.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        dimension_index: { type: "number", description: "Dimension index (0-based)" },
        dimension_id: { type: "string", description: "Dimension ID (alternative to index)" },
        value: { type: "number", description: "New value in mm" },
        expression: { type: "string", description: "Parameter expression (e.g., 'overall_width' or 'overall_width / 2')" },
      },
      required: ["sketch_id"],
    },
  },
  {
    name: "fusion_import_svg",
    description: "Import an SVG file into a sketch on a body face or plane.",
    inputSchema: {
      type: "object" as const,
      properties: {
        svg_path: { type: "string", description: "Absolute path to the SVG file" },
        body_id: { type: "string", description: "Body to place SVG on (uses top face)" },
        plane: { type: "string", description: "Plane ID (xy, xz, yz) - alternative to body_id" },
        x_offset: { type: "number", description: "X offset in mm (default: 0)" },
        y_offset: { type: "number", description: "Y offset in mm (default: 0)" },
        scale: { type: "number", description: "Scale factor (default: 1.0)" },
        sketch_name: { type: "string", description: "Name for the sketch" },
      },
      required: ["svg_path"],
    },
  },
  {
    name: "fusion_add_text",
    description: "Add text to a sketch for engraving or extrusion.",
    inputSchema: {
      type: "object" as const,
      properties: {
        text: { type: "string", description: "The text to add" },
        body_id: { type: "string", description: "Body to place text on (uses top face)" },
        plane: { type: "string", description: "Plane ID - alternative to body_id" },
        sketch_id: { type: "string", description: "Existing sketch to add text to" },
        x: { type: "number", description: "X position in mm" },
        y: { type: "number", description: "Y position in mm" },
        height: { type: "number", description: "Text height in mm (default: 10)" },
        font: { type: "string", description: "Font name (default: Arial)" },
        bold: { type: "boolean", description: "Make text bold" },
        italic: { type: "boolean", description: "Make text italic" },
        sketch_name: { type: "string", description: "Name for the sketch" },
      },
      required: ["text"],
    },
  },

  // ============ 3D Features ============
  {
    name: "fusion_extrude",
    description: `Extrude a sketch profile into a 3D body. Use body_name to give meaningful names instead of 'Body1'. For join/cut operations, specify target_body.

📋 PROFILE SELECTION:
- For multi-profile sketches, use fusion_get_sketch_profiles() first to see all profiles with indices, areas, and bounds
- Then specify profile_index (0-based) to select which profile to extrude
- Default profile_index is 0 (first profile)

⚠️ JOIN OPERATION CRITICAL REQUIREMENTS:
- The extruded geometry MUST physically touch/intersect the target_body
- If they don't touch, Fusion creates an ORPHAN BODY instead of joining (causes "warning": "JOIN_CREATED_ORPHAN_BODY" in response)
- Common fix: Ensure sketch plane is positioned where it touches the target body's surface

⚠️ CUT OPERATION REQUIREMENTS:
- For cuts from face-based sketches, use direction="negative" to cut INTO the body (positive goes AWAY from face)
- Always specify target_body for cut operations to avoid cutting unintended bodies

Example for box joint fingers that join correctly:
- Front panel at Y=[0,12.7], Z=[12.7,88.9] 
- To add fingers at Z=[0,12.7] that join to FrontPanel:
- Sketch must be on XZ plane at Y=0 (where FrontPanel starts)
- Fingers must reach Z=12.7 (where FrontPanel bottom is) to touch it
- Extrude direction must go INTO the FrontPanel (+Y direction)`,
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Source sketch name" },
        profile_index: { type: "number", description: "Profile index (0-based). Use fusion_get_sketch_profiles() to see available profiles. Default: 0" },
        distance: { type: "number", description: "Extrusion distance in mm" },
        direction: { type: "string", enum: ["positive", "negative", "symmetric"], description: "Extrusion direction. For cuts from face sketches, use 'negative' to cut INTO body" },
        operation: { type: "string", enum: ["new_body", "join", "cut", "intersect"], description: "Boolean operation" },
        body_name: { type: "string", description: "Name for the new body (e.g., 'FrontPanel', 'BottomPlate'). Makes model self-documenting!" },
        component: { type: "string", description: "Optional component name to find sketch in" },
        target_body: { type: "string", description: "REQUIRED for cut/join operations. Target body name to cut from or join to" },
      },
      required: ["sketch_id", "distance"],
    },
  },
  {
    name: "fusion_fillet_edges",
    description: "Apply fillets to 3D edges.",
    inputSchema: {
      type: "object" as const,
      properties: {
        edge_ids: { type: "array", items: { type: "string" }, description: "Edge IDs to fillet" },
        radius: { type: "number", description: "Fillet radius in mm" },
        tangent_chain: { type: "boolean", description: "Auto-select tangent edges" },
      },
      required: ["edge_ids", "radius"],
    },
  },
  {
    name: "fusion_chamfer_edges",
    description: "Apply chamfers to 3D edges.",
    inputSchema: {
      type: "object" as const,
      properties: {
        edge_ids: { type: "array", items: { type: "string" }, description: "Edge IDs to chamfer" },
        distance: { type: "number", description: "Chamfer distance in mm" },
      },
      required: ["edge_ids", "distance"],
    },
  },
  {
    name: "fusion_boolean",
    description: "Combine bodies with boolean operations.",
    inputSchema: {
      type: "object" as const,
      properties: {
        operation: { type: "string", enum: ["union", "subtract", "intersect"], description: "Boolean operation" },
        target_body: { type: "string", description: "Body to modify" },
        tool_bodies: { type: "array", items: { type: "string" }, description: "Bodies to combine with" },
        keep_tools: { type: "boolean", description: "Keep tool bodies" },
      },
      required: ["operation", "target_body", "tool_bodies"],
    },
  },

  // ============ Organic Modeling ============
  {
    name: "fusion_loft",
    description: "Loft between multiple sketch profiles to create organic 3D forms. Essential for creating smooth transitions between different cross-sections.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_ids: { type: "array", items: { type: "string" }, description: "List of sketch names containing profiles to loft between (minimum 2)" },
        profile_indices: { type: "array", items: { type: "number" }, description: "Profile indices for each sketch (default: 0 for all)" },
        operation: { type: "string", enum: ["new_body", "join", "cut", "intersect"], description: "Boolean operation (default: new_body)" },
        is_solid: { type: "boolean", description: "Create solid vs surface (default: true)" },
        rails: { type: "array", items: { type: "string" }, description: "Optional rail sketch IDs to guide the loft shape" },
      },
      required: ["sketch_ids"],
    },
  },
  {
    name: "fusion_sweep",
    description: "Sweep a profile along a path curve to create 3D geometry. Useful for creating consistent cross-sections along a curved path.",
    inputSchema: {
      type: "object" as const,
      properties: {
        profile_sketch_id: { type: "string", description: "Sketch containing the profile to sweep" },
        path_sketch_id: { type: "string", description: "Sketch containing the path curve" },
        profile_index: { type: "number", description: "Profile index in the sketch (default: 0)" },
        operation: { type: "string", enum: ["new_body", "join", "cut", "intersect"], description: "Boolean operation (default: new_body)" },
        orientation: { type: "string", enum: ["perpendicular", "parallel"], description: "Profile orientation relative to path (default: perpendicular)" },
        twist_angle: { type: "number", description: "Optional twist angle in degrees along the sweep" },
      },
      required: ["profile_sketch_id", "path_sketch_id"],
    },
  },
  {
    name: "fusion_revolve",
    description: "Revolve a profile around an axis to create 3D geometry. Perfect for creating bowls, vases, and other rotationally symmetric shapes.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Sketch containing the profile to revolve" },
        profile_index: { type: "number", description: "Profile index (default: 0)" },
        axis: { type: "string", enum: ["x", "y", "z"], description: "Axis to revolve around (default: x)" },
        axis_sketch_id: { type: "string", description: "Alternative: sketch containing axis line" },
        axis_line_index: { type: "number", description: "Index of line in axis sketch (default: 0)" },
        angle: { type: "number", description: "Angle in degrees (default: 360 for full revolution)" },
        operation: { type: "string", enum: ["new_body", "join", "cut", "intersect"], description: "Boolean operation (default: new_body)" },
      },
      required: ["sketch_id"],
    },
  },
  {
    name: "fusion_create_sphere",
    description: "Create a sphere primitive body. Useful for boolean operations to create organic concave surfaces.",
    inputSchema: {
      type: "object" as const,
      properties: {
        center: { type: "array", items: { type: "number" }, description: "[x, y, z] center point in mm" },
        radius: { type: "number", description: "Radius in mm" },
        name: { type: "string", description: "Optional name for the body" },
      },
      required: ["radius"],
    },
  },
  {
    name: "fusion_create_cylinder",
    description: "Create a cylinder primitive body. Center is the base center. Use get_body_center first to find where existing geometry is positioned.",
    inputSchema: {
      type: "object" as const,
      properties: {
        center: { type: "array", items: { type: "number" }, description: "[x, y, z] center point of BASE in mm - cylinder extends upward along axis from here" },
        radius: { type: "number", description: "Radius in mm" },
        height: { type: "number", description: "Height in mm" },
        axis: { type: "string", enum: ["x", "y", "z"], description: "Cylinder axis (default: z)" },
        name: { type: "string", description: "Optional name for the body" },
      },
      required: ["radius", "height"],
    },
  },
  {
    name: "fusion_create_box",
    description: "Create a box primitive body. Much simpler than sketch+extrude for boolean operations. Can specify by corners OR by center+dimensions.",
    inputSchema: {
      type: "object" as const,
      properties: {
        corner1: { type: "array", items: { type: "number" }, description: "[x, y, z] first corner in mm" },
        corner2: { type: "array", items: { type: "number" }, description: "[x, y, z] opposite corner in mm" },
        center: { type: "array", items: { type: "number" }, description: "[x, y, z] center point in mm (alternative to corners)" },
        width: { type: "number", description: "Width (X) in mm (used with center)" },
        depth: { type: "number", description: "Depth (Y) in mm (used with center)" },
        height: { type: "number", description: "Height (Z) in mm (used with center)" },
        name: { type: "string", description: "Optional name for the body" },
      },
      required: [],
    },
  },
  {
    name: "fusion_create_hole",
    description: "Create a cylindrical hole (cut) through a body. Much simpler than creating a cylinder and doing boolean subtract. Use for mounting holes, etc.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_id: { type: "string", description: "Target body to cut the hole in" },
        center: { type: "array", items: { type: "number" }, description: "[x, y, z] center point of hole start in mm" },
        diameter: { type: "number", description: "Hole diameter in mm" },
        depth: { type: "number", description: "Hole depth in mm (ignored if through_all is true)" },
        axis: { type: "string", enum: ["x", "y", "z"], description: "Direction of hole (default: z = vertical)" },
        through_all: { type: "boolean", description: "If true, cuts through the entire body" },
      },
      required: ["body_id", "center", "diameter"],
    },
  },
  {
    name: "fusion_extrude_with_draft",
    description: "Extrude a profile with a draft/taper angle. Creates tapered extrusions for organic shapes.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Sketch containing the profile" },
        profile_index: { type: "number", description: "Profile index (default: 0)" },
        distance: { type: "number", description: "Extrusion distance in mm" },
        draft_angle: { type: "number", description: "Taper angle in degrees (positive = outward, negative = inward)" },
        direction: { type: "string", enum: ["positive", "negative", "symmetric"], description: "Extrusion direction" },
        operation: { type: "string", enum: ["new_body", "join", "cut", "intersect"], description: "Boolean operation" },
        target_body: { type: "string", description: "Target body for join/cut operations" },
      },
      required: ["sketch_id", "distance"],
    },
  },

  // ============ Selection & Query ============
  {
    name: "fusion_list_bodies",
    description: "Get all bodies in the design.",
    inputSchema: {
      type: "object" as const,
      properties: {
        component: { type: "string", description: "Component to query (default: root)" },
      },
      required: [],
    },
  },
  {
    name: "fusion_delete_body",
    description: "Delete a body by name.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_name: { type: "string", description: "Name of the body to delete" },
        component: { type: "string", description: "Optional component to search in" },
      },
      required: ["body_name"],
    },
  },
  {
    name: "fusion_delete_sketch",
    description: "Delete a sketch by name.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_name: { type: "string", description: "Name of the sketch to delete" },
        component: { type: "string", description: "Optional component to search in" },
      },
      required: ["sketch_name"],
    },
  },
  {
    name: "fusion_list_edges",
    description: "Get edges from a body.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_id: { type: "string", description: "Body name" },
        filter: {
          type: "object",
          properties: {
            type: { type: "string", enum: ["circular", "linear", "all"] },
            radius_min: { type: "number" },
            radius_max: { type: "number" },
          },
          description: "Filter criteria",
        },
      },
      required: ["body_id"],
    },
  },
  {
    name: "fusion_list_faces",
    description: "Get faces from a body.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_id: { type: "string", description: "Body name" },
        component: { type: "string", description: "Optional component name" },
        filter: {
          type: "object",
          properties: {
            type: { type: "string", enum: ["planar", "cylindrical", "spherical", "all"] },
          },
          description: "Filter criteria",
        },
      },
      required: ["body_id"],
    },
  },
  {
    name: "fusion_get_face_info",
    description: "Get detailed information about a specific face including normal vector, area, center point, and angle relative to world axes. Essential for understanding angled surfaces like miter joints.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_id: { type: "string", description: "Body name" },
        face_id: { type: "string", description: "Face ID" },
        component: { type: "string", description: "Optional component name" },
      },
      required: ["body_id", "face_id"],
    },
  },
  {
    name: "fusion_find_body_intersections",
    description: "Find edges/lines where two bodies meet or intersect. Perfect for locating joint lines like miter joints.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body1: { type: "string", description: "First body name" },
        body2: { type: "string", description: "Second body name" },
        component: { type: "string", description: "Optional component name" },
        tolerance: { type: "number", description: "Distance tolerance in mm (default: 0.01)" },
      },
      required: ["body1", "body2"],
    },
  },
  {
    name: "fusion_select_by_position",
    description: "Find geometry near a 3D point.",
    inputSchema: {
      type: "object" as const,
      properties: {
        point: { type: "array", items: { type: "number" }, description: "[x, y, z] reference point in mm" },
        type: { type: "string", enum: ["edge", "face", "body", "vertex"], description: "Geometry type to find" },
        tolerance: { type: "number", description: "Search radius in mm" },
      },
      required: ["point", "type"],
    },
  },
  {
    name: "fusion_get_body_center",
    description: "Get the center point, bounding box, and dimensions of a body. ESSENTIAL before positioning cuts, holes, or boolean operations to ensure geometry will intersect correctly.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_id: { type: "string", description: "Name of the body to query" },
      },
      required: ["body_id"],
    },
  },
  {
    name: "fusion_get_model_summary",
    description: "Get a comprehensive summary of the entire model: world bounds, orientation analysis (detects if model built into -Z), all components/bodies with dimensions, and parameters. Call this FIRST to understand the current state!",
    inputSchema: {
      type: "object" as const,
      properties: {},
      required: [],
    },
  },

  // ============ Component Management ============
  {
    name: "fusion_list_components",
    description: "List all components in the design with hierarchy information. Returns component tree structure, body counts, sketch counts, and child relationships.",
    inputSchema: {
      type: "object" as const,
      properties: {},
      required: [],
    },
  },
  {
    name: "fusion_get_component_info",
    description: "Get detailed information about a specific component including all bodies, sketches, construction planes, and child occurrences.",
    inputSchema: {
      type: "object" as const,
      properties: {
        component: { type: "string", description: "Component name (e.g., 'Carcass' or 'Carcass:1')" },
      },
      required: ["component"],
    },
  },
  {
    name: "fusion_create_component",
    description: "Create a new component in the design. Can optionally specify a parent component to create a hierarchical structure.",
    inputSchema: {
      type: "object" as const,
      properties: {
        name: { type: "string", description: "Name for the new component" },
        parent: { type: "string", description: "Optional parent component name (default: root component)" },
      },
      required: ["name"],
    },
  },
  {
    name: "fusion_delete_component",
    description: "Delete a component from the design. Cannot delete the root component. Deletes the component occurrence.",
    inputSchema: {
      type: "object" as const,
      properties: {
        component: { type: "string", description: "Component name to delete (e.g., 'Carcass' or 'Carcass:1')" },
      },
      required: ["component"],
    },
  },

  // ============ Transform Operations ============
  {
    name: "fusion_copy_body",
    description: "Copy a body.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_id: { type: "string", description: "Body to copy" },
        name: { type: "string", description: "Name for the copy" },
      },
      required: ["body_id"],
    },
  },
  {
    name: "fusion_move_body",
    description: "Move or rotate a body.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_id: { type: "string", description: "Body to move" },
        translation: { type: "array", items: { type: "number" }, description: "[x, y, z] translation in mm" },
        rotation: {
          type: "object",
          properties: {
            axis: { type: "array", items: { type: "number" }, description: "Rotation axis [x, y, z]" },
            angle: { type: "number", description: "Angle in degrees" },
            origin: { type: "array", items: { type: "number" }, description: "Rotation origin [x, y, z]" },
          },
          description: "Rotation specification",
        },
      },
      required: ["body_id"],
    },
  },
  {
    name: "fusion_mirror_body",
    description: "Mirror a body across a plane.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_id: { type: "string", description: "Body to mirror" },
        plane: { type: "string", description: "Mirror plane (xy, xz, yz, or custom)" },
      },
      required: ["body_id", "plane"],
    },
  },
  {
    name: "fusion_pattern_rectangular",
    description: "Create a rectangular pattern of a body.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_id: { type: "string", description: "Body to pattern" },
        direction1: { type: "array", items: { type: "number" }, description: "First direction [x, y, z]" },
        count1: { type: "number", description: "Count in first direction" },
        spacing1: { type: "number", description: "Spacing in mm" },
        direction2: { type: "array", items: { type: "number" }, description: "Second direction [x, y, z]" },
        count2: { type: "number", description: "Count in second direction" },
        spacing2: { type: "number", description: "Spacing in mm" },
      },
      required: ["body_id", "direction1", "count1", "spacing1"],
    },
  },

  // ============ Parameters ============
  {
    name: "fusion_create_parameter",
    description: "Create a user parameter.",
    inputSchema: {
      type: "object" as const,
      properties: {
        name: { type: "string", description: "Parameter name" },
        value: { type: "number", description: "Initial value" },
        unit: { type: "string", description: "Unit (mm, in, deg, etc.)" },
        comment: { type: "string", description: "Description" },
      },
      required: ["name", "value"],
    },
  },
  {
    name: "fusion_modify_parameter",
    description: "Change a parameter value.",
    inputSchema: {
      type: "object" as const,
      properties: {
        name: { type: "string", description: "Parameter name" },
        value: { type: "number", description: "New value" },
      },
      required: ["name", "value"],
    },
  },
  {
    name: "fusion_list_parameters",
    description: "Get all user parameters.",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
  {
    name: "fusion_list_all_parameters",
    description: "List all parameters including model parameters from features.",
    inputSchema: {
      type: "object" as const,
      properties: {
        include_model_parameters: { type: "boolean", description: "Include model parameters (default: false)" },
      },
      required: [],
    },
  },
  {
    name: "fusion_get_feature_parameters",
    description: "Get all editable parameters for a feature by name or timeline index.",
    inputSchema: {
      type: "object" as const,
      properties: {
        feature_name: { type: "string", description: "Feature name from timeline" },
        feature_index: { type: "number", description: "Timeline index (alternative to name)" },
      },
      required: [],
    },
  },
  {
    name: "fusion_edit_feature_parameter",
    description: "Edit a feature's parameter (e.g., extrude distance). Can set numeric value or parameter expression.",
    inputSchema: {
      type: "object" as const,
      properties: {
        feature_name: { type: "string", description: "Feature name from timeline" },
        feature_index: { type: "number", description: "Timeline index (alternative to name)" },
        parameter_name: { type: "string", description: "Parameter to edit (default: 'distance' for extrudes)" },
        value: { type: "number", description: "New value in mm" },
        expression: { type: "string", description: "Parameter expression (e.g., 'carcass_thickness' or 'overall_width - 2 * carcass_thickness')" },
      },
      required: [],
    },
  },

  // ============ Appearance ============
  {
    name: "fusion_apply_appearance",
    description: "Apply a material appearance to a body.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_id: { type: "string", description: "Target body" },
        appearance: { type: "string", description: "Appearance name (e.g., 'Walnut', 'Oak', 'Aluminum - Brushed')" },
      },
      required: ["body_id", "appearance"],
    },
  },
  {
    name: "fusion_list_appearances",
    description: "Get available appearances from the library.",
    inputSchema: {
      type: "object" as const,
      properties: {
        category: { type: "string", enum: ["Wood", "Metal", "Plastic"], description: "Filter by category" },
      },
      required: [],
    },
  },

  // ============ Utility ============
  {
    name: "fusion_take_screenshot",
    description: "Capture the current viewport as an image.",
    inputSchema: {
      type: "object" as const,
      properties: {
        width: { type: "number", description: "Image width (default: 1920)" },
        height: { type: "number", description: "Image height (default: 1080)" },
        view: { type: "string", enum: ["current", "top", "front", "right", "isometric"], description: "View preset" },
      },
      required: [],
    },
  },
  {
    name: "fusion_set_view",
    description: "Set the camera/viewport.",
    inputSchema: {
      type: "object" as const,
      properties: {
        preset: { type: "string", enum: ["top", "front", "right", "back", "left", "bottom", "isometric"], description: "View preset" },
        fit: { type: "boolean", description: "Zoom to fit all geometry" },
      },
      required: [],
    },
  },
  {
    name: "fusion_undo",
    description: "Undo the last operation.",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
  {
    name: "fusion_redo",
    description: "Redo the last undone operation.",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
  {
    name: "fusion_get_timeline",
    description: "Get the feature timeline.",
    inputSchema: { type: "object" as const, properties: {}, required: [] },
  },
  {
    name: "fusion_export",
    description: "Export the model to a file.",
    inputSchema: {
      type: "object" as const,
      properties: {
        format: { type: "string", enum: ["stl", "step", "iges", "f3d"], description: "Export format" },
        path: { type: "string", description: "Output file path" },
        options: {
          type: "object",
          properties: {
            refinement: { type: "string", enum: ["low", "medium", "high"] },
          },
          description: "Format-specific options",
        },
      },
      required: ["format", "path"],
    },
  },

  // ============ Workspace ============
  {
    name: "fusion_switch_workspace",
    description: "Switch to a different Fusion 360 workspace.",
    inputSchema: {
      type: "object" as const,
      properties: {
        workspace: { 
          type: "string", 
          enum: ["design", "manufacture", "render", "animation", "simulation", "drawing"],
          description: "Workspace to switch to" 
        },
      },
      required: ["workspace"],
    },
  },

  // ============ Frame Management ============
  {
    name: "fusion_create_frame",
    description: "Create a new reference frame for spatial organization and tracking.",
    inputSchema: {
      type: "object" as const,
      properties: {
        name: { type: "string", description: "Frame name" },
        type: { type: "string", enum: ["body", "interface", "sketch", "feature"], description: "Frame type" },
        origin: { type: "array", items: { type: "number" }, description: "[x, y, z] origin in world coords" },
        orientation: { 
          type: "object",
          properties: {
            x: { type: "number" },
            y: { type: "number" },
            z: { type: "number" }
          },
          description: "Euler angles in degrees (default: {x:0, y:0, z:0})"
        },
        parent: { type: "string", description: "Parent frame name (default: WorldFrame)" },
        metadata: { type: "object", description: "Custom metadata for the frame" }
      },
      required: ["name", "type", "origin"]
    }
  },
  {
    name: "fusion_get_frame",
    description: "Get detailed information about a frame including children and relationships.",
    inputSchema: {
      type: "object" as const,
      properties: {
        name: { type: "string", description: "Frame name" },
        include_children: { type: "boolean", description: "Include child frame details" },
        include_mates: { type: "boolean", description: "Include mating frame information" }
      },
      required: ["name"]
    }
  },
  {
    name: "fusion_list_frames",
    description: "List all frames in the current document with optional filtering.",
    inputSchema: {
      type: "object" as const,
      properties: {
        filter: {
          type: "object",
          properties: {
            type: { type: "string", description: "Filter by frame type" },
            parent: { type: "string", description: "Filter by parent frame" }
          }
        }
      },
      required: []
    }
  },
  {
    name: "fusion_delete_frame",
    description: "Delete a frame and all its children.",
    inputSchema: {
      type: "object" as const,
      properties: {
        name: { type: "string", description: "Frame name to delete" }
      },
      required: ["name"]
    }
  },
  {
    name: "fusion_transform_point",
    description: "Transform a point from one frame's coordinate system to another.",
    inputSchema: {
      type: "object" as const,
      properties: {
        point: { type: "array", items: { type: "number" }, description: "[x, y, z] point" },
        from_frame: { type: "string", description: "Source frame name" },
        to_frame: { type: "string", description: "Target frame name" }
      },
      required: ["point", "from_frame", "to_frame"]
    }
  },
  {
    name: "fusion_create_body_frame",
    description: "Automatically create a frame for a body centered at its bounding box. Call this after creating bodies to enable frame-based operations.",
    inputSchema: {
      type: "object" as const,
      properties: {
        body_name: { type: "string", description: "Name of the body" },
        component: { type: "string", description: "Optional component name to search in" }
      },
      required: ["body_name"]
    }
  },
  {
    name: "fusion_create_interface_frame",
    description: "Create an interface frame for a joint between two bodies. Defines connection points and mating relationships.",
    inputSchema: {
      type: "object" as const,
      properties: {
        parent_frame: { type: "string", description: "Parent body frame" },
        name: { type: "string", description: "Interface frame name" },
        origin: { type: "array", items: { type: "number" }, description: "[x, y, z] position in world coords" },
        normal: { type: "array", items: { type: "number" }, description: "[x, y, z] surface normal vector" },
        mates_with: { type: "string", description: "Name of mating interface frame" },
        metadata: { type: "object", description: "Joint metadata (type, pattern, status, etc.)" }
      },
      required: ["parent_frame", "name", "origin", "normal"]
    }
  },
];

// Endpoint mapping
const ENDPOINTS: Record<string, string> = {
  fusion_ping: "/ping",
  fusion_get_document_info: "/info",
  fusion_new_document: "/new_document",
  fusion_open_document: "/open_document",
  fusion_save: "/save",
  fusion_list_planes: "/list_planes",
  fusion_create_offset_plane: "/create_offset_plane",
  fusion_create_sketch: "/create_sketch",
  fusion_create_sketch_on_face: "/create_sketch_on_face",
  fusion_draw_line: "/draw_line",
  fusion_draw_arc: "/draw_arc",
  fusion_draw_arc_3point: "/draw_arc_3point",
  fusion_draw_circle: "/draw_circle",
  fusion_draw_rectangle: "/draw_rectangle",
  fusion_draw_rectangle_3d: "/draw_rectangle_3d",
  fusion_draw_spline: "/draw_spline",
  fusion_sketch_fillet: "/sketch_fillet",
  fusion_finish_sketch: "/finish_sketch",
  fusion_get_sketch_profiles: "/get_sketch_profiles",
  fusion_list_sketch_dimensions: "/list_sketch_dimensions",
  fusion_edit_sketch_dimension: "/edit_sketch_dimension",
  fusion_import_svg: "/import_svg",
  fusion_add_text: "/add_text",
  fusion_list_sketches: "/list_sketches",
  fusion_sketch_to_3d_coords: "/sketch_to_3d_coords",
  fusion_suggest_sketch_coords: "/suggest_sketch_coords",
  fusion_extrude: "/extrude",
  fusion_extrude_with_draft: "/extrude_with_draft",
  fusion_fillet_edges: "/fillet_edges",
  fusion_chamfer_edges: "/chamfer_edges",
  fusion_boolean: "/boolean",
  // Organic Modeling
  fusion_loft: "/loft",
  fusion_sweep: "/sweep",
  fusion_revolve: "/revolve",
  fusion_create_sphere: "/create_sphere",
  fusion_create_cylinder: "/create_cylinder",
  fusion_create_box: "/create_box",
  fusion_create_hole: "/create_hole",
  fusion_list_bodies: "/list_bodies",
  fusion_delete_body: "/delete_body",
  fusion_delete_sketch: "/delete_sketch",
  fusion_list_edges: "/list_edges",
  fusion_list_faces: "/list_faces",
  fusion_get_face_info: "/get_face_info",
  fusion_find_body_intersections: "/find_body_intersections",
  fusion_select_by_position: "/select_by_position",
  fusion_get_body_center: "/get_body_center",
  fusion_get_model_summary: "/get_model_summary",
  fusion_list_components: "/list_components",
  fusion_get_component_info: "/get_component_info",
  fusion_create_component: "/create_component",
  fusion_delete_component: "/delete_component",
  fusion_copy_body: "/copy_body",
  fusion_move_body: "/move_body",
  fusion_mirror_body: "/mirror_body",
  fusion_pattern_rectangular: "/pattern_rectangular",
  fusion_create_parameter: "/create_parameter",
  fusion_modify_parameter: "/modify_parameter",
  fusion_list_parameters: "/list_parameters",
  fusion_list_all_parameters: "/list_all_parameters",
  fusion_get_feature_parameters: "/get_feature_parameters",
  fusion_edit_feature_parameter: "/edit_feature_parameter",
  fusion_apply_appearance: "/apply_appearance",
  fusion_list_appearances: "/list_appearances",
  fusion_take_screenshot: "/take_screenshot",
  fusion_set_view: "/set_view",
  fusion_undo: "/undo",
  fusion_redo: "/redo",
  fusion_get_timeline: "/get_timeline",
  fusion_export: "/export",
  // Workspace
  fusion_switch_workspace: "/switch_workspace",
  // Frame Management
  fusion_create_frame: "/create_frame",
  fusion_get_frame: "/get_frame",
  fusion_list_frames: "/list_frames",
  fusion_delete_frame: "/delete_frame",
  fusion_transform_point: "/transform_point",
  fusion_create_body_frame: "/create_body_frame",
  fusion_create_interface_frame: "/create_interface_frame",
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

  // Handle screenshot specially - return image content
  if (name === "fusion_take_screenshot" && result.image_base64) {
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
  console.error("Fusion Design MCP server running on stdio");
}

main().catch(console.error);

