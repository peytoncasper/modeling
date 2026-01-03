# Frame System Summary

## What We're Building

A **reference frame system** for the Fusion 360 MCP that gives AI models persistent spatial context, making CAD operations predictable and reliable.

## The Core Insight

CAD operations are fundamentally about **relationships between coordinate systems**:
- World frame → Body frame → Interface frame → Sketch frame
- Operations fail when the model loses track of which frame it's operating in
- Explicit frame tracking solves this by making spatial relationships first-class entities

## Key Components

### 1. Frame Types

- **World Frame** - Root coordinate system
- **Body Frames** - One per physical body, centered at bounding box
- **Interface Frames** - Define connection points between bodies
- **Sketch Frames** - Handle 2D↔3D coordinate conversions
- **Feature Frames** - Group related geometry (joints, mortises, etc.)

### 2. Frame Operations

- **Create/Query** - Manage frame hierarchy
- **Transform** - Convert coordinates between frames
- **Validate** - Check if operations will succeed before executing
- **Track** - Maintain state (what's built, what's pending)

### 3. Integration Points

- **Automatic Creation** - Body frames created on extrude
- **Frame-Aware Tools** - Existing tools gain optional frame parameters
- **High-Level Operations** - New tools that work primarily with frames
- **Persistence** - Frames saved to JSON alongside Fusion document

## Problems Solved

### Before Frames

```
❌ Model loses spatial context between tool calls
❌ Coordinate system inversions cause errors
❌ No way to validate before execution → orphan bodies
❌ No tracking of cross-body relationships
❌ Manual calculation of positions/directions
```

### After Frames

```
✅ Persistent spatial context
✅ Automatic coordinate conversions
✅ Pre-validation of operations
✅ Explicit relationship tracking
✅ Automatic calculation from frame relationships
```

## Architecture Overview

```
Model
  ↓ "Create box joint between FrontPanel and BasePanel"
  
MCP Tools (TypeScript)
  ↓ fusion_create_interface_frame(...)
  
Python Bridge
  ↓ FrameManager.create_interface_frame(...)
  
Frame Database (JSON)
  ↓ Persists frames
  
Fusion API
  ↓ Actual geometry operations use frame data
```

## Example Workflow

### Building a Box Joint

**Old Way (40 lines, error-prone):**
```
1. get_body_center("BasePanel")
2. get_body_center("FrontPanel")
3. Calculate edge positions manually
4. Remember XZ plane Y-inversion
5. create_sketch at calculated position
6. Draw slots at calculated positions
7. Hope extrude direction is correct
8. Check if orphan body created
9. Debug and retry if failed
```

**Frame Way (10 lines, reliable):**
```
1. create_body_frame("BasePanel")
2. create_body_frame("FrontPanel")
3. create_interface_frame("BasePanel_FrontEdge", mates_with="FrontPanel_BottomEdge")
4. create_interface_frame("FrontPanel_BottomEdge", mates_with="BasePanel_FrontEdge")
5. validate_mating_frames() → ✅ valid
6. create_box_joint_slots(interface="BasePanel_FrontEdge")
7. create_box_joint_fingers(interface="FrontPanel_BottomEdge")
8. → Success, no debugging needed
```

## Alignment with Existing Methodology

The frame system **extends** your existing patterns, not replaces them:

| Existing Pattern | Frame Enhancement |
|-----------------|-------------------|
| **coordinate-systems.md** | Frames handle inversions automatically |
| **join-operations.md** | Frames validate contact before execution |
| **box-joints.md** | Interface frames track joint relationships |
| **panel-construction.md** | Body frames organize panels hierarchically |

## Implementation Phases

### Phase 1: Foundation (Week 1)
- Python `Frame` class and `FrameManager`
- Frame persistence (JSON save/load)
- Basic coordinate transformations

### Phase 2: API (Week 2)
- HTTP endpoints for frame operations
- Integration with existing bridge

### Phase 3: MCP Tools (Week 3)
- TypeScript tool definitions
- Frame management tools
- Frame query tools

### Phase 4: Frame-Aware Operations (Week 4)
- Add frame parameters to existing tools
- Create high-level frame operations
- Validation tools

### Phase 5: Testing (Week 5)
- Unit tests for transformations
- Integration tests with Fusion
- Real-world project test (bedside table)

### Phase 6: Documentation (Week 6)
- Update pattern files
- Create frame tutorial
- API documentation

