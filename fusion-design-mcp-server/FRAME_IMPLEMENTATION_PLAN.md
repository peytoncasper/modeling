# Frame System Implementation Plan

## Overview

This document outlines the step-by-step implementation of the frame system for the Fusion 360 MCP server.

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Claude Model (MCP Client)                      │
│  - Thinks in frames                             │
│  - Queries frame relationships                  │
│  - Uses frame-aware tools                       │
└─────────────────┬───────────────────────────────┘
                  │ MCP Protocol
┌─────────────────▼───────────────────────────────┐
│  TypeScript MCP Server (index.ts)               │
│  - Exposes frame tools                          │
│  - Forwards to Python bridge                    │
└─────────────────┬───────────────────────────────┘
                  │ HTTP (localhost:8080)
┌─────────────────▼───────────────────────────────┐
│  Python Fusion Bridge (FusionMCPBridge.py)     │
│  - FrameManager class                           │
│  - Frame persistence (JSON file)                │
│  - Coordinate transformations                   │
└─────────────────┬───────────────────────────────┘
                  │ Fusion API
┌─────────────────▼───────────────────────────────┐
│  Fusion 360                                     │
│  - Actual geometry operations                   │
└─────────────────────────────────────────────────┘
```

## Phase 1: Frame Data Structures & Manager

### 1.1 Frame Class (Python)

```python
# fusion-addin/frame_manager.py

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import json
import numpy as np

@dataclass
class Frame:
    """Represents a spatial reference frame."""
    name: str
    type: str  # "world", "body", "interface", "sketch", "feature"
    origin: List[float]  # [x, y, z] in world coordinates
    orientation: Dict[str, float]  # {"x": 0, "y": 90, "z": 0} euler angles
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_transform_matrix(self):
        """Return 4x4 transformation matrix for this frame."""
        # Convert euler angles to rotation matrix
        rx = np.radians(self.orientation.get('x', 0))
        ry = np.radians(self.orientation.get('y', 0))
        rz = np.radians(self.orientation.get('z', 0))
        
        # Rotation matrices
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(rx), -np.sin(rx)],
            [0, np.sin(rx), np.cos(rx)]
        ])
        Ry = np.array([
            [np.cos(ry), 0, np.sin(ry)],
            [0, 1, 0],
            [-np.sin(ry), 0, np.cos(ry)]
        ])
        Rz = np.array([
            [np.cos(rz), -np.sin(rz), 0],
            [np.sin(rz), np.cos(rz), 0],
            [0, 0, 1]
        ])
        
        R = Rz @ Ry @ Rx
        
        # 4x4 transformation matrix
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = self.origin
        
        return T
    
    def to_dict(self):
        """Serialize to JSON-compatible dict."""
        return {
            "name": self.name,
            "type": self.type,
            "origin": self.origin,
            "orientation": self.orientation,
            "parent": self.parent,
            "children": self.children,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data):
        """Deserialize from dict."""
        return cls(**data)


