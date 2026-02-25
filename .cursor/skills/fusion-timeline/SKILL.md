---
name: fusion-timeline
description: Read, navigate, and modify the Fusion 360 parametric timeline. Use when the user asks to list features, roll back/forward, suppress/unsuppress features, delete features, reorder timeline items, edit feature parameters, check feature health, create timeline groups, or analyze feature dependencies.
---

# Fusion 360 Parametric Timeline

Full control of the Fusion 360 timeline via `tools/fusion-timeline`. The timeline is the parametric history — every sketch, feature, and operation is an ordered item. Rolling the marker back hides features; rolling forward reveals them.

## Quick reference

```bash
tools/fusion-timeline list                  # all items + marker position
tools/fusion-timeline marker                # where is the marker?
tools/fusion-timeline item Extrude1         # detail for one feature
tools/fusion-timeline health                # any broken features?
```

## Listing the timeline

```bash
# Full listing (all items with index, name, type, suppressed, health)
tools/fusion-timeline list

# Active features only (skip suppressed)
tools/fusion-timeline list --active

# Paginate (useful for large timelines)
tools/fusion-timeline list --start 10 --limit 20
```

### List output fields

| Field | Description |
|-------|-------------|
| `index` | Position in timeline (0-based) |
| `name` | Feature name (e.g. "Sketch1", "Extrude1") |
| `type` | Feature type (e.g. "ExtrudeFeature", "Sketch") |
| `suppressed` | Whether the feature is suppressed |
| `is_group` | Whether this is a timeline group |
| `health` | "healthy", "warning", "error", or "suppressed" |
| `marker` | Current marker position |
| `count` | Total timeline items |

## Inspecting a single item

Get rich details including parameters, affected bodies, and source sketch.

```bash
# By name
tools/fusion-timeline item Extrude1

# By index
tools/fusion-timeline item --index 3
```

### Item detail fields

Includes all list fields plus:
- `affected_bodies` — bodies created/modified by this feature
- `source_sketch` — sketch that was used as the profile source
- `parameters` — editable parameters with values and expressions
- `related_parameters` — model parameters that reference this feature

## Searching the timeline

```bash
# Find features by name
tools/fusion-timeline search --query extrude

# Find by type
tools/fusion-timeline search --type Sketch

# Combine name + type filter
tools/fusion-timeline search --query base --type Extrude
```

## Feature parameters

```bash
# Get all parameters for a feature
tools/fusion-timeline params Extrude1
tools/fusion-timeline params --index 3
```

## Marker position

```bash
# Check where the marker is
tools/fusion-timeline marker
# Returns: marker position, at_end/at_beginning, last_feature, next_feature,
#          rolled_back_features count

# Quick count
tools/fusion-timeline count
# Returns: total, active, suppressed, marker
```

## Feature health

Check for warnings and errors across the entire timeline.

```bash
tools/fusion-timeline health
# Returns: healthy/warning/error/suppressed counts, plus a list of issues
```

## Navigating the timeline

### Roll to a specific feature

```bash
# Roll to just before a feature (feature is hidden)
tools/fusion-timeline roll Extrude1

# Roll to just after a feature (feature is visible)
tools/fusion-timeline roll Extrude1 --after

# Roll by index
tools/fusion-timeline roll --index 5
tools/fusion-timeline roll --index 5 --after
```

### Roll to start/end

```bash
# Show all features (marker at end)
tools/fusion-timeline roll-end

# Hide all features (marker at beginning)
tools/fusion-timeline roll-beginning
```

### Rolling strategy

When you need to understand what the model looked like at a certain point:

```bash
# Roll back to before a feature
tools/fusion-timeline roll SketchPocket --after
# Now the model shows everything up to and including SketchPocket

# Take a screenshot at this state
tools/fusion-camera screenshot --view isometric

# Roll back to the end
tools/fusion-timeline roll-end
```

## Modifying the timeline

### Suppress / unsuppress

Suppressing a feature temporarily disables it without deleting it.

```bash
# Suppress one feature
tools/fusion-timeline suppress Fillet1

# Suppress multiple by name
tools/fusion-timeline suppress --names Fillet1,Chamfer1,Fillet2

# Suppress by index
tools/fusion-timeline suppress --index 7

# Suppress multiple by index
tools/fusion-timeline suppress --indices 5,7,9

# Unsuppress (same arguments)
tools/fusion-timeline unsuppress Fillet1
tools/fusion-timeline unsuppress --names Fillet1,Chamfer1
```

### Delete

Permanently remove a feature. The feature's entity is deleted, which may cascade to dependent features.

```bash
tools/fusion-timeline delete Fillet1
tools/fusion-timeline delete --index 7
```

### Reorder

Move a feature to a different position in the timeline.

```bash
# Move a feature to the beginning
tools/fusion-timeline move Fillet1 --to 0

# Move to a specific position
tools/fusion-timeline move Fillet1 --to 5

# By index
tools/fusion-timeline move --index 7 --to 3
```

### Edit parameters

Change a feature's parameter value or expression.

