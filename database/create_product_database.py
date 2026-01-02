#!/usr/bin/env python3
"""
Create and populate SQLite database with all product research data.
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

# Database schema
SCHEMA = """
-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Subcategories table
CREATE TABLE IF NOT EXISTS subcategories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    UNIQUE(category_id, name)
);

-- Search terms table
CREATE TABLE IF NOT EXISTS search_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL UNIQUE,
    category TEXT,
    subcategory TEXT,
    total_listings INTEGER,
    competition_level TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shops table
CREATE TABLE IF NOT EXISTS shops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER,
    search_term_id INTEGER,
    product_name TEXT NOT NULL,
    price REAL,
    monthly_sales INTEGER,
    monthly_revenue REAL,
    growth_rate TEXT,
    total_sales INTEGER,
    reviews INTEGER,
    listing_age_months INTEGER,
    category TEXT,
    subcategory TEXT,
    manufacturing_method TEXT,
    complexity TEXT,
    estimated_cogs REAL,
    estimated_margin REAL,
    production_time_minutes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shop_id) REFERENCES shops(id),
    FOREIGN KEY (search_term_id) REFERENCES search_terms(id)
);

-- Product scores table
CREATE TABLE IF NOT EXISTS product_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    opportunity_score REAL,
    market_score REAL,
    feasibility_score REAL,
    profitability_score REAL,
    revenue_potential_score REAL,
    growth_rate_score REAL,
    competition_score REAL,
    tool_compatibility_score REAL,
    margin_score REAL,
    volume_score REAL,
    time_efficiency_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Gap analysis opportunities table
CREATE TABLE IF NOT EXISTS gap_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term TEXT NOT NULL UNIQUE,
    total_listings INTEGER,
    competition_level TEXT,
    opportunity_rating INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Price ranges table
CREATE TABLE IF NOT EXISTS price_ranges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term_id INTEGER,
    low REAL,
    mid REAL,
    high REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (search_term_id) REFERENCES search_terms(id)
);

-- Insights table
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term_id INTEGER,
    volume_leader TEXT,
    revenue_leader TEXT,
    growth_trend TEXT,
    competition_level TEXT,
    best_opportunity TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (search_term_id) REFERENCES search_terms(id)
);

-- Research metadata table
CREATE TABLE IF NOT EXISTS research_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT,
    research_date TEXT,
    source TEXT,
    account TEXT,
    scope TEXT,
    session_id TEXT,
    collected_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_products_shop ON products(shop_id);