class FrameManager:
    """Manages all reference frames for a Fusion document."""
    
    def __init__(self, app):
        self.app = app
        self.frames: Dict[str, Frame] = {}
        self._init_world_frame()
        self._init_construction_plane_frames()
    
    def _init_world_frame(self):
        """Create the root world frame."""
        world = Frame(
            name="WorldFrame",
            type="world",
            origin=[0, 0, 0],
            orientation={"x": 0, "y": 0, "z": 0},
            parent=None,
            metadata={"description": "Root world coordinate system"}
        )
        self.frames["WorldFrame"] = world
    
    def _init_construction_plane_frames(self):
        """Create frames for standard construction planes."""
        self.frames["XY_Frame"] = Frame(
            name="XY_Frame",
            type="plane",
            origin=[0, 0, 0],
            orientation={"x": 0, "y": 0, "z": 0},
            parent="WorldFrame",
            metadata={
                "plane": "xy",
                "normal": [0, 0, 1],
                "coordinate_mapping": {
                    "sketch_x": "world_x",
                    "sketch_y": "world_y"
                }
            }
        )
        
        self.frames["XZ_Frame"] = Frame(
            name="XZ_Frame",
            type="plane",
            origin=[0, 0, 0],
            orientation={"x": -90, "y": 0, "z": 0},
            parent="WorldFrame",
            metadata={
                "plane": "xz",
                "normal": [0, 1, 0],
                "coordinate_mapping": {
                    "sketch_x": "world_x",
                    "sketch_y": "world_-z"
                },
                "inversions": ["y_axis"]
            }
        )
        
        self.frames["YZ_Frame"] = Frame(
            name="YZ_Frame",
            type="plane",
            origin=[0, 0, 0],
            orientation={"x": 0, "y": -90, "z": 0},
            parent="WorldFrame",
            metadata={
                "plane": "yz",
                "normal": [1, 0, 0],
                "coordinate_mapping": {
                    "sketch_x": "world_-z",
                    "sketch_y": "world_y"
                },
                "inversions": ["x_axis"]
            }
        )
    
    def create_frame(self, name: str, type: str, origin: List[float], 
                     orientation: Dict[str, float], parent: Optional[str] = None,
                     metadata: Dict = None) -> Frame:
        """Create a new frame."""
        if name in self.frames:
            raise ValueError(f"Frame {name} already exists")
        
        frame = Frame(
            name=name,
            type=type,
            origin=origin,
            orientation=orientation,
            parent=parent or "WorldFrame",
            metadata=metadata or {}
        )
        
        self.frames[name] = frame
        
        # Add as child to parent
        if frame.parent and frame.parent in self.frames:
            self.frames[frame.parent].children.append(name)
        
        return frame
    
    def get_frame(self, name: str) -> Optional[Frame]:
        """Get frame by name."""
        return self.frames.get(name)
    
    def list_frames(self, filter_type: Optional[str] = None) -> List[Frame]:
        """List all frames, optionally filtered by type."""
        frames = list(self.frames.values())
        if filter_type:
            frames = [f for f in frames if f.type == filter_type]
        return frames
    
    def delete_frame(self, name: str):
        """Delete a frame and its children."""
        if name not in self.frames:
            return
        
        frame = self.frames[name]
        
        # Recursively delete children
        for child_name in frame.children[:]:  # Copy to avoid mutation during iteration
            self.delete_frame(child_name)
        
        # Remove from parent's children list
        if frame.parent and frame.parent in self.frames:
            parent = self.frames[frame.parent]
            if name in parent.children:
                parent.children.remove(name)
        
        del self.frames[name]
    
    def transform_point(self, point: List[float], from_frame: str, to_frame: str) -> List[float]:
        """Transform a point from one frame to another."""
        # Get frames
        frame_from = self.frames.get(from_frame)
        frame_to = self.frames.get(to_frame)
        
        if not frame_from or not frame_to:
            raise ValueError(f"Frame not found: {from_frame} or {to_frame}")
        
        # Convert to homogeneous coordinates
        point_h = np.array([*point, 1])
        
        # Transform to world frame
        T_from = frame_from.get_transform_matrix()
        point_world = T_from @ point_h
        
        # Transform to target frame
        T_to = frame_to.get_transform_matrix()
        T_to_inv = np.linalg.inv(T_to)
        point_target = T_to_inv @ point_world
        
        return point_target[:3].tolist()
    
    def create_body_frame(self, body_name: str, body):
        """Automatically create a frame for a body."""
        # Get body bounding box
        bbox = body.boundingBox
        
        # Frame origin at body center
        origin = [
            (bbox.minPoint.x + bbox.maxPoint.x) / 2,
            (bbox.minPoint.y + bbox.maxPoint.y) / 2,
            (bbox.minPoint.z + bbox.maxPoint.z) / 2
        ]
        
        frame_name = f"{body_name}_Frame"
        
        return self.create_frame(
            name=frame_name,
            type="body",
            origin=origin,
            orientation={"x": 0, "y": 0, "z": 0},
            parent="WorldFrame",
            metadata={
                "body_name": body_name,
                "bounds_local": {
                    "min": [
                        bbox.minPoint.x - origin[0],
                        bbox.minPoint.y - origin[1],
                        bbox.minPoint.z - origin[2]
                    ],
                    "max": [
                        bbox.maxPoint.x - origin[0],
                        bbox.maxPoint.y - origin[1],
                        bbox.maxPoint.z - origin[2]
                    ]
                },
                "volume": body.volume,
                "area": body.area
            }
        )
    
    def create_interface_frame(self, parent_frame: str, name: str, 
                               edge_position: List[float], normal: List[float],
                               mates_with: Optional[str] = None,
                               metadata: Dict = None) -> Frame:
        """Create an interface frame for joints."""
        parent = self.frames.get(parent_frame)
        if not parent:
            raise ValueError(f"Parent frame {parent_frame} not found")
        
        # Calculate orientation from normal vector
        # (simplified - proper implementation would use full vector math)
        orientation = {"x": 0, "y": 0, "z": 0}  # TODO: Calculate from normal
        
        meta = metadata or {}
        if mates_with:
            meta["mates_with"] = mates_with
        meta["normal"] = normal
        
        return self.create_frame(
            name=name,
            type="interface",
            origin=edge_position,
            orientation=orientation,
            parent=parent_frame,
            metadata=meta
        )
    
    def get_mating_frames(self, frame_name: str) -> List[str]:
        """Get all frames that mate with the given frame."""
        frame = self.frames.get(frame_name)
        if not frame:
            return []
        
        mates_with = frame.metadata.get("mates_with")
        if mates_with:
            return [mates_with]
        
        # Also check for frames that mate with this one
        mating = []
        for f in self.frames.values():
            if f.metadata.get("mates_with") == frame_name:
                mating.append(f.name)
        
        return mating
    
    def save_to_file(self, filepath: str):
        """Persist frames to JSON file."""
        data = {
            "frames": [f.to_dict() for f in self.frames.values()]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filepath: str):
        """Load frames from JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.frames = {}
            for frame_data in data.get("frames", []):
                frame = Frame.from_dict(frame_data)
                self.frames[frame.name] = frame
        except FileNotFoundError:
            # No saved frames, start fresh
            self._init_world_frame()
            self._init_construction_plane_frames()
```

### 1.2 Integrate FrameManager into Bridge

```python
# fusion-addin/FusionMCPBridge.py

import adsk.core
import adsk.fusion
from .frame_manager import FrameManager
import os

class FusionMCPBridge:
    def __init__(self, app):
        self.app = app
        self.ui = app.userInterface
        self.frame_manager = FrameManager(app)
        self._load_frames()
    
    def _get_frames_file_path(self):
        """Get path to frames persistence file."""
        doc = self.app.activeDocument
        if doc and doc.dataFile:
            doc_path = doc.dataFile.parentFolder.path
            return os.path.join(doc_path, f"{doc.name}_frames.json")
        return None
    
    def _load_frames(self):
        """Load frames for current document."""
        filepath = self._get_frames_file_path()
        if filepath:
            self.frame_manager.load_from_file(filepath)
    
    def _save_frames(self):
        """Save frames for current document."""
        filepath = self._get_frames_file_path()
        if filepath:
            self.frame_manager.save_to_file(filepath)
    
    # ... existing methods ...
```

## Phase 2: Frame API Endpoints

### 2.1 Add Frame Endpoints to Bridge

```python
# fusion-addin/FusionMCPBridge.py (continued)

class FusionMCPBridge:
    # ... existing code ...
    
    def handle_create_frame(self, data):
        """Create a new reference frame."""
        try:
            frame = self.frame_manager.create_frame(
                name=data.get('name'),
                type=data.get('type'),
                origin=data.get('origin'),
                orientation=data.get('orientation', {"x": 0, "y": 0, "z": 0}),
                parent=data.get('parent'),
                metadata=data.get('metadata')
            )
            self._save_frames()
            return {"success": True, "frame": frame.to_dict()}
        except Exception as e:
            return {"error": True, "message": str(e)}
    
    def handle_get_frame(self, data):
        """Get frame information."""
        frame_name = data.get('name')
        frame = self.frame_manager.get_frame(frame_name)
        
        if not frame:
            return {"error": True, "message": f"Frame {frame_name} not found"}
        
        result = frame.to_dict()
        
        # Include children details if requested
        if data.get('include_children'):
            result['children_details'] = [
                self.frame_manager.get_frame(child).to_dict()
                for child in frame.children
                if self.frame_manager.get_frame(child)
            ]
        
        # Include mating frames if requested
        if data.get('include_mates'):
            result['mating_frames'] = self.frame_manager.get_mating_frames(frame_name)
        
        return result
    
    def handle_list_frames(self, data):
        """List all frames."""
        filter_type = data.get('filter', {}).get('type')
        frames = self.frame_manager.list_frames(filter_type)
        
        return {
            "frames": [f.to_dict() for f in frames],
            "count": len(frames)
        }
    
    def handle_delete_frame(self, data):
        """Delete a frame."""
        frame_name = data.get('name')
        self.frame_manager.delete_frame(frame_name)
        self._save_frames()
        return {"success": True}
    
    def handle_transform_point(self, data):
        """Transform point between frames."""
        try:
            point = data.get('point')
            from_frame = data.get('from_frame')
            to_frame = data.get('to_frame')
            
            result = self.frame_manager.transform_point(point, from_frame, to_frame)
            
            return {
                "point": result,
                "from_frame": from_frame,
                "to_frame": to_frame
            }
        except Exception as e:
            return {"error": True, "message": str(e)}
    
    def handle_create_body_frame(self, data):
        """Automatically create frame for a body."""
        body_name = data.get('body_name')
        
        # Find the body
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        body = self._find_body_by_name(design, body_name)
        
        if not body:
            return {"error": True, "message": f"Body {body_name} not found"}
        
        try:
            frame = self.frame_manager.create_body_frame(body_name, body)
            self._save_frames()
            return {"success": True, "frame": frame.to_dict()}
        except Exception as e:
            return {"error": True, "message": str(e)}
    
    def handle_create_interface_frame(self, data):
        """Create interface frame for joints."""
        try:
            frame = self.frame_manager.create_interface_frame(
                parent_frame=data.get('parent_frame'),
                name=data.get('name'),
                edge_position=data.get('origin'),
                normal=data.get('normal'),
                mates_with=data.get('mates_with'),
                metadata=data.get('metadata')
            )
            self._save_frames()
            return {"success": True, "frame": frame.to_dict()}
        except Exception as e:
            return {"error": True, "message": str(e)}
```

### 2.2 HTTP Routes

```python
# fusion-addin/FusionMCPBridge.py (HTTP server section)

def run_http_server(bridge):
    """Run HTTP server with frame endpoints."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json
    
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            # ... existing routes ...
            
            # Frame management routes
            elif self.path == '/create_frame':
                response = bridge.handle_create_frame(data)
            elif self.path == '/get_frame':
                response = bridge.handle_get_frame(data)
            elif self.path == '/list_frames':
                response = bridge.handle_list_frames(data)
            elif self.path == '/delete_frame':
                response = bridge.handle_delete_frame(data)
            elif self.path == '/transform_point':
                response = bridge.handle_transform_point(data)
            elif self.path == '/create_body_frame':
                response = bridge.handle_create_body_frame(data)
            elif self.path == '/create_interface_frame':
                response = bridge.handle_create_interface_frame(data)
