#!/usr/bin/env python3
"""
Generate Search Term Batch
Creates systematic search terms for data collection
"""

import json
from datetime import datetime
from collect_product_data import SearchTermGenerator


def generate_all_search_terms():
    """Generate comprehensive search term list"""
    generator = SearchTermGenerator()
    
    all_searches = {
        "broad_category": generator.generate_broad_searches(),
        "niche_trending": generator.generate_niche_searches(),
        "timestamp": datetime.now().isoformat()
    }
    
    # Add specific variations
    high_priority_base_terms = [
        "gaming controller stand",
        "phone stand",
        "cutting board",
        "watch box",
        "desk organizer",
        "spice rack",
        "laptop stand",
        "headphone stand",
        "monitor riser",
        "valet tray"
    ]
    
    specific_variations = []
    for base_term in high_priority_base_terms:
        variations = generator.generate_specific_searches(base_term)
        specific_variations.extend(variations)
    
    all_searches["specific_variations"] = specific_variations
    all_searches["total_count"] = (
        len(all_searches["broad_category"]) +
        len(all_searches["niche_trending"]) +
        len(all_searches["specific_variations"])
    )
    
    return all_searches


def main():
    """Generate and save search terms"""
    print("Generating Search Term Batch...")
    
    searches = generate_all_search_terms()
    
    # Save to JSON
    output_file = f"search_terms_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(searches, f, indent=2)
    
    print(f"\nSearch terms saved to: {output_file}")
    print(f"\nSummary:")
    print(f"  Broad Category: {len(searches['broad_category'])} searches")
    print(f"  Niche/Trending: {len(searches['niche_trending'])} searches")
    print(f"  Specific Variations: {len(searches['specific_variations'])} searches")
    print(f"  Total: {searches['total_count']} searches")
    
    # Print first 20 for preview
    print(f"\nPreview (first 20 broad category searches):")
    for i, term in enumerate(searches['broad_category'][:20], 1):
        print(f"  {i:2d}. {term}")
    
    # Print all search terms in a simple list format
    all_terms_file = f"search_terms_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(all_terms_file, 'w') as f:
        f.write("SEARCH TERMS FOR DATA COLLECTION\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("BROAD CATEGORY SEARCHES\n")
        f.write("-" * 50 + "\n")
        for term in searches['broad_category']:
            f.write(f"{term}\n")
        
        f.write("\n\nNICHE/TRENDING SEARCHES\n")
        f.write("-" * 50 + "\n")
        for term in searches['niche_trending']:
            f.write(f"{term}\n")
        
        f.write("\n\nSPECIFIC VARIATIONS\n")
        f.write("-" * 50 + "\n")
        for term in searches['specific_variations']:
            f.write(f"{term}\n")
    
    print(f"\nFull list saved to: {all_terms_file}")


if __name__ == "__main__":
    main()





