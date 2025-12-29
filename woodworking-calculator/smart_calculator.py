#!/usr/bin/env python3
"""
Smart Woodworking Calculator

Analyzes project parts and inventory to determine:
1. Which parts can be cut directly from boards
2. Which parts require glue-up (and optimal strip configuration)
3. Optimal raw lumber to purchase for a project
4. Material efficiency and cost estimates

Usage:
    python smart_calculator.py [config.json]
    python smart_calculator.py --shopping-only parts_config.json
"""

import json
import sys
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from pathlib import Path
from enum import Enum


# ============================================
# CONSTANTS
# ============================================

MM_PER_INCH = 25.4
MM_PER_FOOT = 304.8


# ============================================
# DATA CLASSES
# ============================================

class CutStrategy(Enum):
    DIRECT = "direct"          # Cut directly from single board
    GLUE_UP = "glue_up"        # Edge glue multiple strips
    IMPOSSIBLE = "impossible"  # Can't make with available material


@dataclass
class Part:
    id: str
    name: str
    width_mm: float
    length_mm: float
    quantity_needed: int
    quantity_made: int = 0
    
    @property
    def remaining(self) -> int:
        return max(0, self.quantity_needed - self.quantity_made)
    
    @property
    def min_dimension(self) -> float:
        """Smaller of width/length - determines minimum board width needed."""
        return min(self.width_mm, self.length_mm)
    
    @property
    def max_dimension(self) -> float:
        """Larger of width/length - determines board length needed."""
        return max(self.width_mm, self.length_mm)
    
    def board_feet(self, thickness_mm: float = 19) -> float:
        l_in = self.length_mm / MM_PER_INCH
        w_in = self.width_mm / MM_PER_INCH
        return (l_in * w_in * 1.0) / 144  # 1" nominal


@dataclass
class Board:
    id: str
    length_mm: float
    width_mm: float
    is_processed: bool = True
    end_trim_mm: float = 0
    edge_waste_mm: float = 0
    
    @property
    def usable_length(self) -> float:
        trim = self.end_trim_mm * 2 if not self.is_processed else 0
        return self.length_mm - trim
    
    @property
    def usable_width(self) -> float:
        waste = self.edge_waste_mm * 2 if not self.is_processed else 0
        return self.width_mm - waste
    
    def board_feet(self, rough_thickness_mm: float = 25) -> float:
        l_in = self.length_mm / MM_PER_INCH
        w_in = self.width_mm / MM_PER_INCH
        t_in = rough_thickness_mm / MM_PER_INCH if not self.is_processed else 1.0
        return (l_in * w_in * t_in) / 144
    
    def can_fit_direct(self, part: Part, kerf: float = 3.2) -> bool:
        """Can this board fit the part in a single piece?"""
        # Check both orientations
        if (self.usable_width >= part.width_mm and 
            self.usable_length >= part.length_mm):
            return True
        if (self.usable_width >= part.length_mm and 
            self.usable_length >= part.width_mm):
            return True
        return False


@dataclass
class GlueUpPlan:
    """Plan for creating a panel from edge-glued strips."""
    part: Part
    strip_width_mm: float
    strip_count: int
    strip_length_mm: float
    source_boards: List[str] = field(default_factory=list)
    
    @property
    def total_panel_width(self) -> float:
        return self.strip_width_mm * self.strip_count
    
    @property
    def total_linear_mm(self) -> float:
        return self.strip_length_mm * self.strip_count


@dataclass
class PartSolution:
    """Solution for how to make a specific part."""
    part: Part
    strategy: CutStrategy
    source_board: Optional[str] = None  # For direct cuts
    glue_up_plan: Optional[GlueUpPlan] = None  # For glue-ups
    notes: str = ""


# ============================================
# SMART CALCULATOR
# ============================================