## Success Metrics

1. **Zero orphan bodies** - Frame validation prevents join failures
2. **No coordinate errors** - Automatic transformations handle inversions
3. **Faster development** - Model completes box joint in 1/3 the tool calls
4. **Better debugging** - Frame state shows exactly what's wrong
5. **Maintainable context** - Model can pick up where it left off

## File Structure

```
fusion-design-mcp-server/
├── FRAME_SYSTEM_DESIGN.md          ← Comprehensive design doc
├── FRAME_IMPLEMENTATION_PLAN.md    ← Step-by-step implementation
├── FRAME_SYSTEM_SUMMARY.md         ← This file
└── src/
    └── index.ts                     ← MCP tools (will add frame tools)

fusion-addin/
├── FusionMCPBridge.py              ← Will integrate FrameManager
├── frame_manager.py                ← NEW: Frame classes and logic
└── frames/                          ← NEW: Saved frames per document

fusion-patterns/
├── README.md                        ← Will update with frame references
├── coordinate-systems.md            ← Will add frame examples
├── join-operations.md               ← Will add frame validation
├── box-joints.md                    ← Will add frame-based approach
└── frames-for-cross-body-operations.md  ← NEW: Frame usage guide
```

## Quick Start (After Implementation)

### For Users

```javascript
// 1. Create bodies as normal
fusion_extrude({..., body_name: "MyPanel"});

// 2. System auto-creates "MyPanel_Frame"

// 3. Query frames
const frame = fusion_get_frame({
  name: "MyPanel_Frame",
  include_children: true
});

// 4. Use frames for operations
fusion_create_interface_frame({
  parent_frame: "MyPanel_Frame",
  name: "MyPanel_Edge_Interface",
  edge: "front",
  mates_with: "OtherPanel_Edge_Interface"
});

// 5. Validate before building
const valid = fusion_validate_mating_frames({
  frame_a: "MyPanel_Edge_Interface",
  frame_b: "OtherPanel_Edge_Interface"
});

if (valid.will_mate) {
  // Build joint with confidence
}
```

### For Developers

```python
# 1. Create FrameManager instance
from frame_manager import FrameManager

fm = FrameManager(app)

# 2. Create frames
frame = fm.create_frame(
    name="TestFrame",
    type="body",
    origin=[0, 0, 0],
    orientation={"x": 0, "y": 0, "z": 0}
)

# 3. Transform coordinates
point_world = [10, 20, 30]
point_local = fm.transform_point(
    point_world,
    from_frame="WorldFrame",
    to_frame="TestFrame"
)

# 4. Persist
fm.save_to_file("frames.json")
```

## Next Actions

### Immediate (This Week)
1. ✅ Design complete (these docs)
2. ⏳ Review and validate approach
3. ⏳ Decide on implementation timeline

### Short Term (Next 2 Weeks)
1. Implement Phase 1 (Python frame manager)
2. Add basic frame tools to MCP
3. Test with simple box joint

### Medium Term (Next Month)
1. Complete all implementation phases
2. Update pattern documentation
3. Test with bedside table project

### Long Term (Next Quarter)
1. Expand to advanced features (miters, mortises)
2. Add CAM frame support
3. Create pattern library using frames

## Questions & Decisions Needed

### Design Decisions
- [ ] Should frames auto-save on every operation, or explicit save?
- [ ] How to handle frame naming conventions?
- [ ] Should interface frames be created automatically when bodies are positioned adjacent?

### Technical Decisions
- [ ] Store frames in separate JSON or embedded in F3D file?
- [ ] Use Euler angles or quaternions for orientation?
- [ ] Support non-orthogonal coordinate frames?

### UX Decisions
- [ ] Visualize frames in Fusion viewport?
- [ ] Provide frame inspector UI?
- [ ] Suggest frame creation when operations fail?

## Conclusion

The frame system provides the **missing spatial context layer** that transforms the MCP from a collection of geometric primitives into an intelligent spatial reasoning system.

Instead of:
> "Draw a rectangle here, extrude it there, hope it touches that other body"

We get:
> "These two frames mate at this interface. Build geometry that connects them."

This is the difference between **coordinate manipulation** and **spatial reasoning**.

---

**Status:** Design complete, ready for implementation
**Next Step:** Review with team, begin Phase 1 implementation
**Timeline:** 6 weeks to full implementation
**Impact:** Eliminates majority of spatial reasoning errors







