# Fusion 360 MCP Server Specification

## Overview

MCP server that bridges Claude ↔ Fusion 360 via the Desktop API.  
Runs as a Fusion 360 add-in exposing tools over HTTP/stdio.

---

## Document Lifecycle

### `fusion_new_document`
Create a new Fusion 360 design document.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Document name (default: "Untitled") |

**Returns:**
```json
{
  "document_id": "uuid",
  "name": "string"
}
```

---

### `fusion_save`
Save the active document.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | No | Local path for offline save |

**Returns:**
```json
{
  "success": true,
  "path": "string"
}
```

---

### `fusion_get_document_info`
Get info about the active document.

**Returns:**
```json
{
  "document_id": "uuid",
  "name": "string",
  "units": "mm" | "in",
  "bodies": ["Body1", "Body2"],
  "components": ["RootComponent", "Component1"],
  "timeline_length": 12
}
```

---

## Reference Geometry

### `fusion_list_planes`
Get available construction planes.

**Returns:**
```json
{
  "planes": [
    { "id": "xy", "name": "XY Plane", "origin": [0,0,0], "normal": [0,0,1] },
    { "id": "xz", "name": "XZ Plane", "origin": [0,0,0], "normal": [0,1,0] },
    { "id": "yz", "name": "YZ Plane", "origin": [0,0,0], "normal": [1,0,0] }
  ]
}
```

---

### `fusion_create_offset_plane`
Create an offset construction plane.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `base_plane` | string | Yes | Plane ID to offset from |
| `offset` | number | Yes | Distance in document units |

**Returns:**
```json
{
  "plane_id": "offset_plane_1",
  "name": "Offset Plane 1"
}
```

---

## Sketch Operations

### `fusion_create_sketch`
Start a new sketch on a plane or face.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plane` | string | Yes | Plane ID or face ID |
| `name` | string | No | Sketch name |

**Returns:**
```json
{
  "sketch_id": "sketch_1",
  "name": "Sketch1"
}
```

---

### `fusion_draw_line`
Draw a line in the active sketch.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Target sketch |
| `start` | [number, number] | Yes | Start point [x, y] |
| `end` | [number, number] | Yes | End point [x, y] |
| `construction` | boolean | No | Construction line (default: false) |

**Returns:**
```json
{
  "curve_id": "line_1"
}
```

---

### `fusion_draw_arc`
Draw an arc by center, start, and sweep.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Target sketch |
| `center` | [number, number] | Yes | Arc center [x, y] |
| `radius` | number | Yes | Arc radius |
| `start_angle` | number | Yes | Start angle in degrees |
| `sweep_angle` | number | Yes | Sweep angle in degrees (positive = CCW) |

**Returns:**
```json
{
  "curve_id": "arc_1"
}
```

---

### `fusion_draw_arc_3point`
Draw an arc through three points.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Target sketch |
| `start` | [number, number] | Yes | Start point |
| `mid` | [number, number] | Yes | Point on arc |
| `end` | [number, number] | Yes | End point |

**Returns:**
```json
{
  "curve_id": "arc_2"
}
```

---

### `fusion_draw_circle`
Draw a circle.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Target sketch |
| `center` | [number, number] | Yes | Center point |
| `radius` | number | Yes | Circle radius |

**Returns:**
```json
{
  "curve_id": "circle_1"
}
```

---

### `fusion_draw_rectangle`
Draw a rectangle.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Target sketch |
| `corner1` | [number, number] | Yes | First corner |
| `corner2` | [number, number] | Yes | Opposite corner |

**Returns:**
```json
{
  "curve_ids": ["line_1", "line_2", "line_3", "line_4"]
}
```

---

### `fusion_draw_spline`
Draw a spline through control points.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Target sketch |
| `points` | [[number, number], ...] | Yes | Array of points |
| `closed` | boolean | No | Close the spline (default: false) |

**Returns:**
```json
{
  "curve_id": "spline_1"
}
```

---

### `fusion_sketch_fillet`
Add a fillet between two sketch curves at their intersection.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Target sketch |
| `curve1_id` | string | Yes | First curve |
| `curve2_id` | string | Yes | Second curve |
| `radius` | number | Yes | Fillet radius |

**Returns:**
```json
{
  "curve_id": "fillet_arc_1"
}
```

---

### `fusion_trim_curve`
Trim a curve at intersection points.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Target sketch |
| `curve_id` | string | Yes | Curve to trim |
| `keep_point` | [number, number] | Yes | Point on the segment to keep |

**Returns:**
```json
{
  "success": true
}
```

---

### `fusion_finish_sketch`
Exit sketch editing mode.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Sketch to finish |

**Returns:**
```json
{
  "success": true,
  "is_valid": true,
  "profile_count": 2,
  "open_curves": 0
}
```

---

### `fusion_get_sketch_profiles`
Get all closed profiles in a sketch.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Target sketch |

**Returns:**
```json
{
  "profiles": [
    {
      "profile_id": "profile_1",
      "area": 10000.0,
      "centroid": [50, 50],
      "bounding_box": { "min": [0, 0], "max": [100, 100] }
    }
  ]
}
```

---

## Constraints & Dimensions

### `fusion_add_dimension`
Add a dimension to a sketch element.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Target sketch |
| `type` | string | Yes | "distance", "radius", "diameter", "angle" |
| `target` | string or [string, string] | Yes | Curve ID(s) |
| `value` | number | Yes | Dimension value |

**Returns:**
```json
{
  "dimension_id": "dim_1"
}
```

---

### `fusion_add_constraint`
Add a geometric constraint.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sketch_id` | string | Yes | Target sketch |
| `type` | string | Yes | "horizontal", "vertical", "tangent", "perpendicular", "equal", "concentric", "coincident" |
| `targets` | [string, ...] | Yes | Curve/point IDs to constrain |

