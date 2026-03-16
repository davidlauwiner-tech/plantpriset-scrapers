import json
import re
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.simbadusa.se"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "sv-SE,sv;q=0.9",
}

# Simbadusa uses /sv/articles/CATEGORY_ID/name?page=N
CATEGORY_URLS = [
    "/sv/articles/20/froer",
    "/sv/articles/54/tillbehor",
]

def extract_product(card, cat_url):
    p = {"retailer": "simbadusa", "category_url": cat_url}
    
    # Name
    name_el = card.select_one("h2, h3, .product-name, [class*='title'], [class*='name']")
    if name_el:
        p["name"] = name_el.get_text(strip=True)
    
    # If no name from heading, try link text
    if not p.get("name"):
        link = card.select_one("a")
        if link:
            text = link.get_text(strip=True)
            if text and len(text) > 3:
                p["name"] = text
    
    # URL
    link = card.select_one("a[href]")
    if link:
        href = link.get("href", "")
        if href:
            p["product_url"] = f"{BASE_URL}{href}" if not href.startswith("http") else href
    
    # Price
    for price_sel in [".price", "[class*='price']", "[class*='Price']"]:
        price_el = card.select_one(price_sel)
        if price_el:
            text = price_el.get_text(strip=True)
            cleaned = re.sub(r'[^\d.,]', '', text.replace(",", "."))
            try:
                p["price_sek"] = float(cleaned)
                break
            except: pass
    
    # If no price from selector, try regex on card text
    if not p.get("price_sek"):
        card_text = card.get_text()
        match = re.search(r'(\d+[.,]?\d*)\s*kr', card_text)
        if match:
            try:
                p["price_sek"] = float(match.group(1).replace(",", "."))
            except: pass
    
    # Image
    img = card.select_one("img")
    if img:
        src = img.get("src") or img.get("data-src") or ""
        if src:
            p["image_url"] = src if src.startswith("http") else f"{BASE_URL}{src}"
    
    # Brand
    brand_el = card.select_one("[class*='brand'], [class*='Brand'], [class*='manufacturer']")
    if brand_el:
        p["brand"] = brand_el.get_text(strip=True)
    
    p["scraped_at"] = datetime.utcnow().isoformat()
    return p

def scrape_category(session, cat_url):
    products = []
    page = 1
    while True:
        url = f"{BASE_URL}{cat_url}"
        if page > 1:
            url += f"?page={page}"
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Find product cards — try various selectors
            cards = soup.select(".product-item, .product-card, [class*='product'], article.product, .item")
            if not cards:
                # Try finding by price proximity
                cards = []
                for el in soup.find_all(string=re.compile(r'\d+\s*kr')):
                    parent = el.find_parent(["li", "div", "article"])
                    if parent and parent not in cards:
                        cards.append(parent)
            
            if not cards:
                break
            
            before = len(products)
            for card in cards:
                prod = extract_product(card, cat_url)
                if prod.get("name") and prod.get("price_sek"):
                    products.append(prod)
            
            new = len(products) - before
            if new == 0:
                break
            
            # Check for next page
            next_link = soup.select_one(f'a[href*="page={page+1}"]')
            if next_link:
                page += 1
                time.sleep(1.5)
            else:
                break
        except Exception as e:
            print(f"    ERROR page {page}: {e}")
            break
    return products, page

def main():
    print("=" * 55)
    print("PLANTPRISET — Simbadusa Scraper")
    print("=" * 55)
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_products = []
    for i, cat in enumerate(CATEGORY_URLS, 1):
        products, pages = scrape_category(session, cat)
        page_info = f" ({pages} pages)" if pages > 1 else ""
        print(f"[{i}/{len(CATEGORY_URLS)}] {cat} → {len(products)} products{page_info}")
        all_products.extend(products)
        time.sleep(1.5)
    
    seen = set()
    unique = []
    for p in all_products:
        key = p.get("product_url", p.get("name", ""))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    
    with open("simbadusa_products.json", "w", encoding="utf-8") as f:
        json.dump({
            "retailer": "simbadusa",
            "scraped_at": datetime.utcnow().isoformat(),
            "total_products": len(unique),
            "products": unique,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*55}")
    print(f"DONE! {len(unique)} unique products → simbadusa_products.json")
    prices = [p["price_sek"] for p in unique if p.get("price_sek")]
    if prices:
        print(f"Prices: {min(prices):.0f} – {max(prices):.0f} kr (avg {sum(prices)/len(prices):.0f} kr)")

if __name__ == "__main__":
    main()
