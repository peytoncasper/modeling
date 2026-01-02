#!/usr/bin/env python3
"""
Save search results to JSON
"""

import json
from pathlib import Path
from datetime import datetime

def save_search_result(search_term, products, total_listings):
    """Save search results to JSON file"""
    output_dir = Path("data/raw") / datetime.now().strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    safe_term = "".join(c for c in search_term if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_term = safe_term.replace(' ', '-')
    filename = f"{safe_term}.json"
    filepath = output_dir / filename
    
    data = {
        "search_term": search_term,
        "total_listings": total_listings,
        "top_sellers": products,
        "metadata": {
            "collected_at": datetime.now().isoformat(),
            "source": "Everbee Product Analytics",
            "session_id": "everbee-collection-2024"
        }
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"  ✓ Saved: {filepath}")
    return filepath





