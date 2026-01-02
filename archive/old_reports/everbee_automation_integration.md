# Everbee Browser Automation Integration Guide

## Overview

This guide shows how to integrate the Everbee collector with browser automation using coffeeblack MCP tools.

## Integration Steps

### 1. Browser Session Setup

```python
# Create browser session
session_id = f"everbee-{int(time.time())}"

# Using coffeeblack MCP (when available)
# browser_create_session(session_id=session_id)
```

### 2. Login Flow

```python
def login_to_everbee(email, password):
    # Navigate to Everbee
    browser_goto(url="https://app.everbee.io/product-analytics")
    
    # Wait for login form
    browser_wait_for(text="Sign in")
    
    # Fill email
    browser_fill(selector="#email", value=email)
    
    # Fill password  
    browser_fill(selector="#password", value=password)
    
    # Click submit
    browser_click(selector='button[type="submit"]')
    
    # Wait for dashboard
    browser_wait_for(text="Product Analytics")
```

### 3. Search Execution

```python
def execute_search(search_term):
    # Find search input
    browser_fill(
        selector='input[placeholder*="Search"], input[type="search"]',
        value=search_term
    )
    
    # Submit search (press Enter or click button)
    browser_press_key(key="Enter")
    
    # Wait for results table
    browser_wait_for(selector='table, [role="grid"]', timeout=10000)
    
    # Small delay for data to load
    time.sleep(2)
```

### 4. Data Extraction

```python
def extract_product_data():
    extraction_script = """
    (function() {
        const products = [];
        const rows = document.querySelectorAll('table tbody tr, [role="row"]');
        
        rows.forEach((row, index) => {
            if (index === 0) return; // Skip header
            
            const cells = row.querySelectorAll('td, [role="cell"]');
            if (cells.length >= 6) {
                const product = {
                    shop: cells[0]?.textContent?.trim() || '',
                    product: cells[1]?.textContent?.trim() || '',
                    price: cells[2]?.textContent?.trim() || '',
                    monthly_sales: cells[3]?.textContent?.trim() || '',
                    monthly_revenue: cells[4]?.textContent?.trim() || '',
                    growth_rate: cells[5]?.textContent?.trim() || ''
                };
                
                // Parse numbers
                product.price = parseFloat(product.price.replace(/[^0-9.]/g, '')) || 0;
                product.monthly_sales = parseInt(product.monthly_sales.replace(/[^0-9]/g, '')) || 0;
                product.monthly_revenue = parseFloat(product.monthly_revenue.replace(/[^0-9.]/g, '')) || 0;
                
                if (product.product) {
                    products.push(product);
                }
            }
        });
        
        return products.slice(0, 20); // Top 20
    })();
    """
    
    # Execute extraction
    products = browser_eval(expression=extraction_script)
    
    # Get total listings
    total_script = """
    (function() {
        const text = document.body.textContent;
        const match = text.match(/(\\d{1,3}(?:,\\d{3})*)\\s*listings?/i);
        return match ? parseInt(match[1].replace(/,/g, '')) : 0;
    })();
    """
    
    total_listings = browser_eval(expression=total_script)
    
    return {
        "total_listings": total_listings,
        "top_sellers": products
    }
```

### 5. Complete Workflow

```python
def collect_search_results(search_term):
    try:
        # Execute search
        execute_search(search_term)
        
        # Extract data
        data = extract_product_data()
        data["search_term"] = search_term
        
        # Save results
        save_to_json(search_term, data)
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
```

## Full Integration Example

```python
from everbee_collector import EverbeeCollector, GapFiller

# Initialize
collector = EverbeeCollector(
    email="peyton@coffeeblack.ai",
    password="tejzEn-xemmoc-wiqdo7"
)

# Load gap searches
filler = GapFiller(collector)
searches = filler.load_gap_searches()

# For each search:
for search_term in searches[:10]:  # Test with 10
    # 1. Login (if needed)
    if not collector.logged_in:
        login_to_everbee(collector.email, collector.password)
        collector.logged_in = True
    
    # 2. Execute search
    execute_search(search_term)
    
    # 3. Extract data
    data = extract_product_data()
    data["search_term"] = search_term
    
    # 4. Save
    collector.save_results(search_term, data)
    
    # 5. Rate limiting
    time.sleep(2)
```

## Selector Reference

Based on typical Everbee structure:

- **Search Input**: `input[placeholder*="Search"]` or `input[type="search"]`
- **Results Table**: `table` or `[role="grid"]`
- **Table Rows**: `table tbody tr` or `[role="row"]`
- **Table Cells**: `td` or `[role="cell"]`
- **Total Listings**: Look for text containing "listings"

## Error Handling

```python
def safe_collect(search_term, max_retries=3):
    for attempt in range(max_retries):
        try:
            return collect_search_results(search_term)
        except TimeoutError:
            if attempt < max_retries - 1:
                print(f"Retrying {search_term}...")
                time.sleep(5)
            else:
                print(f"Failed after {max_retries} attempts")
                return False
        except Exception as e:
            print(f"Error: {e}")
            return False
```

## Rate Limiting

- Wait 2-3 seconds between searches
- Wait 5 seconds after login
- Wait 2 seconds after search submission
- Handle rate limit errors gracefully

## Next Steps

1. Test login flow manually
2. Identify exact selectors for Everbee's current UI
3. Test data extraction on sample search
4. Integrate into `everbee_collector.py`
5. Run gap-filling batch





