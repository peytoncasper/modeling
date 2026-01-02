#!/usr/bin/env python3
"""
Product Opportunity Scoring System
Automated scoring and ranking of product opportunities from Everbee data
"""

import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ProductData:
    """Product data structure"""
    search_term: str
    shop: str
    product: str
    price: float
    monthly_sales: int
    monthly_revenue: float
    growth_rate: str
    total_sales: int
    reviews: int
    listing_age_months: int
    total_listings: int
    manufacturing_method: Optional[str] = None
    complexity: Optional[str] = None
    estimated_cogs: Optional[float] = None
    estimated_margin: Optional[float] = None
    production_time_minutes: Optional[int] = None


@dataclass
class ProductScore:
    """Scoring breakdown"""
    product_data: ProductData
    market_score: float
    feasibility_score: float
    profitability_score: float
    opportunity_score: float
    revenue_potential_score: float
    growth_rate_score: float
    competition_score: float
    tool_compatibility_score: float
    margin_score: float
    volume_score: float
    time_efficiency_score: float


class ProductScorer:
    """Calculate opportunity scores for products"""
    
    def __init__(self, available_tools: List[str] = None):
        self.available_tools = available_tools or ['ShopBot', 'CNC']
    
    def parse_growth_rate(self, growth_rate_str: str) -> float:
        """Parse growth rate string to number"""
        if not growth_rate_str or growth_rate_str == "0%":
            return 0.0
        
        # Extract number from string like "500%", "100%", etc.
        match = re.search(r'(\d+)%', str(growth_rate_str))
        if match:
            return float(match.group(1))
        return 0.0
    
    def calculate_revenue_potential_score(self, monthly_revenue: float) -> float:
        """Calculate revenue potential score (0-100)"""
        if monthly_revenue >= 50000:
            return 100.0
        elif monthly_revenue >= 20000:
            return 80.0
        elif monthly_revenue >= 10000:
            return 60.0
        elif monthly_revenue >= 5000:
            return 40.0
        elif monthly_revenue >= 2000:
            return 20.0
        else:
            return 10.0
    
    def calculate_growth_rate_score(self, growth_rate_str: str) -> float:
        """Calculate growth rate score (0-100)"""
        growth_rate = self.parse_growth_rate(growth_rate_str)
        
        if growth_rate >= 500:
            return 100.0
        elif growth_rate >= 300:
            return 80.0
        elif growth_rate >= 200:
            return 60.0
        elif growth_rate >= 100:
            return 40.0
        elif growth_rate >= 50:
            return 20.0
        else:
            return 10.0
    
    def calculate_competition_score(self, total_listings: int) -> float:
        """Calculate competition advantage score (0-100)"""
        if total_listings < 500:
            return 100.0
        elif total_listings < 1000:
            return 80.0
        elif total_listings < 2500:
            return 60.0
        elif total_listings < 5000:
            return 40.0
        elif total_listings < 10000:
            return 20.0
        else:
            return 10.0
    
    def calculate_tool_compatibility_score(self, manufacturing_method: str) -> float:
        """Calculate tool compatibility score (0-100)"""
        method_lower = (manufacturing_method or "").lower()
        
        if 'cnc' in method_lower or 'shopbot' in method_lower:
            return 100.0
        elif 'laser' in method_lower:
            return 80.0
        elif '3d' in method_lower or 'print' in method_lower:
            return 60.0
        elif 'hand' in method_lower or 'traditional' in method_lower:
            return 40.0
        else:
            # Default to CNC if wood product
            return 100.0
    
    def calculate_margin_score(self, price: float, estimated_cogs: Optional[float] = None) -> float:
        """Calculate margin potential score (0-100)"""
        if estimated_cogs:
            margin_pct = ((price - estimated_cogs) / price) * 100
        else:
            # Estimate based on price point (rough heuristic)
            if price > 200:
                margin_pct = 50  # Premium products typically higher margin
            elif price > 100:
                margin_pct = 40
            elif price > 50:
                margin_pct = 30
            else:
                margin_pct = 25
        
        if margin_pct >= 50:
            return 100.0
        elif margin_pct >= 40:
            return 80.0
        elif margin_pct >= 30:
            return 60.0
        elif margin_pct >= 20:
            return 40.0
        else:
            return 20.0
    
    def calculate_volume_score(self, monthly_sales: int) -> float:
        """Calculate volume potential score (0-100)"""
        if monthly_sales >= 500:
            return 100.0
        elif monthly_sales >= 200:
            return 80.0
        elif monthly_sales >= 100:
            return 60.0
        elif monthly_sales >= 50:
            return 40.0
        elif monthly_sales >= 20:
            return 20.0
        else:
            return 10.0
    
    def calculate_time_efficiency_score(self, production_time_minutes: Optional[int] = None) -> float:
        """Calculate time efficiency score (0-100)"""
        if production_time_minutes is None:
            return 60.0  # Default medium score
        
        if production_time_minutes < 15:
            return 100.0
        elif production_time_minutes < 30:
            return 80.0
        elif production_time_minutes < 60:
            return 60.0
        elif production_time_minutes < 120:
            return 40.0
        else:
            return 20.0
    
    def calculate_market_score(self, product: ProductData) -> float:
        """Calculate market score (0-100)"""
        revenue_score = self.calculate_revenue_potential_score(product.monthly_revenue)
        growth_score = self.calculate_growth_rate_score(product.growth_rate)
        competition_score = self.calculate_competition_score(product.total_listings)
        
        return (revenue_score * 0.4) + (growth_score * 0.3) + (competition_score * 0.3)
    
    def calculate_feasibility_score(self, product: ProductData) -> float:
        """Calculate feasibility score (0-100)"""
        tool_score = self.calculate_tool_compatibility_score(product.manufacturing_method)
        skill_score = 80.0  # Default - adjust based on complexity
        material_score = 80.0  # Default - assume materials available
        time_score = self.calculate_time_efficiency_score(product.production_time_minutes)
        
        return (tool_score * 0.3) + (skill_score * 0.3) + (material_score * 0.2) + (time_score * 0.2)
    
    def calculate_profitability_score(self, product: ProductData) -> float:
        """Calculate profitability score (0-100)"""
        margin_score = self.calculate_margin_score(product.price, product.estimated_cogs)
        volume_score = self.calculate_volume_score(product.monthly_sales)
        time_score = self.calculate_time_efficiency_score(product.production_time_minutes)
        
        return (margin_score * 0.4) + (volume_score * 0.3) + (time_score * 0.3)
    
    def score_product(self, product: ProductData) -> ProductScore:
        """Calculate complete opportunity score for a product"""
        market_score = self.calculate_market_score(product)
        feasibility_score = self.calculate_feasibility_score(product)
        profitability_score = self.calculate_profitability_score(product)
        
        opportunity_score = (market_score * 0.4) + (feasibility_score * 0.3) + (profitability_score * 0.3)
        
        return ProductScore(
            product_data=product,
            market_score=market_score,
            feasibility_score=feasibility_score,
            profitability_score=profitability_score,
            opportunity_score=opportunity_score,
            revenue_potential_score=self.calculate_revenue_potential_score(product.monthly_revenue),
            growth_rate_score=self.calculate_growth_rate_score(product.growth_rate),
            competition_score=self.calculate_competition_score(product.total_listings),
            tool_compatibility_score=self.calculate_tool_compatibility_score(product.manufacturing_method),
            margin_score=self.calculate_margin_score(product.price, product.estimated_cogs),
            volume_score=self.calculate_volume_score(product.monthly_sales),
            time_efficiency_score=self.calculate_time_efficiency_score(product.production_time_minutes)
        )


