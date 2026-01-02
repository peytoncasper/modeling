"""Frame management system for spatial reasoning in Fusion 360."""

import json
import math
from typing import Dict, List, Optional, Any


class Frame:
    """Represents a spatial reference frame."""
    
    def __init__(self, name: str, type: str, origin: List[float], 
                 orientation: Dict[str, float], parent: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.type = type
        self.origin = origin
        self.orientation = orientation
        self.parent = parent or "WorldFrame"
        self.children = []
        self.metadata = metadata or {}
    
    def to_dict(self):
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
        frame = cls(
            name=data["name"],
            type=data["type"],
            origin=data["origin"],
            orientation=data["orientation"],
            parent=data.get("parent"),
            metadata=data.get("metadata")
        )
        frame.children = data.get("children", [])
        return frame


class FrameManager:
    """Manages all reference frames."""
    
    def __init__(self):
        self.frames: Dict[str, Frame] = {}
        self._init_default_frames()
    
    def _init_default_frames(self):
        """Create world and construction plane frames."""
        self.frames["WorldFrame"] = Frame(
            name="WorldFrame",
            type="world",
            origin=[0, 0, 0],
            orientation={"x": 0, "y": 0, "z": 0},
            parent=None,
            metadata={"description": "Root world coordinate system"}
        )
        
        self.frames["XY_Frame"] = Frame(
            name="XY_Frame",
            type="plane",
            origin=[0, 0, 0],
            orientation={"x": 0, "y": 0, "z": 0},
            parent="WorldFrame",
            metadata={
                "plane": "xy",
                "normal": [0, 0, 1],
                "coordinate_mapping": {"sketch_x": "world_x", "sketch_y": "world_y"},
                "inversions": []
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
                "coordinate_mapping": {"sketch_x": "world_x", "sketch_y": "world_-z"},
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
                "coordinate_mapping": {"sketch_x": "world_-z", "sketch_y": "world_y"},
                "inversions": ["x_axis"]
            }
        )
    
    def create_frame(self, name: str, type: str, origin: List[float],
                     orientation: Dict[str, float], parent: Optional[str] = None,
                     metadata: Optional[Dict] = None) -> Frame:
        """Create a new frame."""
        if name in self.frames:
            raise ValueError(f"Frame {name} already exists")
        
        frame = Frame(name, type, origin, orientation, parent, metadata)
        self.frames[name] = frame
        
        if frame.parent and frame.parent in self.frames:
            self.frames[frame.parent].children.append(name)
        
        return frame
    
    def get_frame(self, name: str) -> Optional[Frame]:
        """Get frame by name."""
        return self.frames.get(name)
    
    def list_frames(self, filter_type: Optional[str] = None) -> List[Frame]:
        """List frames, optionally filtered by type."""
        frames = list(self.frames.values())
        if filter_type:
            frames = [f for f in frames if f.type == filter_type]
        return frames
    
    def delete_frame(self, name: str):
        """Delete frame and its children."""
        if name not in self.frames:
            return
        
        frame = self.frames[name]
        
        for child_name in frame.children[:]:
            self.delete_frame(child_name)
        
        if frame.parent and frame.parent in self.frames:
            parent = self.frames[frame.parent]
            if name in parent.children:
                parent.children.remove(name)
        
        del self.frames[name]
    
    def create_body_frame(self, body_name: str, bounds_min: List[float], 
                          bounds_max: List[float], volume: float = 0, component: str = None) -> Frame:
        """Create frame for a body at its center.
        
        Args:
            body_name: Name of the body
            bounds_min: Minimum bounds in mm [x, y, z]
            bounds_max: Maximum bounds in mm [x, y, z]
            volume: Volume in mm³
            component: Optional component name
        """
        origin = [
            (bounds_min[0] + bounds_max[0]) / 2,
            (bounds_min[1] + bounds_max[1]) / 2,
            (bounds_min[2] + bounds_max[2]) / 2
        ]
        
        # Include component name in frame name to avoid conflicts
        if component:
            frame_name = f"{component}_{body_name}_Frame"
        else:
            frame_name = f"{body_name}_Frame"
        
        metadata = {
            "body_name": body_name,
            "bounds_world": {"min": bounds_min, "max": bounds_max},
            "bounds_local": {
                "min": [bounds_min[i] - origin[i] for i in range(3)],
                "max": [bounds_max[i] - origin[i] for i in range(3)]
            },
            "volume": volume
        }
        if component:
            metadata["component"] = component
        
        return self.create_frame(
            name=frame_name,
            type="body",
            origin=origin,
            orientation={"x": 0, "y": 0, "z": 0},
            parent="WorldFrame",
            metadata=metadata
        )
    
    def create_interface_frame(self, parent_frame: str, name: str,
                               origin: List[float], normal: List[float],
                               mates_with: Optional[str] = None,
                               metadata: Optional[Dict] = None) -> Frame:
        """Create interface frame for connections/joints.
        
        Args:
            parent_frame: Parent frame name
            name: Interface frame name
            origin: Position in mm [x, y, z]
            normal: Normal vector [x, y, z]
            mates_with: Optional mating interface name
            metadata: Optional metadata dict
        """
        """Create interface frame for joints."""
        parent = self.frames.get(parent_frame)
        if not parent:
            raise ValueError(f"Parent frame {parent_frame} not found")
        
        meta = metadata or {}
        if mates_with:
            meta["mates_with"] = mates_with
        meta["normal"] = normal
        
        return self.create_frame(
            name=name,
            type="interface",
            origin=origin,
            orientation={"x": 0, "y": 0, "z": 0},
            parent=parent_frame,
            metadata=meta
        )
    
    def get_mating_frames(self, frame_name: str) -> List[str]:
        """Get frames that mate with given frame."""
        frame = self.frames.get(frame_name)
        if not frame:
            return []
        
        mates_with = frame.metadata.get("mates_with")
        mating = [mates_with] if mates_with else []
        
        for f in self.frames.values():
            if f.metadata.get("mates_with") == frame_name:
                mating.append(f.name)
        
        return mating
    
    def transform_point_between_frames(self, point: List[float],
                                       from_frame: str, to_frame: str) -> List[float]:
        """Transform point from one frame to another."""
        frame_from = self.frames.get(from_frame)
        frame_to = self.frames.get(to_frame)
        
        if not frame_from or not frame_to:
            raise ValueError(f"Frame not found")
        
        # Simple translation-only transform for now
        # TODO: Add rotation support
        dx = frame_to.origin[0] - frame_from.origin[0]
        dy = frame_to.origin[1] - frame_from.origin[1]
        dz = frame_to.origin[2] - frame_from.origin[2]
        
        return [
            point[0] - dx,
            point[1] - dy,
            point[2] - dz
        ]
    
    def save_to_dict(self) -> Dict:
        """Serialize all frames."""
        return {
            "frames": [f.to_dict() for f in self.frames.values()]
        }
    
    def load_from_dict(self, data: Dict):
        """Load frames from dict."""
        self.frames = {}
        for frame_data in data.get("frames", []):
            frame = Frame.from_dict(frame_data)
            self.frames[frame.name] = frame

