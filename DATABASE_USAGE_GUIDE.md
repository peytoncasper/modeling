# Product Research Database - Usage Guide

## 📚 Quick Start

Your product research data has been organized into a SQLite database with 316 products, 81 shops, 162 search terms, and 49 gap opportunities.

## 🗂️ Files Created

### Database Files
- **`product_research.db`** - Main SQLite database (all data)
- **`csv_exports/`** - Folder with 16 CSV files for Excel/Sheets

### Python Scripts
- **`create_product_database.py`** - Creates and populates database
- **`query_database.py`** - Interactive query tool
- **`quick_queries.py`** - Command-line queries
- **`generate_db_report.py`** - Generate markdown report
- **`export_to_csv.py`** - Export to CSV files

### Documentation
- **`DATABASE_README.md`** - Complete database documentation
- **`DATABASE_REPORT.md`** - Generated analysis report
- **`DATABASE_USAGE_GUIDE.md`** - This file

## 🚀 Quick Commands

### View Top Products
```bash
python3 quick_queries.py top_revenue
python3 quick_queries.py best_scores
python3 quick_queries.py low_competition
```

### Category Analysis
```bash
python3 quick_queries.py gaming
python3 quick_queries.py wedding
python3 quick_queries.py cnc_opportunities
```

### Generate Reports
```bash
python3 generate_db_report.py
```

### Export to CSV
```bash
python3 export_to_csv.py
```

### Interactive Queries
```bash
python3 query_database.py
```

## 📊 Key CSV Files

### For Product Selection
1. **`top_opportunities.csv`** - 45 products with opportunity score > 60
2. **`low_competition_with_data.csv`** - 47 search terms with < 500 competitors
3. **`products_full_details.csv`** - All 316 products with complete data

### For Market Analysis
4. **`category_summary.csv`** - Performance by category
5. **`shop_performance.csv`** - Top performing shops

### For Specific Niches
6. **`gaming_opportunities.csv`** - 30 gaming product opportunities
7. **`cnc_opportunities.csv`** - 12 CNC-specific opportunities
8. **`wedding_opportunities.csv`** - 18 wedding product opportunities

## 💡 Common Use Cases

### 1. Find Low Competition Products
```bash
# Command line
python3 quick_queries.py low_competition

# Or open CSV
open csv_exports/low_competition_with_data.csv
```

### 2. Analyze Best Opportunities
```bash
# View in terminal
python3 quick_queries.py combined

# Or open CSV for sorting/filtering
open csv_exports/top_opportunities.csv
```

### 3. Research Gaming Products
```bash
# Detailed analysis
python3 quick_queries.py gaming

# Or CSV for spreadsheet
open csv_exports/gaming_opportunities.csv
```

### 4. Study Successful Shops
```bash
# View shop performance
python3 -c "from query_database import ProductQuery; q = ProductQuery(); q.shop_analysis(); q.close()"

# Or open CSV
open csv_exports/shop_performance.csv
```

## 🔍 SQL Query Examples

### Direct Database Queries
```bash
sqlite3 product_research.db
```

#### Find Products Under $50 with High Revenue
```sql
SELECT product_name, price, monthly_revenue, monthly_sales
FROM products
WHERE price < 50 AND monthly_revenue > 10000
ORDER BY monthly_revenue DESC;
```

#### Search Terms with < 100 Competitors
```sql
SELECT term, total_listings
FROM search_terms
WHERE total_listings < 100
ORDER BY total_listings ASC;
```

#### Products by Category
```sql
SELECT category, COUNT(*) as count, AVG(monthly_revenue) as avg_revenue
FROM products
WHERE category IS NOT NULL
GROUP BY category
ORDER BY avg_revenue DESC;
```

#### High Growth Products
```sql
SELECT product_name, growth_rate, monthly_revenue, listing_age_months
FROM products
WHERE CAST(growth_rate AS INTEGER) > 200
ORDER BY CAST(growth_rate AS INTEGER) DESC;
```

## 📈 Analysis Workflow

### Step 1: Identify Opportunities
```bash
# Generate comprehensive report
python3 generate_db_report.py

# Review DATABASE_REPORT.md for overview
```

### Step 2: Deep Dive into Categories
```bash
# Analyze specific niches
python3 quick_queries.py gaming
python3 quick_queries.py wedding
python3 quick_queries.py cnc_opportunities
```

### Step 3: Export for Detailed Analysis
```bash
# Export all data to CSV
python3 export_to_csv.py

# Open in Excel/Google Sheets for filtering and sorting
```

### Step 4: Research Competitors
```bash
# Find top shops in your niche
python3 -c "
from query_database import ProductQuery
q = ProductQuery()
q.search_by_category('gaming')  # or 'wedding', 'cnc', etc.
q.close()
"
```

## 🎯 Top Insights from Database

### Highest Revenue Products
1. **Personalized Serving Board** - $149,590/month (MontiqueCrafts)
2. **Wooden World Map** - $115,207/month (EnjoyTheWood)
3. **Personalized Desk Organizer** - $96,238/month (WoodGothicCraft)

### Lowest Competition Opportunities
1. **CNC Shower Caddy** - Only 1 listing!
2. **Gaming Desk Hutch** - 3 listings
3. **Gaming Microphone Stand** - 24 listings

### Best Opportunity Scores
1. **Gaming Keyboard Stand** - 68.5 score
2. **Gaming Controller Stand** - 68.4 score
3. **Personalized Serving Board** - 68.2 score

### Most Profitable Categories
1. **Wall Art** - $80,038 avg revenue
2. **CNC/Laser Products** - $69,226 avg revenue
3. **Resin + Wood** - High-end custom pieces

## 🔧 Database Maintenance

### Backup Database
```bash
cp product_research.db backups/product_research_$(date +%Y%m%d).db
```

### Add New Data
1. Add new JSON files to appropriate location
2. Update `create_product_database.py` import functions
3. Re-run: `python3 create_product_database.py`

### Refresh Reports
```bash
python3 generate_db_report.py
python3 export_to_csv.py
```

## 📱 Opening CSV Files

### Mac
```bash
open csv_exports/top_opportunities.csv
```

### Windows
```bash
start csv_exports/top_opportunities.csv
```

### Linux
```bash
xdg-open csv_exports/top_opportunities.csv
```

## 🆘 Troubleshooting

### Database Not Found
```bash
# Recreate database
python3 create_product_database.py
```

### Missing Python Module
```bash
# The query tool works without tabulate
# But for better formatting:
pip3 install --user tabulate
```

### CSV Files Not Generated
```bash
# Re-export
python3 export_to_csv.py
```

## 📞 Next Steps

1. **Review** `DATABASE_REPORT.md` for complete analysis
2. **Open** CSV files in Excel/Sheets for sorting and filtering
3. **Query** database for specific insights using Python scripts
4. **Export** custom queries as needed
5. **Select** products based on opportunity scores and competition levels

## 🎓 Learning Resources

### Understanding the Data
- **Opportunity Score**: 0-100, higher = better opportunity
- **Competition**: Number of Etsy listings for that search term
- **Growth Rate**: Percentage increase in sales
- **Monthly Revenue**: Estimated monthly revenue from Everbee

### Key Metrics
- **Low Competition**: < 500 listings
- **High Opportunity**: Score > 65
- **Good Revenue**: > $5,000/month
- **High Growth**: > 100% growth rate

---

**Database Created:** 2026-01-02
**Total Products:** 316
**Total Opportunities:** 49
**Data Sources:** 8 JSON files + 96 raw search results

