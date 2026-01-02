# Using Frames for Cross-Body Operations

## The Problem with Cross-Body Operations

When working with multiple bodies (panels, components, etc.), the model struggles to:

1. **Track relationships** - Which body connects to which?
2. **Position features correctly** - Where exactly should a joint be placed?
3. **Validate before execution** - Will this JOIN actually work?
4. **Maintain context** - What operations have been done already?

## The Frame Solution

Frames provide **explicit spatial relationships** between bodies, making cross-body operations predictable and verifiable.

## Example: Box Joint Between Two Panels

### Without Frames (Error-Prone)

```
1. Model: "I need to join BasePanel and FrontPanel"
2. Model: get_body_center("BasePanel")
   → {min: [0,0,0], max: [254,400,12.7]}
3. Model: get_body_center("FrontPanel") 
   → {min: [0,0,12.7], max: [254,12.7,88.9]}
4. Model: "FrontPanel bottom is at Z=12.7, BasePanel top is at Z=12.7"
5. Model: "I'll create a sketch at Z=0 and extrude up to Z=12.7"
6. Model: create_sketch(plane="xz", ...)
7. Model: draw_rectangle(corner1=[0,0], corner2=[12.7, 12.7])
8. Model: extrude(distance=12.7, direction="positive", operation="join")
9. Result: ❌ ORPHAN BODY - sketch Y coordinate was inverted!
```

**Problems:**
- Manual coordinate calculation every time
- Easy to forget XZ plane Y-inversion
- No validation before execution
- Lost context if model needs to retry

### With Frames (Reliable)

```
1. Model: "I need to join BasePanel and FrontPanel"

2. Model: fusion_create_body_frame("BasePanel")
   → Creates "BasePanel_Frame" at center of body

3. Model: fusion_create_body_frame("FrontPanel")
   → Creates "FrontPanel_Frame" at center of body

4. Model: fusion_create_interface_frame({
     parent_frame: "BasePanel_Frame",
     name: "BasePanel_FrontEdge_Interface",
     edge: "front",  // Automatically calculates position
     mates_with: "FrontPanel_BottomEdge_Interface",
     metadata: { joint_type: "box_joint", finger_width: 12.7 }
   })

5. Model: fusion_create_interface_frame({
     parent_frame: "FrontPanel_Frame",
     name: "FrontPanel_BottomEdge_Interface",
     edge: "bottom",
     mates_with: "BasePanel_FrontEdge_Interface",
     metadata: { joint_type: "box_joint", finger_width: 12.7 }
   })

6. Model: fusion_validate_interface_mating({
     frame_a: "BasePanel_FrontEdge_Interface",
     frame_b: "FrontPanel_BottomEdge_Interface"
   })
   → {valid: true, contact_line: [[0,0,12.7], [254,0,12.7]], gap: 0}

7. Model: fusion_create_sketch_in_frame({
     frame: "FrontPanel_BottomEdge_Interface",
     name: "FrontFingers"
   })
   → Sketch automatically positioned correctly

8. Model: fusion_draw_box_joint_pattern_in_frame({
     sketch: "FrontFingers",
     frame: "FrontPanel_BottomEdge_Interface",
     finger_width: 12.7,
     count: 10,
     pattern: "fingers"
   })
   → Automatically handles coordinate system

9. Model: fusion_extrude_between_frames({
     sketch: "FrontFingers",
     from_frame: "FrontPanel_BottomEdge_Interface",
     to_frame: "BasePanel_FrontEdge_Interface",
     operation: "join",
     target_body: "FrontPanel"
   })
   → Automatically calculates direction and distance
   → ✅ SUCCESS - fingers joined to FrontPanel
```

**Benefits:**
- Spatial relationships explicitly defined
- Validation before execution
- Automatic coordinate conversions
- Persistent context for retry/modification

## Frame Types for Cross-Body Operations

### 1. Body Frames (Tracking Individual Bodies)

Each body gets a frame at its center:

```json
{
  "name": "FrontPanel_Frame",
  "type": "body",
  "origin": [127, 6.35, 50.8],  // Body center
  "bounds_local": {
    "min": [-127, -6.35, -44.45],
    "max": [127, 6.35, 44.45]
  },
  "children": [
    "FrontPanel_BottomEdge_Interface",
    "FrontPanel_LeftEdge_Interface",
    "FrontPanel_RightEdge_Interface"
  ]
}
```

### 2. Interface Frames (Defining Connections)

Each connection point between bodies gets an interface frame:

```json
{
  "name": "FrontPanel_BottomEdge_Interface",
  "type": "interface",
  "parent": "FrontPanel_Frame",
  "origin": [127, 0, 12.7],  // World coords of interface
  "normal": [0, -1, 0],       // Points toward BasePanel
  "mates_with": "BasePanel_FrontEdge_Interface",
  "metadata": {
    "joint_type": "box_joint",
    "status": "fingers_added",
    "finger_positions": [0, 25.4, 50.8, ...],
    "finger_width": 12.7
  }
}
```

### 3. Feature Frames (Grouping Related Geometry)

Complex features get their own frames:

```json
{
  "name": "FrontBottomJoint_Feature",
  "type": "feature",
  "parent": "FrontPanel_BottomEdge_Interface",
  "metadata": {
    "components": {
      "slots": ["slot_0", "slot_2", "slot_4"],
      "fingers": ["finger_0", "finger_2", "finger_4"]
    },
    "assembly_status": "complete"
  }
}
```

## Cross-Body Operation Patterns

### Pattern 1: Joint Validation Before Execution

