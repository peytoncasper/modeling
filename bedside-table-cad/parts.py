"""
Bedside Table - Part Definitions
================================
Simple part list with dimensions from Fusion model.
"""

from parameters import (
    OVERALL_WIDTH, OVERALL_DEPTH, OVERALL_HEIGHT,
    CARCASS_THICKNESS, BACK_THICKNESS, FALSE_FLOOR_THICKNESS,
    FALSE_FLOOR_Z, FALSE_FLOOR_WIDTH, FALSE_FLOOR_DEPTH,
    PLINTH_WIDTH, PLINTH_DEPTH, PLINTH_HEIGHT
)


# =============================================================================
# CARCASS PARTS
# =============================================================================

CARCASS_PARTS = {
    "Bottom Panel": {
        "width": OVERALL_WIDTH,
        "depth": OVERALL_DEPTH,
        "height": CARCASS_THICKNESS,
        "position": {"x": -225, "y": -200, "z": 0},
    },
    "Top Panel": {
        "width": OVERALL_WIDTH,
        "depth": OVERALL_DEPTH,
        "height": CARCASS_THICKNESS,
        "position": {"x": -225, "y": -200, "z": OVERALL_HEIGHT - CARCASS_THICKNESS},
    },
    "Left Panel": {
        "width": CARCASS_THICKNESS,
        "depth": OVERALL_DEPTH,
        "height": OVERALL_HEIGHT,
        "position": {"x": OVERALL_WIDTH/2 - CARCASS_THICKNESS, "y": -200, "z": 0},
    },
    "Right Panel": {
        "width": CARCASS_THICKNESS,
        "depth": OVERALL_DEPTH,
        "height": OVERALL_HEIGHT,
        "position": {"x": -OVERALL_WIDTH/2, "y": -200, "z": 0},
    },
    "Back Panel": {
        "width": 432,
        "depth": BACK_THICKNESS,
        "height": 561,
        "position": {"x": -216, "y": -200, "z": 9},
    },
    "False Floor": {
        "width": FALSE_FLOOR_WIDTH,
        "depth": FALSE_FLOOR_DEPTH,
        "height": FALSE_FLOOR_THICKNESS,
        "position": {"x": -212, "y": -166, "z": FALSE_FLOOR_Z},
    },
}


# =============================================================================
# PLINTH
# =============================================================================

PLINTH_PARTS = {
    "Plinth": {
        "width": PLINTH_WIDTH,
        "depth": PLINTH_DEPTH,
        "height": PLINTH_HEIGHT,
        "position": {"x": -PLINTH_WIDTH/2, "y": -PLINTH_DEPTH/2, "z": -PLINTH_HEIGHT},
    },
}


def print_parts_list():
    """Print all parts with dimensions."""
    print("=" * 50)
    print("BEDSIDE TABLE - PARTS LIST")
    print("=" * 50)
    
    print("\nCARCASS:")
    for name, part in CARCASS_PARTS.items():
        print(f"  {name}: {part['width']} × {part['depth']} × {part['height']}mm")
    
    print("\nPLINTH:")
    for name, part in PLINTH_PARTS.items():
        print(f"  {name}: {part['width']} × {part['depth']} × {part['height']}mm")


if __name__ == "__main__":
    print_parts_list()