**Returns:**
```json
{
  "constraint_id": "constraint_1"
}
```

---

## 3D Features

### `fusion_extrude`
Extrude a sketch profile into a 3D body.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `profile_id` | string | Yes | Profile to extrude |
| `distance` | number | Yes | Extrusion distance |
| `direction` | string | No | "positive", "negative", "symmetric" (default: "positive") |
| `operation` | string | No | "new_body", "join", "cut", "intersect" (default: "new_body") |
| `taper_angle` | number | No | Draft angle in degrees (default: 0) |

**Returns:**
```json
{
  "feature_id": "extrude_1",
  "body_id": "Body1"
}
```

---

### `fusion_fillet_edges`
Apply fillets to 3D edges.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `edge_ids` | [string, ...] | Yes | Edges to fillet |
| `radius` | number | Yes | Fillet radius |
| `tangent_chain` | boolean | No | Auto-select tangent edges (default: true) |

**Returns:**
```json
{
  "feature_id": "fillet_1"
}
```

---

### `fusion_chamfer_edges`
Apply chamfers to 3D edges.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `edge_ids` | [string, ...] | Yes | Edges to chamfer |
| `distance` | number | Yes | Chamfer distance |
| `type` | string | No | "equal_distance", "two_distances", "distance_angle" |

**Returns:**
```json
{
  "feature_id": "chamfer_1"
}
```

---

### `fusion_boolean`
Combine bodies with boolean operations.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `operation` | string | Yes | "union", "subtract", "intersect" |
| `target_body` | string | Yes | Body to modify |
| `tool_bodies` | [string, ...] | Yes | Bodies to combine with |
| `keep_tools` | boolean | No | Keep tool bodies (default: false) |

**Returns:**
```json
{
  "success": true,
  "result_body": "Body1"
}
```

---

## Selection & Query

### `fusion_list_bodies`
Get all bodies in the design.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `component` | string | No | Component to query (default: root) |

**Returns:**
```json
{
  "bodies": [
    {
      "body_id": "Body1",
      "name": "Body1",
      "is_solid": true,
      "volume": 10000.0,
      "bounding_box": { "min": [0,0,0], "max": [100,100,10] }
    }
  ]
}
```

---

### `fusion_list_edges`
Get edges from a body.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `body_id` | string | Yes | Body to query |
| `filter` | object | No | Filter criteria |

