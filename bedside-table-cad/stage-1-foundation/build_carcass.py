"""
Stage 1: Foundation - Build Carcass Panels
==========================================
Instructions for creating the 4 main panels in Fusion 360.

The panels are positioned so the cabinet is centered at origin (X=0, Y=0)
with the bottom at Z=0.
"""

from parameters import (
    OVERALL_WIDTH, OVERALL_DEPTH, OVERALL_HEIGHT, CARCASS_THICKNESS
)

# =============================================================================
# PANEL DEFINITIONS
# =============================================================================
# Each panel: sketch plane, rectangle corners, extrusion distance

PANELS = {
    "Bottom_Panel": {
        "description": "Horizontal panel at Z=0",
        "sketch_plane": "XY at Z=0",
        "corner1": (-OVERALL_WIDTH/2, -OVERALL_DEPTH/2),  # (-225, -200)
        "corner2": (OVERALL_WIDTH/2, OVERALL_DEPTH/2),    # (225, 200)
        "extrude": CARCASS_THICKNESS,                      # 19mm up
        "extrude_dir": "positive (up)",
    },
    
    "Top_Panel": {
        "description": "Horizontal panel at top",
        "sketch_plane": f"XY at Z={OVERALL_HEIGHT - CARCASS_THICKNESS}",  # Z=560
        "corner1": (-OVERALL_WIDTH/2, -OVERALL_DEPTH/2),
        "corner2": (OVERALL_WIDTH/2, OVERALL_DEPTH/2),
        "extrude": CARCASS_THICKNESS,
        "extrude_dir": "positive (up)",
    },
    
    "Left_Panel": {
        "description": "Vertical panel on +X side",
        "sketch_plane": "YZ at X=0 (then offset)",
        "corner1": (-OVERALL_DEPTH/2, 0),                  # Y, Z
        "corner2": (OVERALL_DEPTH/2, OVERALL_HEIGHT),
        "x_position": OVERALL_WIDTH/2 - CARCASS_THICKNESS, # X=206
        "extrude": CARCASS_THICKNESS,
        "extrude_dir": "positive (+X)",
    },
    
    "Right_Panel": {
        "description": "Vertical panel on -X side", 
        "sketch_plane": "YZ at X=0 (then offset)",
        "corner1": (-OVERALL_DEPTH/2, 0),
        "corner2": (OVERALL_DEPTH/2, OVERALL_HEIGHT),
        "x_position": -OVERALL_WIDTH/2,                    # X=-225
        "extrude": CARCASS_THICKNESS,
        "extrude_dir": "positive (+X)",
    },
}


# =============================================================================
# BUILD SEQUENCE (for Fusion MCP)
# =============================================================================
BUILD_SEQUENCE = """
FUSION 360 BUILD SEQUENCE
=========================

1. CREATE BOTTOM PANEL
   - Sketch on XY plane
   - Rectangle: corner1=(-225, -200), corner2=(225, 200)
   - Extrude: 19mm positive (up)
   - Rename body: "Bottom_Panel"

2. CREATE TOP PANEL  
   - Create offset plane: XY + 560mm
   - Sketch on offset plane
   - Rectangle: corner1=(-225, -200), corner2=(225, 200)
   - Extrude: 19mm positive (up)
   - Rename body: "Top_Panel"

3. CREATE LEFT PANEL (+X side)
   - Sketch on YZ plane
   - Rectangle: corner1=(-200, 0), corner2=(200, 579)
   - Extrude: 19mm toward +X, starting at X=206
   - Rename body: "Left_Panel"

4. CREATE RIGHT PANEL (-X side)
   - Sketch on YZ plane  
   - Rectangle: corner1=(-200, 0), corner2=(200, 579)
   - Extrude: 19mm toward +X, starting at X=-225
   - Rename body: "Right_Panel"

VERIFICATION
============
- Overall bounding box: 450 × 400 × 579mm
- Internal cavity: 412 × 400 × 541mm
- All panels overlap at corners (will be mitered in Stage 3)
"""


def print_build_instructions():
    """Print detailed build instructions."""
    print("=" * 60)
    print("STAGE 1: BUILD CARCASS PANELS")
    print("=" * 60)
    
    for name, panel in PANELS.items():
        print(f"\n{name}:")
        print(f"  {panel['description']}")
        print(f"  Sketch plane: {panel['sketch_plane']}")
        print(f"  Rectangle: {panel['corner1']} to {panel['corner2']}")
        print(f"  Extrude: {panel['extrude']}mm {panel['extrude_dir']}")
    
    print(BUILD_SEQUENCE)


if __name__ == "__main__":
    print_build_instructions()









