"""
Stage 3: Miter Joints - 45° Corner Cuts
=======================================
Cut triangular sections to create clean miter joints at all 4 corners.
"""

import sys
sys.path.insert(0, '../stage-1-foundation')
from parameters import OVERALL_WIDTH, OVERALL_HEIGHT, CARCASS_THICKNESS

# =============================================================================
# MITER GEOMETRY EXPLANATION
# =============================================================================
"""
Each corner has two overlapping panels. We cut a triangular prism from each
to create a 45° miter joint.

BEFORE (top-left corner, viewed from front):
    ┌───────────────────────┬───┐
    │      TOP PANEL        │   │
    │                       │ L │
    ├───────────────────────┤ E │
    │                       │ F │
    │                       │ T │
                            
AFTER (miter cut):
    ┌───────────────────────╲───┐
    │      TOP PANEL         ╲  │
    │                         ╲ │ LEFT
    │                          ╲│
    │                           │
    │                           │

The miter line is the diagonal where the 45° cuts meet.
"""

# =============================================================================
# CORNER DEFINITIONS
# =============================================================================
# X and Z coordinates of each corner's overlap region

HALF_W = OVERALL_WIDTH / 2    # 225
T = CARCASS_THICKNESS         # 19

CORNERS = {
    "top_left": {
        "description": "Top panel meets left panel (+X, +Z corner)",
        "x_range": (HALF_W - T, HALF_W),          # (206, 225)
        "z_range": (OVERALL_HEIGHT - T, OVERALL_HEIGHT),  # (560, 579)
        "panels": ["Top_Panel", "Left_Panel"],
    },
    "top_right": {
        "description": "Top panel meets right panel (-X, +Z corner)",
        "x_range": (-HALF_W, -HALF_W + T),        # (-225, -206)
        "z_range": (OVERALL_HEIGHT - T, OVERALL_HEIGHT),
        "panels": ["Top_Panel", "Right_Panel"],
    },
    "bottom_left": {
        "description": "Bottom panel meets left panel (+X, 0 corner)",
        "x_range": (HALF_W - T, HALF_W),          # (206, 225)
        "z_range": (0, T),                         # (0, 19)
        "panels": ["Bottom_Panel", "Left_Panel"],
    },
    "bottom_right": {
        "description": "Bottom panel meets right panel (-X, 0 corner)",
        "x_range": (-HALF_W, -HALF_W + T),        # (-225, -206)
        "z_range": (0, T),
        "panels": ["Bottom_Panel", "Right_Panel"],
    },
}

# =============================================================================
# MITER CUT GEOMETRY
# =============================================================================
"""
For each corner, we create TWO triangular cuts (one per panel).
The cuts are extruded the full depth of the cabinet (400mm in Y).

TOP-LEFT corner example:
  - Top Panel cut: Triangle with vertices at (206,579), (225,579), (225,560)
  - Left Panel cut: Triangle with vertices at (206,579), (206,560), (225,560)
  
These two triangles together fill the 19×19mm overlap square.
"""

