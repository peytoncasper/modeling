#!/usr/bin/env python3
"""
Query tool for product research database.
Provides useful queries and analysis functions.
"""

import sqlite3
import json
from pathlib import Path

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


class ProductQuery:
    def __init__(self, db_path="product_research.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def close(self):
        self.conn.close()
    
    def execute_query(self, query, params=None):
        """Execute a query and return results as list of dicts."""
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
    
    def print_results(self, results, title=None):
        """Print results in a nice table format."""
        if title:
            print(f"\n{'=' * 80}")
            print(f"📊 {title}")
            print('=' * 80)
        
        if not results:
            print("No results found.")
            return
        
        if HAS_TABULATE:
            print(tabulate(results, headers="keys", tablefmt="grid"))
        else:
            # Fallback: simple JSON-like output
            for i, row in enumerate(results, 1):
                print(f"\n--- Result {i} ---")
                for key, value in row.items():
                    print(f"  {key}: {value}")
        
        print(f"\nTotal: {len(results)} rows")
    
    def top_revenue_products(self, limit=20):
        """Get top products by monthly revenue."""
        query = """
            SELECT 
                p.product_name,
                s.name as shop,
                p.price,
                p.monthly_sales,
                p.monthly_revenue,
                p.growth_rate,
                p.reviews,
                p.category,
                st.term as search_term,
                st.total_listings
            FROM products p
            LEFT JOIN shops s ON p.shop_id = s.id
            LEFT JOIN search_terms st ON p.search_term_id = st.id
            WHERE p.monthly_revenue IS NOT NULL
            ORDER BY p.monthly_revenue DESC
            LIMIT ?
        """
        results = self.execute_query(query, (limit,))
        self.print_results(results, f"Top {limit} Products by Monthly Revenue")
        return results
    
    def top_volume_products(self, limit=20):
        """Get top products by monthly sales volume."""
        query = """
            SELECT 
                p.product_name,
                s.name as shop,
                p.price,
                p.monthly_sales,
                p.monthly_revenue,
                p.reviews,
                p.category,
                st.term as search_term
            FROM products p
            LEFT JOIN shops s ON p.shop_id = s.id
            LEFT JOIN search_terms st ON p.search_term_id = st.id
            WHERE p.monthly_sales IS NOT NULL
            ORDER BY p.monthly_sales DESC
            LIMIT ?
        """
        results = self.execute_query(query, (limit,))
        self.print_results(results, f"Top {limit} Products by Monthly Sales Volume")
        return results
    
    def best_scored_products(self, limit=20):
        """Get products with best opportunity scores."""
        query = """
            SELECT 
                p.product_name,
                s.name as shop,
                p.price,
                p.monthly_sales,
                p.monthly_revenue,
                ps.opportunity_score,
                ps.market_score,
                ps.feasibility_score,
                ps.profitability_score,
                st.term as search_term,
                st.total_listings
            FROM products p
            LEFT JOIN shops s ON p.shop_id = s.id
            LEFT JOIN search_terms st ON p.search_term_id = st.id
            LEFT JOIN product_scores ps ON p.id = ps.product_id
            WHERE ps.opportunity_score IS NOT NULL
            ORDER BY ps.opportunity_score DESC
            LIMIT ?
        """
        results = self.execute_query(query, (limit,))
        self.print_results(results, f"Top {limit} Products by Opportunity Score")
        return results
    
    def low_competition_opportunities(self, max_listings=500):
        """Get low competition opportunities."""
        query = """
            SELECT 
                search_term,
                total_listings,
                competition_level,
                notes
            FROM gap_opportunities
            WHERE total_listings <= ?
            ORDER BY total_listings ASC
        """
        results = self.execute_query(query, (max_listings,))
        self.print_results(results, f"Low Competition Opportunities (<= {max_listings} listings)")
        return results
    
    def search_by_category(self, category):
        """Get all products in a category."""
        query = """
            SELECT 
                p.product_name,
                s.name as shop,
                p.price,
                p.monthly_sales,
                p.monthly_revenue,
                p.subcategory,
                st.term as search_term
            FROM products p
            LEFT JOIN shops s ON p.shop_id = s.id
            LEFT JOIN search_terms st ON p.search_term_id = st.id
            WHERE LOWER(p.category) LIKE LOWER(?)
            ORDER BY p.monthly_revenue DESC
        """
        results = self.execute_query(query, (f'%{category}%',))
        self.print_results(results, f"Products in Category: {category}")
        return results
    
    def shop_analysis(self, shop_name=None):
        """Analyze shops - all or specific shop."""
        if shop_name:
            query = """
                SELECT 
                    p.product_name,
                    p.price,
                    p.monthly_sales,
                    p.monthly_revenue,
                    p.reviews,
                    p.category,
                    st.term as search_term
                FROM products p
                LEFT JOIN shops s ON p.shop_id = s.id
                LEFT JOIN search_terms st ON p.search_term_id = st.id
                WHERE s.name = ?
                ORDER BY p.monthly_revenue DESC
            """
            results = self.execute_query(query, (shop_name,))
            self.print_results(results, f"Products from Shop: {shop_name}")
        else:
            query = """
                SELECT 
                    s.name as shop,
                    COUNT(p.id) as product_count,
                    SUM(p.monthly_revenue) as total_revenue,
                    AVG(p.monthly_revenue) as avg_revenue,
                    SUM(p.monthly_sales) as total_sales,
                    AVG(p.price) as avg_price
                FROM shops s
                LEFT JOIN products p ON s.id = p.shop_id
                GROUP BY s.id, s.name
                ORDER BY total_revenue DESC
            """
            results = self.execute_query(query)
            self.print_results(results, "Shop Performance Analysis")
        
        return results
    
    def price_analysis_by_category(self):
        """Analyze price ranges by category."""
        query = """
            SELECT 
                category,
                COUNT(*) as product_count,
                MIN(price) as min_price,
                AVG(price) as avg_price,
                MAX(price) as max_price,
                AVG(monthly_revenue) as avg_revenue
            FROM products
            WHERE price IS NOT NULL AND category IS NOT NULL
            GROUP BY category
            ORDER BY avg_revenue DESC
        """
        results = self.execute_query(query)
        self.print_results(results, "Price Analysis by Category")
        return results
    
    def high_growth_products(self, min_growth=100, limit=20):
        """Find products with high growth rates."""
        query = """
            SELECT 
                p.product_name,
                s.name as shop,
                p.price,
                p.monthly_sales,
                p.monthly_revenue,
                p.growth_rate,
                p.listing_age_months,
                st.term as search_term
            FROM products p
            LEFT JOIN shops s ON p.shop_id = s.id
            LEFT JOIN search_terms st ON p.search_term_id = st.id
            WHERE CAST(REPLACE(p.growth_rate, '%', '') AS INTEGER) >= ?
            ORDER BY CAST(REPLACE(p.growth_rate, '%', '') AS INTEGER) DESC
            LIMIT ?
        """
        results = self.execute_query(query, (min_growth, limit))
        self.print_results(results, f"High Growth Products (>= {min_growth}%)")
        return results
    
    def search_terms_analysis(self):
        """Analyze search terms by competition."""
        query = """
            SELECT 
                term,
                total_listings,
                category,
                COUNT(p.id) as products_tracked
            FROM search_terms st
            LEFT JOIN products p ON st.id = p.search_term_id
            WHERE total_listings IS NOT NULL
            GROUP BY st.id, term, total_listings, category
            ORDER BY total_listings ASC
            LIMIT 50
        """
        results = self.execute_query(query)
        self.print_results(results, "Search Terms - Lowest Competition")
        return results
    
    def best_opportunities_combined(self, limit=20):
        """Combine multiple factors to find best opportunities."""
        query = """
            SELECT 
                p.product_name,
                s.name as shop,
                p.price,
                p.monthly_sales,
                p.monthly_revenue,
                p.growth_rate,
                st.term as search_term,
                st.total_listings as competition,
                ps.opportunity_score,
                CASE 
                    WHEN st.total_listings < 100 THEN 'Very Low'
                    WHEN st.total_listings < 500 THEN 'Low'
                    WHEN st.total_listings < 2000 THEN 'Medium'
                    ELSE 'High'
                END as competition_level
            FROM products p
            LEFT JOIN shops s ON p.shop_id = s.id
            LEFT JOIN search_terms st ON p.search_term_id = st.id
            LEFT JOIN product_scores ps ON p.id = ps.product_id
            WHERE p.monthly_revenue > 5000 
                AND st.total_listings < 2000
                AND ps.opportunity_score > 60
            ORDER BY ps.opportunity_score DESC, st.total_listings ASC
            LIMIT ?
        """
        results = self.execute_query(query, (limit,))
        self.print_results(results, f"Best Combined Opportunities (High Revenue + Low Competition + High Score)")
        return results
    
    def export_to_json(self, results, filename):
        """Export results to JSON file."""
        filepath = Path(filename)
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Exported {len(results)} results to: {filename}")


def main():
    """Interactive query menu."""
    print("=" * 80)
    print("🔍 PRODUCT RESEARCH DATABASE QUERY TOOL")
    print("=" * 80)
    
    db_path = Path(__file__).parent / "product_research.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Run create_product_database.py first!")
        return
    
    query = ProductQuery(str(db_path))
    
    try:
        while True:
            print("\n" + "=" * 80)
            print("QUERY OPTIONS:")
            print("=" * 80)
            print("1.  Top Revenue Products")
            print("2.  Top Volume Products")
            print("3.  Best Scored Products")
            print("4.  Low Competition Opportunities")
            print("5.  High Growth Products")
            print("6.  Search Terms Analysis")
            print("7.  Price Analysis by Category")
            print("8.  Shop Performance Analysis")
            print("9.  Best Combined Opportunities")
            print("10. Search by Category")
            print("11. Analyze Specific Shop")
            print("0.  Exit")
            print("=" * 80)
            
            choice = input("\nEnter choice (0-11): ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                query.top_revenue_products()
            elif choice == '2':
                query.top_volume_products()
            elif choice == '3':
                query.best_scored_products()
            elif choice == '4':
                query.low_competition_opportunities()
            elif choice == '5':
                query.high_growth_products()
            elif choice == '6':
                query.search_terms_analysis()
            elif choice == '7':
                query.price_analysis_by_category()
            elif choice == '8':
                query.shop_analysis()
            elif choice == '9':
                query.best_opportunities_combined()
            elif choice == '10':
                category = input("Enter category name: ").strip()
                query.search_by_category(category)
            elif choice == '11':
                shop = input("Enter shop name: ").strip()
                query.shop_analysis(shop)
            else:
                print("Invalid choice!")
            
            input("\nPress Enter to continue...")
    
    except KeyboardInterrupt:
        print("\n\nExiting...")
    
    finally:
        query.close()
        print("\n✅ Database connection closed")


if __name__ == "__main__":
    main()

