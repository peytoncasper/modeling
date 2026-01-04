# Frame System Design for Fusion MCP

## The Core Problem

Models struggle with spatial reasoning in CAD because they lack a **persistent frame-of-reference system**. Each tool call is independent, and the model must reconstruct spatial context from scratch every time.

## What is a Frame?

A **frame** is a named coordinate system with:
1. **Origin** - Position in world space
2. **Orientation** - Rotation relative to world axes
3. **Parent** - Optional parent frame (for hierarchical transforms)
4. **Children** - Bodies, sketches, features attached to this frame
5. **Metadata** - Semantic information about what this frame represents

## Frame Hierarchy Example

```
WorldFrame (origin: [0,0,0])
├─ BasePanel_Frame
│  ├─ origin: [127, 200, 6.35]  (center of panel)
│  ├─ bounds_local: [-127, -200, -6.35] to [127, 200, 6.35]
│  ├─ orientation: [0°, 0°, 0°]
│  ├─ children:
│  │  ├─ BasePanel_Body
│  │  ├─ FrontEdge_Frame
│  │  │  ├─ origin: [0, -200, 0] (in BasePanel coords)
│  │  │  ├─ purpose: "box_joint_interface"
│  │  │  ├─ mating_frame: "FrontPanel_BottomEdge_Frame"
│  │  │  └─ features: [slot_0, slot_2, slot_4, ...]
│  │  └─ BackEdge_Frame
│
├─ FrontPanel_Frame
│  ├─ origin: [127, 6.35, 50.8]
│  ├─ orientation: [90°, 0°, 0°] (rotated to vertical)
│  ├─ children:
│  │  ├─ FrontPanel_Body
│  │  ├─ BottomEdge_Frame
│  │  │  ├─ origin: [0, 0, -44.45] (in FrontPanel coords)
│  │  │  ├─ purpose: "box_joint_interface"
│  │  │  ├─ mating_frame: "BasePanel_FrontEdge_Frame"
│  │  │  └─ features: [finger_0, finger_2, finger_4, ...]
│
└─ ConstructionPlanes
   ├─ XY_Frame (world aligned)
   ├─ XZ_Frame (world aligned)
   └─ YZ_Frame (world aligned)
```

## Why Frames Solve the Problems

### Problem 1: Lost Context Between Operations
**Before (no frames):**
```
Model: "I need to add fingers to FrontPanel"
Model calls: get_body_center("FrontPanel")
Model: "OK it's at min=[0,0,12.7], max=[254,12.7,88.9]"
Model: "Now I'll create a sketch... wait, where should the sketch be?"
Model: "Let me call get_body_center again..."
```

**After (with frames):**
```
Model: "I need to add fingers to FrontPanel"
Model calls: get_frame("FrontPanel")
Returns: {
  origin: [127, 6.35, 50.8],
  orientation: [90°, 0°, 0°],
  interfaces: {
    bottom_edge: {
      frame: "FrontPanel_BottomEdge_Frame",
      mates_with: "BasePanel_FrontEdge_Frame",
      world_position: [0, 0, 12.7],
      type: "box_joint"
    }
  }
}
Model: "I'll create a sketch in the FrontPanel_BottomEdge_Frame"
```

### Problem 2: Coordinate System Confusion
**Before:**
```
Model draws on XZ plane, forgets Y is inverted
Rectangle: corner1=[0,0], corner2=[12.7, 50]
Result: Goes from Z=0 to Z=-50 (wrong direction!)
```

**After:**
```
Model: create_sketch_in_frame("FrontPanel_BottomEdge_Frame")
Frame manager: "This frame is on XZ plane, Y is inverted"
Model: use_frame_coords(frame="...", world_points=[[0,0,0], [12.7,0,50]])
Returns: sketch_coords=[[0,-50], [12.7,0]] (auto-converted)
```

### Problem 3: Spatial Relationships
**Before:**
```
Model: "Will this extrusion touch that body?"
Model: *has no way to check*
Model: *tries the extrusion*
Result: Orphan body created
```

