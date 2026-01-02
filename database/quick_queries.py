#!/usr/bin/env python3
"""
Quick query scripts for common analyses.
Run specific queries without interactive menu.
"""

import sys
from query_database import ProductQuery


def print_header(title):
    print("\n" + "=" * 80)
    print(f"📊 {title}")
    print("=" * 80 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 quick_queries.py <query_name>")
        print("\nAvailable queries:")
        print("  top_revenue       - Top 20 products by revenue")
        print("  low_competition   - Low competition opportunities")
        print("  best_scores       - Best opportunity scores")
        print("  high_growth       - High growth products")
        print("  gaming            - Gaming accessories analysis")
        print("  wedding           - Wedding products analysis")
        print("  cnc_opportunities - CNC-specific opportunities")
        print("  price_analysis    - Price analysis by category")
        print("  shop_leaders      - Top performing shops")
        print("  combined          - Best combined opportunities")
        return
    
    query_name = sys.argv[1].lower()
    db = ProductQuery("product_research.db")
    
    try:
        if query_name == "top_revenue":
            db.top_revenue_products(20)
        
        elif query_name == "low_competition":
            db.low_competition_opportunities(500)
        
        elif query_name == "best_scores":
            db.best_scored_products(20)
        
        elif query_name == "high_growth":
            db.high_growth_products(100, 20)
        
        elif query_name == "gaming":
            print_header("Gaming Accessories Analysis")
            results = db.search_by_category("gaming")
            
            # Also show gaming gap opportunities
            print("\n" + "-" * 80)
            print("Gaming Gap Opportunities:")
            print("-" * 80)
            db.cursor.execute("""
                SELECT search_term, total_listings, competition_level
                FROM gap_opportunities
                WHERE search_term LIKE '%gaming%'
                ORDER BY total_listings ASC
            """)
            gaming_gaps = [dict(row) for row in db.cursor.fetchall()]
            db.print_results(gaming_gaps, None)
        
        elif query_name == "wedding":
            print_header("Wedding Products Analysis")
            results = db.search_by_category("wedding")
            
            # Show wedding search terms
            print("\n" + "-" * 80)
            print("Wedding Search Terms:")
            print("-" * 80)
            db.cursor.execute("""
                SELECT term, total_listings, COUNT(p.id) as products_tracked
                FROM search_terms st
                LEFT JOIN products p ON st.id = p.search_term_id
                WHERE term LIKE '%wedding%'
                GROUP BY st.id, term, total_listings
                ORDER BY total_listings ASC
            """)
            wedding_terms = [dict(row) for row in db.cursor.fetchall()]
            db.print_results(wedding_terms, None)
        
        elif query_name == "cnc_opportunities":
            print_header("CNC-Specific Opportunities")
            db.cursor.execute("""
                SELECT 
                    search_term,
                    total_listings,
                    competition_level,
                    notes
                FROM gap_opportunities
                WHERE search_term LIKE '%cnc%'
                ORDER BY total_listings ASC
            """)
            cnc_gaps = [dict(row) for row in db.cursor.fetchall()]
            db.print_results(cnc_gaps, None)
            
            # Also show CNC products
            print("\n" + "-" * 80)
            print("CNC Products in Database:")
            print("-" * 80)
            db.cursor.execute("""
                SELECT 
                    p.product_name,
                    s.name as shop,
                    p.price,
                    p.monthly_revenue,
                    st.term as search_term
                FROM products p
                LEFT JOIN shops s ON p.shop_id = s.id
                LEFT JOIN search_terms st ON p.search_term_id = st.id
                WHERE st.term LIKE '%cnc%' OR p.manufacturing_method LIKE '%CNC%'
                ORDER BY p.monthly_revenue DESC
                LIMIT 20
            """)
            cnc_products = [dict(row) for row in db.cursor.fetchall()]
            db.print_results(cnc_products, None)
        
        elif query_name == "price_analysis":
            db.price_analysis_by_category()
        
        elif query_name == "shop_leaders":
            db.shop_analysis()
        
        elif query_name == "combined":
            db.best_opportunities_combined(20)
        
        else:
            print(f"Unknown query: {query_name}")
            print("Run without arguments to see available queries.")
    
    finally:
        db.close()


if __name__ == "__main__":
    main()

