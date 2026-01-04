"""
Stage 4: Joint Reinforcement - Corner Blocks
============================================
Triangular hardwood braces that reinforce miter joints.
"""

import sys
sys.path.insert(0, '../stage-1-foundation')
from parameters import (
    OVERALL_WIDTH, OVERALL_HEIGHT, CARCASS_THICKNESS, BACK_THICKNESS
)

# =============================================================================
# CORNER BLOCK DIMENSIONS
# =============================================================================
BLOCK_LEG = 50           # Triangle leg length (both legs equal)
BLOCK_LENGTH = 80        # Extrusion length along Y axis
BLOCK_RABBET = 6         # Optional alignment rabbet depth

# Y positions (distance from front of cabinet)
Y_FRONT = 60             # Front block position
Y_REAR = 400 - BACK_THICKNESS - 60  # 334mm - Rear block position

# =============================================================================
# CORNER BLOCK GEOMETRY
# =============================================================================
"""
Corner blocks are right-angle triangular prisms that sit in the
interior corners of the cabinet.

Cross-section (looking along Y axis):

    TOP PANEL
    ─────────────────────
         ╲
          ╲  CORNER
           ╲  BLOCK     
            ╲ (50×50)
             ╲
    ─────────┘
    SIDE PANEL

The hypotenuse faces the interior of the cabinet.
"""

# Calculate corner positions
HALF_W = OVERALL_WIDTH / 2  # 225
T = CARCASS_THICKNESS       # 19

# =============================================================================
# ALL 8 CORNER BLOCK POSITIONS
# =============================================================================

CORNER_BLOCKS = {
    # TOP-LEFT corner (2 blocks)
    "TL_front": {
        "corner": "top-left",
        "triangle_vertices_xz": [
            (HALF_W - T, OVERALL_HEIGHT - T),           # (206, 560) - inner corner
            (HALF_W - T, OVERALL_HEIGHT - T - BLOCK_LEG),  # (206, 510)
            (HALF_W - T - BLOCK_LEG, OVERALL_HEIGHT - T),  # (156, 560)
        ],
        "y_center": Y_FRONT,
        "y_range": (Y_FRONT - BLOCK_LENGTH/2, Y_FRONT + BLOCK_LENGTH/2),  # (20, 100)
    },
    "TL_rear": {
        "corner": "top-left",
        "triangle_vertices_xz": [
            (HALF_W - T, OVERALL_HEIGHT - T),
            (HALF_W - T, OVERALL_HEIGHT - T - BLOCK_LEG),
            (HALF_W - T - BLOCK_LEG, OVERALL_HEIGHT - T),
        ],
        "y_center": Y_REAR,
        "y_range": (Y_REAR - BLOCK_LENGTH/2, Y_REAR + BLOCK_LENGTH/2),  # (294, 374)
    },
    
    # TOP-RIGHT corner (2 blocks)
    "TR_front": {
        "corner": "top-right",
        "triangle_vertices_xz": [
            (-HALF_W + T, OVERALL_HEIGHT - T),          # (-206, 560)
            (-HALF_W + T, OVERALL_HEIGHT - T - BLOCK_LEG),
            (-HALF_W + T + BLOCK_LEG, OVERALL_HEIGHT - T),
        ],
        "y_center": Y_FRONT,
        "y_range": (Y_FRONT - BLOCK_LENGTH/2, Y_FRONT + BLOCK_LENGTH/2),
    },
    "TR_rear": {
        "corner": "top-right",
        "triangle_vertices_xz": [
            (-HALF_W + T, OVERALL_HEIGHT - T),
            (-HALF_W + T, OVERALL_HEIGHT - T - BLOCK_LEG),
            (-HALF_W + T + BLOCK_LEG, OVERALL_HEIGHT - T),
        ],
        "y_center": Y_REAR,
        "y_range": (Y_REAR - BLOCK_LENGTH/2, Y_REAR + BLOCK_LENGTH/2),
    },
    
    # BOTTOM-LEFT corner (2 blocks)
    "BL_front": {
        "corner": "bottom-left",
        "triangle_vertices_xz": [
            (HALF_W - T, T),                            # (206, 19) - inner corner
            (HALF_W - T, T + BLOCK_LEG),                # (206, 69)
            (HALF_W - T - BLOCK_LEG, T),                # (156, 19)
        ],
        "y_center": Y_FRONT,
        "y_range": (Y_FRONT - BLOCK_LENGTH/2, Y_FRONT + BLOCK_LENGTH/2),
    },
    "BL_rear": {
        "corner": "bottom-left",
        "triangle_vertices_xz": [
            (HALF_W - T, T),
            (HALF_W - T, T + BLOCK_LEG),
            (HALF_W - T - BLOCK_LEG, T),
        ],
        "y_center": Y_REAR,
        "y_range": (Y_REAR - BLOCK_LENGTH/2, Y_REAR + BLOCK_LENGTH/2),
    },
    
    # BOTTOM-RIGHT corner (2 blocks)
    "BR_front": {
        "corner": "bottom-right",
        "triangle_vertices_xz": [
            (-HALF_W + T, T),                           # (-206, 19)
            (-HALF_W + T, T + BLOCK_LEG),
            (-HALF_W + T + BLOCK_LEG, T),
        ],
        "y_center": Y_FRONT,
        "y_range": (Y_FRONT - BLOCK_LENGTH/2, Y_FRONT + BLOCK_LENGTH/2),
    },
    "BR_rear": {
        "corner": "bottom-right",
        "triangle_vertices_xz": [
            (-HALF_W + T, T),
            (-HALF_W + T, T + BLOCK_LEG),
            (-HALF_W + T + BLOCK_LEG, T),
        ],
        "y_center": Y_REAR,
        "y_range": (Y_REAR - BLOCK_LENGTH/2, Y_REAR + BLOCK_LENGTH/2),
    },
}


def print_corner_block_instructions():
    """Print corner block build instructions."""
    print("=" * 60)
    print("STAGE 4: CORNER BLOCKS (8 total)")
    print("=" * 60)
    print(f"\nBlock dimensions: {BLOCK_LEG}×{BLOCK_LEG}×{BLOCK_LENGTH}mm triangular prism")
    print(f"Y positions: {Y_FRONT}mm (front), {Y_REAR}mm (rear)")
    
    for name, block in CORNER_BLOCKS.items():
        print(f"\n{name} ({block['corner']}):")
        print(f"  Triangle XZ: {block['triangle_vertices_xz']}")
        print(f"  Y range: {block['y_range'][0]} to {block['y_range'][1]}")
    
    print("\n" + "=" * 60)
    print("FUSION BUILD SEQUENCE")
    print("=" * 60)
    print("""
Option 1: Build one, pattern the rest
1. Create sketch on XZ plane at Y = 20 (front of first block)
2. Draw triangle: (206, 560), (206, 510), (156, 560)
3. Extrude 80mm in +Y direction
4. Use rectangular pattern to create others

Option 2: Build all 8 individually
- Create each block using triangle sketch + extrude
- Position using Y coordinates from table above

MATERIAL: Apply hardwood appearance (Oak, Maple, etc.)
""")


if __name__ == "__main__":
    print_corner_block_instructions()