**Filter options:**
```json
{
  "type": "circular" | "linear" | "all",
  "radius_min": number,
  "radius_max": number,
  "length_min": number,
  "length_max": number
}
```

**Returns:**
```json
{
  "edges": [
    {
      "edge_id": "edge_1",
      "type": "circular",
      "length": 31.4159,
      "radius": 5.0,
      "midpoint": [50, 50, 10]
    }
  ]
}
```

---

### `fusion_list_faces`
Get faces from a body.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `body_id` | string | Yes | Body to query |
| `filter` | object | No | Filter criteria |

**Filter options:**
```json
{
  "type": "planar" | "cylindrical" | "spherical" | "all",
  "normal": [number, number, number],
  "area_min": number,
  "area_max": number
}
```

**Returns:**
```json
{
  "faces": [
    {
      "face_id": "face_1",
      "type": "planar",
      "area": 10000.0,
      "normal": [0, 0, 1],
      "centroid": [50, 50, 10]
    }
  ]
}
```

---

### `fusion_select_by_position`
Find geometry near a 3D point.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `point` | [number, number, number] | Yes | Reference point |
| `type` | string | Yes | "edge", "face", "body", "vertex" |
| `tolerance` | number | No | Search radius (default: 1.0) |

**Returns:**
```json
{
  "matches": [
    { "id": "edge_1", "distance": 0.5 }
  ]
}
```

---

## Transform Operations

### `fusion_copy_body`
Copy a body.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `body_id` | string | Yes | Body to copy |
| `name` | string | No | Name for the copy |

**Returns:**
```json
{
  "body_id": "Body2",
  "name": "Body2"
}
```

---

### `fusion_move_body`
Move/rotate a body.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `body_id` | string | Yes | Body to move |
| `translation` | [number, number, number] | No | Translation vector |
| `rotation` | object | No | Rotation specification |

**Rotation object:**
```json
{
  "axis": [0, 0, 1],
  "angle": 90,
  "origin": [0, 0, 0]
}
```

**Returns:**
```json
{
  "success": true
}
```

---

### `fusion_mirror_body`
Mirror a body across a plane.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `body_id` | string | Yes | Body to mirror |
| `plane` | string | Yes | Mirror plane ID |

**Returns:**
```json
{
  "body_id": "Body3",
  "name": "Body3"
}
```

---

### `fusion_pattern_rectangular`
Create a rectangular pattern of a body.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `body_id` | string | Yes | Body to pattern |
| `direction1` | [number, number, number] | Yes | First direction vector |
| `count1` | number | Yes | Count in first direction |
| `spacing1` | number | Yes | Spacing in first direction |
| `direction2` | [number, number, number] | No | Second direction vector |
| `count2` | number | No | Count in second direction |
| `spacing2` | number | No | Spacing in second direction |

**Returns:**
```json
{
  "feature_id": "pattern_1",
  "body_ids": ["Body2", "Body3", "Body4"]
}
```

---

## Parameters

### `fusion_create_parameter`
Create a user parameter.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Parameter name |
| `value` | number | Yes | Initial value |
| `unit` | string | No | Unit type (default: document units) |
| `comment` | string | No | Description |

**Returns:**
```json
{
  "parameter_id": "coaster_size"
}
```

---

### `fusion_modify_parameter`
Change a parameter value.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Parameter name |
| `value` | number | Yes | New value |

**Returns:**
```json
{
  "success": true,
  "affected_features": ["extrude_1", "fillet_1"]
}
```

---

### `fusion_list_parameters`
Get all user parameters.

**Returns:**
```json
{
  "parameters": [
    { "name": "coaster_size", "value": 100, "unit": "mm", "comment": "Overall size" }
  ]
}
```

---

## Appearance

### `fusion_apply_appearance`
Apply a material appearance to a body.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `body_id` | string | Yes | Target body |
| `appearance` | string | Yes | Appearance name from library |

**Common appearances:**
- `"Walnut"`, `"Oak"`, `"Maple"`, `"Cherry"`
- `"Aluminum - Brushed"`, `"Steel - Satin"`
- `"Plastic - Matte (Black)"`

