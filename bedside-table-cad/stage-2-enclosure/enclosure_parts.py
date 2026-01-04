"""
Stage 2: Enclosure - Back Panel & False Floor
==============================================
Parts that close in the cabinet.
"""

import sys
sys.path.insert(0, '../stage-1-foundation')
from parameters import (
    OVERALL_WIDTH, OVERALL_DEPTH, OVERALL_HEIGHT,
    CARCASS_THICKNESS, BACK_THICKNESS, FALSE_FLOOR_THICKNESS
)

# Rabbet/dado dimensions
RABBET_DEPTH = 9
DADO_DEPTH = 6
FALSE_FLOOR_Z = 344

# =============================================================================
# BACK PANEL
# =============================================================================
"""
The back panel sits in the rabbets cut into all 4 carcass panels.
It's slightly smaller than the opening to allow easy insertion.
"""

BACK_PANEL = {
    "name": "Back_Panel",
    "material": "6mm plywood",
    
    # Dimensions
    "width": OVERALL_WIDTH - (2 * CARCASS_THICKNESS) + (2 * RABBET_DEPTH),  # 412 + 18 = 430mm
    "height": OVERALL_HEIGHT - (2 * CARCASS_THICKNESS) + (2 * RABBET_DEPTH), # 541 + 18 = 559mm  
    "thickness": BACK_THICKNESS,  # 6mm
    
    # Position (back face flush with cabinet back)
    "position": {
        "x": -(OVERALL_WIDTH/2 - CARCASS_THICKNESS + RABBET_DEPTH),  # -215
        "y": OVERALL_DEPTH/2 - BACK_THICKNESS,  # 194
        "z": CARCASS_THICKNESS - RABBET_DEPTH,   # 10
    },
    
    # Build instruction
    "build": """
    1. Create sketch on XZ plane at Y = 194
    2. Rectangle from (-215, 10) to (215, 569)
    3. Extrude 6mm in +Y direction
    4. Rename body: "Back_Panel"
    """
}

# =============================================================================
# FALSE FLOOR
# =============================================================================
"""
The false floor divides the cabinet into two drawer sections.
It sits in dados cut into the side panels.
The front edge is set back from the cabinet front.
"""

FALSE_FLOOR = {
    "name": "False_Floor",
    "material": "12mm plywood",
    
    # Dimensions (extends into dados on each side)
    "width": OVERALL_WIDTH - (2 * CARCASS_THICKNESS) + (2 * DADO_DEPTH),  # 412 + 12 = 424mm
    "depth": OVERALL_DEPTH - BACK_THICKNESS - 25 - (-OVERALL_DEPTH/2),    # ~369mm (stopped dado)
    "thickness": FALSE_FLOOR_THICKNESS,  # 12mm
    
    # Position
    "position": {
        "x": -(OVERALL_WIDTH/2 - CARCASS_THICKNESS + DADO_DEPTH),  # -212
        "y": -OVERALL_DEPTH/2,  # -200 (front edge at cabinet front)
        "z": FALSE_FLOOR_Z,      # 344
    },
    
    # Build instruction  
    "build": """
    1. Create sketch on XY plane at Z = 344
    2. Rectangle from (-212, -200) to (212, 169)
       Note: Y=169 is where dado stops (200 - 6 - 25 = 169)
    3. Extrude 12mm in +Z direction
    4. Rename body: "False_Floor"
    """
}

# =============================================================================
# VERIFICATION
# =============================================================================

def verify_fit():
    """Verify parts fit correctly."""
    print("=" * 60)
    print("STAGE 2: ENCLOSURE PARTS")
    print("=" * 60)
    
    print("\n--- BACK PANEL ---")
    bp = BACK_PANEL
    print(f"  Size: {bp['width']:.0f} × {bp['height']:.0f} × {bp['thickness']}mm")
    print(f"  Position: X={bp['position']['x']}, Y={bp['position']['y']}, Z={bp['position']['z']}")
    print(bp['build'])
    
    print("\n--- FALSE FLOOR ---")
    ff = FALSE_FLOOR
    print(f"  Size: {ff['width']:.0f} × {ff['depth']:.0f} × {ff['thickness']}mm")
    print(f"  Position: X={ff['position']['x']}, Y={ff['position']['y']}, Z={ff['position']['z']}")
    print(ff['build'])
    
    print("\n--- VERIFICATION CHECKS ---")
    
    # Back panel should fit in rabbets
    rabbet_opening_w = OVERALL_WIDTH - 2*CARCASS_THICKNESS + 2*RABBET_DEPTH
    rabbet_opening_h = OVERALL_HEIGHT - 2*CARCASS_THICKNESS + 2*RABBET_DEPTH
    print(f"  Back panel width ({bp['width']:.0f}) fits in rabbet opening ({rabbet_opening_w:.0f})? "
          f"{'✓' if bp['width'] <= rabbet_opening_w else '✗'}")
    print(f"  Back panel height ({bp['height']:.0f}) fits in rabbet opening ({rabbet_opening_h:.0f})? "
          f"{'✓' if bp['height'] <= rabbet_opening_h else '✗'}")
    
    # False floor should fit in dados
    dado_opening = OVERALL_WIDTH - 2*CARCASS_THICKNESS + 2*DADO_DEPTH
    print(f"  False floor width ({ff['width']:.0f}) fits in dado opening ({dado_opening:.0f})? "
          f"{'✓' if ff['width'] <= dado_opening else '✗'}")


if __name__ == "__main__":
    verify_fit()









