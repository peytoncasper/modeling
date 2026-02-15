#!/usr/bin/env python3
"""
Script to analyze and fix unclosed sketches in Fusion 360.
Requires the FusionMCPBridge add-in to be running.
"""

import requests
import json
import sys

FUSION_URL = "http://localhost:8080"


def call_fusion(endpoint, body=None):
    """Call a Fusion 360 bridge endpoint."""
    url = f"{FUSION_URL}{endpoint}"
    try:
        response = requests.post(url, json=body or {})
        return response.json()
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to Fusion 360. Is the MCP Bridge add-in running?")
        sys.exit(1)


def list_sketches():
    """List all sketches and their profile counts."""
    result = call_fusion("/list_sketches")
    
    print("\n" + "="*60)
    print("SKETCHES IN DOCUMENT")
    print("="*60)
    
    unclosed = []
    for sketch in result.get("sketches", []):
        status = "✓ CLOSED" if sketch["profile_count"] > 0 else "✗ OPEN"
        print(f"\n  {sketch['name']}:")
        print(f"    Profiles: {sketch['profile_count']}")
        print(f"    Curves: {sketch['curve_count']}")
        print(f"    Status: {status}")
        print(f"    Plane: {sketch['plane_info']}")
        
        if sketch["profile_count"] == 0 and sketch["curve_count"] > 0:
            unclosed.append(sketch["name"])
    
    return unclosed


def analyze_sketch(sketch_id, tolerance=0.1):
    """Analyze a sketch for gaps."""
    print(f"\n{'='*60}")
    print(f"ANALYZING: {sketch_id}")
    print("="*60)
    
    result = call_fusion("/analyze_sketch_gaps", {
        "sketch_id": sketch_id,
        "tolerance": tolerance
    })
    
    if "error" in result:
        print(f"  ERROR: {result.get('message', result)}")
        return None
    
    summary = result.get("summary", {})
    print(f"\n  Profile count: {result['profile_count']}")
    print(f"  Curve count: {result['curve_count']}")
    print(f"  Total gaps found: {summary.get('total_gaps', 0)}")
    print(f"  Auto-closeable (within {tolerance}mm): {summary.get('auto_closeable_gaps', 0)}")
    print(f"  Dangling endpoints: {summary.get('dangling_count', 0)}")
    
    # Show gap details
    gaps = result.get("gaps", [])
    if gaps:
        print(f"\n  GAPS:")
        for i, gap in enumerate(gaps[:10]):  # Show first 10
            auto = "✓" if gap["can_auto_close"] else " "
            print(f"    [{auto}] Curve {gap['curve1_index']} ({gap['curve1_point']}) <-> "
                  f"Curve {gap['curve2_index']} ({gap['curve2_point']}): "
                  f"{gap['distance_mm']:.4f} mm")
        if len(gaps) > 10:
            print(f"    ... and {len(gaps) - 10} more gaps")
    
    # Show dangling endpoints
    dangling = result.get("dangling_endpoints", [])
    if dangling:
        print(f"\n  DANGLING ENDPOINTS:")
        for d in dangling[:5]:
            print(f"    Curve {d['curve_index']} ({d['point_type']}): [{d['coords'][0]:.2f}, {d['coords'][1]:.2f}]")
        if len(dangling) > 5:
            print(f"    ... and {len(dangling) - 5} more")
    
    return result


def close_gaps(sketch_id, tolerance=0.01, max_line_gap=1.0, dry_run=True):
    """Close gaps in a sketch."""
    mode = "DRY RUN" if dry_run else "FIXING"
    print(f"\n{'='*60}")
    print(f"{mode}: {sketch_id}")
    print("="*60)
    
    result = call_fusion("/close_sketch_gaps", {
        "sketch_id": sketch_id,
        "tolerance": tolerance,
        "max_line_gap": max_line_gap,
        "dry_run": dry_run
    })
    
    if "error" in result:
        print(f"  ERROR: {result.get('message', result)}")
        return None
    
    summary = result.get("summary", {})
    print(f"\n  Original profiles: {result['original_profile_count']}")
    print(f"  New profiles: {result['new_profile_count']}")
    print(f"  Points merged: {summary.get('points_merged', 0)}")
    print(f"  Lines added: {summary.get('lines_added', 0)}")
    print(f"  Profiles created: {summary.get('profiles_created', 0)}")
    
    actions = result.get("actions", [])
    if actions:
        print(f"\n  ACTIONS {'(would be taken)' if dry_run else 'TAKEN'}:")
        for action in actions:
            if action["type"] == "merge":
                status = "" if dry_run else (" ✓" if action.get("success") else f" ✗ {action.get('error', '')}")
                print(f"    MERGE: Curve {action['from_curve']} -> Curve {action['to_curve']} "
                      f"({action['distance_mm']:.4f}mm){status}")
            elif action["type"] == "bridge_line":
                status = "" if dry_run else (" ✓" if action.get("success") else f" ✗ {action.get('error', '')}")
                print(f"    LINE: Curve {action['from_curve']} <-> Curve {action['to_curve']} "
                      f"({action['distance_mm']:.4f}mm){status}")
    
    return result


def main():
    print("\n" + "="*60)
    print("FUSION 360 SKETCH GAP FIXER")
    print("="*60)
    
    # Check connection
    ping = call_fusion("/ping")
    if ping.get("status") != "ok":
        print("ERROR: Fusion 360 bridge not responding correctly")
        sys.exit(1)
    print("\n✓ Connected to Fusion 360")
    
    # List all sketches
    unclosed = list_sketches()
    
    if not unclosed:
        print("\n✓ All sketches are properly closed!")
        return
    
    print(f"\n{'='*60}")
    print(f"FOUND {len(unclosed)} UNCLOSED SKETCH(ES): {', '.join(unclosed)}")
    print("="*60)
    
    # Analyze each unclosed sketch
    for sketch_id in unclosed:
        analysis = analyze_sketch(sketch_id, tolerance=0.5)  # Use larger tolerance for detection
        
        if analysis and analysis.get("summary", {}).get("needs_fixing"):
            # First do a dry run
            print(f"\n  Attempting to fix {sketch_id}...")
            dry_result = close_gaps(sketch_id, tolerance=0.05, max_line_gap=2.0, dry_run=True)
            
            if dry_result and dry_result.get("actions"):
                # Ask user if they want to apply
                response = input(f"\n  Apply fixes to {sketch_id}? (y/n): ").strip().lower()
                if response == 'y':
                    close_gaps(sketch_id, tolerance=0.05, max_line_gap=2.0, dry_run=False)
                else:
                    print("  Skipped.")
    
    print("\n" + "="*60)
    print("DONE")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
