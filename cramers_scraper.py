import json
import re
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://shop.cramersblommor.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "sv-SE,sv;q=0.9",
}

CATEGORY_URLS = [
    "/froer/",
    "/froer/blommande-ettariga-annueller/",
    "/froer/blommande-tvariga-bienner/",
    "/froer/blommande-flerariga-perenner/",
    "/froer/luktart/",
    "/froer/palettbladsfroer/",
    "/froer/ekologiska/",
    "/froer/gronsaksfroer/",
    "/froer/froer-kryddvaxter/",
    "/froer/micro-leaf-groddar/",
    "/froer/grasfron/",
    "/froer/jora-dahl/",
    "/froer/nordfro/",
    "/odlingstillbehor/",
    "/tradgardstillbehor/",
]

def extract_product(card, cat_url):
    p = {"retailer": "cramers", "category_url": cat_url}
    
    # data attributes on the li element
    p["article_number"] = card.get("data-artno", "")
    p["in_stock"] = card.get("data-buyable") == "1"
    p["on_sale"] = card.get("data-iscampaign") == "1"
    
    data_price = card.get("data-price")
    if data_price:
        try:
            p["price_sek"] = float(data_price)
        except: pass
    
    p["name"] = card.get("data-title", "")
    
    # Name from h3
    h3 = card.select_one(".product-item__heading")
    if h3:
        p["name"] = h3.get_text(strip=True)
    
    # Latin name
    latin = card.select_one(".product-item__heading--latin")
    if latin:
        p["latin_name"] = latin.get_text(strip=True)
    
    # URL
    link = card.select_one("a[href]")
    if link:
        href = link.get("href", "")
        if href:
            p["product_url"] = f"{BASE_URL}{href}" if not href.startswith("http") else href
    
    # Price from span.price (backup)
    if not p.get("price_sek"):
        price_el = card.select_one(".price")
        if price_el:
            cleaned = re.sub(r'[^\d.,]', '', price_el.get_text().replace(",", "."))
            try:
                p["price_sek"] = float(cleaned)
            except: pass
    
    # Campaign price
    camp_el = card.select_one(".price--campaign, .price--sale, [class*='campaign']")
    if camp_el:
        cleaned = re.sub(r'[^\d.,]', '', camp_el.get_text().replace(",", "."))
        try:
            p["price_campaign_sek"] = float(cleaned)
            p["price_sek"] = p["price_campaign_sek"]
        except: pass
    
    # Image
    img = card.select_one("img")
    if img:
        src = img.get("src", "")
        if src:
            p["image_url"] = f"{BASE_URL}{src}" if not src.startswith("http") else src
    
    p["scraped_at"] = datetime.utcnow().isoformat()
    return p

def main():
    print("=" * 55)
    print("PLANTPRISET — Cramers Blommor Scraper")
    print("=" * 55)
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_products = []
    for i, cat in enumerate(CATEGORY_URLS, 1):
        print(f"[{i}/{len(CATEGORY_URLS)}] {cat}")
        try:
            resp = session.get(f"{BASE_URL}{cat}", timeout=30)
            if resp.status_code != 200:
                print(f"  HTTP {resp.status_code}")
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(".product-item")
            count = 0
            for card in cards:
                prod = extract_product(card, cat)
                if prod.get("name") and prod.get("price_sek"):
                    all_products.append(prod)
                    count += 1
            print(f"  {count} products")
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(2)
    
    seen = set()
    unique = []
    for p in all_products:
        key = p.get("product_url", p.get("name", ""))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    
    with open("cramers_products.json", "w", encoding="utf-8") as f:
        json.dump({
            "retailer": "cramers",
            "scraped_at": datetime.utcnow().isoformat(),
            "total_products": len(unique),
            "products": unique,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*55}")
    print(f"DONE! {len(unique)} unique products → cramers_products.json")
    prices = [p["price_sek"] for p in unique if p.get("price_sek")]
    if prices:
        print(f"Prices: {min(prices):.0f} – {max(prices):.0f} kr (avg {sum(prices)/len(prices):.0f} kr)")
    with_latin = sum(1 for p in unique if p.get("latin_name"))
    print(f"With Latin names: {with_latin}/{len(unique)}")

if __name__ == "__main__":
    main()
