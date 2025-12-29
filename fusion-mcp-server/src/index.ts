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
    name: "fusion360",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool definitions
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
    name: "fusion_draw_line",
    description: "Draw a line in a sketch.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        start: { type: "array", items: { type: "number" }, description: "[x, y] start point in mm" },
        end: { type: "array", items: { type: "number" }, description: "[x, y] end point in mm" },
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
    description: "Draw a rectangle.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
        corner1: { type: "array", items: { type: "number" }, description: "[x, y] first corner" },
        corner2: { type: "array", items: { type: "number" }, description: "[x, y] opposite corner" },
      },
      required: ["sketch_id", "corner1", "corner2"],
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
    description: "Get all closed profiles in a sketch.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Target sketch name" },
      },
      required: ["sketch_id"],
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
    description: "Extrude a sketch profile into a 3D body. For join/cut operations within a component, specify target_body.",
    inputSchema: {
      type: "object" as const,
      properties: {
        sketch_id: { type: "string", description: "Source sketch name" },
        profile_index: { type: "number", description: "Profile index (0-based)" },
        distance: { type: "number", description: "Extrusion distance in mm" },
        direction: { type: "string", enum: ["positive", "negative", "symmetric"], description: "Extrusion direction" },
        operation: { type: "string", enum: ["new_body", "join", "cut", "intersect"], description: "Boolean operation" },
        component: { type: "string", description: "Optional component name to find sketch in" },
        target_body: { type: "string", description: "Optional target body name for join/cut operations (must be in same component as sketch)" },
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
  fusion_ping: "/ping",
  fusion_get_document_info: "/info",
  fusion_new_document: "/new_document",
  fusion_save: "/save",
  fusion_list_planes: "/list_planes",
  fusion_create_offset_plane: "/create_offset_plane",
  fusion_create_sketch: "/create_sketch",
  fusion_draw_line: "/draw_line",
  fusion_draw_arc: "/draw_arc",
  fusion_draw_arc_3point: "/draw_arc_3point",
  fusion_draw_circle: "/draw_circle",
  fusion_draw_rectangle: "/draw_rectangle",
  fusion_draw_spline: "/draw_spline",
  fusion_sketch_fillet: "/sketch_fillet",
  fusion_finish_sketch: "/finish_sketch",
  fusion_get_sketch_profiles: "/get_sketch_profiles",
  fusion_list_sketch_dimensions: "/list_sketch_dimensions",
  fusion_edit_sketch_dimension: "/edit_sketch_dimension",
  fusion_import_svg: "/import_svg",
  fusion_add_text: "/add_text",
  fusion_extrude: "/extrude",
  fusion_fillet_edges: "/fillet_edges",
  fusion_chamfer_edges: "/chamfer_edges",
  fusion_boolean: "/boolean",
  fusion_list_bodies: "/list_bodies",
  fusion_delete_body: "/delete_body",
  fusion_delete_sketch: "/delete_sketch",
  fusion_list_edges: "/list_edges",
  fusion_list_faces: "/list_faces",
  fusion_select_by_position: "/select_by_position",
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
  console.error("Fusion 360 MCP server running on stdio");
}

main().catch(console.error);