```bash
# Set by expression (recommended — supports units and parameter references)
tools/fusion-timeline edit-param Extrude1 --param distance --expr "20 mm"
tools/fusion-timeline edit-param Extrude1 --param distance --expr "width / 2"

# Set by raw value (mm for lengths)
tools/fusion-timeline edit-param Extrude1 --param distance --value 25

# By index
tools/fusion-timeline edit-param --index 3 --param distance --expr "15 mm"
```

### Rename

```bash
tools/fusion-timeline rename Extrude1 --new-name BaseExtrude
tools/fusion-timeline rename --index 3 --new-name TopChamfer
```

### Undo / redo

```bash
# Delete the last unsuppressed feature
tools/fusion-timeline undo

# Unsuppress the last suppressed feature
tools/fusion-timeline redo
```

## Timeline groups

Organize related features into collapsible groups.

```bash
# Create a group from items 0 through 3
tools/fusion-timeline group --start 0 --end 3

# Collapse a group (hide its children in the timeline)
tools/fusion-timeline collapse GroupName

# Expand a group
tools/fusion-timeline expand GroupName
```

## Dependency analysis

Find what features feed into or depend on a given feature.

```bash
tools/fusion-timeline deps Extrude1
tools/fusion-timeline deps --index 3
```

### Dependency output

```json
{
  "feature": "Extrude1",
  "index": 2,
  "upstream": [
    {"index": 0, "name": "Sketch1", "relation": "source_sketch"}
  ],
  "downstream": [
    {"index": 4, "name": "Fillet1", "shared_bodies": ["Body1"]},
    {"index": 5, "name": "Chamfer1", "shared_bodies": ["Body1"]}
  ],
  "affected_bodies": ["Body1"],
  "source_sketch": "Sketch1"
}
```

## Complete command reference

### Query

| Command | What it does |
|---------|-------------|
| `list [--active] [--start N] [--limit N]` | List all timeline items |
| `item NAME [--index N]` | Detail for a single item |
| `marker` | Current marker position + context |
| `count` | Quick total/active/suppressed count |
| `search [--query Q] [--type T]` | Search by name/type substring |
| `health` | Feature health report (warnings, errors) |
| `params NAME [--index N]` | Parameters for a feature |

### Navigate

| Command | What it does |
|---------|-------------|
| `roll NAME [--index N] [--after]` | Roll marker to feature |
| `roll-end` | Roll marker to end (all visible) |
| `roll-beginning` | Roll marker to beginning (all hidden) |

### Modify

| Command | What it does |
|---------|-------------|
| `suppress NAME [--names A,B] [--indices 1,2]` | Suppress feature(s) |
| `unsuppress NAME [--names A,B] [--indices 1,2]` | Unsuppress feature(s) |
| `delete NAME [--index N]` | Delete a feature permanently |
| `move NAME [--index N] --to T` | Reorder to position T |
| `edit-param NAME [--index N] --param P [--expr E] [--value V]` | Edit parameter |
| `rename NAME [--index N] --new-name NEW` | Rename a feature |
| `undo` | Delete last unsuppressed feature |
| `redo` | Unsuppress last suppressed feature |

### Groups

| Command | What it does |
|---------|-------------|
| `group --start S --end E` | Create group from index range |
| `collapse NAME [--index N]` | Collapse a group |
| `expand NAME [--index N]` | Expand a group |

### Analysis

| Command | What it does |
|---------|-------------|
| `deps NAME [--index N]` | Upstream/downstream dependencies |

## Common patterns

### "What features make up this model?"

```bash
tools/fusion-timeline list
```

### "Something is broken"

```bash
tools/fusion-timeline health
# If issues found, inspect them:
tools/fusion-timeline item BrokenFeature
tools/fusion-timeline deps BrokenFeature
```

### "Try the model without these fillets"

```bash
tools/fusion-timeline suppress --names Fillet1,Fillet2,Fillet3
# Check the result...
tools/fusion-camera screenshot --view isometric
# Restore them
tools/fusion-timeline unsuppress --names Fillet1,Fillet2,Fillet3
```

### "Change the base extrude height"

```bash
tools/fusion-timeline params Extrude1
# See that "distance" is currently "10 mm"
tools/fusion-timeline edit-param Extrude1 --param distance --expr "18 mm"
```

### "Organize the timeline"

```bash
# Group the base sketch + extrude together
tools/fusion-timeline group --start 0 --end 1
# Group all the edge treatments
tools/fusion-timeline group --start 5 --end 9
tools/fusion-timeline collapse Group2
```

### "What depends on this sketch?"

```bash
tools/fusion-timeline deps Sketch1
# Shows all features downstream that use Sketch1 as their source
```

### "Step through the build history"

```bash
tools/fusion-timeline roll-beginning
tools/fusion-timeline roll --index 0 --after
tools/fusion-camera screenshot --view isometric
tools/fusion-timeline roll --index 1 --after
tools/fusion-camera screenshot --view isometric
# ... continue stepping through
tools/fusion-timeline roll-end
```