```

## Phase 3: MCP Server Frame Tools

### 3.1 Add Frame Tools to TypeScript Server

```typescript
// fusion-design-mcp-server/src/index.ts

// Add to TOOLS array:

// ============ Frame Management ============
{
  name: "fusion_create_frame",
  description: "Create a new reference frame for spatial organization.",
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
        description: "Euler angles in degrees"
      },
      parent: { type: "string", description: "Parent frame name" },
      metadata: { type: "object", description: "Custom metadata" }
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
  description: "Automatically create a frame for a body centered at its bounding box.",
  inputSchema: {
    type: "object" as const,
    properties: {
      body_name: { type: "string", description: "Name of the body" }
    },
    required: ["body_name"]
  }
},
{
  name: "fusion_create_interface_frame",
  description: "Create an interface frame for a joint between two bodies.",
  inputSchema: {
    type: "object" as const,
    properties: {
      parent_frame: { type: "string", description: "Parent body frame" },
      name: { type: "string", description: "Interface frame name" },
      origin: { type: "array", items: { type: "number" }, description: "[x, y, z] position" },
      normal: { type: "array", items: { type: "number" }, description: "[x, y, z] surface normal" },
      mates_with: { type: "string", description: "Name of mating interface frame" },
      metadata: { type: "object", description: "Joint metadata (type, pattern, etc.)" }
    },
    required: ["parent_frame", "name", "origin", "normal"]
  }
}

