"""
Stage 2: Enclosure - Rabbets and Dados
======================================
Cut locations for back panel rabbets and false floor dados.
"""

# Import from stage 1
import sys
sys.path.insert(0, '../stage-1-foundation')
from parameters import (
    OVERALL_WIDTH, OVERALL_DEPTH, OVERALL_HEIGHT,
    CARCASS_THICKNESS, BACK_THICKNESS, FALSE_FLOOR_THICKNESS
)

# =============================================================================
# RABBET DIMENSIONS (for back panel)
# =============================================================================
RABBET_DEPTH = 9          # How deep into panel
RABBET_WIDTH = BACK_THICKNESS  # 6mm - matches back panel thickness

# =============================================================================
# DADO DIMENSIONS (for false floor)
# =============================================================================
DADO_DEPTH = 6            # How deep into side panels
DADO_WIDTH = FALSE_FLOOR_THICKNESS  # 12mm - matches false floor
FALSE_FLOOR_Z = 344       # Z position of false floor top surface

# =============================================================================
# RABBET CUT LOCATIONS
# =============================================================================
"""
Rabbets are cut along the BACK EDGE of all 4 carcass panels.
They create a step for the back panel to sit in.

Cross-section view (looking from above):
                    
    ┌────────────────────────┐
    │                        │
    │   INTERIOR             │
    │                    ┌───┤ ← 9mm deep rabbet
    │                    │   │ ← 6mm wide
    └────────────────────┴───┘
                         ↑
                    Back edge
"""

RABBET_CUTS = {
    "Bottom_Panel": {
        "edge": "back (Y = +200)",
        "cut_box": {
            "x_start": -OVERALL_WIDTH/2 + CARCASS_THICKNESS,  # -206
            "x_end": OVERALL_WIDTH/2 - CARCASS_THICKNESS,     # 206
            "y_start": OVERALL_DEPTH/2 - RABBET_WIDTH,        # 194
            "y_end": OVERALL_DEPTH/2,                          # 200
            "z_start": CARCASS_THICKNESS - RABBET_DEPTH,      # 10
            "z_end": CARCASS_THICKNESS,                        # 19
        }
    },
    "Top_Panel": {
        "edge": "back (Y = +200)",
        "cut_box": {
            "x_start": -OVERALL_WIDTH/2 + CARCASS_THICKNESS,
            "x_end": OVERALL_WIDTH/2 - CARCASS_THICKNESS,
            "y_start": OVERALL_DEPTH/2 - RABBET_WIDTH,
            "y_end": OVERALL_DEPTH/2,
            "z_start": OVERALL_HEIGHT - CARCASS_THICKNESS,     # 560
            "z_end": OVERALL_HEIGHT - CARCASS_THICKNESS + RABBET_DEPTH,  # 569
        }
    },
    "Left_Panel": {
        "edge": "back (Y = +200)",
        "cut_box": {
            "x_start": OVERALL_WIDTH/2 - CARCASS_THICKNESS,    # 206
            "x_end": OVERALL_WIDTH/2 - CARCASS_THICKNESS + RABBET_DEPTH,  # 215
            "y_start": OVERALL_DEPTH/2 - RABBET_WIDTH,
            "y_end": OVERALL_DEPTH/2,
            "z_start": CARCASS_THICKNESS,                      # 19
            "z_end": OVERALL_HEIGHT - CARCASS_THICKNESS,       # 560
        }
    },
    "Right_Panel": {
        "edge": "back (Y = +200)",
        "cut_box": {
            "x_start": -OVERALL_WIDTH/2,                       # -225
            "x_end": -OVERALL_WIDTH/2 + RABBET_DEPTH,          # -216
            "y_start": OVERALL_DEPTH/2 - RABBET_WIDTH,
            "y_end": OVERALL_DEPTH/2,
            "z_start": CARCASS_THICKNESS,
            "z_end": OVERALL_HEIGHT - CARCASS_THICKNESS,
        }
    },
}

# =============================================================================
# DADO CUT LOCATIONS (side panels only)
# =============================================================================
"""
Dados are horizontal grooves in the LEFT and RIGHT panels
for the false floor to sit in.

Cross-section view (looking from front):

    │ LEFT │                          │RIGHT │
    │PANEL │                          │PANEL │
    │      │                          │      │
    │  ════╪══════════════════════════╪════  │ ← False floor in dados
    │      │                          │      │
    │      │                          │      │
"""

DADO_CUTS = {
    "Left_Panel": {
        "description": "Horizontal groove for false floor",
        "cut_box": {
            "x_start": OVERALL_WIDTH/2 - CARCASS_THICKNESS,    # 206 (inner face)
            "x_end": OVERALL_WIDTH/2 - CARCASS_THICKNESS + DADO_DEPTH,  # 212
            "y_start": -OVERALL_DEPTH/2,                       # -200
            "y_end": OVERALL_DEPTH/2 - BACK_THICKNESS - 25,    # Stop before back, leave 25mm
            "z_start": FALSE_FLOOR_Z,                          # 344
            "z_end": FALSE_FLOOR_Z + DADO_WIDTH,               # 356
        }
    },
    "Right_Panel": {
        "description": "Horizontal groove for false floor",
        "cut_box": {
            "x_start": -OVERALL_WIDTH/2 + CARCASS_THICKNESS - DADO_DEPTH,  # -218
            "x_end": -OVERALL_WIDTH/2 + CARCASS_THICKNESS,     # -212
            "y_start": -OVERALL_DEPTH/2,
            "y_end": OVERALL_DEPTH/2 - BACK_THICKNESS - 25,
            "z_start": FALSE_FLOOR_Z,
            "z_end": FALSE_FLOOR_Z + DADO_WIDTH,
        }
    },
}


def print_cut_instructions():
    """Print cutting instructions."""
    print("=" * 60)
    print("STAGE 2: RABBET AND DADO CUTS")
    print("=" * 60)
    
    print("\n--- RABBETS (for back panel) ---")
    print(f"Dimensions: {RABBET_DEPTH}mm deep × {RABBET_WIDTH}mm wide\n")
    
    for panel, data in RABBET_CUTS.items():
        box = data['cut_box']
        print(f"{panel}:")
        print(f"  Create box: X({box['x_start']}, {box['x_end']}), "
              f"Y({box['y_start']}, {box['y_end']}), Z({box['z_start']}, {box['z_end']})")
        print(f"  Boolean subtract from {panel}")
    
    print("\n--- DADOS (for false floor) ---")
    print(f"Dimensions: {DADO_DEPTH}mm deep × {DADO_WIDTH}mm wide at Z={FALSE_FLOOR_Z}\n")
    
    for panel, data in DADO_CUTS.items():
        box = data['cut_box']
        print(f"{panel}:")
        print(f"  Create box: X({box['x_start']}, {box['x_end']}), "
              f"Y({box['y_start']}, {box['y_end']}), Z({box['z_start']}, {box['z_end']})")
        print(f"  Boolean subtract from {panel}")


if __name__ == "__main__":
    print_cut_instructions()