```javascript
// Check if two interface frames will mate correctly
function validateJoint(frameA, frameB) {
  const result = fusion_validate_interface_mating({
    frame_a: frameA,
    frame_b: frameB
  });
  
  if (!result.valid) {
    console.error(`Joint validation failed: ${result.reason}`);
    console.log(`Gap: ${result.gap}mm`);
    console.log(`Suggestion: ${result.suggestion}`);
    return false;
  }
  
  return true;
}

// Use before creating joint geometry
if (validateJoint("FrontPanel_BottomEdge_Interface", "BasePanel_FrontEdge_Interface")) {
  // Proceed with joint creation
}
```

### Pattern 2: Symmetric Joint Creation

For joints like box joints, create both sides symmetrically:

```javascript
function createBoxJoint(frameA, frameB, fingerWidth) {
  // Validate first
  if (!validateJoint(frameA, frameB)) {
    throw new Error("Frames don't mate");
  }
  
  // Create slots in frame A
  fusion_create_box_joint_slots({
    interface_frame: frameA,
    finger_width: fingerWidth,
    pattern: "slots"
  });
  
  // Create fingers in frame B
  fusion_create_box_joint_fingers({
    interface_frame: frameB,
    mating_frame: frameA,
    finger_width: fingerWidth,
    pattern: "fingers"
  });
}
```

### Pattern 3: Assembly Status Tracking

Track which joints are complete:

```javascript
function getIncompleteJoints() {
  const interfaces = fusion_list_frames({
    filter: { type: "interface" }
  });
  
  return interfaces.frames.filter(f => 
    f.metadata.status !== "complete"
  );
}

function markJointComplete(frameA, frameB) {
  // Update both frames
  fusion_update_frame_metadata({
    frame: frameA,
    metadata: { status: "complete" }
  });
  
  fusion_update_frame_metadata({
    frame: frameB,
    metadata: { status: "complete" }
  });
}
```

### Pattern 4: Automatic Direction Calculation

Let frames determine extrusion direction:

```javascript
function extrudeBetweenBodies(sketchFrame, targetFrame, operation) {
  // Frame system calculates:
  // - Direction vector from sketchFrame to targetFrame
  // - Distance between frames
  // - Whether they will intersect
  
  return fusion_extrude_between_frames({
    sketch: sketchFrame.metadata.sketch_id,
    from_frame: sketchFrame.name,
    to_frame: targetFrame.name,
    operation: operation,
    target_body: targetFrame.parent  // Automatically get parent body
  });
}
```

## Complex Example: Four-Panel Corner

When multiple bodies meet at a corner:

```
TopPanel
   │
   ├── TopPanel_LeftEdge_Interface ──→ LeftPanel_TopEdge_Interface
   │
   ├── TopPanel_FrontEdge_Interface ──→ FrontPanel_TopEdge_Interface
   │
   └── TopPanel_FrontLeft_Corner_Feature
          │
          ├── Miter joint with Front
          ├── Miter joint with Left
          └── Corner block attachment point
```

Frames make this explicit:

```javascript
// Query: "What needs to be built at this corner?"
const corner = fusion_get_frame("TopPanel_FrontLeft_Corner_Feature");

const relatedFrames = [
  fusion_get_frame(corner.metadata.miter_front),
  fusion_get_frame(corner.metadata.miter_left),
  fusion_get_frame(corner.metadata.block_attachment)
];

// Check status of each
relatedFrames.forEach(frame => {
  console.log(`${frame.name}: ${frame.metadata.status}`);
});

// Build missing features
relatedFrames
  .filter(f => f.metadata.status === "pending")
  .forEach(frame => buildFeature(frame));
```

## Integration with Existing Patterns

### Coordinate Systems Pattern

Frames **augment** the coordinate system pattern by:
- Automatically tracking which plane inversions apply
- Converting coordinates through frame transforms
- Providing verification tools

```javascript
// Old way: Manual calculation
const sketchY = -worldZ;  // Remember to invert!

// Frame way: Automatic
const sketchCoords = fusion_transform_point({
  point: [worldX, worldY, worldZ],
  from_frame: "WorldFrame",
  to_frame: "MySketch_Frame"
});
```

### Join Operations Pattern

Frames **enhance** join operations by:
- Pre-validating contact
- Tracking what's been joined
- Providing debug information

```javascript
// Old way: Hope it works
fusion_extrude({...operation: "join"...});
// Check afterward if orphan body created

// Frame way: Validate first
const valid = fusion_check_frame_intersection({...});
if (valid.will_intersect) {
  fusion_extrude({...operation: "join"...});
}
```

### Box Joints Pattern

Frames **simplify** box joints by:
- Defining interfaces explicitly
- Calculating positions automatically
- Tracking which joints are complete

```javascript
// Old way: Calculate each finger position
for (let i = 0; i < 10; i += 2) {
  const x = i * fingerWidth;
  fusion_draw_rectangle(...);
}

// Frame way: Pattern-based
fusion_create_box_joint_pattern({
  interface_frame: "FrontPanel_BottomEdge_Interface",
  finger_width: 12.7
});
```

## Summary: Why Frames Solve Cross-Body Problems

| Problem | Without Frames | With Frames |
|---------|----------------|-------------|
| **"Where do these bodies touch?"** | Call get_body_center repeatedly, calculate manually | Query interface frames, get contact line |
| **"Will this join work?"** | Try it and see | Validate with check_frame_intersection |
| **"What's the extrusion direction?"** | Manual calculation, easy to get wrong | Automatic from from_frame to to_frame |
| **"What joints are incomplete?"** | No tracking mechanism | Query frames by status metadata |
| **"How do I handle coordinate inversions?"** | Remember rules, apply manually | Automatic through transform_point |
| **"Can I retry after failure?"** | Lost context, start over | Frames persist, exact state known |

Frames provide the **persistent spatial context** that makes cross-body operations reliable and debuggable.

