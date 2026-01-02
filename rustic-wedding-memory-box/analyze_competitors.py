
import json
import re

def analyze_competitors():
    """Analyze competitor data to identify premium vs budget features"""
    
    # Load competitor data
    with open('rustic-wedding-memory-box/competitor_analysis.json', 'r') as f:
        data = json.load(f)
    
    competitors = data['competitors']
    
    # Price analysis
    prices = [c['price'] for c in competitors]
    prices.sort()
    
    print("=" * 70)
    print("COMPETITOR PRICING ANALYSIS")
    print("=" * 70)
    print(f"\nPrice Range: ${min(prices):.2f} - ${max(prices):.2f}")
    print(f"Median Price: ${prices[len(prices)//2]:.2f}")
    print(f"Average Price: ${sum(prices)/len(prices):.2f}")
    
    # Identify gaps
    print("\n" + "=" * 70)
    print("PRICE GAP ANALYSIS")
    print("=" * 70)
    
    gaps = []
    for i in range(len(prices) - 1):
        gap = prices[i+1] - prices[i]
        if gap > 20:  # Significant gap
            gaps.append({
                'low': prices[i],
                'high': prices[i+1],
                'gap': gap,
                'midpoint': (prices[i] + prices[i+1]) / 2
            })
    
    if gaps:
        print("\nSignificant Price Gaps Found:")
        for gap in gaps:
            print(f"   ${gap['low']:.2f} → ${gap['high']:.2f} (Gap: ${gap['gap']:.2f}, Midpoint: ${gap['midpoint']:.2f})")
    
    # Sales volume vs price
    print("\n" + "=" * 70)
    print("SALES VOLUME vs PRICE ANALYSIS")
    print("=" * 70)
    
    print("\nHigh Volume, Low Price:")
    for c in competitors:
        if c['monthly_sales'] > 100 and c['price'] < 60:
            print(f"   {c['shop']}: ${c['price']:.2f}, {c['monthly_sales']} sales/mo")
    
    print("\nHigh Volume, Mid Price:")
    for c in competitors:
        if c['monthly_sales'] > 50 and 60 <= c['price'] < 100:
            print(f"   {c['shop']}: ${c['price']:.2f}, {c['monthly_sales']} sales/mo")
    
    print("\nLow Volume, High Price:")
    for c in competitors:
        if c['monthly_sales'] < 30 and c['price'] > 100:
            print(f"   {c['shop']}: ${c['price']:.2f}, {c['monthly_sales']} sales/mo")
    
    # Market opportunities
    print("\n" + "=" * 70)
    print("MARKET OPPORTUNITY ANALYSIS")
    print("=" * 70)
    
    # Sweet spot: $100-120 range
    sweet_spot_competitors = [c for c in competitors if 100 <= c['price'] <= 120]
    if sweet_spot_competitors:
        print("\nSweet Spot ($100-120):")
        for c in sweet_spot_competitors:
            print(f"   {c['shop']}: ${c['price']:.2f}, {c['monthly_sales']} sales/mo")
        avg_sales = sum(c['monthly_sales'] for c in sweet_spot_competitors) / len(sweet_spot_competitors)
        print(f"   Average Sales: {avg_sales:.0f}/month")
        print(f"   Opportunity: Moderate competition, good price point")
    
    # Under-served: $120-150 range
    underserved = [c for c in competitors if 120 < c['price'] < 150]
    if underserved:
        print("\nUnder-served ($120-150):")
        for c in underserved:
            print(f"   {c['shop']}: ${c['price']:.2f}, {c['monthly_sales']} sales/mo")
        print(f"   Opportunity: Less competition, premium positioning possible")
    
    return {
        'price_gaps': gaps,
        'sweet_spot': sweet_spot_competitors,
        'underserved': underserved
    }

if __name__ == '__main__':
    analyze_competitors()
