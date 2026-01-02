#!/usr/bin/env python3
"""
Generate a comprehensive markdown report from the database.
"""

import sqlite3
from datetime import datetime
from pathlib import Path


def generate_report(db_path="product_research.db", output_path="DATABASE_REPORT.md"):
    """Generate comprehensive markdown report."""
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    report = []
    report.append("# Product Research Database Report")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n---\n")
    
    # Database Statistics
    report.append("## 📊 Database Statistics\n")
    
    stats = [
        ("Total Products", "SELECT COUNT(*) FROM products"),
        ("Total Shops", "SELECT COUNT(*) FROM shops"),
        ("Total Search Terms", "SELECT COUNT(*) FROM search_terms"),
        ("Gap Opportunities", "SELECT COUNT(*) FROM gap_opportunities"),
        ("Products with Scores", "SELECT COUNT(*) FROM product_scores"),
    ]
    
    for label, query in stats:
        cursor.execute(query)
        count = cursor.fetchone()[0]
        report.append(f"- **{label}:** {count:,}")
    
    # Top 10 Revenue Products
    report.append("\n---\n")
    report.append("## 💰 Top 10 Revenue Products\n")
    
    cursor.execute("""
        SELECT 
            p.product_name,
            s.name as shop,
            p.price,
            p.monthly_sales,
            p.monthly_revenue,
            p.growth_rate,
            st.term as search_term
        FROM products p
        LEFT JOIN shops s ON p.shop_id = s.id
        LEFT JOIN search_terms st ON p.search_term_id = st.id
        WHERE p.monthly_revenue IS NOT NULL
        ORDER BY p.monthly_revenue DESC
        LIMIT 10
    """)
    
    report.append("| Rank | Product | Shop | Price | Monthly Sales | Monthly Revenue | Growth |")
    report.append("|------|---------|------|-------|---------------|-----------------|--------|")
    
    for i, row in enumerate(cursor.fetchall(), 1):
        report.append(
            f"| {i} | {row['product_name'][:50]} | {row['shop']} | "
            f"${row['price']:.2f} | {row['monthly_sales']} | "
            f"${row['monthly_revenue']:,.0f} | {row['growth_rate']}% |"
        )
    
    # Top 10 Volume Products
    report.append("\n---\n")
    report.append("## 📦 Top 10 Volume Products (Monthly Sales)\n")
    
    cursor.execute("""
        SELECT 
            p.product_name,
            s.name as shop,
            p.price,
            p.monthly_sales,
            p.monthly_revenue,
            st.term as search_term
        FROM products p
        LEFT JOIN shops s ON p.shop_id = s.id
        LEFT JOIN search_terms st ON p.search_term_id = st.id
        WHERE p.monthly_sales IS NOT NULL
        ORDER BY p.monthly_sales DESC
        LIMIT 10
    """)
    
    report.append("| Rank | Product | Shop | Price | Monthly Sales | Monthly Revenue |")
    report.append("|------|---------|------|-------|---------------|-----------------|")
    
    for i, row in enumerate(cursor.fetchall(), 1):
        report.append(
            f"| {i} | {row['product_name'][:50]} | {row['shop']} | "
            f"${row['price']:.2f} | {row['monthly_sales']} | "
            f"${row['monthly_revenue']:,.0f} |"
        )
    
    # Best Opportunity Scores
    report.append("\n---\n")
    report.append("## 🎯 Top 10 Opportunity Scores\n")
    
    cursor.execute("""
        SELECT 
            p.product_name,
            s.name as shop,
            p.price,
            p.monthly_revenue,
            ps.opportunity_score,
            ps.market_score,
            ps.feasibility_score,
            st.total_listings
        FROM products p
        LEFT JOIN shops s ON p.shop_id = s.id
        LEFT JOIN search_terms st ON p.search_term_id = st.id
        LEFT JOIN product_scores ps ON p.id = ps.product_id
        WHERE ps.opportunity_score IS NOT NULL
        ORDER BY ps.opportunity_score DESC
        LIMIT 10
    """)
    
    report.append("| Rank | Product | Shop | Opp Score | Market | Feasibility | Competition |")
    report.append("|------|---------|------|-----------|--------|-------------|-------------|")
    
    for i, row in enumerate(cursor.fetchall(), 1):
        report.append(
            f"| {i} | {row['product_name'][:40]} | {row['shop']} | "
            f"{row['opportunity_score']:.1f} | {row['market_score']:.1f} | "
            f"{row['feasibility_score']:.1f} | {row['total_listings']} |"
        )
    
    # Low Competition Opportunities
    report.append("\n---\n")
    report.append("## 🔓 Top 20 Low Competition Opportunities\n")
    
    cursor.execute("""
        SELECT 
            search_term,
            total_listings,
            competition_level
        FROM gap_opportunities
        ORDER BY total_listings ASC
        LIMIT 20
    """)
    
    report.append("| Rank | Search Term | Listings | Competition Level |")
    report.append("|------|-------------|----------|-------------------|")
    
    for i, row in enumerate(cursor.fetchall(), 1):
        report.append(
            f"| {i} | {row['search_term']} | {row['total_listings']} | "
            f"{row['competition_level']} |"
        )
    
    # Category Analysis
    report.append("\n---\n")
    report.append("## 📂 Category Analysis\n")
    
    cursor.execute("""
        SELECT 
            category,
            COUNT(*) as product_count,
            MIN(price) as min_price,
            AVG(price) as avg_price,
            MAX(price) as max_price,
            AVG(monthly_revenue) as avg_revenue,
            AVG(monthly_sales) as avg_sales
        FROM products
        WHERE price IS NOT NULL AND category IS NOT NULL
        GROUP BY category
        ORDER BY avg_revenue DESC
    """)
    
    report.append("| Category | Products | Avg Price | Price Range | Avg Revenue | Avg Sales |")
    report.append("|----------|----------|-----------|-------------|-------------|-----------|")
    
    for row in cursor.fetchall():
        report.append(
            f"| {row['category']} | {row['product_count']} | "
            f"${row['avg_price']:.2f} | ${row['min_price']:.2f} - ${row['max_price']:.2f} | "
            f"${row['avg_revenue']:,.0f} | {row['avg_sales']:.0f} |"
        )
    
    # Top Shops
    report.append("\n---\n")
    report.append("## 🏪 Top 10 Shops by Revenue\n")
    
    cursor.execute("""
        SELECT 
            s.name as shop,
            COUNT(p.id) as product_count,
            SUM(p.monthly_revenue) as total_revenue,
            AVG(p.monthly_revenue) as avg_revenue,
            SUM(p.monthly_sales) as total_sales,
            AVG(p.price) as avg_price
        FROM shops s
        LEFT JOIN products p ON s.id = p.shop_id
        WHERE p.monthly_revenue IS NOT NULL
        GROUP BY s.id, s.name
        ORDER BY total_revenue DESC
        LIMIT 10
    """)
    
    report.append("| Rank | Shop | Products | Total Revenue | Avg Revenue | Total Sales | Avg Price |")
    report.append("|------|------|----------|---------------|-------------|-------------|-----------|")
    
    for i, row in enumerate(cursor.fetchall(), 1):
        report.append(
            f"| {i} | {row['shop']} | {row['product_count']} | "
            f"${row['total_revenue']:,.0f} | ${row['avg_revenue']:,.0f} | "
            f"{row['total_sales']} | ${row['avg_price']:.2f} |"
        )
    
    # High Growth Products
    report.append("\n---\n")
    report.append("## 📈 Top 10 High Growth Products\n")
    
    cursor.execute("""
        SELECT 
            p.product_name,
            s.name as shop,
            p.price,
            p.monthly_sales,
            p.monthly_revenue,
            p.growth_rate,
            p.listing_age_months
        FROM products p
        LEFT JOIN shops s ON p.shop_id = s.id
        WHERE p.growth_rate IS NOT NULL 
            AND CAST(p.growth_rate AS INTEGER) > 0
        ORDER BY CAST(p.growth_rate AS INTEGER) DESC
        LIMIT 10
    """)
    
    report.append("| Rank | Product | Shop | Growth | Monthly Revenue | Age (months) |")
    report.append("|------|---------|------|--------|-----------------|--------------|")
    
    for i, row in enumerate(cursor.fetchall(), 1):
        report.append(
            f"| {i} | {row['product_name'][:45]} | {row['shop']} | "
            f"{row['growth_rate']}% | ${row['monthly_revenue']:,.0f} | "
            f"{row['listing_age_months']} |"
        )
    
    # CNC Opportunities
    report.append("\n---\n")
    report.append("## 🔧 CNC-Specific Opportunities\n")
    
    cursor.execute("""
        SELECT 
            search_term,
            total_listings,
            competition_level
        FROM gap_opportunities
        WHERE search_term LIKE '%cnc%'
        ORDER BY total_listings ASC
    """)
    
    report.append("| Search Term | Listings | Competition |")
    report.append("|-------------|----------|-------------|")
    
    for row in cursor.fetchall():
        report.append(
            f"| {row['search_term']} | {row['total_listings']} | "
            f"{row['competition_level']} |"
        )
    
    # Gaming Opportunities
    report.append("\n---\n")
    report.append("## 🎮 Gaming Accessories Opportunities\n")
    
    cursor.execute("""
        SELECT 
            search_term,
            total_listings,
            competition_level
        FROM gap_opportunities
        WHERE search_term LIKE '%gaming%'
        ORDER BY total_listings ASC
        LIMIT 15
    """)
    
    report.append("| Search Term | Listings | Competition |")
    report.append("|-------------|----------|-------------|")
    
    for row in cursor.fetchall():
        report.append(
            f"| {row['search_term']} | {row['total_listings']} | "
            f"{row['competition_level']} |"
        )
    
    # Wedding Opportunities
    report.append("\n---\n")
    report.append("## 💒 Wedding Products Opportunities\n")
    
    cursor.execute("""
        SELECT 
            term,
            total_listings
        FROM search_terms
        WHERE term LIKE '%wedding%'
        ORDER BY total_listings ASC
        LIMIT 15
    """)
    
    report.append("| Search Term | Listings |")
    report.append("|-------------|----------|")
    
    for row in cursor.fetchall():
        report.append(f"| {row['term']} | {row['total_listings']} |")
    
    # Summary Insights
    report.append("\n---\n")
    report.append("## 💡 Key Insights\n")
    
    # Highest revenue product
    cursor.execute("""
        SELECT product_name, monthly_revenue 
        FROM products 
        ORDER BY monthly_revenue DESC 
        LIMIT 1
    """)
    top_revenue = cursor.fetchone()
    report.append(f"\n### Revenue Leaders")
    report.append(f"- **Highest Revenue Product:** {top_revenue['product_name']} (${top_revenue['monthly_revenue']:,.0f}/month)")
    
    # Lowest competition
    cursor.execute("""
        SELECT search_term, total_listings 
        FROM gap_opportunities 
        ORDER BY total_listings ASC 
        LIMIT 1
    """)
    lowest_comp = cursor.fetchone()
    report.append(f"\n### Competition Analysis")
    report.append(f"- **Lowest Competition:** {lowest_comp['search_term']} ({lowest_comp['total_listings']} listings)")
    
    # Best opportunity score
    cursor.execute("""
        SELECT p.product_name, ps.opportunity_score
        FROM products p
        JOIN product_scores ps ON p.id = ps.product_id
        ORDER BY ps.opportunity_score DESC
        LIMIT 1
    """)
    best_opp = cursor.fetchone()
    report.append(f"\n### Opportunity Scores")
    report.append(f"- **Best Opportunity Score:** {best_opp['product_name']} ({best_opp['opportunity_score']:.1f})")
    
    # Average metrics
    cursor.execute("""
        SELECT 
            AVG(price) as avg_price,
            AVG(monthly_revenue) as avg_revenue,
            AVG(monthly_sales) as avg_sales
        FROM products
        WHERE price IS NOT NULL
    """)
    avgs = cursor.fetchone()
    report.append(f"\n### Market Averages")
    report.append(f"- **Average Price:** ${avgs['avg_price']:.2f}")
    report.append(f"- **Average Monthly Revenue:** ${avgs['avg_revenue']:,.0f}")
    report.append(f"- **Average Monthly Sales:** {avgs['avg_sales']:.0f} units")
    
    # Close connection
    conn.close()
    
    # Write report
    report_text = "\n".join(report)
    with open(output_path, 'w') as f:
        f.write(report_text)
    
    print(f"✅ Report generated: {output_path}")
    print(f"📄 Total lines: {len(report)}")
    
    return report_text


if __name__ == "__main__":
    generate_report()

