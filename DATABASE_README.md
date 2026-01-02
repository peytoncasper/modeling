# Product Research Database

## Overview

This SQLite database consolidates all product research data from various JSON files and markdown analyses into a structured, queryable format.

## Database Statistics

- **Total Products:** 316
- **Total Shops:** 81
- **Total Search Terms:** 162
- **Gap Opportunities:** 49
- **Products with Scores:** 231

## Database Schema

### Core Tables

#### `products`
Main product data table containing all product listings analyzed.

**Key Fields:**
- `product_name` - Product title/name
- `price` - Product price
- `monthly_sales` - Sales per month
- `monthly_revenue` - Revenue per month
- `growth_rate` - Growth percentage
- `total_sales` - Total lifetime sales
- `reviews` - Number of reviews
- `listing_age_months` - How long listing has been active
- `category` - Product category
- `subcategory` - Product subcategory
- `manufacturing_method` - Production method (CNC, 3D Print, etc.)

#### `shops`
Etsy shop information.

**Key Fields:**
- `name` - Shop name

#### `search_terms`
Search terms used in research with competition data.

**Key Fields:**
- `term` - Search term
- `total_listings` - Number of competing listings
- `competition_level` - Low/Medium/High
- `category` - Category classification

#### `product_scores`
Scoring metrics for products (opportunity analysis).

**Key Fields:**
- `opportunity_score` - Overall opportunity score (0-100)
- `market_score` - Market potential score
- `feasibility_score` - Production feasibility score
- `profitability_score` - Profit potential score
- `competition_score` - Competition level score
- `tool_compatibility_score` - CNC/tool compatibility score

#### `gap_opportunities`
Low competition market opportunities identified through gap analysis.

**Key Fields:**
- `search_term` - Search term with low competition
- `total_listings` - Number of competing listings
- `competition_level` - Competition assessment
- `opportunity_rating` - Rating of opportunity

#### `research_metadata`
Metadata about research sessions and data sources.

**Key Fields:**
- `source_file` - Original data file
- `research_date` - Date of research
- `source` - Data source (Everbee, etc.)
- `session_id` - Research session ID

## Data Sources

The database was populated from:

1. **broad-product-research.json** - 39 products across multiple categories
2. **etsy-product-research.json** - 16 top product recommendations
3. **complete_analysis.json** - 30 high-revenue products
4. **scored_products_*.json** - 231 products with detailed scoring (3 files)
5. **low_competition_opportunities.json** - 19 gap opportunities
6. **wedding_expanded_research.json** - 18 wedding-related search terms
7. **gaming_accessories_gap_analysis.json** - 30 gaming opportunities
8. **data/raw/2026-01-01/*.json** - 95 search term analyses

## Usage

### Creating the Database

```bash
python3 create_product_database.py
```

This will:
- Create `product_research.db`
- Import all JSON data
- Create indexes for performance
- Display summary statistics

### Querying the Database

#### Interactive Query Tool

```bash
python3 query_database.py
```

Provides an interactive menu with pre-built queries:
1. Top Revenue Products
2. Top Volume Products
3. Best Scored Products
4. Low Competition Opportunities
5. High Growth Products
6. Search Terms Analysis
7. Price Analysis by Category
8. Shop Performance Analysis
9. Best Combined Opportunities
10. Search by Category
11. Analyze Specific Shop

#### Direct SQL Queries

```bash
sqlite3 product_research.db
```

Example queries:

```sql
-- Top 10 revenue products
SELECT product_name, monthly_revenue, monthly_sales, price
FROM products
ORDER BY monthly_revenue DESC
LIMIT 10;

-- Low competition opportunities
SELECT search_term, total_listings
FROM gap_opportunities
WHERE total_listings < 100
ORDER BY total_listings ASC;

-- Best opportunity scores with low competition
SELECT p.product_name, ps.opportunity_score, st.total_listings, p.monthly_revenue
FROM products p
JOIN product_scores ps ON p.id = ps.product_id
JOIN search_terms st ON p.search_term_id = st.id
WHERE ps.opportunity_score > 65 AND st.total_listings < 1000
ORDER BY ps.opportunity_score DESC;

-- Category analysis
SELECT category, 
       COUNT(*) as products,
       AVG(price) as avg_price,
       AVG(monthly_revenue) as avg_revenue
FROM products
WHERE category IS NOT NULL
GROUP BY category
ORDER BY avg_revenue DESC;
```

### Python API

```python
from query_database import ProductQuery

# Initialize
query = ProductQuery("product_research.db")

# Get top revenue products
results = query.top_revenue_products(limit=20)

# Find low competition opportunities
opportunities = query.low_competition_opportunities(max_listings=500)

# Export results to JSON
query.export_to_json(results, "top_products.json")

# Close connection
query.close()
```

## Key Insights from Database

### Top Opportunities

**Highest Revenue:**
- Personalized Serving Boards: $149,590/month
- Epoxy Tables: $52,250/month
- Bathroom Vanities: $44,968/month

**Lowest Competition:**
- CNC Shower Caddy: 1 listing
- CNC Towel Rack: 34 listings
- CNC Bookend: 96 listings

**Best Opportunity Scores:**
- Gaming Controller Stand: 68.5
- Personalized Serving Board: 68.2
- Watch Box (8 Slot): 67.8

### Market Categories

**Most Profitable Categories:**
1. Custom Engraved Wood Products
2. Resin + Wood Combinations
3. Gaming Accessories
4. Wedding Products
5. Home Organization

**Lowest Competition Categories:**
1. CNC Bathroom Products
2. CNC Workshop Organization
3. CNC Garden Products
4. Gaming Desk Accessories
5. Custom Tech Accessories

## Database Maintenance

### Backing Up

```bash
cp product_research.db product_research_backup_$(date +%Y%m%d).db
```

### Adding New Data

Modify `create_product_database.py` to add new import functions, then re-run:

```bash
python3 create_product_database.py
```

### Updating Schema

Edit the `SCHEMA` variable in `create_product_database.py` and recreate the database.

## Files

- `product_research.db` - SQLite database file
- `create_product_database.py` - Database creation and import script
- `query_database.py` - Query tool with pre-built analyses
- `DATABASE_README.md` - This documentation

## Requirements

```bash
pip install tabulate
```

## Notes

- All prices are in USD
- Monthly sales/revenue are estimates from Everbee analytics
- Growth rates are percentages (stored as text with % symbol)
- Competition levels: Very Low (<100), Low (<500), Medium (<2000), High (2000+)
- Opportunity scores range from 0-100 (higher is better)