class ProductAnalyzer:
    """Analyze and rank products"""
    
    def __init__(self, scorer: ProductScorer):
        self.scorer = scorer
    
    def load_products_from_json(self, filepath: str) -> List[ProductData]:
        """Load products from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        products = []
        
        # Handle different JSON structures
        if 'top_sellers' in data:
            sellers = data['top_sellers']
        elif isinstance(data, list):
            sellers = data
        else:
            sellers = []
        
        for seller in sellers:
            try:
                product = ProductData(
                    search_term=data.get('search_term', ''),
                    shop=seller.get('shop', ''),
                    product=seller.get('product', ''),
                    price=float(seller.get('price', 0)),
                    monthly_sales=int(seller.get('monthly_sales', 0)),
                    monthly_revenue=float(seller.get('monthly_revenue', 0)),
                    growth_rate=str(seller.get('growth_rate', '0%')),
                    total_sales=int(seller.get('total_sales', 0)),
                    reviews=int(seller.get('reviews', 0)),
                    listing_age_months=int(seller.get('listing_age_months', 0)),
                    total_listings=data.get('total_listings', 0),
                    manufacturing_method=seller.get('manufacturing_method'),
                    complexity=seller.get('complexity'),
                    estimated_cogs=seller.get('estimated_cogs'),
                    estimated_margin=seller.get('estimated_margin'),
                    production_time_minutes=seller.get('production_time_minutes')
                )
                products.append(product)
            except (ValueError, KeyError) as e:
                print(f"Error parsing product: {e}")
                continue
        
        return products
    
    def score_and_rank_products(self, products: List[ProductData]) -> List[ProductScore]:
        """Score and rank all products"""
        scored_products = []
        
        for product in products:
            score = self.scorer.score_product(product)
            scored_products.append(score)
        
        # Sort by opportunity score (descending)
        scored_products.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        return scored_products
    
    def generate_report(self, scored_products: List[ProductScore], output_file: str = None):
        """Generate analysis report"""
        report_lines = []
        report_lines.append("# Product Opportunity Analysis Report")
        report_lines.append(f"Generated: {datetime.now().isoformat()}")
        report_lines.append(f"Total Products Analyzed: {len(scored_products)}\n")
        
        # Top 20 Opportunities
        report_lines.append("## Top 20 Opportunities\n")
        report_lines.append("| Rank | Product | Shop | Price | Monthly Sales | Revenue | Opportunity Score |")
        report_lines.append("|------|---------|------|-------|---------------|---------|-------------------|")
        
        for i, score in enumerate(scored_products[:20], 1):
            product = score.product_data
            report_lines.append(
                f"| {i} | {product.product[:50]} | {product.shop[:20]} | ${product.price:.2f} | "
                f"{product.monthly_sales} | ${product.monthly_revenue:,.0f} | {score.opportunity_score:.1f} |"
            )
        
        # Score Breakdown for Top 10
        report_lines.append("\n## Score Breakdown - Top 10\n")
        report_lines.append("| Rank | Product | Market | Feasibility | Profitability | Opportunity |")
        report_lines.append("|------|---------|--------|-------------|--------------|-------------|")
        
        for i, score in enumerate(scored_products[:10], 1):
            product = score.product_data
            report_lines.append(
                f"| {i} | {product.product[:40]} | {score.market_score:.1f} | "
                f"{score.feasibility_score:.1f} | {score.profitability_score:.1f} | {score.opportunity_score:.1f} |"
            )
        
        # Category Summary
        report_lines.append("\n## Category Summary\n")
        categories = {}
        for score in scored_products:
            category = score.product_data.search_term.split()[0] if score.product_data.search_term else "Unknown"
            if category not in categories:
                categories[category] = []
            categories[category].append(score)
        
        for category, scores in sorted(categories.items(), key=lambda x: len(x[1]), reverse=True):
            avg_score = sum(s.opportunity_score for s in scores) / len(scores)
            report_lines.append(f"- **{category}**: {len(scores)} products, Avg Score: {avg_score:.1f}")
        
        report_text = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
        
        return report_text
    
    def export_to_json(self, scored_products: List[ProductScore], output_file: str):
        """Export scored products to JSON"""
        data = {
            "generated": datetime.now().isoformat(),
            "total_products": len(scored_products),
            "products": []
        }
        
        for score in scored_products:
            product_dict = {
                "product_data": asdict(score.product_data),
                "scores": {
                    "opportunity_score": score.opportunity_score,
                    "market_score": score.market_score,
                    "feasibility_score": score.feasibility_score,
                    "profitability_score": score.profitability_score,
                    "revenue_potential_score": score.revenue_potential_score,
                    "growth_rate_score": score.growth_rate_score,
                    "competition_score": score.competition_score,
                    "tool_compatibility_score": score.tool_compatibility_score,
                    "margin_score": score.margin_score,
                    "volume_score": score.volume_score,
                    "time_efficiency_score": score.time_efficiency_score
                }
            }
            data["products"].append(product_dict)
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)


def main():
    """Example usage"""
    # Initialize scorer
    scorer = ProductScorer(available_tools=['ShopBot', 'CNC'])
    analyzer = ProductAnalyzer(scorer)
    
    # Example: Load from existing JSON file
    # products = analyzer.load_products_from_json('data/raw/wood-gaming-controller-stand.json')
    
    # Example: Create sample product
    sample_product = ProductData(
        search_term="wood gaming controller stand",
        shop="LampByGift",
        product="Personalized Gaming Controller and Headphone Stand",
        price=61.99,
        monthly_sales=227,
        monthly_revenue=14072.0,
        growth_rate="500%",
        total_sales=1861,
        reviews=277,
        listing_age_months=13,
        total_listings=6540,
        manufacturing_method="CNC Wood",
        complexity="Medium",
        estimated_cogs=25.0,
        estimated_margin=60.0,
        production_time_minutes=30
    )
    
    # Score the product
    score = scorer.score_product(sample_product)
    
    print(f"Product: {sample_product.product}")
    print(f"Opportunity Score: {score.opportunity_score:.1f}")
    print(f"  Market Score: {score.market_score:.1f}")
    print(f"  Feasibility Score: {score.feasibility_score:.1f}")
    print(f"  Profitability Score: {score.profitability_score:.1f}")
    print(f"\nBreakdown:")
    print(f"  Revenue Potential: {score.revenue_potential_score:.1f}")
    print(f"  Growth Rate: {score.growth_rate_score:.1f}")
    print(f"  Competition: {score.competition_score:.1f}")
    print(f"  Tool Compatibility: {score.tool_compatibility_score:.1f}")
    print(f"  Margin: {score.margin_score:.1f}")
    print(f"  Volume: {score.volume_score:.1f}")
    print(f"  Time Efficiency: {score.time_efficiency_score:.1f}")


if __name__ == "__main__":
    main()