**After:**
```
Model: check_intersection_between_frames(
  "FrontPanel_BottomEdge_Frame",
  "BasePanel_FrontEdge_Frame"
)
Returns: {
  will_mate: true,
  contact_line: [[0,0,12.7], [254,0,12.7]],
  gap: 0.0,
  recommendation: "Extrude from BottomEdge_Frame in +Y direction by 12.7mm"
}
```

## Frame Types

### 1. Body Frames
Attached to physical bodies. Origin at body center, axes aligned to body's natural orientation.

```json
{
  "type": "body_frame",
  "name": "FrontPanel_Frame",
  "body": "FrontPanel",
  "origin_world": [127, 6.35, 50.8],
  "orientation": {"x": 0, "y": 90, "z": 0},
  "bounds_local": {
    "min": [-127, -6.35, -44.45],
    "max": [127, 6.35, 44.45]
  }
}
```

### 2. Interface Frames
Attached to edges/faces where bodies join. Defines connection semantics.

```json
{
  "type": "interface_frame",
  "name": "FrontPanel_BottomEdge_Frame",
  "parent": "FrontPanel_Frame",
  "origin_local": [0, -6.35, -44.45],
  "origin_world": [127, 0, 6.35],
  "normal": [0, -1, 0],
  "purpose": "box_joint_interface",
  "mates_with": "BasePanel_FrontEdge_Frame",
  "features": {
    "finger_spacing": 12.7,
    "finger_positions": [0, 25.4, 50.8, 76.2, ...]
  }
}
```

### 3. Sketch Frames
Attached to sketch planes. Handles coordinate conversions.

```json
{
  "type": "sketch_frame",
  "name": "FrontFingers_Sketch_Frame",
  "sketch": "FrontFingers",
  "plane": "xz",
  "origin_world": [0, 0, 0],
  "coordinate_mapping": {
    "sketch_x": "world_x",
    "sketch_y": "world_-z",
    "inversions": ["y_axis"]
  }
}
```

### 4. Feature Frames
Attached to specific features (joints, mortises, etc.). Groups related geometry.

```json
{
  "type": "feature_frame",
  "name": "FrontBottomJoint_Frame",
  "feature_type": "box_joint",
  "parent": "FrontPanel_BottomEdge_Frame",
  "components": {
    "fingers": ["finger_0", "finger_2", "finger_4"],
    "slots": ["slot_1", "slot_3", "slot_5"]
  },
  "mate_status": "assembled"
}
```

## Frame Operations API

### Core Frame Management

#### `fusion_create_frame`
Create a new named frame.
```json
{
  "name": "MyFrame",
  "type": "body_frame",
  "origin": [100, 50, 25],
  "orientation": {"x": 0, "y": 90, "z": 0},
  "parent": "WorldFrame"
}
```

#### `fusion_get_frame`
Query frame information.
```json
{
  "name": "FrontPanel_Frame",
  "include_children": true,
  "include_interfaces": true
}
```

#### `fusion_list_frames`
List all frames, optionally filtered.
```json
{
  "filter": {
    "type": "interface_frame",
    "purpose": "box_joint_interface"
  }
}
```

### Frame Transforms

#### `fusion_transform_point`
Convert coordinates between frames.
```json
{
  "point": [10, 20, 30],
  "from_frame": "FrontPanel_Frame",
  "to_frame": "WorldFrame"
}
```

#### `fusion_transform_sketch_coords`
Convert between sketch 2D and world 3D.
```json
{
  "sketch_id": "MySketch",
  "points_2d": [[0, 50], [12.7, 0]],
  "to_frame": "WorldFrame"
}
```

### Frame-Aware Creation

#### `fusion_create_sketch_in_frame`
Create sketch positioned by frame.
```json
{
  "frame": "FrontPanel_BottomEdge_Frame",
  "name": "FrontFingers",
  "offset": 0
}
// Returns sketch already positioned at frame's origin/orientation
```

