#!/usr/bin/env python3
"""
Gap Analysis - Identify Missing Product Categories
"""

import json
from pathlib import Path
from collections import defaultdict


def analyze_coverage():
    """Analyze what we've covered and identify gaps"""
    
    # Load existing data
    with open('broad-product-research.json', 'r') as f:
        data = json.load(f)
    
    # Extract all search terms we've covered
    covered_terms = set()
    covered_categories = set()
    
    # From product_categories
    if 'product_categories' in data:
        for cat_key, cat_data in data['product_categories'].items():
            covered_categories.add(cat_key)
            if 'subcategories' in cat_data:
                for subcat_key, subcat_data in cat_data['subcategories'].items():
                    if 'search_term' in subcat_data:
                        covered_terms.add(subcat_data['search_term'].lower())
    
    # From branch_categories
    if 'branch_categories' in data:
        for cat_key, cat_data in data['branch_categories'].items():
            covered_categories.add(cat_key)
            if 'search_term' in cat_data:
                covered_terms.add(cat_data['search_term'].lower())
    
    # Define comprehensive product areas
    all_areas = {
        'materials': ['wood', '3d printed', 'resin', 'epoxy', 'cnc', 'laser cut'],
        'categories': [
            'desk', 'kitchen', 'gaming', 'tech', 'home decor', 'office',
            'bathroom', 'outdoor', 'storage', 'organization', 'gift',
            'nursery', 'pet', 'garden', 'workshop', 'bedroom', 'living room'
        ],
        'product_types': [
            'stand', 'organizer', 'box', 'tray', 'holder', 'shelf',
            'rack', 'display', 'case', 'board', 'sign', 'lamp',
            'coaster', 'planter', 'frame', 'hanger', 'hook', 'basket'
        ],
        'specific_products': [
            'cutting board', 'serving board', 'spice rack', 'watch box',
            'jewelry box', 'phone stand', 'laptop stand', 'monitor riser',
            'headphone stand', 'controller stand', 'keyboard stand',
            'cable management', 'valet tray', 'utensil holder',
            'wine rack', 'bookend', 'picture frame', 'floating shelf',
            'plant stand', 'wall art', 'name sign', 'pet urn',
            'birdhouse', 'soap dispenser', 'toothbrush holder',
            'towel rack', 'shower caddy', 'garden planter',
            'tool holder', 'pegboard', 'workshop organizer',
            'kids toy', 'nursery decor', 'growth chart',
            'holiday decor', 'christmas', 'wedding gift'
        ]
    }
    
    # Identify gaps
    gaps = {
        'missing_materials': [],
        'missing_categories': [],
        'missing_product_types': [],
        'missing_specific_products': [],
        'recommended_searches': []
    }
    
    # Check material coverage
    for material in all_areas['materials']:
        found = any(material in term for term in covered_terms)
        if not found and material not in ['wood', '3d printed', 'resin', 'cnc']:
            gaps['missing_materials'].append(material)
    
    # Check category coverage
    for category in all_areas['categories']:
        found = any(category in term for term in covered_terms)
        if not found:
            gaps['missing_categories'].append(category)
    
    # Check product type coverage
    for ptype in all_areas['product_types']:
        found = any(ptype in term for term in covered_terms)
        if not found:
            gaps['missing_product_types'].append(ptype)
    
    # Check specific product coverage
    for product in all_areas['specific_products']:
        found = any(product in term for term in covered_terms)
        if not found:
            gaps['missing_specific_products'].append(product)
    
    # Generate recommended searches to fill gaps
    high_priority_gaps = [
        'wine rack', 'bookend', 'picture frame', 'floating shelf',
        'plant stand', 'towel rack', 'shower caddy', 'garden planter',
        'tool holder', 'pegboard', 'workshop organizer', 'kids toy',
        'nursery decor', 'growth chart', 'holiday decor'
    ]
    
    for gap in high_priority_gaps:
        gaps['recommended_searches'].extend([
            f"wood {gap}",
            f"cnc {gap}",
            f"custom {gap}",
            f"personalized {gap}"
        ])
    
    # Add material + category combinations we're missing
    missing_combos = []
    for material in ['wood', 'cnc', 'laser cut']:
        for category in gaps['missing_categories'][:5]:  # Top 5 missing
            missing_combos.append(f"{material} {category}")
    
    gaps['recommended_searches'].extend(missing_combos)
    
    return {
        'covered_terms': list(covered_terms),
        'covered_categories': list(covered_categories),
        'gaps': gaps,
        'total_covered': len(covered_terms),
        'total_gaps': len(gaps['recommended_searches'])
    }


def main():
    """Run gap analysis"""
    print("=" * 70)
    print("Product Research Gap Analysis")
    print("=" * 70)
    
    analysis = analyze_coverage()
    
    print(f"\nCurrent Coverage:")
    print(f"  Search Terms Covered: {analysis['total_covered']}")
    print(f"  Categories Covered: {len(analysis['covered_categories'])}")
    
    print(f"\nCovered Categories:")
    for cat in sorted(analysis['covered_categories']):
        print(f"  - {cat}")
    
    print(f"\n{'='*70}")
    print("IDENTIFIED GAPS")
    print("=" * 70)
    
    gaps = analysis['gaps']
    
    print(f"\nMissing Categories ({len(gaps['missing_categories'])}):")
    for cat in gaps['missing_categories'][:10]:
        print(f"  - {cat}")
    
    print(f"\nMissing Product Types ({len(gaps['missing_product_types'])}):")
    for ptype in gaps['missing_product_types'][:10]:
        print(f"  - {ptype}")
    
    print(f"\nMissing Specific Products ({len(gaps['missing_specific_products'])}):")
    for product in gaps['missing_specific_products'][:15]:
        print(f"  - {product}")
    
    print(f"\n{'='*70}")
    print(f"RECOMMENDED SEARCHES TO FILL GAPS")
    print("=" * 70)
    print(f"Total Recommended: {len(gaps['recommended_searches'])} searches")
    
    # Save recommended searches
    output = {
        'analysis_date': '2024-12-31',
        'coverage_summary': {
            'total_covered': analysis['total_covered'],
            'categories_covered': len(analysis['covered_categories'])
        },
        'gaps': gaps,
        'recommended_searches': gaps['recommended_searches'][:50]  # Top 50
    }
    
    with open('gap_analysis_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nTop 30 Recommended Searches:")
    for i, search in enumerate(gaps['recommended_searches'][:30], 1):
        print(f"  {i:2d}. {search}")
    
    print(f"\nFull list saved to: gap_analysis_results.json")


if __name__ == "__main__":
    main()





