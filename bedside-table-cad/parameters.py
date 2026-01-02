"""
Bedside Table - Master Parameters
=================================
All dimensions in mm. Single source of truth.
"""

# =============================================================================
# OVERALL DIMENSIONS
# =============================================================================
OVERALL_WIDTH = 450       # Total cabinet width (X)
OVERALL_DEPTH = 400       # Total cabinet depth (Y)
OVERALL_HEIGHT = 579      # Total cabinet height (Z) - matches Fusion model

# =============================================================================
# MATERIAL THICKNESSES
# =============================================================================
CARCASS_THICKNESS = 19    # Side, top, bottom panels (3/4" plywood)
BACK_THICKNESS = 6        # Back panel (1/4" plywood)
FALSE_FLOOR_THICKNESS = 12

# =============================================================================
# PLINTH
# =============================================================================
PLINTH_HEIGHT = 40
PLINTH_INSET = 25
PLINTH_WIDTH = OVERALL_WIDTH - (2 * PLINTH_INSET)   # 400mm
PLINTH_DEPTH = OVERALL_DEPTH - (2 * PLINTH_INSET)   # 350mm

# =============================================================================
# INTERNAL DIMENSIONS
# =============================================================================
INTERNAL_WIDTH = OVERALL_WIDTH - (2 * CARCASS_THICKNESS)   # 412mm
INTERNAL_HEIGHT = OVERALL_HEIGHT - (2 * CARCASS_THICKNESS) # 541mm

# =============================================================================
# JOINERY - MITERS
# =============================================================================
MITER_ANGLE = 45  # degrees

# =============================================================================
# JOINERY - SPLINES (alignment in miter joints)
# =============================================================================
SPLINE_THICKNESS = 4      # 1/8" plywood
SPLINE_WIDTH = 30         # Depth into each panel
SPLINE_SLOT_DEPTH = 16    # Slot depth per panel
SPLINE_SPACING = 100      # Between splines along joint
SPLINE_EDGE_INSET = 50    # From front/back edge

# =============================================================================
# JOINERY - CORNER BLOCKS (triangular braces)
# =============================================================================
CORNER_BLOCK_LEG = 50     # Triangle leg length
CORNER_BLOCK_LENGTH = 80  # Along joint
CORNER_BLOCK_RABBET = 6   # Alignment rabbet depth
CORNER_BLOCK_SCREW = 32   # #8 × 1-1/4"

# Positions along Y axis (2 per corner = 8 total)
CORNER_BLOCK_FRONT_Y = 60
CORNER_BLOCK_REAR_Y = OVERALL_DEPTH - BACK_THICKNESS - 60  # 334mm

# =============================================================================
# JOINERY - DADOS & RABBETS
# =============================================================================
DADO_DEPTH = 6
DADO_WIDTH = FALSE_FLOOR_THICKNESS
RABBET_DEPTH = 9
RABBET_WIDTH = BACK_THICKNESS

# =============================================================================
# FALSE FLOOR
# =============================================================================
FALSE_FLOOR_Z = 344       # Z position (from Fusion model)
FALSE_FLOOR_WIDTH = 424   # Extends into dados
FALSE_FLOOR_DEPTH = 347   # Stops before front

# =============================================================================
# DRAWER FACES
# =============================================================================
DRAWER_FACE_SHADOW_GAP = 3
DRAWER_FACE_GAP = 3       # Between the two faces
