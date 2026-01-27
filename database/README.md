# 📊 Product Research Database

**316 products** | **81 shops** | **162 search terms** | **49 opportunities**

---

## 🚀 Quick Start

```bash
# View top opportunities
python3 quick_queries.py low_competition

# Analyze gaming products
python3 quick_queries.py gaming

# Interactive queries
python3 query_database.py

# Open in spreadsheet
open csv_exports/top_opportunities.csv
```

---

## 📂 Files

- **`product_research.db`** - SQLite database (184 KB)
- **`csv_exports/`** - 14 CSV files ready for Excel/Sheets
- **`query_database.py`** - Interactive query tool
- **`quick_queries.py`** - Command-line queries
- **`generate_db_report.py`** - Generate markdown reports
- **`export_to_csv.py`** - Export data to CSV
- **`create_product_database.py`** - Rebuild database

---

## 💡 Top Insights

### Best Opportunities (Low Competition)
1. **CNC Shower Caddy** - 1 competitor ⭐⭐⭐⭐⭐
2. **Gaming Desk Hutch** - 3 competitors ⭐⭐⭐⭐⭐
3. **Gaming Microphone Stand** - 24 competitors ⭐⭐⭐⭐

### Highest Revenue
1. **Personalized Serving Board** - $149,590/month
2. **Wooden World Map** - $115,207/month
3. **Personalized Desk Organizer** - $96,238/month

### Best Opportunity Scores
1. **Gaming Keyboard Stand** - 68.5
2. **Gaming Controller Stand** - 68.4
3. **Personalized Serving Board** - 68.2

---

## 📊 CSV Exports

Open these in Excel or Google Sheets:

1. **`top_opportunities.csv`** - 45 best scored products
2. **`low_competition_with_data.csv`** - 47 low-competition niches
3. **`products_full_details.csv`** - All 316 products with complete data
4. **`gaming_opportunities.csv`** - 30 gaming product opportunities
5. **`cnc_opportunities.csv`** - 12 CNC-specific opportunities
6. **`wedding_opportunities.csv`** - 18 wedding product opportunities
7. **`category_summary.csv`** - Performance by category
8. **`shop_performance.csv`** - Top performing shops
9. Plus 6 more data files

---

## 🔧 Available Queries

```bash
# View options
python3 quick_queries.py

# Specific queries
python3 quick_queries.py top_revenue
python3 quick_queries.py low_competition
python3 quick_queries.py best_scores
python3 quick_queries.py high_growth
python3 quick_queries.py gaming
python3 quick_queries.py wedding
python3 quick_queries.py cnc_opportunities
python3 quick_queries.py price_analysis
python3 quick_queries.py shop_leaders
python3 quick_queries.py combined
```

---

## 📖 Full Documentation

**Read:** [../DATABASE_INDEX.md](../DATABASE_INDEX.md) - Complete guide with examples

---

## 🗄️ Database Contents

### Tables
- **products** (316 rows) - All product data
- **shops** (81 rows) - Shop information
- **search_terms** (162 rows) - Search terms with competition
- **gap_opportunities** (49 rows) - Low competition niches
- **product_scores** (231 rows) - Opportunity scoring
- **categories** - Product categories
- **subcategories** - Subcategory data

### Key Metrics
- **Opportunity Score** - 0-100 (higher = better)
- **Competition** - Number of Etsy listings
- **Monthly Revenue** - Estimated revenue per month
- **Growth Rate** - Sales growth percentage

---

## 💻 Direct SQL Access

```bash
sqlite3 product_research.db

# Example queries:
sqlite> SELECT * FROM products WHERE monthly_revenue > 10000 LIMIT 5;
sqlite> SELECT * FROM gap_opportunities WHERE total_listings < 100;
sqlite> .exit
```

---

**Database created:** January 2, 2026  
**Last updated:** January 2, 2026



