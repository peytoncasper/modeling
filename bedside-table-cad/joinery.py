"""
Bedside Table - Joinery Specification
=====================================
Simple, clean specification for carcass assembly.
"""

from parameters import (
    OVERALL_WIDTH, OVERALL_DEPTH, OVERALL_HEIGHT,
    CARCASS_THICKNESS, BACK_THICKNESS,
    SPLINE_THICKNESS, SPLINE_SLOT_DEPTH, SPLINE_SPACING, SPLINE_EDGE_INSET,
    CORNER_BLOCK_LEG, CORNER_BLOCK_LENGTH, CORNER_BLOCK_FRONT_Y, CORNER_BLOCK_REAR_Y,
    DADO_DEPTH, RABBET_DEPTH, RABBET_WIDTH,
    FALSE_FLOOR_Z, FALSE_FLOOR_THICKNESS
)


# =============================================================================
# CARCASS JOINERY SUMMARY
# =============================================================================
"""
MITER JOINTS (4 corners):
- 45° miters where side panels meet top/bottom
- Creates clean, modern look with no visible end grain

SPLINES (4 per corner = 16 total):
- 4mm plywood strips hidden inside miter faces
- Provides alignment during glue-up
- 3-4 splines per joint at 100mm spacing

CORNER BLOCKS (2 per corner = 8 total):
- 50mm × 50mm × 80mm triangular hardwood braces
- Sit in interior corner with alignment rabbets
- Screwed into both panels for mechanical strength
- Positions: 60mm and 334mm from front edge

BACK PANEL:
- Sits in 9mm deep × 6mm wide rabbets
- Cut into back edge of all four carcass panels

FALSE FLOOR:
- Sits in 6mm deep stopped dados in side panels
- Dados stop 25mm from front (blind/invisible)
"""


def get_spline_positions():
    """Calculate spline positions along the miter joint."""
    joint_length = OVERALL_DEPTH - RABBET_WIDTH  # ~394mm
    positions = []
    y = SPLINE_EDGE_INSET
    while y <= joint_length - SPLINE_EDGE_INSET:
        positions.append(y)
        y += SPLINE_SPACING
    return positions


def get_corner_block_positions():
    """Return Y positions for corner blocks."""
    return [CORNER_BLOCK_FRONT_Y, CORNER_BLOCK_REAR_Y]


# =============================================================================
# JOINERY DIMENSIONS
# =============================================================================

JOINERY = {
    "miter": {
        "angle": 45,
        "length": OVERALL_DEPTH,
        "locations": [
            "Left Panel ↔ Top Panel",
            "Left Panel ↔ Bottom Panel", 
            "Right Panel ↔ Top Panel",
            "Right Panel ↔ Bottom Panel",
        ]
    },
    
    "splines": {
        "thickness": SPLINE_THICKNESS,
        "slot_depth": SPLINE_SLOT_DEPTH,
        "positions": get_spline_positions(),
        "per_joint": len(get_spline_positions()),
        "total": len(get_spline_positions()) * 4,
    },
    
    "corner_blocks": {
        "leg": CORNER_BLOCK_LEG,
        "length": CORNER_BLOCK_LENGTH,
        "positions": get_corner_block_positions(),
        "per_corner": 2,
        "total": 8,
    },
    
    "rabbets": {
        "depth": RABBET_DEPTH,
        "width": RABBET_WIDTH,
        "for": "back panel",
    },
    
    "dados": {
        "depth": DADO_DEPTH,
        "width": FALSE_FLOOR_THICKNESS,
        "z_position": FALSE_FLOOR_Z,
        "for": "false floor",
    },
}


def print_joinery_summary():
    """Print a clean summary of all joinery."""
    print("=" * 50)
    print("BEDSIDE TABLE - JOINERY SUMMARY")
    print("=" * 50)
    
    print("\nMITER JOINTS (45°):")
    for loc in JOINERY["miter"]["locations"]:
        print(f"  • {loc}")
    
    print(f"\nSPLINES ({JOINERY['splines']['total']} total):")
    print(f"  • {JOINERY['splines']['thickness']}mm thick × {JOINERY['splines']['slot_depth']}mm slot depth")
    print(f"  • {JOINERY['splines']['per_joint']} per joint at Y = {JOINERY['splines']['positions']}")
    
    print(f"\nCORNER BLOCKS ({JOINERY['corner_blocks']['total']} total):")
    print(f"  • {JOINERY['corner_blocks']['leg']}mm legs × {JOINERY['corner_blocks']['length']}mm long")
    print(f"  • 2 per corner at Y = {JOINERY['corner_blocks']['positions']}")
    
    print(f"\nRABBETS (for back panel):")
    print(f"  • {JOINERY['rabbets']['depth']}mm deep × {JOINERY['rabbets']['width']}mm wide")
    
    print(f"\nDADOS (for false floor):")
    print(f"  • {JOINERY['dados']['depth']}mm deep at Z = {JOINERY['dados']['z_position']}")


if __name__ == "__main__":
    print_joinery_summary()
