#!/usr/bin/env python3
"""
Process All Research Data - Comprehensive Analysis
Merges all data sources and creates final analysis
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def load_all_data():
    """Load all research data"""
    # Existing research
    with open('broad-product-research.json', 'r') as f:
        existing = json.load(f)
    
    # Gap searches
    gap_dir = Path('data/raw/2026-01-01')
    gap_searches = {}
    
    if gap_dir.exists():
        for json_file in gap_dir.glob('*.json'):
            if json_file.name == 'progress.json':
                continue
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    search_term = data.get('search_term', '')
                    if search_term:
                        gap_searches[search_term] = {
                            'total_listings': data.get('total_listings', 0),
                            'collected_at': data.get('metadata', {}).get('collected_at', '')
                        }
            except:
                continue
    
    # Existing products
    existing_products = []
    if 'product_categories' in existing:
        for cat_key, cat_data in existing['product_categories'].items():
            if 'subcategories' in cat_data:
                for subcat_key, subcat_data in cat_data['subcategories'].items():
                    if 'top_sellers' in subcat_data:
                        for seller in subcat_data['top_sellers']:
                            seller['search_term'] = subcat_data.get('search_term', '')
                            seller['category'] = cat_key
                            seller['subcategory'] = subcat_key
                            seller['total_listings'] = subcat_data.get('total_listings', 0)
                            existing_products.append(seller)
    
    if 'branch_categories' in existing:
        for cat_key, cat_data in existing['branch_categories'].items():
            if 'top_sellers' in cat_data:
                for seller in cat_data['top_sellers']:
                    seller['search_term'] = cat_data.get('search_term', cat_key)
                    seller['category'] = 'branch'
                    seller['subcategory'] = cat_key
                    seller['total_listings'] = cat_data.get('total_listings', 0)
                    existing_products.append(seller)
    
    return existing_products, gap_searches

def analyze_opportunities(existing_products, gap_searches):
    """Analyze and rank opportunities"""
    
    # Filter products with active sales
    active_products = [
        p for p in existing_products 
        if p.get('monthly_sales', 0) > 0 and p.get('monthly_revenue', 0) > 0
    ]
    
    # Sort by revenue
    active_products.sort(key=lambda x: x.get('monthly_revenue', 0), reverse=True)
    
    # Categorize gap searches
    low_comp = []
    med_comp = []
    high_comp = []
    
    for search_term, data in gap_searches.items():
        listings = data['total_listings']
        if listings < 500:
            low_comp.append({'search_term': search_term, 'listings': listings})
        elif listings < 5000:
            med_comp.append({'search_term': search_term, 'listings': listings})
        else:
            high_comp.append({'search_term': search_term, 'listings': listings})
    
    low_comp.sort(key=lambda x: x['listings'])
    med_comp.sort(key=lambda x: x['listings'])
    
    return {
        'top_revenue_products': active_products[:30],
        'low_competition_searches': low_comp[:20],
        'medium_competition_searches': med_comp[:20],
        'total_products_analyzed': len(existing_products),
        'active_products': len(active_products),
        'total_gap_searches': len(gap_searches),
        'processed_at': datetime.now().isoformat()
    }

def generate_report(analysis):
    """Generate markdown report"""
    report = []
    report.append("# Complete Research Data Analysis")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n## Summary Statistics")
    report.append(f"- Total Products Analyzed: {analysis['total_products_analyzed']}")
    report.append(f"- Products with Active Sales: {analysis['active_products']}")
    report.append(f"- Gap Searches Completed: {analysis['total_gap_searches']}")
    
    report.append(f"\n## Top 20 Products by Monthly Revenue")
    report.append("\n| Rank | Product | Shop | Sales/Mo | Revenue/Mo | Price |")
    report.append("|------|---------|------|----------|-------------|-------|")
    
    for i, product in enumerate(analysis['top_revenue_products'][:20], 1):
        name = product.get('product', '')[:50]
        shop = product.get('shop', '')[:20]
        sales = product.get('monthly_sales', 0)
        revenue = product.get('monthly_revenue', 0)
        price = product.get('price', 0)
        report.append(f"| {i} | {name} | {shop} | {sales} | ${revenue:,.0f} | ${price:.2f} |")
    
    report.append(f"\n## Low Competition Opportunities (<500 listings)")
    report.append("\n| Rank | Search Term | Listings |")
    report.append("|------|-------------|----------|")
    
    for i, search in enumerate(analysis['low_competition_searches'][:20], 1):
        term = search['search_term']
        listings = search['listings']
        report.append(f"| {i} | {term} | {listings:,} |")
    
    report.append(f"\n## Medium Competition Opportunities (500-5000 listings)")
    report.append("\n| Rank | Search Term | Listings |")
    report.append("|------|-------------|----------|")
    
    for i, search in enumerate(analysis['medium_competition_searches'][:20], 1):
        term = search['search_term']
        listings = search['listings']
        report.append(f"| {i} | {term} | {listings:,} |")
    
    return "\n".join(report)

def main():
    """Main processing function"""
    print("=" * 70)
    print("PROCESSING ALL RESEARCH DATA")
    print("=" * 70)
    
    # Load data
    print("\n1. Loading all data...")
    existing_products, gap_searches = load_all_data()
    print(f"   ✓ Loaded {len(existing_products)} existing products")
    print(f"   ✓ Loaded {len(gap_searches)} gap searches")
    
    # Analyze
    print("\n2. Analyzing opportunities...")
    analysis = analyze_opportunities(existing_products, gap_searches)
    print(f"   ✓ Found {analysis['active_products']} products with active sales")
    print(f"   ✓ Identified {len(analysis['low_competition_searches'])} low competition opportunities")
    
    # Save analysis
    print("\n3. Saving analysis...")
    with open('complete_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2)
    print("   ✓ Saved to: complete_analysis.json")
    
    # Generate report
    print("\n4. Generating report...")
    report = generate_report(analysis)
    report_file = f"complete_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"   ✓ Saved to: {report_file}")
    
    print("\n" + "=" * 70)
    print("✅ PROCESSING COMPLETE")
    print("=" * 70)
    print(f"\nTop 5 Products by Revenue:")
    for i, product in enumerate(analysis['top_revenue_products'][:5], 1):
        print(f"  {i}. {product.get('product', '')[:50]}")
        print(f"     ${product.get('monthly_revenue', 0):,.0f}/month, {product.get('monthly_sales', 0)} sales")

if __name__ == "__main__":
    main()





