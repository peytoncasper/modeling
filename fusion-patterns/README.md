# Fusion 360 Pattern Library

A knowledge base for accomplishing complex CAD operations using primitive tools.

## ⚠️ IMPORTANT: Read Before Building

**Before attempting ANY complex operation (box joints, mortises, multi-panel assemblies):**

1. **Read the relevant pattern file** in this library
2. **Understand the concepts** - WHY things work, not just HOW
3. **Note the common pitfalls** - these are hard-won lessons from failures
4. **Apply primitive tools** as described in the patterns
5. **Follow verification steps** after each operation

## Why This Library Exists

Instead of specialized tools for each operation, this library teaches you to use **primitive tools** correctly. Benefits:

- **Transferable knowledge** - Works for any model, not just specific cases
- **Understanding over memorization** - Learn why operations work
- **Flexibility** - Adapt patterns to your specific needs
- **Debugging** - Know what went wrong and how to fix it

## How to Use This Library

### Before Starting a Complex Task

```
1. Identify what you're trying to accomplish (e.g., "box joints")
2. Read the corresponding pattern file (e.g., box-joints.md)
3. Read coordinate-systems.md if working on XZ or YZ planes
4. Read join-operations.md if using cut/join operations
5. Plan your approach based on the patterns
```

### During Implementation

```
1. Follow the step-by-step approach from the pattern
2. Use verification steps after each operation
3. Check for warnings in tool responses
4. If something fails, refer back to the pattern's "Common Mistakes" section
```

## 🎯 Frame System (Coming Soon)

The **reference frame system** will provide persistent spatial context for CAD operations, making cross-body operations reliable and predictable.

**Key Benefits:**
- Automatic coordinate conversions (no more XZ/YZ confusion)
- Pre-validation of operations (no more orphan bodies)
- Explicit tracking of body relationships
- Reduced cognitive load

📖 **See:** `frames-for-cross-body-operations.md` for details

## Pattern Index

| Pattern | File | When to Read |
|---------|------|--------------|
| **Coordinate Systems** | `coordinate-systems.md` | ⚠️ ALWAYS read first for XZ/YZ planes |
| **Join Operations** | `join-operations.md` | Before any cut/join extrusion |
| **Frame-Based Operations** | `frames-for-cross-body-operations.md` | 🚀 Next-gen approach using frames |
| **Lidded Box** | `lidded-box.md` | ✨ Classic keepsake box with overhanging lid |
| **Panel Construction** | `panel-construction.md` | Building boxes from flat panels |
| **Box Joints** | `box-joints.md` | Finger/box joints (high-strength applications) |
| **Mortises** | `mortises.md` | Recessed pockets for hardware |
| **Corner Splines** | `corner-splines.md` | Structural corner braces with dados and screw holes |

### Reading Order for Box Projects

1. `coordinate-systems.md` - Understand the coordinate inversions
2. `panel-construction.md` - How to position panels correctly  
3. `join-operations.md` - How cut/join actually work
4. `corner-splines.md` - Structural corner reinforcement and alignment
5. `box-joints.md` - The box joint process
6. `mortises.md` - Adding hardware pockets

## Primitive Tools Available

These are the basic building blocks:

**Sketching:**
- `fusion_create_sketch` - Start a sketch on a plane
- `fusion_draw_rectangle` - Draw rectangle in sketch coordinates
- `fusion_draw_rectangle_3d` - Draw rectangle using world coordinates (auto-converts)
- `fusion_draw_line`, `fusion_draw_circle`, `fusion_draw_arc`
- `fusion_finish_sketch` - Complete and validate sketch

**3D Operations:**
- `fusion_extrude` - Extrude profile (new_body, join, cut, intersect)
- `fusion_create_box` - Quick box primitive
- `fusion_boolean` - Combine bodies

**Query:**
- `fusion_get_body_center` - Get body bounds and position
- `fusion_get_model_summary` - Overview of entire model
- `fusion_list_bodies` - All bodies with details

**Planes:**
- `fusion_create_offset_plane` - Create construction plane at offset