CREATE INDEX IF NOT EXISTS idx_products_search_term ON products(search_term_id);
CREATE INDEX IF NOT EXISTS idx_products_monthly_revenue ON products(monthly_revenue DESC);
CREATE INDEX IF NOT EXISTS idx_products_monthly_sales ON products(monthly_sales DESC);
CREATE INDEX IF NOT EXISTS idx_product_scores_opportunity ON product_scores(opportunity_score DESC);
CREATE INDEX IF NOT EXISTS idx_search_terms_listings ON search_terms(total_listings);
CREATE INDEX IF NOT EXISTS idx_gap_opportunities_listings ON gap_opportunities(total_listings);
"""


class ProductDatabase:
    def __init__(self, db_path="product_research.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connect to database and create schema."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.cursor.executescript(SCHEMA)
        self.conn.commit()
        print(f"✅ Connected to database: {self.db_path}")
        
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            print(f"✅ Closed database connection")
    
    def get_or_create_shop(self, shop_name):
        """Get shop ID or create if doesn't exist."""
        if not shop_name:
            return None
        
        self.cursor.execute("SELECT id FROM shops WHERE name = ?", (shop_name,))
        result = self.cursor.fetchone()
        
        if result:
            return result[0]
        
        self.cursor.execute("INSERT INTO shops (name) VALUES (?)", (shop_name,))
        return self.cursor.lastrowid
    
    def get_or_create_search_term(self, term, category=None, subcategory=None, total_listings=None):
        """Get search term ID or create if doesn't exist."""
        if not term:
            return None
            
        self.cursor.execute("SELECT id FROM search_terms WHERE term = ?", (term,))
        result = self.cursor.fetchone()
        
        if result:
            return result[0]
        
        self.cursor.execute(
            """INSERT INTO search_terms (term, category, subcategory, total_listings) 
               VALUES (?, ?, ?, ?)""",
            (term, category, subcategory, total_listings)
        )
        return self.cursor.lastrowid
    
    def insert_product(self, product_data):
        """Insert product into database."""
        shop_id = self.get_or_create_shop(product_data.get('shop'))
        search_term_id = self.get_or_create_search_term(
            product_data.get('search_term'),
            product_data.get('category'),
            product_data.get('subcategory'),
            product_data.get('total_listings')
        )
        
        # Clean growth rate
        growth_rate = product_data.get('growth_rate', '')
        if isinstance(growth_rate, str):
            growth_rate = growth_rate.replace('%', '').strip()
        
        self.cursor.execute(
            """INSERT INTO products (
                shop_id, search_term_id, product_name, price, monthly_sales,
                monthly_revenue, growth_rate, total_sales, reviews, listing_age_months,
                category, subcategory, manufacturing_method, complexity,
                estimated_cogs, estimated_margin, production_time_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                shop_id,
                search_term_id,
                product_data.get('product'),
                product_data.get('price'),
                product_data.get('monthly_sales'),
                product_data.get('monthly_revenue'),
                growth_rate,
                product_data.get('total_sales'),
                product_data.get('reviews'),
                product_data.get('listing_age_months'),
                product_data.get('category'),
                product_data.get('subcategory'),
                product_data.get('manufacturing_method'),
                product_data.get('complexity'),
                product_data.get('estimated_cogs'),
                product_data.get('estimated_margin'),
                product_data.get('production_time_minutes')
            )
        )
        return self.cursor.lastrowid
    
    def insert_product_scores(self, product_id, scores):
        """Insert product scores."""
        self.cursor.execute(
            """INSERT INTO product_scores (
                product_id, opportunity_score, market_score, feasibility_score,
                profitability_score, revenue_potential_score, growth_rate_score,
                competition_score, tool_compatibility_score, margin_score,
                volume_score, time_efficiency_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                product_id,
                scores.get('opportunity_score'),
                scores.get('market_score'),
                scores.get('feasibility_score'),
                scores.get('profitability_score'),
                scores.get('revenue_potential_score'),
                scores.get('growth_rate_score'),
                scores.get('competition_score'),
                scores.get('tool_compatibility_score'),
                scores.get('margin_score'),
                scores.get('volume_score'),
                scores.get('time_efficiency_score')
            )
        )
    
    def insert_gap_opportunity(self, search_term, total_listings, competition_level, notes=None):
        """Insert gap analysis opportunity."""
        try:
            self.cursor.execute(
                """INSERT INTO gap_opportunities (search_term, total_listings, competition_level, notes)
                   VALUES (?, ?, ?, ?)""",
                (search_term, total_listings, competition_level, notes)
            )
        except sqlite3.IntegrityError:
            # Already exists, skip
            pass
    
    def insert_research_metadata(self, source_file, data):
        """Insert research metadata."""
        self.cursor.execute(
            """INSERT INTO research_metadata (
                source_file, research_date, source, account, scope, session_id, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                source_file,
                data.get('research_date'),
                data.get('source'),
                data.get('account'),
                data.get('scope'),
                data.get('metadata', {}).get('session_id') if isinstance(data.get('metadata'), dict) else None,
                data.get('metadata', {}).get('collected_at') if isinstance(data.get('metadata'), dict) else None
            )
        )


def import_broad_research(db, filepath):
    """Import broad-product-research.json"""
    print(f"\n📥 Importing: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    db.insert_research_metadata(filepath, data)
    
    product_count = 0
    # Navigate through nested structure
    for category_key, category_data in data.get('product_categories', {}).items():
        category_name = category_data.get('category_name', category_key)
        
        for subcat_key, subcat_data in category_data.get('subcategories', {}).items():
            search_term = subcat_data.get('search_term')
            total_listings = subcat_data.get('total_listings')
            
            # Import top sellers
            for product in subcat_data.get('top_sellers', []):
                product['search_term'] = search_term
                product['category'] = category_name
                product['subcategory'] = subcat_key
                product['total_listings'] = total_listings
                db.insert_product(product)
                product_count += 1
    
    print(f"  ✓ Imported {product_count} products")


def import_etsy_research(db, filepath):
    """Import etsy-product-research.json"""
    print(f"\n📥 Importing: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    db.insert_research_metadata(filepath, data)
    
    product_count = 0
    # Import top 5 recommendations
    for rec in data.get('top_5_recommendations', []):
        category = rec.get('category')
        
        for product in rec.get('top_sellers', []):
            product['category'] = category
            product['search_term'] = rec.get('product')
            db.insert_product(product)
            product_count += 1
    
    print(f"  ✓ Imported {product_count} products")


def import_complete_analysis(db, filepath):
    """Import complete_analysis.json"""
    print(f"\n📥 Importing: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    product_count = 0
    # Import top revenue products
    for product in data.get('top_revenue_products', []):
        db.insert_product(product)
        product_count += 1
    
    print(f"  ✓ Imported {product_count} products")


def import_scored_products(db, filepath):
    """Import scored_products JSON files"""
    print(f"\n📥 Importing: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    product_count = 0
    for item in data.get('products', []):
        product_data = item.get('product_data', {})
        scores = item.get('scores', {})
        
        product_id = db.insert_product(product_data)
        db.insert_product_scores(product_id, scores)
        product_count += 1
    
    print(f"  ✓ Imported {product_count} scored products")


def import_gap_opportunities(db, filepath):
    """Import low_competition_opportunities.json"""
    print(f"\n📥 Importing: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    count = 0
    for opp in data.get('opportunities', []):
        db.insert_gap_opportunity(
            opp.get('search_term'),
            opp.get('total_listings'),
            opp.get('competition_level')
        )
        count += 1
    
    print(f"  ✓ Imported {count} gap opportunities")


def import_raw_data_files(db, raw_dir):
    """Import all JSON files from data/raw/2026-01-01/"""
    print(f"\n📥 Importing raw data files from: {raw_dir}")
    
    if not os.path.exists(raw_dir):
        print(f"  ⚠️  Directory not found: {raw_dir}")
        return
    
    files = [f for f in os.listdir(raw_dir) if f.endswith('.json')]
    print(f"  Found {len(files)} JSON files")
    
    search_term_count = 0
    for filename in files:
        filepath = os.path.join(raw_dir, filename)
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            search_term = data.get('search_term')
            total_listings = data.get('total_listings')
            
            if search_term:
                db.get_or_create_search_term(
                    search_term,
                    data.get('metadata', {}).get('category'),
                    None,
                    total_listings
                )
                search_term_count += 1
                
                # Import top sellers if present
                for product in data.get('top_sellers', []):
                    product['search_term'] = search_term
                    product['total_listings'] = total_listings
                    db.insert_product(product)
        
        except Exception as e:
            print(f"  ⚠️  Error processing {filename}: {e}")
    
    print(f"  ✓ Processed {search_term_count} search terms")


def import_wedding_research(db, filepath):
    """Import wedding_expanded_research.json"""
    print(f"\n📥 Importing: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    count = 0
    for search_term, details in data.get('results', {}).items():
        db.get_or_create_search_term(
            search_term,
            'wedding',
            None,
            details.get('total_listings')
        )
        count += 1
    
    print(f"  ✓ Imported {count} wedding search terms")


def import_gaming_gap_analysis(db, filepath):
    """Import gaming_accessories_gap_analysis.json"""
    print(f"\n📥 Importing: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    count = 0
    for competition_level in ['low_competition', 'medium_competition', 'high_competition']:
        for item in data.get(competition_level, []):
            search_term = item.get('search_term')
            total_listings = item.get('total_listings')
            
            if search_term:
                db.insert_gap_opportunity(
                    search_term,
                    total_listings,
                    competition_level.replace('_', ' ').title()
                )
                count += 1
    
    print(f"  ✓ Imported {count} gaming opportunities")


def main():
    """Main import function."""
    print("=" * 60)
    print("🗄️  PRODUCT RESEARCH DATABASE IMPORTER")
    print("=" * 60)
    
    base_dir = Path(__file__).parent
    db = ProductDatabase(str(base_dir / "product_research.db"))
    
    try:
        db.connect()
        
        # Import main research files
        files_to_import = [
            ('broad-product-research.json', import_broad_research),
            ('etsy-product-research.json', import_etsy_research),
            ('complete_analysis.json', import_complete_analysis),
            ('low_competition_opportunities.json', import_gap_opportunities),
            ('wedding_expanded_research.json', import_wedding_research),
            ('gaming_accessories_gap_analysis.json', import_gaming_gap_analysis),
        ]
        
        for filename, import_func in files_to_import:
            filepath = base_dir / filename
            if filepath.exists():
                import_func(db, str(filepath))
            else:
                print(f"  ⚠️  File not found: {filename}")
        
        # Import scored products files
        for scored_file in base_dir.glob('scored_products_*.json'):
            import_scored_products(db, str(scored_file))
        
        # Import raw data files
        raw_dir = base_dir / 'data' / 'raw' / '2026-01-01'
        import_raw_data_files(db, str(raw_dir))
        
        db.conn.commit()
        
        # Print summary statistics
        print("\n" + "=" * 60)
        print("📊 DATABASE SUMMARY")
        print("=" * 60)
        
        stats = [
            ("Total Products", "SELECT COUNT(*) FROM products"),
            ("Total Shops", "SELECT COUNT(*) FROM shops"),
            ("Total Search Terms", "SELECT COUNT(*) FROM search_terms"),
            ("Total Gap Opportunities", "SELECT COUNT(*) FROM gap_opportunities"),
            ("Products with Scores", "SELECT COUNT(*) FROM product_scores"),
        ]
        
        for label, query in stats:
            db.cursor.execute(query)
            count = db.cursor.fetchone()[0]
            print(f"  {label}: {count:,}")
        
        print("\n" + "=" * 60)
        print("✅ IMPORT COMPLETE!")
        print("=" * 60)
        print(f"\nDatabase saved to: {db.db_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()