// Add to ENDPOINTS mapping:
const ENDPOINTS: Record<string, string> = {
  // ... existing endpoints ...
  fusion_create_frame: "/create_frame",
  fusion_get_frame: "/get_frame",
  fusion_list_frames: "/list_frames",
  fusion_delete_frame: "/delete_frame",
  fusion_transform_point: "/transform_point",
  fusion_create_body_frame: "/create_body_frame",
  fusion_create_interface_frame: "/create_interface_frame",
};
```

## Phase 4: Frame-Aware Geometry Operations

### 4.1 Modify Extrude to Support Frames

```python
# fusion-addin/FusionMCPBridge.py

def handle_extrude(self, data):
    """Extrude with optional frame support."""
    sketch_id = data.get('sketch_id')
    distance = data.get('distance')
    direction = data.get('direction', 'positive')
    operation = data.get('operation', 'new_body')
    
    # NEW: Frame-aware extrusion
    from_frame = data.get('from_frame')
    to_frame = data.get('to_frame')
    
    if to_frame:
        # Calculate direction and distance automatically
        from_f = self.frame_manager.get_frame(from_frame or sketch_id + "_Frame")
        to_f = self.frame_manager.get_frame(to_frame)
        
        if from_f and to_f:
            # Calculate vector from origin to origin
            vec = [
                to_f.origin[i] - from_f.origin[i]
                for i in range(3)
            ]
            distance = np.linalg.norm(vec)
            # Determine direction from vector
            # (implementation details...)
    
    # ... rest of existing extrude logic ...
