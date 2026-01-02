"""
Stage 1: Foundation - Master Parameters
=======================================
All dimensions in mm. Create these as User Parameters in Fusion 360.
"""

# =============================================================================
# OVERALL DIMENSIONS
# =============================================================================
OVERALL_WIDTH = 450       # Total cabinet width (X)
OVERALL_DEPTH = 400       # Total cabinet depth (Y)
OVERALL_HEIGHT = 579      # Total cabinet height (Z)

# =============================================================================
# MATERIAL THICKNESSES
# =============================================================================
CARCASS_THICKNESS = 19    # Side, top, bottom panels (3/4" plywood)
BACK_THICKNESS = 6        # Back panel (1/4" plywood)
FALSE_FLOOR_THICKNESS = 12

# =============================================================================
# DERIVED DIMENSIONS (calculated from above)
# =============================================================================
INTERNAL_WIDTH = OVERALL_WIDTH - (2 * CARCASS_THICKNESS)   # 412mm
INTERNAL_HEIGHT = OVERALL_HEIGHT - (2 * CARCASS_THICKNESS) # 541mm


# =============================================================================
# FUSION 360 PARAMETER SETUP
# =============================================================================
FUSION_PARAMETERS = [
    # (name, value, unit, comment)
    ("overall_width", 450, "mm", "Total cabinet width"),
    ("overall_depth", 400, "mm", "Total cabinet depth"),
    ("overall_height", 579, "mm", "Total cabinet height"),
    ("carcass_thickness", 19, "mm", "Panel thickness (3/4 inch plywood)"),
    ("back_thickness", 6, "mm", "Back panel thickness"),
    ("false_floor_thickness", 12, "mm", "False floor thickness"),
]


def print_parameters():
    """Print parameters for manual entry into Fusion 360."""
    print("=" * 60)
    print("STAGE 1: CREATE THESE PARAMETERS IN FUSION 360")
    print("=" * 60)
    print("\nModify > Change Parameters > + (User Parameter)\n")
    
    for name, value, unit, comment in FUSION_PARAMETERS:
        print(f"  {name} = {value} {unit}  // {comment}")
    
    print("\n" + "=" * 60)
    print("DERIVED VALUES (for verification):")
    print("=" * 60)
    print(f"  internal_width = overall_width - 2*carcass_thickness = {INTERNAL_WIDTH}mm")
    print(f"  internal_height = overall_height - 2*carcass_thickness = {INTERNAL_HEIGHT}mm")


if __name__ == "__main__":
    print_parameters()


