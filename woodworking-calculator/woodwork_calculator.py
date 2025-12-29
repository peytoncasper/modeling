#!/usr/bin/env python3
"""
Woodworking Project Calculator

A tool for accurate material planning, cut optimization, and board feet calculation.

Usage:
    python woodwork_calculator.py [config.json]
    
If no config file specified, uses project_config.json in same directory.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from pathlib import Path
import math


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class Part:
    id: str
    name: str
    width_mm: float
    length_mm: float
    quantity_needed: int
    quantity_made: int = 0
    notes: str = ""
    
    @property
    def remaining(self) -> int:
        return max(0, self.quantity_needed - self.quantity_made)
    
    @property
    def area_mm2(self) -> float:
        return self.width_mm * self.length_mm
    
    @property
    def area_sqft(self) -> float:
        return self.area_mm2 / 92903.04  # mm² to ft²
    
    def board_feet(self, thickness_mm: float) -> float:
        """Calculate board feet for this part."""
        # BF = (L" × W" × T") / 144
        length_in = self.length_mm / 25.4
        width_in = self.width_mm / 25.4
        # Use 1" nominal for 4/4 stock (standard practice)
        thickness_in = 1.0 if thickness_mm <= 25.4 else thickness_mm / 25.4
        return (length_in * width_in * thickness_in) / 144


@dataclass
class Board:
    id: str
    length_mm: float
    width_mm: float
    thickness_mm: float = 19
    rough_thickness_mm: float = 25
    end_trim_mm: float = 0
    edge_waste_mm: float = 0
    notes: str = ""
    is_processed: bool = True
    
    @property
    def usable_length(self) -> float:
        return self.length_mm - (self.end_trim_mm * 2 if not self.is_processed else 0)
    
    @property
    def usable_width(self) -> float:
        return self.width_mm - (self.edge_waste_mm * 2 if not self.is_processed else 0)
    
    @property
    def area_mm2(self) -> float:
        return self.length_mm * self.width_mm
    
    @property
    def usable_area_mm2(self) -> float:
        return self.usable_length * self.usable_width
    
    def board_feet(self) -> float:
        """Calculate board feet (uses rough thickness for raw lumber)."""
        length_in = self.length_mm / 25.4
        width_in = self.width_mm / 25.4
        # Use rough thickness for BF calculation (industry standard)
        thickness_in = self.rough_thickness_mm / 25.4 if not self.is_processed else 1.0
        return (length_in * width_in * thickness_in) / 144


@dataclass
class Strip:
    """A strip cut from a board for edge gluing."""
    source_board_id: str
    length_mm: float
    width_mm: float
    thickness_mm: float
    assigned_to: Optional[str] = None  # Part ID
    
    def board_feet(self) -> float:
        length_in = self.length_mm / 25.4
        width_in = self.width_mm / 25.4
        return (length_in * width_in * 1.0) / 144  # 1" nominal


@dataclass 
class CutPlan:
    """A plan for cutting strips from a board."""
    board: Board
    strips: List[Tuple[float, str]] = field(default_factory=list)  # (length, purpose)
    waste_mm: float = 0
    
    def add_strip(self, length_mm: float, purpose: str):
        self.strips.append((length_mm, purpose))
    
    @property
    def total_cut_length(self) -> float:
        return sum(s[0] for s in self.strips)
    
    @property
    def strip_count(self) -> int:
        return len(self.strips)


# ============================================
# CALCULATOR CLASS
# ============================================

class WoodworkCalculator:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.parts: List[Part] = []
        self.processed_boards: List[Board] = []
        self.unprocessed_boards: List[Board] = []
        self._parse_config()
    
    def _load_config(self, path: str) -> dict:
        with open(path, 'r') as f:
            return json.load(f)
    
    def _parse_config(self):
        """Parse configuration into data objects."""
        # Parse parts
        for p in self.config.get('parts', []):
            self.parts.append(Part(
                id=p['id'],
                name=p['name'],
                width_mm=p['width_mm'],
                length_mm=p['length_mm'],
                quantity_needed=p['quantity_needed'],
                quantity_made=p.get('quantity_made', 0),
                notes=p.get('notes', '')
            ))
        
        # Parse processed boards
        for b in self.config.get('inventory', {}).get('processed_boards', []):
            self.processed_boards.append(Board(
                id=b['id'],
                length_mm=b['length_mm'],
                width_mm=b['width_mm'],
                thickness_mm=b.get('thickness_mm', 19),
                is_processed=True,
                notes=b.get('notes', '')
            ))
        
        # Parse unprocessed boards
        for b in self.config.get('inventory', {}).get('unprocessed_boards', []):
            self.unprocessed_boards.append(Board(
                id=b['id'],
                length_mm=b['length_mm'],
                width_mm=b['width_mm'],
                thickness_mm=b.get('final_thickness_mm', 19),
                rough_thickness_mm=b.get('rough_thickness_mm', 25),
                end_trim_mm=b.get('end_trim_mm', 50),
                edge_waste_mm=b.get('edge_waste_mm', 10),
                is_processed=False,
                notes=b.get('notes', '')
            ))
    
    @property
    def remaining_parts(self) -> List[Part]:
        return [p for p in self.parts if p.remaining > 0]
    
    @property
    def completed_parts(self) -> List[Part]:
        return [p for p in self.parts if p.remaining == 0]
    
    @property
    def all_boards(self) -> List[Board]:
        return self.processed_boards + self.unprocessed_boards
    
    @property
    def kerf_mm(self) -> float:
        return self.config.get('kerf_mm', 3.2)
    
    @property
    def material_thickness(self) -> float:
        return self.config.get('material_thickness_mm', 19)
    
    @property
    def strip_width(self) -> float:
        return self.config.get('glue_up_config', {}).get('target_strip_width_mm', 150)
    
    @property
    def strips_per_panel(self) -> int:
        return self.config.get('glue_up_config', {}).get('strips_per_panel', 3)
    
    # ----------------------------------------
    # CALCULATIONS
    # ----------------------------------------
    
    def calculate_total_inventory_bf(self) -> Tuple[float, float, float]:
        """Returns (processed_bf, unprocessed_bf, total_bf)"""
        processed_bf = sum(b.board_feet() for b in self.processed_boards)
        unprocessed_bf = sum(b.board_feet() for b in self.unprocessed_boards)
        return processed_bf, unprocessed_bf, processed_bf + unprocessed_bf
    
    def calculate_parts_bf(self) -> Tuple[float, float, float]:
        """Returns (completed_bf, remaining_bf, total_bf)"""
        completed_bf = sum(
            p.board_feet(self.material_thickness) * p.quantity_made 
            for p in self.parts
        )
        remaining_bf = sum(
            p.board_feet(self.material_thickness) * p.remaining 
            for p in self.parts
        )
        return completed_bf, remaining_bf, completed_bf + remaining_bf
    
    def calculate_strips_needed(self) -> dict:
        """Calculate strips needed for each remaining part."""
        strips_needed = {}
        glue_config = self.config.get('glue_up_config', {})
        trim_margin = glue_config.get('panel_trim_margin_mm', 10)
        
        for part in self.remaining_parts:
            # Determine strip length (longer dimension + trim margin)
            strip_length = max(part.width_mm, part.length_mm) + trim_margin
            strips_needed[part.id] = {
                'part_name': part.name,
                'strip_length_mm': strip_length,
                'strip_count': self.strips_per_panel * part.remaining,
                'strip_width_mm': self.strip_width
            }
        
        return strips_needed
    
    def calculate_strips_available(self) -> List[dict]:
        """Calculate how many strips can be cut from each board."""
        strips_available = []
        
        for board in self.all_boards:
            usable_length = board.usable_length
            usable_width = board.usable_width
            
            # How many strips width-wise? (typically 1 for narrow boards)
            strips_across = int(usable_width // self.strip_width)
            
            strips_available.append({
                'board_id': board.id,
                'usable_length_mm': usable_length,
                'usable_width_mm': usable_width,
                'strips_across': max(1, strips_across),
                'max_strip_length_mm': usable_length,
                'is_processed': board.is_processed,
                'board_feet': board.board_feet()
            })
        
        return strips_available
    
    def generate_cut_plan(self) -> List[CutPlan]:
        """Generate optimized cut plan for all boards."""
        strips_needed = self.calculate_strips_needed()
        
        # Flatten strips needed into a list sorted by length (longest first)
        all_strips = []
        for part_id, info in strips_needed.items():
            for _ in range(info['strip_count']):
                all_strips.append({
                    'length': info['strip_length_mm'],
                    'part_id': part_id,
                    'part_name': info['part_name']
                })
        
        all_strips.sort(key=lambda x: x['length'], reverse=True)
        
        # Sort boards by usable length (longest first)
        boards = sorted(self.all_boards, key=lambda b: b.usable_length, reverse=True)
        
        cut_plans = []
        remaining_strips = all_strips.copy()
        
        for board in boards:
            plan = CutPlan(board=board)
            available_length = board.usable_length
            
            # First-fit decreasing algorithm
            strips_to_remove = []
            for i, strip in enumerate(remaining_strips):
                strip_with_kerf = strip['length'] + self.kerf_mm
                if strip_with_kerf <= available_length:
                    plan.add_strip(strip['length'], f"{strip['part_name']}")
                    available_length -= strip_with_kerf
                    strips_to_remove.append(i)
            
            # Remove assigned strips (in reverse order to maintain indices)
            for i in reversed(strips_to_remove):
                remaining_strips.pop(i)
            
            plan.waste_mm = available_length
            if plan.strips:
                cut_plans.append(plan)
        
        # Check if any strips couldn't be assigned
        if remaining_strips:
            print(f"\n⚠️  WARNING: {len(remaining_strips)} strips could not be assigned!")
            print("   You may need additional material.")
            for strip in remaining_strips:
                print(f"   - {strip['length']}mm for {strip['part_name']}")
        
        return cut_plans
    
    def generate_glue_up_plan(self) -> dict:
        """Generate which strips go together for each panel."""
        cut_plans = self.generate_cut_plan()
        
        # Group strips by part
        strips_by_part = {}
        for plan in cut_plans:
            for length, part_name in plan.strips:
                if part_name not in strips_by_part:
                    strips_by_part[part_name] = []
                strips_by_part[part_name].append({
                    'length_mm': length,
                    'source_board': plan.board.id,
                    'width_mm': self.strip_width
                })
        
        return strips_by_part
    
    # ----------------------------------------
    # REPORTS
    # ----------------------------------------
    
    def print_summary(self):
        """Print full project summary."""
        print("=" * 70)
        print(f"  {self.config.get('project_name', 'Woodworking Project').upper()}")
        print(f"  Material: {self.material_thickness}mm stock")
        print("=" * 70)
        
        self._print_parts_status()
        self._print_inventory()
        self._print_board_feet_analysis()
        self._print_strips_analysis()
        self._print_cut_plan()
        self._print_glue_up_plan()
    
    def _print_parts_status(self):
        print("\n" + "─" * 70)
        print("PARTS STATUS")
        print("─" * 70)
        
        print("\n✅ Completed:")
        for p in self.completed_parts:
            bf = p.board_feet(self.material_thickness)
            print(f"   {p.name}: {p.width_mm}×{p.length_mm}mm ({bf:.2f} BF)")
        
        if not self.completed_parts:
            print("   (none)")
        
        print("\n⏳ Remaining:")
        for p in self.remaining_parts:
            bf = p.board_feet(self.material_thickness)
            print(f"   {p.name}: {p.width_mm}×{p.length_mm}mm ({bf:.2f} BF) × {p.remaining}")
        
        if not self.remaining_parts:
            print("   (none - all parts complete!)")
    
    def _print_inventory(self):
        print("\n" + "─" * 70)
        print("INVENTORY")
        print("─" * 70)
        
        print("\n📦 Processed Boards (ready to cut):")
        for b in self.processed_boards:
            print(f"   [{b.id}] {b.length_mm}×{b.width_mm}×{b.thickness_mm}mm = {b.board_feet():.2f} BF")
        
        if not self.processed_boards:
            print("   (none)")
        
        print("\n🪵 Unprocessed Boards (need jointer/planer):")
        for b in self.unprocessed_boards:
            print(f"   [{b.id}] {b.length_mm}×{b.width_mm}mm (rough {b.rough_thickness_mm}mm)")
            print(f"         Usable: ~{b.usable_length:.0f}×{b.usable_width:.0f}mm = {b.board_feet():.2f} BF")
        
        if not self.unprocessed_boards:
            print("   (none)")
    
    def _print_board_feet_analysis(self):
        print("\n" + "─" * 70)
        print("BOARD FEET ANALYSIS")
        print("─" * 70)
        
        proc_bf, unproc_bf, total_inv_bf = self.calculate_total_inventory_bf()
        comp_bf, rem_bf, total_parts_bf = self.calculate_parts_bf()
        
        print(f"""
