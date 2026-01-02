"""
Stage 5: Plinth & Finishing - Base Platform
===========================================
The plinth is an inset base that lifts the cabinet off the floor.
"""

import sys
sys.path.insert(0, '../stage-1-foundation')
from parameters import OVERALL_WIDTH, OVERALL_DEPTH

# =============================================================================
# PLINTH DIMENSIONS
# =============================================================================
PLINTH_HEIGHT = 40        # Height of plinth
PLINTH_INSET = 25         # How far inset from cabinet edges

PLINTH_WIDTH = OVERALL_WIDTH - (2 * PLINTH_INSET)   # 450 - 50 = 400mm
PLINTH_DEPTH = OVERALL_DEPTH - (2 * PLINTH_INSET)   # 400 - 50 = 350mm

# =============================================================================
# PLINTH POSITION
# =============================================================================
"""
The plinth sits centered under the cabinet, inset 25mm from all edges.
It extends from Z = -40 to Z = 0 (cabinet bottom is at Z = 0).

Top view:
    ┌─────────────────────────────┐
    │                             │  CABINET (450 × 400)
    │   ┌───────────────────┐     │
    │   │                   │     │  PLINTH (400 × 350)
    │   │                   │     │  25mm inset all around
    │   └───────────────────┘     │
    │                             │
    └─────────────────────────────┘
"""

PLINTH = {
    "name": "Plinth",
    "material": "19mm plywood (can be hollow frame)",
    
    "width": PLINTH_WIDTH,    # 400mm
    "depth": PLINTH_DEPTH,    # 350mm  
    "height": PLINTH_HEIGHT,  # 40mm
    
    "position": {
        "x": -PLINTH_WIDTH/2,   # -200
        "y": -PLINTH_DEPTH/2,   # -175
        "z": -PLINTH_HEIGHT,    # -40 (below cabinet bottom)
    },
    
    "build": """
    1. Create sketch on XY plane at Z = -40
    2. Rectangle from (-200, -175) to (200, 175)
    3. Extrude 40mm in +Z direction
    4. Rename body: "Plinth"
    
    Alternative (hollow frame for lighter weight):
    1. Draw outer rectangle: (-200, -175) to (200, 175)
    2. Draw inner rectangle: (-170, -145) to (170, 145) [30mm frame]
    3. Extrude the frame profile
    """
}


def print_plinth_instructions():
    """Print plinth build instructions."""
    print("=" * 60)
    print("STAGE 5: PLINTH")
    print("=" * 60)
    
    p = PLINTH
    print(f"\nDimensions: {p['width']} × {p['depth']} × {p['height']}mm")
    print(f"Position: X={p['position']['x']}, Y={p['position']['y']}, Z={p['position']['z']}")
    print(f"Inset from cabinet edges: {PLINTH_INSET}mm")
    print(p['build'])


if __name__ == "__main__":
    print_plinth_instructions()