**Returns:**
```json
{
  "success": true
}
```

---

### `fusion_list_appearances`
Get available appearances from the library.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | No | Filter by category: "Wood", "Metal", "Plastic", etc. |

**Returns:**
```json
{
  "appearances": [
    { "name": "Walnut", "category": "Wood" },
    { "name": "Oak", "category": "Wood" }
  ]
}
```

---

## Utility

### `fusion_take_screenshot`
Capture the current viewport.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `width` | number | No | Image width (default: 1920) |
| `height` | number | No | Image height (default: 1080) |
| `view` | string | No | "current", "top", "front", "right", "isometric" |

**Returns:**
```json
{
  "image_base64": "...",
  "format": "png"
}
```

---

### `fusion_set_view`
Set the camera/viewport.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `preset` | string | No | "top", "front", "right", "back", "left", "bottom", "isometric" |
| `fit` | boolean | No | Zoom to fit all geometry (default: true) |

**Returns:**
```json
{
  "success": true
}
```

---

### `fusion_undo`
Undo the last operation.

**Returns:**
```json
{
  "success": true,
  "undone_feature": "fillet_1"
}
```

---

### `fusion_redo`
Redo the last undone operation.

**Returns:**
```json
{
  "success": true
}
```

---

### `fusion_get_timeline`
Get the feature timeline.

**Returns:**
```json
{
  "features": [
    { "index": 0, "name": "Sketch1", "type": "sketch", "suppressed": false },
    { "index": 1, "name": "Extrude1", "type": "extrude", "suppressed": false },
    { "index": 2, "name": "Fillet1", "type": "fillet", "suppressed": false }
  ]
}
```

---

### `fusion_export`
Export the model to a file.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `format` | string | Yes | "stl", "step", "iges", "obj", "f3d" |
| `path` | string | Yes | Output file path |
| `body_ids` | [string, ...] | No | Bodies to export (default: all) |
| `options` | object | No | Format-specific options |

**STL options:**
```json
{
  "refinement": "low" | "medium" | "high",
  "binary": true
}
```

**Returns:**
```json
{
  "success": true,
  "path": "/path/to/output.stl",
  "file_size": 125000
}
```

---

## Error Handling

All tools return errors in this format:

```json
{
  "error": true,
  "code": "INVALID_PROFILE",
  "message": "Profile 'profile_1' is not closed and cannot be extruded",
  "suggestion": "Check sketch for open curves using fusion_finish_sketch"
}
```

**Common error codes:**
- `DOCUMENT_NOT_FOUND`
- `SKETCH_NOT_FOUND`
- `INVALID_PROFILE`
- `GEOMETRY_ERROR`
- `SELECTION_EMPTY`
- `OPERATION_FAILED`
- `PARAMETER_INVALID`

---

## Example Workflow: Puzzle Coaster

```
1. fusion_new_document(name="PuzzleCoasters")
2. fusion_create_parameter(name="size", value=100)
3. fusion_create_parameter(name="thickness", value=10)
4. fusion_create_parameter(name="tab_radius", value=12)

5. fusion_create_sketch(plane="xy")
6. -- draw puzzle piece profile with lines and arcs --
7. fusion_finish_sketch(sketch_id="sketch_1")
8. fusion_get_sketch_profiles(sketch_id="sketch_1")

9. fusion_extrude(profile_id="profile_1", distance=10)
10. fusion_list_edges(body_id="Body1", filter={type:"all"})
11. fusion_fillet_edges(edge_ids=[...], radius=1.5)

12. fusion_apply_appearance(body_id="Body1", appearance="Walnut")
13. fusion_take_screenshot(view="isometric")

14. -- copy and position remaining 3 pieces --
15. fusion_export(format="stl", path="coasters.stl")
```

---

## MCP Server Configuration

Add to Cursor's MCP settings:

```json
{
  "mcpServers": {
    "fusion360": {
      "command": "python",
      "args": ["/path/to/fusion-mcp-server/main.py"],
      "env": {
        "FUSION_API_PORT": "8080"
      }
    }
  }
}
```

The server connects to the Fusion 360 add-in running on `localhost:8080`.