def get_miter_cuts():
    """Generate miter cut definitions for all corners."""
    cuts = {}
    
    # Top-Left: cut removes upper-right triangle from top, lower-left from side
    cuts["top_left_top_panel"] = {
        "target": "Top_Panel",
        "triangle_vertices_xz": [
            (HALF_W - T, OVERALL_HEIGHT),      # (206, 579) - inner top
            (HALF_W, OVERALL_HEIGHT),          # (225, 579) - outer top  
            (HALF_W, OVERALL_HEIGHT - T),      # (225, 560) - outer bottom
        ],
        "y_range": (-200, 200),  # Full depth
        "note": "Cuts off outer triangle from top panel"
    }
    
    cuts["top_left_left_panel"] = {
        "target": "Left_Panel",
        "triangle_vertices_xz": [
            (HALF_W - T, OVERALL_HEIGHT),      # (206, 579)
            (HALF_W - T, OVERALL_HEIGHT - T),  # (206, 560)
            (HALF_W, OVERALL_HEIGHT - T),      # (225, 560)
        ],
        "y_range": (-200, 200),
        "note": "Cuts off inner triangle from left panel"
    }
    
    # Top-Right: mirror of top-left
    cuts["top_right_top_panel"] = {
        "target": "Top_Panel",
        "triangle_vertices_xz": [
            (-HALF_W + T, OVERALL_HEIGHT),     # (-206, 579)
            (-HALF_W, OVERALL_HEIGHT),         # (-225, 579)
            (-HALF_W, OVERALL_HEIGHT - T),     # (-225, 560)
        ],
        "y_range": (-200, 200),
        "note": "Cuts off outer triangle from top panel"
    }
    
    cuts["top_right_right_panel"] = {
        "target": "Right_Panel",
        "triangle_vertices_xz": [
            (-HALF_W + T, OVERALL_HEIGHT),     # (-206, 579)
            (-HALF_W + T, OVERALL_HEIGHT - T), # (-206, 560)
            (-HALF_W, OVERALL_HEIGHT - T),     # (-225, 560)
        ],
        "y_range": (-200, 200),
        "note": "Cuts off inner triangle from right panel"
    }
    
    # Bottom-Left
    cuts["bottom_left_bottom_panel"] = {
        "target": "Bottom_Panel",
        "triangle_vertices_xz": [
            (HALF_W - T, 0),                   # (206, 0)
            (HALF_W, 0),                       # (225, 0)
            (HALF_W, T),                       # (225, 19)
        ],
        "y_range": (-200, 200),
        "note": "Cuts off outer triangle from bottom panel"
    }
    
    cuts["bottom_left_left_panel"] = {
        "target": "Left_Panel", 
        "triangle_vertices_xz": [
            (HALF_W - T, 0),                   # (206, 0)
            (HALF_W - T, T),                   # (206, 19)
            (HALF_W, T),                       # (225, 19)
        ],
        "y_range": (-200, 200),
        "note": "Cuts off inner triangle from left panel"
    }
    
    # Bottom-Right
    cuts["bottom_right_bottom_panel"] = {
        "target": "Bottom_Panel",
        "triangle_vertices_xz": [
            (-HALF_W + T, 0),                  # (-206, 0)
            (-HALF_W, 0),                      # (-225, 0)
            (-HALF_W, T),                      # (-225, 19)
        ],
        "y_range": (-200, 200),
        "note": "Cuts off outer triangle from bottom panel"
    }
    
    cuts["bottom_right_right_panel"] = {
        "target": "Right_Panel",
        "triangle_vertices_xz": [
            (-HALF_W + T, 0),                  # (-206, 0)
            (-HALF_W + T, T),                  # (-206, 19)
            (-HALF_W, T),                      # (-225, 19)
        ],
        "y_range": (-200, 200),
        "note": "Cuts off inner triangle from right panel"
    }
    
    return cuts


def print_miter_instructions():
    """Print miter cutting instructions."""
    print("=" * 60)
    print("STAGE 3: MITER CUTS (8 triangular cuts)")
    print("=" * 60)
    
    cuts = get_miter_cuts()
    
    for name, cut in cuts.items():
        print(f"\n{name}:")
        print(f"  Target: {cut['target']}")
        print(f"  Triangle (XZ): {cut['triangle_vertices_xz']}")
        print(f"  Extrude Y: {cut['y_range'][0]} to {cut['y_range'][1]}")
        print(f"  Note: {cut['note']}")
    
    print("\n" + "=" * 60)
    print("FUSION BUILD SEQUENCE")
    print("=" * 60)
    print("""
For each cut:
1. Create sketch on XZ plane (or offset plane)
2. Draw triangle using 3 lines connecting the vertices
3. Extrude as CUT through the target body
4. Extrude distance: 400mm (full Y depth)

Alternative approach (simpler):
1. Create a single sketch with triangular profile
2. Use Extrude > Cut > Select Bodies to cut multiple panels
""")


if __name__ == "__main__":
    print_miter_instructions()








