---
name: fusion-assembly
description: Manage Fusion 360 assembly structure — components, hierarchy, body organization, visibility, occurrence transforms, and joints. Use when the user asks to create components, organize bodies into components, move/copy/rename components or bodies, show/hide parts, position component instances, create joints between components, or query the assembly tree.
---

# Fusion 360 Assembly / Component / Organization

Control Fusion 360's assembly structure via `tools/fusion-assembly`. All dimensions are mm. Output is JSON.

## Orient yourself first

Before organizing, understand the current assembly:

```bash
tools/fusion-assembly context                   # full assembly snapshot: components, positions, joints
tools/fusion-assembly list                      # component tree with body/sketch counts
tools/fusion-assembly info --component Carcass  # detailed info for one component
tools/fusion-assembly bodies --component Carcass  # all bodies in a component (deep)
```

## Component lifecycle

### Create components

Create components to organize your design into logical groups (subassemblies, individual parts, etc.):

```bash
# Create a top-level component
tools/fusion-assembly create --name Carcass

# Create a nested component (child of Carcass)
tools/fusion-assembly create --name Shelf --parent Carcass

# Typical furniture hierarchy:
tools/fusion-assembly create --name Frame
tools/fusion-assembly create --name Legs --parent Frame
tools/fusion-assembly create --name Aprons --parent Frame
tools/fusion-assembly create --name Top
```

### Rename, duplicate, delete

```bash
# Rename a component
tools/fusion-assembly rename --component Component1 --new-name Carcass

# Duplicate a component (creates a linked copy — same definition)
tools/fusion-assembly duplicate --component Leg --new-name Leg_Copy

# Delete a component (removes the occurrence and all contents)
tools/fusion-assembly delete --component TempComponent
```

## Body organization

After creating bodies (via fusion-solid or fusion-sketch + extrude), move them into the right components:

```bash
# Rename bodies for clarity
tools/fusion-assembly rename-body --body Body1 --new-name TopPanel
tools/fusion-assembly rename-body --body Body2 --new-name SidePanel

# Move a body from root into a component
tools/fusion-assembly move-body --body TopPanel --to Carcass

# Move from a specific source component
tools/fusion-assembly move-body --body Shelf1 --to Shelves --source Carcass

# Copy a body into another component (keeps original)
tools/fusion-assembly copy-body --body TopPanel --to Reference --name TopPanel_Ref
```

### Typical workflow: build then organize

```bash
# 1. Build all bodies in root (simpler coordinate system)
tools/fusion-solid box --c1 0,0,0 --c2 600,400,19 --name TopPanel
tools/fusion-solid box --c1 0,0,-500 --c2 19,400,0 --name LeftSide
tools/fusion-solid box --c1 581,0,-500 --c2 600,400,0 --name RightSide

# 2. Create component structure
tools/fusion-assembly create --name Carcass

# 3. Move bodies into components
tools/fusion-assembly move-body --body TopPanel --to Carcass
tools/fusion-assembly move-body --body LeftSide --to Carcass
tools/fusion-assembly move-body --body RightSide --to Carcass
```

## Visibility control

Toggle visibility of components and individual bodies:

```bash
# Hide/show entire components (hides all bodies + children)
tools/fusion-assembly hide --component Hardware
tools/fusion-assembly show --component Hardware

# Hide/show individual bodies
tools/fusion-assembly hide-body --body ConstructionHelper
tools/fusion-assembly show-body --body TopPanel
tools/fusion-assembly show-body --body Shelf1 --component Carcass
```

## Occurrence transforms

Move component instances (occurrences) in the assembly:

```bash
# Translate a component
tools/fusion-assembly move --component Leg --translate 100,0,0

# Rotate a component
tools/fusion-assembly move --component Door --rotate-axis 0,0,1 --rotate-angle 90

# Rotate around a specific point
tools/fusion-assembly move --component Door --rotate-axis 0,0,1 --rotate-angle 90 --rotate-origin 0,400,0

# Ground a component (lock it in place)
tools/fusion-assembly ground --component Base

# Unground (allow movement)
tools/fusion-assembly unground --component Leg
```

