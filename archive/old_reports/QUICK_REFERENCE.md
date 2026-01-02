# Product Analysis Quick Reference

## 🎯 Opportunity Score Formula

```
Opportunity Score = (Market × 0.4) + (Feasibility × 0.3) + (Profitability × 0.3)
```

### Market Score Components
- **Revenue Potential** (40%): Based on top seller revenue
- **Growth Rate** (30%): Based on growth percentage
- **Competition** (30%): Based on total listings

### Feasibility Score Components
- **Tool Compatibility** (30%): ShopBot/CNC availability
- **Skill Match** (30%): Your skill level
- **Material Availability** (20%): Material sourcing
- **Production Speed** (20%): Time per unit

### Profitability Score Components
- **Margin Potential** (40%): Estimated margin %
- **Volume Potential** (30%): Monthly sales volume
- **Time Efficiency** (30%): $/hour potential

---

## 📊 Scoring Thresholds

### Revenue Potential
- $50K+/mo = 100 points
- $20K+/mo = 80 points
- $10K+/mo = 60 points
- $5K+/mo = 40 points
- $2K+/mo = 20 points

### Growth Rate
- 500%+ = 100 points
- 300-499% = 80 points
- 200-299% = 60 points
- 100-199% = 40 points
- 50-99% = 20 points

### Competition
- <500 listings = 100 points
- 500-999 = 80 points
- 1,000-2,499 = 60 points
- 2,500-4,999 = 40 points
- 5,000-9,999 = 20 points
- 10,000+ = 10 points

### Volume Potential
- 500+/mo = 100 points
- 200-499 = 80 points
- 100-199 = 60 points
- 50-99 = 40 points
- 20-49 = 20 points
- <20 = 10 points

---

## ✅ Product Selection Criteria

### Must Have (All Required)
- ✅ Opportunity Score > 70
- ✅ Tool Compatibility = 100 (ShopBot available)
- ✅ Estimated Margin > 30%
- ✅ Competition Score > 60

### Should Have (At Least 3)
- ✅ Growth Rate > 100%
- ✅ Volume Potential > 40
- ✅ Revenue Potential > 40
- ✅ Time Efficiency > 60
- ✅ Customization Opportunity
- ✅ Gift Market Potential

---

## 🚀 Quick Start Workflow

1. **Search** → Use search term generator
2. **Extract** → Capture top 20 sellers
3. **Score** → Run scoring script
4. **Rank** → Sort by opportunity score
5. **Analyze** → Deep dive top 20
6. **Decide** → Select based on criteria
7. **Launch** → Create and list products

---

## 📁 File Structure

```
modeling/
├── product-analysis-framework.md  # Full framework
├── product_scoring.py              # Scoring automation
├── collect_product_data.py         # Data collection
├── broad-product-research.json     # Research data
└── data/
    ├── raw/
    │   └── YYYY-MM-DD/
    │       └── search-term.json
    └── processed/
        └── scored-products.json
```

---

## 🔧 Usage Examples

### Score a Product
```python
from product_scoring import ProductScorer, ProductData

scorer = ProductScorer(available_tools=['ShopBot', 'CNC'])

product = ProductData(
    search_term="wood gaming controller stand",
    shop="LampByGift",
    product="Controller Stand",
    price=61.99,
    monthly_sales=227,
    monthly_revenue=14072.0,
    growth_rate="500%",
    total_listings=6540,
    # ... other fields
)

score = scorer.score_product(product)
print(f"Opportunity Score: {score.opportunity_score:.1f}")
```

### Generate Search Terms
```python
from collect_product_data import SearchTermGenerator

generator = SearchTermGenerator()
searches = generator.generate_broad_searches()
# Returns: ["wood desk", "wood kitchen", "3D printed desk", ...]
```

---

## 📈 Key Metrics to Track

- **Opportunity Score**: Overall potential (0-100)
- **Market Score**: Market attractiveness (0-100)
- **Feasibility Score**: Can you make it? (0-100)
- **Profitability Score**: Will it make money? (0-100)
- **Competition Score**: How crowded? (0-100)
- **Volume Score**: Sales potential (0-100)

---

## 🎯 Decision Matrix

| Opportunity Score | Action |
|------------------|--------|
| 80-100 | **HIGH PRIORITY** - Launch ASAP |
| 70-79 | **MEDIUM PRIORITY** - Consider for portfolio |
| 60-69 | **LOW PRIORITY** - Monitor, may improve |
| <60 | **SKIP** - Not worth pursuing |

---

## 💡 Pro Tips

1. **Focus on scores >70** for initial launches
2. **Balance portfolio**: Mix high-volume and high-margin
3. **Track trends**: Re-run searches monthly
4. **Validate manually**: Always review top 20 scored products
5. **Iterate**: Refine scoring based on actual results

---

## 🔄 Update Schedule

- **Weekly**: New trending searches
- **Monthly**: Full category sweep
- **Quarterly**: Review scoring algorithm
- **Annually**: Major framework update





