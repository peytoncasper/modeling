#!/usr/bin/env python3
"""
Cut Optimizer for Woodworking Project
Calculates optimal board processing sizes for 19mm thick white oak pieces.
"""

from dataclasses import dataclass
from typing import List, Tuple
import itertools

# ============================================
# PART DEFINITIONS (all 19mm thick pieces)
# ============================================

@dataclass
class Part:
    name: str
    width: float  # mm
    length: float  # mm
    quantity_needed: int
    quantity_made: int = 0
    
    @property
    def remaining(self) -> int:
        return self.quantity_needed - self.quantity_made
    
    def __repr__(self):
        return f"{self.name}: {self.width}x{self.length}mm (need {self.remaining} more)"

@dataclass
class Board:
    name: str
    length: float  # mm
    width: float  # mm
    processed: bool = True
    wastage_factor: float = 1.0  # 1.0 = no wastage, 0.9 = 10% wastage
    
    @property
    def usable_length(self) -> float:
        return self.length * self.wastage_factor
    
    @property
    def usable_width(self) -> float:
        return self.width * self.wastage_factor
    
    def __repr__(self):
        status = "Processed" if self.processed else f"Unprocessed (~{int(self.wastage_factor*100)}% usable)"
        return f"{self.name}: {self.length}x{self.width}mm ({status})"


# ============================================
# PROJECT SPECIFICATIONS FROM PLAN
# ============================================

# Carcass outer dimensions
CARCASS_WIDTH = 450  # mm
CARCASS_DEPTH = 400  # mm
CARCASS_HEIGHT = 579  # mm
MATERIAL_THICKNESS = 19  # mm

# Miter allowance (add a bit for the miter joint cuts)
MITER_ALLOWANCE = 5  # mm extra per edge that gets mitered

# Calculate actual panel sizes
# Top/Bottom panels: full width x full depth (mitered on all 4 edges)
TOP_BOTTOM_WIDTH = CARCASS_WIDTH + MITER_ALLOWANCE * 2
TOP_BOTTOM_DEPTH = CARCASS_DEPTH + MITER_ALLOWANCE * 2

# Side panels: depth x height (mitered top and bottom)
SIDE_DEPTH = CARCASS_DEPTH + MITER_ALLOWANCE * 2
SIDE_HEIGHT = CARCASS_HEIGHT + MITER_ALLOWANCE * 2

# Drawer fronts (from plan)
TOP_DRAWER_FRONT_WIDTH = 438
TOP_DRAWER_FRONT_HEIGHT = 217
BOTTOM_DRAWER_FRONT_WIDTH = 438
BOTTOM_DRAWER_FRONT_HEIGHT = 344

# False floor
FALSE_FLOOR_WIDTH = CARCASS_WIDTH - 2 * MATERIAL_THICKNESS  # Internal width = 412mm
FALSE_FLOOR_DEPTH = 381  # From plan

# Kerf/saw blade allowance
KERF = 4  # mm per cut


# ============================================
# DEFINE ALL PARTS NEEDED
# ============================================

all_parts = [
    # Carcass panels
    Part("Carcass Top", TOP_BOTTOM_WIDTH, TOP_BOTTOM_DEPTH, quantity_needed=1, quantity_made=0),
    Part("Carcass Bottom", TOP_BOTTOM_WIDTH, TOP_BOTTOM_DEPTH, quantity_needed=1, quantity_made=0),
    Part("Carcass Side (Left)", SIDE_DEPTH, SIDE_HEIGHT, quantity_needed=1, quantity_made=1),  # ONE MADE
    Part("Carcass Side (Right)", SIDE_DEPTH, SIDE_HEIGHT, quantity_needed=1, quantity_made=0),
    
    # Drawer fronts
    Part("Top Drawer Front", TOP_DRAWER_FRONT_WIDTH, TOP_DRAWER_FRONT_HEIGHT, quantity_needed=1, quantity_made=1),  # MADE
    Part("Bottom Drawer Front", BOTTOM_DRAWER_FRONT_WIDTH, BOTTOM_DRAWER_FRONT_HEIGHT, quantity_needed=1, quantity_made=1),  # MADE
    
    # False floor
    Part("False Floor", FALSE_FLOOR_WIDTH, FALSE_FLOOR_DEPTH, quantity_needed=1, quantity_made=0),
]