┌────────────────────────────────────────────────────────────────────┐
│  INVENTORY                                                         │
│    Processed boards:      {proc_bf:6.2f} BF                            │
│    Unprocessed boards:    {unproc_bf:6.2f} BF                            │
│    ─────────────────────────────                                   │
│    TOTAL INVENTORY:       {total_inv_bf:6.2f} BF                            │
├────────────────────────────────────────────────────────────────────┤
│  PARTS (net, no waste)                                             │
│    Already made:          {comp_bf:6.2f} BF                            │
│    Still needed:          {rem_bf:6.2f} BF                            │
│    ─────────────────────────────                                   │
│    TOTAL PARTS:           {total_parts_bf:6.2f} BF                            │
├────────────────────────────────────────────────────────────────────┤
│  WASTE ALLOWANCE                                                   │
│    Inventory - Parts:     {total_inv_bf - total_parts_bf:6.2f} BF available for waste        │
│    Efficiency estimate:   {(total_parts_bf/total_inv_bf*100) if total_inv_bf > 0 else 0:5.1f}%                              │
└────────────────────────────────────────────────────────────────────┘
        """)
    
    def _print_strips_analysis(self):
        print("\n" + "─" * 70)
        print("STRIPS ANALYSIS")
        print("─" * 70)
        
        strips_needed = self.calculate_strips_needed()
        total_strips = sum(s['strip_count'] for s in strips_needed.values())
        
        print(f"\n📏 Strip dimensions: {self.strip_width}mm wide × {self.material_thickness}mm thick")
        print(f"   Strips per panel: {self.strips_per_panel}")
        print(f"\n   STRIPS NEEDED:")
        
        for part_id, info in strips_needed.items():
            print(f"   • {info['part_name']}: {info['strip_count']}× strips @ {info['strip_length_mm']:.0f}mm")
        
        print(f"\n   TOTAL STRIPS NEEDED: {total_strips}")
        
        # Check availability
        strips_avail = self.calculate_strips_available()
        print(f"\n   STRIPS AVAILABLE FROM BOARDS:")
        
        total_available_length = 0
        for s in strips_avail:
            print(f"   • [{s['board_id']}]: up to {s['max_strip_length_mm']:.0f}mm length ({s['board_feet']:.2f} BF)")
            total_available_length += s['max_strip_length_mm']
        
        print(f"\n   Total linear material: {total_available_length:.0f}mm")
    
    def _print_cut_plan(self):
        print("\n" + "─" * 70)
        print("CUT PLAN")
        print("─" * 70)
        
        cut_plans = self.generate_cut_plan()
        
        for plan in cut_plans:
            board = plan.board
            status = "PROCESSED" if board.is_processed else "UNPROCESSED"
            print(f"\n┌─ [{board.id}] {status} ─────────────────────────────────────────")
            print(f"│  Board: {board.length_mm}×{board.width_mm}mm")
            print(f"│  Usable: {board.usable_length:.0f}×{board.usable_width:.0f}mm")
            print(f"│")
            print(f"│  CUTS ({plan.strip_count} strips):")
            
            running_total = 0
            for i, (length, purpose) in enumerate(plan.strips, 1):
                running_total += length + self.kerf_mm
                print(f"│    {i}. {length:.0f}mm → {purpose}")
            
            print(f"│")
            print(f"│  Used: {plan.total_cut_length:.0f}mm + {plan.strip_count * self.kerf_mm:.0f}mm kerf")
            print(f"│  Remaining: {plan.waste_mm:.0f}mm")
            print(f"└─────────────────────────────────────────────────────────────────")
    
    def _print_glue_up_plan(self):
        print("\n" + "─" * 70)
        print("GLUE-UP PLAN")
        print("─" * 70)
        
        glue_plan = self.generate_glue_up_plan()
        
        panel_num = 1
        for part_name, strips in glue_plan.items():
            print(f"\n┌─ PANEL {panel_num}: {part_name} ────────────────────────────────────")
            print(f"│")
            
            for i, strip in enumerate(strips, 1):
                print(f"│  Strip {i}: {strip['width_mm']}mm × {strip['length_mm']:.0f}mm")
                print(f"│           from [{strip['source_board']}]")
            
            total_width = len(strips) * self.strip_width
            print(f"│")
            print(f"│  Glued width: ~{total_width}mm")
            print(f"└─────────────────────────────────────────────────────────────────")
            panel_num += 1


# ============================================
# MAIN
# ============================================

def main():
    # Determine config file path
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        # Default to project_config.json in same directory
        script_dir = Path(__file__).parent
        config_path = script_dir / "project_config.json"
    
    if not Path(config_path).exists():
        print(f"Error: Config file not found: {config_path}")
        print("\nUsage: python woodwork_calculator.py [config.json]")
        sys.exit(1)
    
    print(f"Loading config from: {config_path}\n")
    
    calc = WoodworkCalculator(str(config_path))
    calc.print_summary()


if __name__ == "__main__":
    main()




