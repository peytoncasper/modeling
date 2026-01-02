"""
Bedside Table - Design Validation
=================================
Simple validation of key dimensions.
"""

from parameters import *


def validate():
    """Run basic validation checks."""
    print("=" * 50)
    print("BEDSIDE TABLE - VALIDATION")
    print("=" * 50)
    
    checks = []
    
    # Internal width
    expected = OVERALL_WIDTH - (2 * CARCASS_THICKNESS)
    checks.append(("Internal Width", INTERNAL_WIDTH == expected, 
                   f"{INTERNAL_WIDTH}mm (450 - 2×19 = {expected}mm)"))
    
    # Spline slot depth leaves enough material
    remaining = CARCASS_THICKNESS - SPLINE_SLOT_DEPTH
    checks.append(("Spline Slot Safe", remaining >= 3,
                   f"{SPLINE_SLOT_DEPTH}mm slot leaves {remaining}mm material"))
    
    # Corner block fits inside
    checks.append(("Corner Block Size", CORNER_BLOCK_LEG <= 60,
                   f"{CORNER_BLOCK_LEG}mm leg fits in corner"))
    
    # Dado depth reasonable
    checks.append(("Dado Depth", 4 <= DADO_DEPTH <= 10,
                   f"{DADO_DEPTH}mm dado depth"))
    
    # Rabbet covers back panel
    checks.append(("Rabbet Width", RABBET_WIDTH >= BACK_THICKNESS,
                   f"{RABBET_WIDTH}mm rabbet for {BACK_THICKNESS}mm back panel"))
    
    # Print results
    passed = 0
    for name, ok, msg in checks:
        status = "✓" if ok else "✗"
        if ok:
            passed += 1
        print(f"  {status} {name}: {msg}")
    
    print(f"\n{passed}/{len(checks)} checks passed")
    return passed == len(checks)


if __name__ == "__main__":
    validate()