# Filter to remaining parts only
remaining_parts = [p for p in all_parts if p.remaining > 0]


# ============================================
# AVAILABLE BOARDS
# ============================================

processed_boards = [
    Board("Processed Board 1", 780, 150, processed=True),
    Board("Processed Board 2", 643, 160, processed=True),
    Board("Processed Board 3", 458, 150, processed=True),
]

unprocessed_boards = [
    Board("Unprocessed Board 1", 2786, 185, processed=False, wastage_factor=0.85),
    Board("Unprocessed Board 2", 2410, 175, processed=False, wastage_factor=0.85),
]

all_boards = processed_boards + unprocessed_boards


# ============================================
# ANALYSIS FUNCTIONS
# ============================================

def can_fit_part(board: Board, part: Part) -> Tuple[bool, str]:
    """Check if a part can fit on a board (considering both orientations)."""
    b_len = board.usable_length
    b_wid = board.usable_width
    p_wid = part.width
    p_len = part.length
    
    # Orientation 1: part width along board length
    if p_wid <= b_len and p_len <= b_wid:
        return True, f"Fits: part {p_wid}x{p_len} on board {b_len:.0f}x{b_wid:.0f}"
    
    # Orientation 2: part length along board length  
    if p_len <= b_len and p_wid <= b_wid:
        return True, f"Fits (rotated): part {p_len}x{p_wid} on board {b_len:.0f}x{b_wid:.0f}"
    
    return False, f"NO FIT: part {p_wid}x{p_len} cannot fit on board {b_len:.0f}x{b_wid:.0f}"


def analyze_board_for_parts(board: Board, parts: List[Part]) -> dict:
    """Analyze which parts can be cut from a board."""
    results = {
        "board": board,
        "fits": [],
        "no_fit": [],
    }
    
    for part in parts:
        can_fit, msg = can_fit_part(board, part)
        if can_fit:
            results["fits"].append((part, msg))
        else:
            results["no_fit"].append((part, msg))
    
    return results