class SmartCalculator:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.parts: List[Part] = []
        self.boards: List[Board] = []
        self.kerf = self.config.get('kerf_mm', 3.2)
        self.thickness = self.config.get('material_thickness_mm', 19)
        self._parse_config()
    
    def _load_config(self, path: str) -> dict:
        with open(path, 'r') as f:
            return json.load(f)
    
    def _parse_config(self):
        for p in self.config.get('parts', []):
            self.parts.append(Part(
                id=p['id'],
                name=p['name'],
                width_mm=p['width_mm'],
                length_mm=p['length_mm'],
                quantity_needed=p['quantity_needed'],
                quantity_made=p.get('quantity_made', 0)
            ))
        
        for b in self.config.get('inventory', []):
            self.boards.append(Board(
                id=b['id'],
                length_mm=b['length_mm'],
                width_mm=b['width_mm'],
                is_processed=b.get('is_processed', True),
                end_trim_mm=b.get('end_trim_mm', 0),
                edge_waste_mm=b.get('edge_waste_mm', 0)
            ))
    
    @property
    def remaining_parts(self) -> List[Part]:
        return [p for p in self.parts if p.remaining > 0]
    
    @property
    def max_board_width(self) -> float:
        """Widest usable board in inventory."""
        if not self.boards:
            return 0
        return max(b.usable_width for b in self.boards)
    
    # ----------------------------------------
    # ANALYSIS
    # ----------------------------------------
    
    def analyze_part_requirements(self) -> Dict[str, dict]:
        """Analyze each part to determine cutting strategy."""
        results = {}
        
        for part in self.remaining_parts:
            min_width_needed = part.min_dimension
            can_direct = any(b.can_fit_direct(part) for b in self.boards)
            
            if can_direct:
                strategy = CutStrategy.DIRECT
                boards_that_fit = [b.id for b in self.boards if b.can_fit_direct(part)]
            else:
                strategy = CutStrategy.GLUE_UP
                boards_that_fit = []
            
            results[part.id] = {
                'part': part,
                'min_width_needed_mm': min_width_needed,
                'max_board_width_mm': self.max_board_width,
                'strategy': strategy,
                'boards_that_fit': boards_that_fit,
                'width_gap_mm': min_width_needed - self.max_board_width
            }
        
        return results
    
    def calculate_glue_up_requirements(self, part: Part, 
                                        target_strip_width: float = None) -> GlueUpPlan:
        """Calculate glue-up requirements for a part that can't be cut directly."""
        # Determine optimal strip width based on available board widths
        if target_strip_width is None:
            # Use the widest usable board width as strip width
            target_strip_width = self.max_board_width
        
        # How many strips needed to achieve part width?
        part_width = part.min_dimension  # The dimension we're gluing to achieve
        part_length = part.max_dimension  # Strip length
        
        # Account for trim after glue-up (10mm margin)
        required_width = part_width + 10
        
        strips_needed = math.ceil(required_width / target_strip_width)
        
        # Strip length needs margin for trimming
        strip_length = part_length + 10
        
        return GlueUpPlan(
            part=part,
            strip_width_mm=target_strip_width,
            strip_count=strips_needed,
            strip_length_mm=strip_length
        )
    
    def calculate_optimal_lumber(self) -> dict:
        """Calculate optimal raw lumber to buy for remaining parts."""
        lumber_opts = self.config.get('lumber_options', {})
        available_widths = lumber_opts.get('available_widths_inches', [4, 5, 6, 8, 10, 12])
        available_lengths = lumber_opts.get('available_lengths_feet', [6, 8, 10, 12])
        price_per_bf = lumber_opts.get('price_per_bf', 12.00)
        
        # Convert to mm
        widths_mm = [w * MM_PER_INCH for w in available_widths]
        lengths_mm = [l * MM_PER_FOOT for l in available_lengths]
        
        results = {
            'scenario_direct': None,  # If we buy wide enough lumber
            'scenario_glue_up': None,  # If we use narrow lumber + glue
            'recommendation': None
        }
        
        # Find minimum width needed for direct cuts
        max_part_min_dim = max(p.min_dimension for p in self.remaining_parts)
        
        # Scenario 1: Buy lumber wide enough for direct cuts
        direct_width_needed = max_part_min_dim + 20  # 20mm margin
        suitable_widths = [w for w in widths_mm if w >= direct_width_needed]
        
        if suitable_widths:
            optimal_width = min(suitable_widths)
            optimal_width_in = optimal_width / MM_PER_INCH
            
            # Calculate total length needed
            total_length_needed = sum(
                p.max_dimension + self.kerf for p in self.remaining_parts
            ) * 1.15  # 15% waste factor
            
            # Find optimal board length
            suitable_lengths = [l for l in lengths_mm if l >= total_length_needed]
            if suitable_lengths:
                optimal_length = min(suitable_lengths)
                boards_needed = 1
            else:
                optimal_length = max(lengths_mm)
                boards_needed = math.ceil(total_length_needed / optimal_length)
            
            bf_needed = (optimal_length / MM_PER_INCH * optimal_width_in * 1.0) / 144 * boards_needed
            
            results['scenario_direct'] = {
                'description': 'Buy wide lumber for direct cuts (no glue-up)',
                'board_width_mm': optimal_width,
                'board_width_inches': optimal_width_in,
                'board_length_mm': optimal_length,
                'board_length_feet': optimal_length / MM_PER_FOOT,
                'boards_needed': boards_needed,
                'board_feet': bf_needed,
                'estimated_cost': bf_needed * price_per_bf,
                'pros': ['No glue-up required', 'Faster workflow', 'Seamless panels'],
                'cons': ['Higher cost', 'Wide boards harder to find', 'More waste']
            }
        
        # Scenario 2: Use narrow lumber + glue-up
        narrow_width = 150  # Typical for 6" rough boards
        
        total_strips = 0
        total_strip_length = 0
        
        for part in self.remaining_parts:
            plan = self.calculate_glue_up_requirements(part, narrow_width)
            total_strips += plan.strip_count
            total_strip_length += plan.total_linear_mm
        
        # Calculate narrow boards needed
        board_length = max(lengths_mm)  # Use longest available
        strips_per_board = int(board_length // (max(p.max_dimension for p in self.remaining_parts) + self.kerf))
        boards_needed = math.ceil(total_strips / max(1, strips_per_board))
        
        bf_narrow = (board_length / MM_PER_INCH * narrow_width / MM_PER_INCH * 1.0) / 144 * boards_needed
        
        results['scenario_glue_up'] = {
            'description': 'Buy narrow lumber and edge-glue panels',
            'board_width_mm': narrow_width,
            'board_width_inches': narrow_width / MM_PER_INCH,
            'board_length_mm': board_length,
            'board_length_feet': board_length / MM_PER_FOOT,
            'boards_needed': boards_needed,
            'total_strips_needed': total_strips,
            'board_feet': bf_narrow,
            'estimated_cost': bf_narrow * price_per_bf,
            'pros': ['Lower material cost', 'Easier to find', 'More stable panels'],
            'cons': ['Requires glue-up time', 'More setup', 'Visible glue lines']
        }
        
        # Recommendation
        if results['scenario_direct'] and results['scenario_glue_up']:
            direct_cost = results['scenario_direct']['estimated_cost']
            glue_cost = results['scenario_glue_up']['estimated_cost']
            
            if direct_cost <= glue_cost * 1.3:  # Within 30% more expensive
                results['recommendation'] = 'direct'
                results['recommendation_reason'] = 'Wide lumber is cost-effective for this project'
            else:
                results['recommendation'] = 'glue_up'
                results['recommendation_reason'] = f'Glue-up saves ${direct_cost - glue_cost:.2f} ({((direct_cost/glue_cost)-1)*100:.0f}% savings)'
        elif results['scenario_direct']:
            results['recommendation'] = 'direct'
            results['recommendation_reason'] = 'Wide lumber available'
        else:
            results['recommendation'] = 'glue_up'
            results['recommendation_reason'] = 'Parts too wide for available lumber'
        
        return results
    
    def solve_with_inventory(self) -> List[PartSolution]:
        """Generate solutions for all parts using current inventory."""
        solutions = []
        analysis = self.analyze_part_requirements()
        
        # Track board usage
        board_remaining = {b.id: b.usable_length for b in self.boards}
        
        for part in self.remaining_parts:
            info = analysis[part.id]
            
            if info['strategy'] == CutStrategy.DIRECT:
                # Find best board for direct cut
                best_board = None
                for board_id in info['boards_that_fit']:
                    board = next(b for b in self.boards if b.id == board_id)
                    length_needed = part.max_dimension + self.kerf
                    if board_remaining[board_id] >= length_needed:
                        best_board = board_id
                        board_remaining[board_id] -= length_needed
                        break
                
                solutions.append(PartSolution(
                    part=part,
                    strategy=CutStrategy.DIRECT,
                    source_board=best_board,
                    notes=f"Cut directly from board" if best_board else "No board with space"
                ))
            
            else:  # GLUE_UP
                glue_plan = self.calculate_glue_up_requirements(part)
                
                # Assign strips to boards
                strips_assigned = 0
                for board in self.boards:
                    while (board_remaining[board.id] >= glue_plan.strip_length_mm + self.kerf 
                           and strips_assigned < glue_plan.strip_count):
                        glue_plan.source_boards.append(board.id)
                        board_remaining[board.id] -= glue_plan.strip_length_mm + self.kerf
                        strips_assigned += 1
                
                missing = glue_plan.strip_count - strips_assigned
                
                solutions.append(PartSolution(
                    part=part,
                    strategy=CutStrategy.GLUE_UP,
                    glue_up_plan=glue_plan,
                    notes=f"Need {missing} more strips" if missing > 0 else "All strips assigned"
                ))
        
        return solutions
    
    # ----------------------------------------
    # REPORTS
    # ----------------------------------------
    
    def print_full_report(self):
        """Print comprehensive project report."""
        print("=" * 70)
        print(f"  {self.config.get('project_name', 'Project').upper()} - SMART ANALYSIS")
        print("=" * 70)
        
        self._print_parts_analysis()
        self._print_inventory_analysis()
        self._print_strategy_determination()
        self._print_solutions()
        self._print_lumber_recommendations()
    
    def _print_parts_analysis(self):
        print("\n" + "─" * 70)
        print("PARTS ANALYSIS")
        print("─" * 70)
        
        print("\n┌────────────────────────────────┬───────────────┬──────────────────┐")
        print("│ Part                           │ Size (mm)     │ Min Board Width  │")
        print("├────────────────────────────────┼───────────────┼──────────────────┤")
        
        for part in self.remaining_parts:
            name = part.name[:30].ljust(30)
            size = f"{part.width_mm:.0f}×{part.length_mm:.0f}".ljust(13)
            min_w = f"{part.min_dimension:.0f}mm".ljust(16)
            print(f"│ {name} │ {size} │ {min_w} │")
        
        print("└────────────────────────────────┴───────────────┴──────────────────┘")
        
        max_needed = max(p.min_dimension for p in self.remaining_parts)
        print(f"\n   ➤ Widest board needed for direct cuts: {max_needed:.0f}mm ({max_needed/MM_PER_INCH:.1f}\")")
    
    def _print_inventory_analysis(self):
        print("\n" + "─" * 70)
        print("INVENTORY ANALYSIS")
        print("─" * 70)
        
        if not self.boards:
            print("\n   (No inventory - see lumber recommendations)")
            return
        
        print(f"\n   Max usable board width: {self.max_board_width:.0f}mm ({self.max_board_width/MM_PER_INCH:.1f}\")")
        
        print("\n   Boards:")
        for b in self.boards:
            status = "ready" if b.is_processed else "needs processing"
            print(f"   • [{b.id}] {b.length_mm:.0f}×{b.width_mm:.0f}mm "
                  f"(usable: {b.usable_length:.0f}×{b.usable_width:.0f}mm) - {status}")
    
    def _print_strategy_determination(self):
        print("\n" + "─" * 70)
        print("STRATEGY DETERMINATION")
        print("─" * 70)
        
        analysis = self.analyze_part_requirements()
        
        direct_parts = [p for p, info in analysis.items() if info['strategy'] == CutStrategy.DIRECT]
        glue_parts = [p for p, info in analysis.items() if info['strategy'] == CutStrategy.GLUE_UP]
        
        print(f"\n   Parts that can be cut DIRECTLY: {len(direct_parts)}")
        for pid in direct_parts:
            part = analysis[pid]['part']
            boards = analysis[pid]['boards_that_fit']
            print(f"   ✓ {part.name} - fits on: {', '.join(boards)}")
        
        print(f"\n   Parts that require GLUE-UP: {len(glue_parts)}")
        for pid in glue_parts:
            part = analysis[pid]['part']
            gap = analysis[pid]['width_gap_mm']
            print(f"   ⊞ {part.name} - boards are {gap:.0f}mm too narrow")
    
    def _print_solutions(self):
        print("\n" + "─" * 70)
        print("SOLUTIONS WITH CURRENT INVENTORY")
        print("─" * 70)
        
        solutions = self.solve_with_inventory()
        
        for sol in solutions:
            if sol.strategy == CutStrategy.DIRECT:
                print(f"\n   {sol.part.name}:")
                print(f"   └─ DIRECT CUT from [{sol.source_board}]")
            
            elif sol.strategy == CutStrategy.GLUE_UP:
                plan = sol.glue_up_plan
                print(f"\n   {sol.part.name}:")
                print(f"   └─ GLUE-UP: {plan.strip_count} strips × {plan.strip_width_mm:.0f}mm × {plan.strip_length_mm:.0f}mm")
                
                if plan.source_boards:
                    # Group by board
                    from collections import Counter
                    board_counts = Counter(plan.source_boards)
                    for board_id, count in board_counts.items():
                        print(f"      • {count}× from [{board_id}]")
                
                if "more strips" in sol.notes:
                    print(f"      ⚠️  {sol.notes}")
    
    def _print_lumber_recommendations(self):
        print("\n" + "─" * 70)
        print("OPTIMAL LUMBER RECOMMENDATIONS")
        print("─" * 70)
        
        lumber = self.calculate_optimal_lumber()
        
        # Scenario 1: Direct
        if lumber['scenario_direct']:
            s = lumber['scenario_direct']
            print(f"""
   OPTION A: Wide Lumber (Direct Cuts)
   ────────────────────────────────────
   Buy: {s['boards_needed']}× boards @ {s['board_width_inches']:.1f}" × {s['board_length_feet']:.0f}ft
   Board Feet: {s['board_feet']:.1f} BF
   Est. Cost: ${s['estimated_cost']:.2f}
   
   Pros: {', '.join(s['pros'])}
   Cons: {', '.join(s['cons'])}
            """)
        
        # Scenario 2: Glue-up
        if lumber['scenario_glue_up']:
            s = lumber['scenario_glue_up']
            print(f"""
   OPTION B: Narrow Lumber (Edge Glue)
   ────────────────────────────────────
   Buy: {s['boards_needed']}× boards @ {s['board_width_inches']:.1f}" × {s['board_length_feet']:.0f}ft
   Board Feet: {s['board_feet']:.1f} BF
   Est. Cost: ${s['estimated_cost']:.2f}
   Strips needed: {s['total_strips_needed']}
   
   Pros: {', '.join(s['pros'])}
   Cons: {', '.join(s['cons'])}
            """)
        
        # Recommendation
        print(f"""
   ═══════════════════════════════════════════════════════════════════
   RECOMMENDATION: {"WIDE LUMBER" if lumber['recommendation'] == 'direct' else "NARROW + GLUE-UP"}
   Reason: {lumber['recommendation_reason']}
   ═══════════════════════════════════════════════════════════════════
        """)


# ============================================
# MAIN
# ============================================

def main():
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        script_dir = Path(__file__).parent
        config_path = script_dir / "project_config_v2.json"
    
    if not Path(config_path).exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)
    
    calc = SmartCalculator(str(config_path))
    calc.print_full_report()


if __name__ == "__main__":
    main()