#### `fusion_draw_rectangle_in_frame`
Draw using frame's coordinate system.
```json
{
  "sketch_id": "MySketch",
  "frame": "FrontPanel_BottomEdge_Frame",
  "corner1_frame_coords": [0, 0],
  "corner2_frame_coords": [12.7, 50]
}
// Automatically handles coordinate inversions
```

#### `fusion_extrude_between_frames`
Extrude from one frame toward another (automatic direction/distance).
```json
{
  "sketch_id": "FrontFingers",
  "from_frame": "FrontPanel_BottomEdge_Frame",
  "to_frame": "BasePanel_FrontEdge_Frame",
  "operation": "join",
  "target_body": "FrontPanel"
}
// Calculates direction and distance automatically
```

### Frame Queries

#### `fusion_check_frame_intersection`
Check if geometry in frame A will touch frame B.
```json
{
  "frame_a": "FrontPanel_BottomEdge_Frame",
  "frame_b": "BasePanel_FrontEdge_Frame",
  "geometry_a": "sketch_profile_0"
}
// Returns: { will_intersect: true, gap: 0, contact_line: [...] }
```

#### `fusion_get_mating_frames`
Find all frames that should mate with given frame.
```json
{
  "frame": "FrontPanel_BottomEdge_Frame"
}
// Returns: ["BasePanel_FrontEdge_Frame"]
```

#### `fusion_validate_joint`
Pre-validate a joint operation using frames.
```json
{
  "joint_type": "box_joint",
  "frame_a": "FrontPanel_BottomEdge_Frame",
  "frame_b": "BasePanel_FrontEdge_Frame",
  "finger_width": 12.7
}
// Returns success/failure prediction with detailed reasoning
```

## Frame Metadata for Context

Frames carry semantic information to help model reasoning:

```json
{
  "name": "BasePanel_FrontEdge_Frame",
  "metadata": {
    "purpose": "Receives fingers from FrontPanel",
    "joint_type": "box_joint",
    "edge_length": 254,
    "thickness": 12.7,
    "finger_width": 12.7,
    "pattern": "slots at even positions",
    "mating_panel": "FrontPanel",
    "mating_edge": "bottom",
    "construction_order": 2,
    "status": "slots_cut"
  }
}
```

Model can query: "What joints still need to be built?"
```json
fusion_list_frames({
  filter: { "metadata.status": "pending" }
})
```

## Frame-Based Workflow

### Building Box Joints with Frames

```javascript
// 1. Model creates panel frames automatically when bodies are created
fusion_extrude(sketch="BasePanel", ..., body_name="BasePanel")
// → Automatically creates "BasePanel_Frame"

// 2. Model explicitly defines interface frames for joints
fusion_create_interface_frame({
  parent: "BasePanel_Frame",
  name: "BasePanel_FrontEdge_Frame",
  edge: "front",  // or specify world coordinates
  purpose: "box_joint",
  mates_with: "FrontPanel_BottomEdge_Frame",
  metadata: {
    joint_type: "box_joint",
    finger_width: 12.7,
    pattern: "slots"
  }
})

// 3. Model uses frame-aware sketch creation
fusion_create_sketch_in_frame({
  frame: "BasePanel_FrontEdge_Frame",
  name: "BaseSlots"
})
// Sketch is automatically positioned on the edge

// 4. Model draws in frame coordinates (no inversions to worry about!)
fusion_draw_rectangles_in_frame({
  sketch_id: "BaseSlots",
  frame: "BasePanel_FrontEdge_Frame",
  pattern: "alternating",
  width: 12.7,
  depth: 12.7,
  count: 10
})

// 5. Model cuts slots
fusion_extrude_in_frame({
  sketch_id: "BaseSlots",
  frame: "BasePanel_FrontEdge_Frame",
  direction: "into_panel",  // Frame knows which way is "in"
  distance: 12.7,
  operation: "cut",
  target_body: "BasePanel"
})

// 6. Model validates before creating fingers
fusion_validate_mating_frames({
  frame_a: "FrontPanel_BottomEdge_Frame",
  frame_b: "BasePanel_FrontEdge_Frame"
})
// Returns: "Ready to add fingers. Use same positions as slots."

// 7. Model creates fingers (frame handles positioning)
fusion_create_fingers_in_frame({
  frame: "FrontPanel_BottomEdge_Frame",
  mating_frame: "BasePanel_FrontEdge_Frame",
  target_body: "FrontPanel"
})
// Automatic: positions, direction, distance, join operation
```