## Joints

Define how components relate to each other mechanically:

### As-built joints (simplest — preserves current positions)

```bash
# Rigid joint: components stay exactly where they are
tools/fusion-assembly as-built-joint --comp1 Base --comp2 Leg --type rigid

# Revolute joint: allows rotation (hinge)
tools/fusion-assembly as-built-joint --comp1 Frame --comp2 Door --type revolute --name DoorHinge

# Slider joint: allows linear motion
tools/fusion-assembly as-built-joint --comp1 Frame --comp2 Drawer --type slider
```

### Geometry-based joints (more control)

```bash
# Joint at component origins
tools/fusion-assembly joint \
  --geo1-type origin --geo1-component Base \
  --geo2-type origin --geo2-component Leg \
  --type rigid

# Joint at specific points
tools/fusion-assembly joint \
  --geo1-type point --geo1-component Frame --geo1-point 0,0,0 \
  --geo2-type point --geo2-component Leg --geo2-point 50,0,0 \
  --type revolute --name HingeJoint
```

### Query and manage joints

```bash
# List all joints
tools/fusion-assembly joints

# Delete a joint
tools/fusion-assembly delete-joint --name Joint1
```

## Assembly query

```bash
# Full assembly context (all components + positions + joints)
tools/fusion-assembly context

# Get a component's transform (position + rotation matrix)
tools/fusion-assembly transform --component Leg

# List all bodies in a component (including children)
tools/fusion-assembly bodies --component Carcass

# Exclude child component bodies
tools/fusion-assembly bodies --component Carcass --no-children
```

## Joint types reference

| Type | Degrees of freedom | Use case |
|------|-------------------|----------|
| rigid | 0 | Fixed connections, glue joints |
| revolute | 1 rotation | Hinges, pivots, doors |
| slider | 1 translation | Drawer slides, linear motion |
| cylindrical | 1 rotation + 1 translation | Pistons, telescoping |
| pin_slot | 1 rotation + 1 translation (diff. axes) | Cam followers |
| planar | 2 translation + 1 rotation | Flat sliding surfaces |
| ball | 3 rotation | Ball joints, universal joints |

## Common patterns

### Furniture with removable components

```bash
# Create component per part
tools/fusion-assembly create --name Top
tools/fusion-assembly create --name Legs
tools/fusion-assembly create --name Aprons

# Build bodies and move into components
tools/fusion-solid box --c1 0,0,0 --c2 800,400,25 --name TopSlab
tools/fusion-assembly move-body --body TopSlab --to Top

# Create as-built joints (parts stay in position)
tools/fusion-assembly as-built-joint --comp1 Top --comp2 Legs --type rigid
tools/fusion-assembly as-built-joint --comp1 Legs --comp2 Aprons --type rigid
```

### Symmetric parts (duplicate + mirror)

```bash
# Build one leg
tools/fusion-assembly create --name FrontLeftLeg
tools/fusion-solid box --c1 0,0,0 --c2 38,38,700 --name Leg
tools/fusion-assembly move-body --body Leg --to FrontLeftLeg

# Duplicate for other legs
tools/fusion-assembly duplicate --component FrontLeftLeg --new-name FrontRightLeg
tools/fusion-assembly move --component FrontRightLeg --translate 762,0,0
```

### Hide construction helpers

```bash
# Hide temporary geometry used during construction
tools/fusion-assembly hide-body --body _temp_construction
tools/fusion-assembly hide --component ConstructionHelpers
```

## Decision guide

| I want to... | Command |
|--------------|---------|
| See the full assembly | `context` |
| Create a new part group | `create --name X` |
| Put a body in a component | `move-body --body B --to C` |
| Give a body a better name | `rename-body --body B --new-name N` |
| Hide clutter | `hide --component C` or `hide-body --body B` |
| Lock a part in place | `ground --component C` |
| Connect parts with a hinge | `as-built-joint --comp1 A --comp2 B --type revolute` |
| Fix parts together | `as-built-joint --comp1 A --comp2 B --type rigid` |
| Position a component | `move --component C --translate x,y,z` |
| Make a copy of a part | `duplicate --component C` |