```

## Phase 5: Testing & Validation

### 5.1 Test Suite

Create tests for:
- Frame creation and hierarchy
- Coordinate transformations
- Body frame auto-creation
- Interface frame mating
- Persistence (save/load)

### 5.2 Example Workflow Test

```python
# Test: Build simple box joint with frames

# 1. Create panels
create_panel("BasePanel", [0,0,0], [254, 400, 12.7])
create_panel("FrontPanel", [0, 0, 12.7], [254, 12.7, 88.9])

# 2. Auto-create body frames
fusion_create_body_frame("BasePanel")
fusion_create_body_frame("FrontPanel")

# 3. Create interface frames
fusion_create_interface_frame({
  parent_frame: "BasePanel_Frame",
  name: "BasePanel_FrontEdge_Frame",
  origin: [127, 0, 12.7],
  normal: [0, -1, 0],
  mates_with: "FrontPanel_BottomEdge_Frame",
  metadata: { joint_type: "box_joint", finger_width: 12.7 }
})

# 4. Verify frames exist
frames = fusion_list_frames({ filter: { type: "interface" }})
assert len(frames) >= 1

# 5. Use frame for sketch positioning
# (implementation continues...)
```

## Phase 6: Documentation Update

### 6.1 Update Pattern Files

Update existing patterns to use frame-based approach:
- `coordinate-systems.md` → Add frame explanation
- `box-joints.md` → Rewrite using frames
- `join-operations.md` → Add frame validation

### 6.2 Create Frame Tutorial

New file: `fusion-patterns/using-frames.md`
- What frames are
- When to create them
- How to use frame-aware tools
- Common patterns

## Timeline

- **Week 1:** Phase 1 - Frame data structures and manager
- **Week 2:** Phase 2 - Frame API endpoints
- **Week 3:** Phase 3 - MCP server frame tools
- **Week 4:** Phase 4 - Frame-aware geometry operations
- **Week 5:** Phase 5 - Testing and validation
- **Week 6:** Phase 6 - Documentation

## Success Criteria

1. ✅ Model can create and query frames
2. ✅ Body frames auto-created on extrude
3. ✅ Interface frames track joint relationships
4. ✅ Coordinate transformations work correctly
5. ✅ Frames persist across sessions
6. ✅ Box joints work reliably using frames
7. ✅ No more orphan body warnings
8. ✅ Documentation complete