def suggest_processing_dimensions(board: Board, target_parts: List[Part]) -> List[dict]:
    """
    For an unprocessed board, suggest optimal dimensions to process it into
    to maximize usable parts.
    """
    suggestions = []
    b_len = board.usable_length
    b_wid = board.usable_width
    
    # Sort parts by area (largest first - greedy approach)
    sorted_parts = sorted(target_parts, key=lambda p: p.width * p.length, reverse=True)
    
    for part in sorted_parts:
        p_wid = part.width
        p_len = part.length
        
        # How many of this part could we get lengthwise?
        # Option 1: Width of board matches part width
        if b_wid >= p_wid:
            num_along_length = int(b_len // (p_len + KERF))
            if num_along_length > 0:
                target_width = p_wid + 10  # Add margin for processing
                target_length = (p_len + KERF) * num_along_length
                suggestions.append({
                    "part": part,
                    "orientation": "width_matches",
                    "target_dimensions": (target_length, target_width),
                    "parts_possible": num_along_length,
                    "efficiency": (p_wid * p_len * num_along_length) / (b_len * b_wid) * 100
                })
        
        # Option 2: Width of board matches part length (rotated)
        if b_wid >= p_len:
            num_along_length = int(b_len // (p_wid + KERF))
            if num_along_length > 0:
                target_width = p_len + 10
                target_length = (p_wid + KERF) * num_along_length
                suggestions.append({
                    "part": part,
                    "orientation": "length_matches (rotated)",
                    "target_dimensions": (target_length, target_width),
                    "parts_possible": num_along_length,
                    "efficiency": (p_wid * p_len * num_along_length) / (b_len * b_wid) * 100
                })
    
    return suggestions


def calculate_optimal_cut_plan():
    """Main function to calculate and display optimal cutting plan."""
    
    print("=" * 70)
    print("WOODWORKING PROJECT - CUT OPTIMIZATION ANALYSIS")
    print("=" * 70)
    
    # Show all parts needed
    print("\n📋 ALL PARTS (19mm thick white oak):")
    print("-" * 50)
    for part in all_parts:
        status = "✅ MADE" if part.remaining == 0 else f"⏳ Need {part.remaining}"
        print(f"  {part.name}: {part.width}mm x {part.length}mm - {status}")
    
    # Show remaining parts
    print("\n📌 REMAINING PARTS TO MAKE:")
    print("-" * 50)
    for part in remaining_parts:
        print(f"  • {part.name}: {part.width}mm x {part.length}mm")
    
    # Show available boards
    print("\n🪵 AVAILABLE BOARDS:")
    print("-" * 50)
    print("\nProcessed Boards:")
    for board in processed_boards:
        print(f"  • {board.length}mm x {board.width}mm")
    print("\nUnprocessed Boards (assuming 15% wastage):")
    for board in unprocessed_boards:
        print(f"  • {board.length}mm x {board.width}mm → usable: ~{board.usable_length:.0f}mm x {board.usable_width:.0f}mm")
    
    # Analyze processed boards
    print("\n" + "=" * 70)
    print("ANALYSIS: PROCESSED BOARDS vs REMAINING PARTS")
    print("=" * 70)
    
    for board in processed_boards:
        print(f"\n📐 {board.name} ({board.length}mm x {board.width}mm):")
        analysis = analyze_board_for_parts(board, remaining_parts)
        
        if analysis["fits"]:
            print("  ✅ Can fit:")
            for part, msg in analysis["fits"]:
                print(f"     - {part.name} ({part.width}x{part.length}mm)")
        if analysis["no_fit"]:
            print("  ❌ Cannot fit:")
            for part, msg in analysis["no_fit"]:
                print(f"     - {part.name} ({part.width}x{part.length}mm) - board too narrow")
    
    # Analyze unprocessed boards
    print("\n" + "=" * 70)
    print("ANALYSIS: UNPROCESSED BOARDS - OPTIMAL PROCESSING SIZES")
    print("=" * 70)
    
    for board in unprocessed_boards:
        print(f"\n📐 {board.name}")
        print(f"   Raw: {board.length}mm x {board.width}mm")
        print(f"   Usable (after processing): ~{board.usable_length:.0f}mm x {board.usable_width:.0f}mm")
        
        suggestions = suggest_processing_dimensions(board, remaining_parts)
        
        print("\n   💡 SUGGESTED PROCESSING OPTIONS:")
        for i, sug in enumerate(suggestions, 1):
            part = sug["part"]
            dims = sug["target_dimensions"]
            print(f"\n   Option {i}: For {part.name}")
            print(f"      Target board size: {dims[0]:.0f}mm x {dims[1]:.0f}mm")
            print(f"      Parts possible: {sug['parts_possible']}")
            print(f"      Material efficiency: {sug['efficiency']:.1f}%")
    
    # RECOMMENDED CUT PLAN
    print("\n" + "=" * 70)
    print("🎯 RECOMMENDED CUT PLAN")
    print("=" * 70)
    
    print("""
REMAINING PARTS TO MAKE:
  1. Carcass Top: 460mm x 410mm
  2. Carcass Bottom: 460mm x 410mm  
  3. Carcass Side (Right): 410mm x 589mm
  4. False Floor: 412mm x 381mm

ISSUE: Your processed boards (150-160mm wide) are too narrow for any remaining parts.
       The narrowest part (False Floor) needs 381mm in one dimension.

SOLUTION: Process the unprocessed boards to these target widths:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UNPROCESSED BOARD 1 (2786mm x 185mm):
  → Process to: 420mm wide strips
  → This board is only 185mm wide raw, which limits options
  → BEST USE: Cut lengthwise sections for edge-gluing to make wider panels

UNPROCESSED BOARD 2 (2410mm x 175mm):  
  → Same situation - only 175mm wide
  → BEST USE: Edge-glue with Board 1 strips to create wider panels

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  CRITICAL FINDING:
    None of your boards are wide enough for the remaining parts!
    
    Minimum widths needed:
    • Carcass Side: 410mm wide
    • Carcass Top/Bottom: 410mm wide  
    • False Floor: 381mm wide
    
    Your widest boards:
    • Processed: 160mm
    • Unprocessed: 185mm (raw)
    
RECOMMENDED APPROACH:
    """)
    
    print_edge_glue_plan()


def print_edge_glue_plan():
    """Print detailed edge-gluing plan."""
    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    EDGE-GLUING STRATEGY                             │
└─────────────────────────────────────────────────────────────────────┘

To achieve 410-460mm wide panels, you'll need to edge-glue 3 strips together.
With 3 x 150mm strips = 450mm total width (perfect for your parts).

════════════════════════════════════════════════════════════════════════
                    OPTIMAL PROCESSING PLAN
════════════════════════════════════════════════════════════════════════

STEP 1: Process UNPROCESSED boards on jointer/planer/table saw
────────────────────────────────────────────────────────────────────────

   UNPROCESSED BOARD 1 (2786mm x 185mm raw):
   ┌──────────────────────────────────────────────────────────────────┐
   │  1. Joint one face flat                                         │
   │  2. Plane to 19mm thickness                                     │
   │  3. Joint one edge straight                                     │
   │  4. Rip to 150mm wide (one clean strip, ~30mm waste edge)       │
   │  5. Crosscut into these pieces:                                 │
   │     • 600mm  → Side panel strip 1                               │
   │     • 475mm  → Top panel strip 1                                │
   │     • 475mm  → Bottom panel strip 1                             │
   │     • 475mm  → Bottom panel strip 3 (EXTRA!)                    │
   │     • 430mm  → False floor strip 1                              │
   │     ─────────────────────────────────────────────────           │
   │     Total: 2455mm used from ~2650mm usable (after end trim)     │
   │     Remaining: ~195mm (good for test pieces/mistakes)           │
   └──────────────────────────────────────────────────────────────────┘

   UNPROCESSED BOARD 2 (2410mm x 175mm raw):
   ┌──────────────────────────────────────────────────────────────────┐
   │  1. Joint one face flat                                         │
   │  2. Plane to 19mm thickness                                     │
   │  3. Joint one edge straight                                     │
   │  4. Rip to 150mm wide (one clean strip, ~20mm waste edge)       │
   │  5. Crosscut into these pieces:                                 │
   │     • 600mm  → Side panel strip 2                               │
   │     • 475mm  → Top panel strip 2                                │
   │     • 430mm  → False floor strip 2                              │
   │     ─────────────────────────────────────────────────           │
   │     Total: 1505mm used from ~2275mm usable                      │
   │     Remaining: ~770mm (for extras/mistakes)                     │
   └──────────────────────────────────────────────────────────────────┘

STEP 2: Cut PROCESSED boards to length
────────────────────────────────────────────────────────────────────────

   PROCESSED BOARD 1 (780mm x 150mm):
   ┌──────────────────────────────────────────────────────────────────┐
   │  Already at 150mm width ✓                                       │
   │  Crosscut:                                                      │
   │     • 600mm  → Side panel strip 3                               │
   │     Remaining: 180mm scrap                                      │
   └──────────────────────────────────────────────────────────────────┘

   PROCESSED BOARD 2 (643mm x 160mm):
   ┌──────────────────────────────────────────────────────────────────┐
   │  Rip to 150mm width first (10mm waste)                          │
   │  Crosscut:                                                      │
   │     • 475mm  → Top panel strip 3                                │
   │     Remaining: 168mm scrap                                      │
   └──────────────────────────────────────────────────────────────────┘

   PROCESSED BOARD 3 (458mm x 150mm):
   ┌──────────────────────────────────────────────────────────────────┐
   │  Already at 150mm width ✓                                       │
   │  Crosscut:                                                      │
   │     • 430mm  → False floor strip 3                              │
   │     Remaining: 28mm scrap                                       │
   └──────────────────────────────────────────────────────────────────┘

STEP 3: Edge-glue into wide panels
────────────────────────────────────────────────────────────────────────

   PANEL A - CARCASS SIDE (Right): Final size 410mm x 589mm
   ┌──────────────────────────────────────────────────────────────────┐
   │  Glue 3 strips @ 150mm x 600mm each:                            │
   │    [Strip 1] + [Strip 2] + [Strip 3] = ~450mm wide              │
   │                                                                  │
   │  After glue-up:                                                 │
   │    → Joint/sand edges flat                                      │
   │    → Trim to 420mm x 600mm                                      │
   │    → Final cut to 410mm x 589mm (+ miter allowance)             │
   └──────────────────────────────────────────────────────────────────┘

   PANEL B - CARCASS TOP: Final size 460mm x 410mm
   ┌──────────────────────────────────────────────────────────────────┐
   │  Glue 3 strips @ 150mm x 475mm each:                            │
   │    [Strip 1] + [Strip 2] + [Strip 3] = ~450mm wide              │
   │                                                                  │
   │  After glue-up:                                                 │
   │    → Joint/sand edges flat                                      │
   │    → Trim to 470mm x 420mm                                      │
   │    → Final cut to 460mm x 410mm (+ miter allowance)             │
   └──────────────────────────────────────────────────────────────────┘

   PANEL C - CARCASS BOTTOM: Final size 460mm x 410mm  
   ┌──────────────────────────────────────────────────────────────────┐
   │  Glue 3 strips @ 150mm x 475mm each:                            │
   │    [Strip 1] + [Strip 2] + [Strip 3] = ~450mm wide              │
   │                                                                  │
   │  After glue-up:                                                 │
   │    → Joint/sand edges flat                                      │
   │    → Trim to 470mm x 420mm                                      │
   │    → Final cut to 460mm x 410mm (+ miter allowance)             │
   └──────────────────────────────────────────────────────────────────┘

   PANEL D - FALSE FLOOR: Final size 412mm x 381mm
   ┌──────────────────────────────────────────────────────────────────┐
   │  Glue 3 strips @ 150mm x 430mm each:                            │
   │    [Strip 1] + [Strip 2] + [Strip 3] = ~450mm wide              │
   │                                                                  │
   │  After glue-up:                                                 │
   │    → Joint/sand edges flat                                      │
   │    → Trim to 420mm x 390mm                                      │
   │    → Final cut to 412mm x 381mm                                 │
   └──────────────────────────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════════════
                         MASTER CUT LIST
════════════════════════════════════════════════════════════════════════

STRIPS NEEDED (all 150mm wide x 19mm thick):
─────────────────────────────────────────────
  For Side Panel:      3 × (150mm × 600mm)
  For Top Panel:       3 × (150mm × 475mm)  
  For Bottom Panel:    3 × (150mm × 475mm)
  For False Floor:     3 × (150mm × 430mm)
─────────────────────────────────────────────
  TOTAL: 12 strips

STRIP ALLOCATION:
─────────────────────────────────────────────
  From Unprocessed Board 1:  5 strips (600, 475, 475, 475, 430mm)
  From Unprocessed Board 2:  3 strips (600, 475, 430mm)
  From Processed Board 1:    1 strip  (600mm)
  From Processed Board 2:    1 strip  (475mm)
  From Processed Board 3:    1 strip  (430mm)
─────────────────────────────────────────────
  TOTAL: 11 strips... WAIT, need 12!

  ✅ SOLUTION: Cut additional 475mm strip from Unprocessed Board 2's
               remaining 770mm material!

  REVISED From Unprocessed Board 2: 4 strips (600, 475, 475, 430mm)
  Total from Board 2: 1980mm (fits in ~2275mm usable)

═══════════════════════════════════════════════════════════════════════
                     ✅ MATERIAL CHECK: SUFFICIENT!
═══════════════════════════════════════════════════════════════════════

REMAINING MATERIAL AFTER ALL CUTS:
─────────────────────────────────────────────
  Unprocessed Board 1: ~195mm × 150mm (test piece)
  Unprocessed Board 2: ~295mm × 150mm (backup strip)
  Processed Board 1:   180mm × 150mm (scrap)
  Processed Board 2:   168mm × 150mm (scrap)
  Processed Board 3:   28mm × 150mm (scrap)

════════════════════════════════════════════════════════════════════════
                    MACHINE TIME ESTIMATES
════════════════════════════════════════════════════════════════════════

JOINTER:
  • 4 face passes (2 boards × 2 faces).............. ~15 min
  • 2 edge passes (2 boards)....................... ~5 min
  
PLANER:
  • Thickness both unprocessed boards to 19mm...... ~20 min
  
TABLE SAW:
  • Rip 2 unprocessed boards to 150mm width........ ~10 min
  • Rip processed board 2 to 150mm................. ~3 min
  • Crosscut 12 strips to length................... ~25 min
  
EDGE GLUING:
  • 4 panel glue-ups (can do 2 at a time).......... ~45 min active
  • Curing time................................... 4-24 hours
  
CNC ROUTER (optional for miters):
  • If cutting miters on CNC....................... ~30 min setup + cut

TOTAL ACTIVE MACHINE TIME: ~2.5 hours (plus glue cure overnight)
    """)


if __name__ == "__main__":
    calculate_optimal_cut_plan()

