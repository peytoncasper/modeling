#!/usr/bin/env python3
"""
Run Product Analysis on Existing Research Data
Tests scoring system and generates reports
"""

import json
from pathlib import Path
from product_scoring import ProductScorer, ProductData, ProductAnalyzer
from datetime import datetime


def load_broad_research_data(filepath: str) -> list:
    """Load products from broad-product-research.json"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    products = []
    
    # Extract products from all categories
    if 'product_categories' in data:
        for category_key, category_data in data['product_categories'].items():
            if 'subcategories' in category_data:
                for subcat_key, subcat_data in category_data['subcategories'].items():
                    if 'top_sellers' in subcat_data:
                        for seller in subcat_data['top_sellers']:
                            try:
                                # Determine manufacturing method from category
                                manufacturing_method = None
                                if 'cnc' in category_key or 'laser' in category_key:
                                    manufacturing_method = "CNC/Laser"
                                elif '3d' in category_key:
                                    manufacturing_method = "3D Printed"
                                elif 'resin' in category_key:
                                    manufacturing_method = "Resin/Epoxy"
                                else:
                                    manufacturing_method = "Wood"
                                
                                product = ProductData(
                                    search_term=f"{category_key} {subcat_key}",
                                    shop=seller.get('shop', ''),
                                    product=seller.get('product', '')[:100],  # Truncate long names
                                    price=float(seller.get('price', 0)),
                                    monthly_sales=int(seller.get('monthly_sales', 0)),
                                    monthly_revenue=float(seller.get('monthly_revenue', 0)),
                                    growth_rate=str(seller.get('growth_rate', '0%')),
                                    total_sales=int(seller.get('total_sales', 0)),
                                    reviews=int(seller.get('reviews', 0)),
                                    listing_age_months=int(seller.get('listing_age_months', 0)),
                                    total_listings=subcat_data.get('total_listings', 0),
                                    manufacturing_method=manufacturing_method,
                                    complexity="Medium",  # Default
                                    estimated_cogs=None,
                                    estimated_margin=None,
                                    production_time_minutes=None
                                )
                                products.append(product)
                            except (ValueError, KeyError) as e:
                                print(f"Error parsing product: {e}")
                                continue
    
    # Extract from branch categories
    if 'branch_categories' in data:
        for category_key, category_data in data['branch_categories'].items():
            if 'top_sellers' in category_data:
                for seller in category_data['top_sellers']:
                    try:
                        manufacturing_method = "Wood"  # Most branch categories are wood
                        if 'magsafe' in category_key or 'wireless' in category_key:
                            manufacturing_method = "Wood + Electronics"
                        
                        product = ProductData(
                            search_term=category_data.get('search_term', category_key),
                            shop=seller.get('shop', ''),
                            product=seller.get('product', '')[:100],
                            price=float(seller.get('price', 0)),
                            monthly_sales=int(seller.get('monthly_sales', 0)),
                            monthly_revenue=float(seller.get('monthly_revenue', 0)),
                            growth_rate=str(seller.get('growth_rate', '0%')),
                            total_sales=int(seller.get('total_sales', 0)),
                            reviews=int(seller.get('reviews', 0)),
                            listing_age_months=int(seller.get('listing_age_months', 0)),
                            total_listings=category_data.get('total_listings', 0),
                            manufacturing_method=manufacturing_method,
                            complexity="Medium",
                            estimated_cogs=None,
                            estimated_margin=None,
                            production_time_minutes=None
                        )
                        products.append(product)
                    except (ValueError, KeyError) as e:
                        print(f"Error parsing branch product: {e}")
                        continue
    
    return products


def main():
    """Run analysis on existing research data"""
    print("=" * 70)
    print("Product Analysis - Scoring Existing Research Data")
    print("=" * 70)
    
    # Initialize
    scorer = ProductScorer(available_tools=['ShopBot', 'CNC'])
    analyzer = ProductAnalyzer(scorer)
    
    # Load data
    data_file = Path("broad-product-research.json")
    if not data_file.exists():
        print(f"Error: {data_file} not found")
        return
    
    print(f"\nLoading data from {data_file}...")
    products = load_broad_research_data(str(data_file))
    print(f"Loaded {len(products)} products")
    
    # Score and rank
    print("\nScoring products...")
    scored_products = analyzer.score_and_rank_products(products)
    
    # Generate report
    print("\nGenerating report...")
    report_file = f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report = analyzer.generate_report(scored_products, report_file)
    print(f"Report saved to: {report_file}")
    
    # Export JSON
    json_file = f"scored_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    analyzer.export_to_json(scored_products, json_file)
    print(f"JSON data saved to: {json_file}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("TOP 10 OPPORTUNITIES")
    print("=" * 70)
    print(f"{'Rank':<6} {'Score':<8} {'Product':<50} {'Revenue':<12} {'Sales':<8}")
    print("-" * 70)
    
    for i, score in enumerate(scored_products[:10], 1):
        product = score.product_data
        print(f"{i:<6} {score.opportunity_score:<8.1f} {product.product[:48]:<50} "
              f"${product.monthly_revenue:>10,.0f} {product.monthly_sales:>6}")
    
    # Statistics
    print("\n" + "=" * 70)
    print("STATISTICS")
    print("=" * 70)
    print(f"Total Products Analyzed: {len(scored_products)}")
    print(f"Products Scoring >80: {sum(1 for s in scored_products if s.opportunity_score > 80)}")
    print(f"Products Scoring >70: {sum(1 for s in scored_products if s.opportunity_score > 70)}")
    print(f"Products Scoring >60: {sum(1 for s in scored_products if s.opportunity_score > 60)}")
    print(f"Average Score: {sum(s.opportunity_score for s in scored_products) / len(scored_products):.1f}")
    print(f"Highest Score: {scored_products[0].opportunity_score:.1f}")
    print(f"Lowest Score: {scored_products[-1].opportunity_score:.1f}")
    
    # Category breakdown
    categories = {}
    for score in scored_products:
        category = score.product_data.search_term.split()[0] if score.product_data.search_term else "Unknown"
        if category not in categories:
            categories[category] = []
        categories[category].append(score)
    
    print("\n" + "=" * 70)
    print("TOP CATEGORIES BY AVERAGE SCORE")
    print("=" * 70)
    category_avg = [(cat, sum(s.opportunity_score for s in scores) / len(scores), len(scores))
                    for cat, scores in categories.items()]
    category_avg.sort(key=lambda x: x[1], reverse=True)
    
    print(f"{'Category':<20} {'Avg Score':<12} {'Count':<8}")
    print("-" * 70)
    for cat, avg_score, count in category_avg[:10]:
        print(f"{cat[:18]:<20} {avg_score:<12.1f} {count:<8}")


if __name__ == "__main__":
    main()





