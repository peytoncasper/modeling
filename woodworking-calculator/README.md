# Woodworking Project Tools

A set of scripts for accurate material planning, cut optimization, and board feet calculation.

## Quick Start

```bash
cd tools
python woodwork_calculator.py
```

Or specify a custom config:
```bash
python woodwork_calculator.py my_project_config.json
```

## Configuration File Format

Create a JSON file with your project specs:

### `project_config.json`

```json
{
  "project_name": "My Project",
  "material_thickness_mm": 19,
  "kerf_mm": 3.2,
  "edge_joint_loss_mm": 3,
  "min_scrap_length_mm": 100,
  
  "parts": [...],
  "inventory": {...},
  "glue_up_config": {...}
}
```

### Parts Array

Each part you need to make:

```json
{
  "id": "unique_id",
  "name": "Human Readable Name",
  "width_mm": 460,
  "length_mm": 410,
  "quantity_needed": 1,
  "quantity_made": 0,
  "notes": "Optional notes"
}
```

### Inventory Object

#### Processed Boards (already dimensioned)

```json
"processed_boards": [
  {
    "id": "proc_1",
    "length_mm": 780,
    "width_mm": 150,
    "thickness_mm": 19,
    "notes": "Ready to use"
  }
]
```

#### Unprocessed Boards (rough lumber)

```json
"unprocessed_boards": [
  {
    "id": "raw_1",
    "length_mm": 2786,
    "width_mm": 185,
    "rough_thickness_mm": 25,
    "final_thickness_mm": 19,
    "end_trim_mm": 50,
    "edge_waste_mm": 10,
    "notes": "8ft rough white oak"
  }
]
```

### Glue-Up Configuration

For edge-glued panels:

```json
"glue_up_config": {
  "target_strip_width_mm": 150,
  "strips_per_panel": 3,
  "glue_line_loss_mm": 1,
  "panel_trim_margin_mm": 10
}
```

## Output

The calculator provides:

1. **Parts Status** - What's made vs. remaining
2. **Inventory** - All boards with dimensions and board feet
3. **Board Feet Analysis** - Total material consumption
4. **Strips Analysis** - How many strips needed for glue-ups
5. **Cut Plan** - Exactly what to cut from each board
6. **Glue-Up Plan** - Which strips go together for each panel

## Board Feet Calculation

The calculator uses industry-standard board feet formula:

```
BF = (Length" × Width" × Thickness") / 144
```

- For rough lumber: uses rough thickness
- For processed lumber: uses 1" nominal (4/4 stock)

## Tips

1. **Update as you go**: After making parts, update `quantity_made` in the config
2. **Account for waste**: The calculator factors in kerf and trim, but add extra for mistakes
3. **Verify dimensions**: Measure your actual boards before trusting the plan
4. **Save configs**: Keep a config file for each project

## Example Workflow

1. Create `project_config.json` with your project specs
2. Run `python woodwork_calculator.py`
3. Process unprocessed boards per the cut plan
4. Update inventory in config as boards are processed
5. Re-run to get updated glue-up assignments
6. Mark parts as made when complete




