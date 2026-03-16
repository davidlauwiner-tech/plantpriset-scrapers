import json
import time
from datetime import datetime
import requests

BASE_URL = "https://zetas.se"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

def main():
    print("=" * 55)
    print("PLANTPRISET — Zetas Trädgård Scraper (Shopify API)")
    print("=" * 55)
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_products = []
    page = 1
    
    while True:
        url = f"{BASE_URL}/products.json?limit=250&page={page}"
        print(f"  Fetching page {page}...")
        resp = session.get(url, timeout=15)
        
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code} — stopping")
            break
        
        data = resp.json()
        products = data.get("products", [])
        
        if not products:
            break
        
        for sp in products:
            # Get the first variant's price
            variants = sp.get("variants", [])
            price = None
            if variants:
                try:
                    price = float(variants[0].get("price", 0))
                except: pass
            
            p = {
                "retailer": "zetas",
                "name": sp.get("title", ""),
                "product_url": f"{BASE_URL}/products/{sp.get('handle', '')}",
                "price_sek": price,
                "product_type": sp.get("product_type", ""),
                "brand": sp.get("vendor", ""),
                "tags": sp.get("tags", []),
                "image_url": sp.get("images", [{}])[0].get("src", "") if sp.get("images") else "",
                "in_stock": variants[0].get("available", False) if variants else False,
                "article_number": variants[0].get("sku", "") if variants else "",
                "scraped_at": datetime.utcnow().isoformat(),
            }
            
            # Multiple variants = different sizes/options
            if len(variants) > 1:
                p["variants"] = [
                    {"title": v.get("title"), "price": v.get("price"), "sku": v.get("sku"), "available": v.get("available")}
                    for v in variants
                ]
            
            if p.get("name") and p.get("price_sek"):
                all_products.append(p)
        
        print(f"  Page {page}: {len(products)} products")
        
        if len(products) < 250:
            break
        
        page += 1
        time.sleep(1.5)
    
    with open("zetas_products.json", "w", encoding="utf-8") as f:
        json.dump({
            "retailer": "zetas",
            "scraped_at": datetime.utcnow().isoformat(),
            "total_products": len(all_products),
            "products": all_products,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*55}")
    print(f"DONE! {len(all_products)} products → zetas_products.json")
    prices = [p["price_sek"] for p in all_products if p.get("price_sek")]
    if prices:
        print(f"Prices: {min(prices):.0f} – {max(prices):.0f} kr (avg {sum(prices)/len(prices):.0f} kr)")
    types = {}
    for p in all_products:
        t = p.get("product_type", "unknown")
        types[t] = types.get(t, 0) + 1
    print(f"Product types: {dict(sorted(types.items(), key=lambda x: -x[1])[:10])}")

if __name__ == "__main__":
    main()