## Implementation Strategy

### Phase 1: Frame Registry (Backend)
Add frame tracking to Python bridge:
```python
class FrameManager:
    def __init__(self):
        self.frames = {}
    
    def create_frame(self, name, type, origin, orientation, parent=None):
        frame = Frame(name, type, origin, orientation, parent)
        self.frames[name] = frame
        return frame
    
    def get_transform(self, from_frame, to_frame):
        # Calculate transformation matrix
        pass
```

### Phase 2: Frame-Aware Tools (API)
Add frame parameters to existing tools:
- `fusion_create_sketch` → add optional `frame` parameter
- `fusion_extrude` → add optional `from_frame`, `to_frame` parameters
- All drawing tools → add optional `frame` parameter

### Phase 3: High-Level Frame Operations (Convenience)
Add new tools that work primarily with frames:
- `fusion_create_interface_frame`
- `fusion_extrude_between_frames`
- `fusion_validate_mating_frames`

### Phase 4: Pattern Libraries with Frames
Update patterns to use frame-based thinking:
- Box joints: Define interface frames first, then build features
- Mortises: Define feature frames for each mortise location
- Miters: Define miter interface frames with angle metadata

## Benefits

1. **Persistent Context** - Model maintains spatial understanding across operations
2. **Automatic Conversions** - Frame system handles coordinate transforms
3. **Validation** - Check operations before executing (reduce orphan bodies)
4. **Semantic Reasoning** - "What mates with what?" is explicit
5. **Hierarchical Structure** - Natural organization matches assembly process
6. **Reduced Cognitive Load** - Model thinks in logical frames, not raw coordinates

## Example: Complete Frame Tree for Bedside Table

```
WorldFrame
├─ BasePanel_Frame
│  ├─ BasePanel_Body
│  ├─ FrontEdge_Interface_Frame → mates BasePanel↔Front
│  ├─ BackEdge_Interface_Frame → mates BasePanel↔Back
│  ├─ LeftEdge_Interface_Frame → mates BasePanel↔Left
│  └─ RightEdge_Interface_Frame → mates BasePanel↔Right
│
├─ FrontPanel_Frame
│  ├─ FrontPanel_Body
│  ├─ BottomEdge_Interface_Frame → mates Front↔Base
│  ├─ LeftEdge_Interface_Frame → mates Front↔Left
│  ├─ RightEdge_Interface_Frame → mates Front↔Right
│  ├─ MiterTopLeft_Feature_Frame
│  └─ MortiseTopLeft_Feature_Frame
│
├─ LeftPanel_Frame
│  ├─ LeftPanel_Body
│  ├─ BottomEdge_Interface_Frame → mates Left↔Base
│  ├─ FrontEdge_Interface_Frame → mates Left↔Front
│  ├─ BackEdge_Interface_Frame → mates Left↔Back
│  ├─ Dado_Feature_Frame (for false floor)
│  └─ SplineSlots_Feature_Frame (4 slots along miter edges)
│
└─ Assembly_Frame
   ├─ BoxJoint_FrontBase_Joint_Frame
   ├─ BoxJoint_LeftBase_Joint_Frame
   ├─ Miter_TopLeftCorner_Joint_Frame
   └─ ... (all joints)
```

## Next Steps

1. Design frame data structures (JSON schema)
2. Implement FrameManager in Python bridge
3. Add frame parameters to existing MCP tools
4. Create new frame-specific tools
5. Update pattern documentation to use frames
6. Test with complex project (bedside table)








