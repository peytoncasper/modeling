#!/usr/bin/env python3
"""
Export database tables to CSV files for analysis in Excel/Google Sheets.
"""

import sqlite3
import csv
from pathlib import Path


def export_table_to_csv(db_path, table_name, output_dir="csv_exports"):
    """Export a single table to CSV."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Get all rows
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"  ⚠️  Table {table_name} is empty")
        conn.close()
        return
    
    # Get column names
    columns = rows[0].keys()
    
    # Write to CSV
    csv_file = output_path / f"{table_name}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    
    print(f"  ✓ Exported {len(rows)} rows to {csv_file}")
    conn.close()


def export_custom_query(db_path, query, filename, output_dir="csv_exports"):
    """Export custom query results to CSV."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Execute query
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print(f"  ⚠️  Query returned no results")
        conn.close()
        return
    
    # Get column names
    columns = rows[0].keys()
    
    # Write to CSV
    csv_file = output_path / filename
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    
    print(f"  ✓ Exported {len(rows)} rows to {csv_file}")
    conn.close()


def main():
    """Export all useful data to CSV files."""
    print("=" * 80)
    print("📤 EXPORTING DATABASE TO CSV FILES")
    print("=" * 80)
    
    db_path = "product_research.db"
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return
    
    # Export main tables
    print("\n📋 Exporting main tables...")
    tables = [
        "products",
        "shops",
        "search_terms",
        "gap_opportunities",
        "product_scores",
        "research_metadata"
    ]
    
    for table in tables:
        export_table_to_csv(db_path, table)
    
    # Export useful joined views
    print("\n📊 Exporting analysis views...")
    
    # Products with all details
    export_custom_query(
        db_path,
        """
        SELECT 
            p.id,
            p.product_name,
            s.name as shop_name,
            p.price,
            p.monthly_sales,
            p.monthly_revenue,
            p.growth_rate,
            p.total_sales,
            p.reviews,
            p.listing_age_months,
            p.category,
            p.subcategory,
            st.term as search_term,
            st.total_listings as competition,
            p.manufacturing_method,
            p.complexity,
            p.estimated_cogs,
            p.estimated_margin,
            ps.opportunity_score,
            ps.market_score,
            ps.feasibility_score,
            ps.profitability_score
        FROM products p
        LEFT JOIN shops s ON p.shop_id = s.id
        LEFT JOIN search_terms st ON p.search_term_id = st.id
        LEFT JOIN product_scores ps ON p.id = ps.product_id
        ORDER BY p.monthly_revenue DESC
        """,
        "products_full_details.csv"
    )
    
    # Top opportunities
    export_custom_query(
        db_path,
        """
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
            ps.market_score,
            ps.feasibility_score,
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
        WHERE ps.opportunity_score > 60
        ORDER BY ps.opportunity_score DESC
        """,
        "top_opportunities.csv"
    )
    
    # Low competition with revenue data
    export_custom_query(
        db_path,
        """
        SELECT 
            st.term as search_term,
            st.total_listings as competition,
            COUNT(p.id) as products_tracked,
            AVG(p.monthly_revenue) as avg_revenue,
            MAX(p.monthly_revenue) as max_revenue,
            AVG(p.price) as avg_price
        FROM search_terms st
        LEFT JOIN products p ON st.id = p.search_term_id
        WHERE st.total_listings < 500
        GROUP BY st.id, st.term, st.total_listings
        ORDER BY st.total_listings ASC
        """,
        "low_competition_with_data.csv"
    )
    
    # Category summary
    export_custom_query(
        db_path,
        """
        SELECT 
            category,
            COUNT(*) as product_count,
            MIN(price) as min_price,
            AVG(price) as avg_price,
            MAX(price) as max_price,
            AVG(monthly_revenue) as avg_revenue,
            AVG(monthly_sales) as avg_sales,
            SUM(monthly_revenue) as total_revenue
        FROM products
        WHERE price IS NOT NULL AND category IS NOT NULL
        GROUP BY category
        ORDER BY avg_revenue DESC
        """,
        "category_summary.csv"
    )
    
    # Shop performance
    export_custom_query(
        db_path,
        """
        SELECT 
            s.name as shop,
            COUNT(p.id) as product_count,
            SUM(p.monthly_revenue) as total_revenue,
            AVG(p.monthly_revenue) as avg_revenue,
            SUM(p.monthly_sales) as total_sales,
            AVG(p.price) as avg_price,
            AVG(p.reviews) as avg_reviews
        FROM shops s
        LEFT JOIN products p ON s.id = p.shop_id
        WHERE p.monthly_revenue IS NOT NULL
        GROUP BY s.id, s.name
        ORDER BY total_revenue DESC
        """,
        "shop_performance.csv"
    )
    
    # Gaming opportunities
    export_custom_query(
        db_path,
        """
        SELECT 
            search_term,
            total_listings as competition,
            competition_level
        FROM gap_opportunities
        WHERE search_term LIKE '%gaming%'
        ORDER BY total_listings ASC
        """,
        "gaming_opportunities.csv"
    )
    
    # CNC opportunities
    export_custom_query(
        db_path,
        """
        SELECT 
            search_term,
            total_listings as competition,
            competition_level
        FROM gap_opportunities
        WHERE search_term LIKE '%cnc%'
        ORDER BY total_listings ASC
        """,
        "cnc_opportunities.csv"
    )
    
    # Wedding opportunities
    export_custom_query(
        db_path,
        """
        SELECT 
            term as search_term,
            total_listings as competition,
            category
        FROM search_terms
        WHERE term LIKE '%wedding%'
        ORDER BY total_listings ASC
        """,
        "wedding_opportunities.csv"
    )
    
    print("\n" + "=" * 80)
    print("✅ EXPORT COMPLETE!")
    print("=" * 80)
    print(f"\nAll CSV files saved to: csv_exports/")
    print("\nYou can now open these files in Excel, Google Sheets, or any spreadsheet software.")


if __name__ == "__main__":
    main()

