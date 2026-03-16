import json
import re
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.blomsterlandet.se"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "sv-SE,sv;q=0.9",
}

CATEGORY_URLS = [
    # Fröer
    "/produkter/vaxter/froer/gronsaksfroer/bonor-arter/",
    "/produkter/vaxter/froer/gronsaksfroer/chili-paprika/",
    "/produkter/vaxter/froer/gronsaksfroer/groddar/",
    "/produkter/vaxter/froer/gronsaksfroer/gurka-melon/",
    "/produkter/vaxter/froer/gronsaksfroer/kalvaxter/",
    "/produkter/vaxter/froer/gronsaksfroer/lokvaxter/",
    "/produkter/vaxter/froer/gronsaksfroer/pumpa-squash/",
    "/produkter/vaxter/froer/gronsaksfroer/rotfrukter/",
    "/produkter/vaxter/froer/gronsaksfroer/sallat-bladvaxter/",
    "/produkter/vaxter/froer/gronsaksfroer/tomat-aubergin/",
    "/produkter/vaxter/froer/gronsaksfroer/ovriga-gronsaksfroer/",
    "/produkter/vaxter/froer/blomsterfroer/",
    "/produkter/vaxter/froer/kryddfroer/",
    "/produkter/vaxter/froer/angsfroer/",
    # Tillbehör
    "/produkter/tillbehor/jord-godsel-naring/",
    "/produkter/tillbehor/krukor-ytterkrukor/",
    "/produkter/tillbehor/odling-drivhus/",
    "/produkter/tillbehor/redskap-verktyg/",
    "/produkter/tillbehor/bevattning/",
    "/produkter/tillbehor/vaxtskydd/",
    "/produkter/tillbehor/vaxtbelysning/",
    # Växter
    "/produkter/vaxter/perenner/",
    "/produkter/vaxter/buskar/",
    "/produkter/vaxter/trad/",
    "/produkter/vaxter/krukvaxter/",
    "/produkter/vaxter/utplanteringsvaxter/",
    "/produkter/vaxter/lokar-knolar/",
]

def extract_product(card, cat_url):
    p = {"retailer": "blomsterlandet", "category_url": cat_url}
    
    # Name from h2
    name_el = card.select_one("h2")
    if name_el:
        p["name"] = name_el.get_text(strip=True)
    
    # Brand from the descriptor p tag
    brand_el = card.select_one("p[class*='ProductDescriptor']")
    if brand_el:
        p["brand"] = brand_el.get_text(strip=True)
    
    # Product URL from parent <a>
    parent_link = card.find_parent("a")
    if parent_link:
        href = parent_link.get("href", "")
        if href:
            p["product_url"] = f"{BASE_URL}{href}" if not href.startswith("http") else href
    
    # Price: kronor in Normal span, öre in Elevated span
    kr_el = card.select_one("[class*='Normal-sc']")
    ore_el = card.select_one("[class*='Elevated-sc']")
    if kr_el:
        kr = kr_el.get_text(strip=True)
        ore = ore_el.get_text(strip=True) if ore_el else "00"
        try:
            p["price_sek"] = float(f"{kr}.{ore}")
        except:
            pass
    
    # Sale price — check for campaign/sale styling
    sale_el = card.select_one("[class*='Campaign'], [class*='Sale'], [class*='campaign']")
    if sale_el:
        p["on_sale"] = True
    
    # Original price (if on sale)
    ord_el = card.select_one("[class*='Ordinary'], [class*='ordinary'], [class*='OrdPrice']")
    if ord_el:
        ord_text = ord_el.get_text(strip=True)
        ord_price = re.sub(r'[^\d]', '', ord_text)
        if ord_price:
            try:
                p["price_original_sek"] = float(ord_price) / 100
            except:
                pass
    
    # Stock status
    stock_el = card.select_one("[class*='stock'], [class*='Stock'], [class*='lager']")
    if stock_el:
        stock_text = stock_el.get_text(strip=True).lower()
        p["in_stock"] = "i lager" in stock_text or "lager" in stock_text
    
    # Image
    img = card.select_one("img")
    if img:
        src = img.get("src") or img.get("data-src") or ""
        if src:
            p["image_url"] = src if src.startswith("http") else f"{BASE_URL}{src}"
    
    p["scraped_at"] = datetime.utcnow().isoformat()
    return p

def scrape_category(session, cat_url):
    products = []
    page_num = 1
    while True:
        url = f"{BASE_URL}{cat_url}"
        if page_num > 1:
            separator = "&" if "?" in cat_url else "?"
            url = f"{BASE_URL}{cat_url}{separator}page={page_num}&sorting=Name"
        
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                break
            
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(".wrapper-big-card")
            
            if not cards:
                break
            
            for card in cards:
                prod = extract_product(card, cat_url)
                if prod.get("name") and prod.get("price_sek"):
                    products.append(prod)
            
            # Check for next page
            next_link = soup.select_one(f'a[href*="page={page_num + 1}"]')
            if next_link:
                page_num += 1
                time.sleep(1.5)
            else:
                break
        except Exception as e:
            print(f"    ERROR page {page_num}: {e}")
            break
    
    return products, page_num

def main():
    print("=" * 55)
    print("PLANTPRISET — Blomsterlandet Scraper")
    print("=" * 55)
    print(f"Categories: {len(CATEGORY_URLS)}")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    print("Getting cookies...")
    session.get(BASE_URL, timeout=15)
    time.sleep(1)
    
    all_products = []
    for i, cat in enumerate(CATEGORY_URLS, 1):
        products, pages = scrape_category(session, cat)
        page_info = f" ({pages} pages)" if pages > 1 else ""
        print(f"[{i}/{len(CATEGORY_URLS)}] {cat} → {len(products)} products{page_info}")
        all_products.extend(products)
        time.sleep(1.5)
    
    # Deduplicate
    seen = set()
    unique = []
    for p in all_products:
        key = p.get("product_url", p.get("name", ""))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    
    with open("blomsterlandet_products.json", "w", encoding="utf-8") as f:
        json.dump({
            "retailer": "blomsterlandet",
            "scraped_at": datetime.utcnow().isoformat(),
            "total_products": len(unique),
            "categories_scraped": len(CATEGORY_URLS),
            "products": unique,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*55}")
    print(f"DONE! {len(unique)} unique products → blomsterlandet_products.json")
    prices = [p["price_sek"] for p in unique if p.get("price_sek")]
    if prices:
        print(f"Prices: {min(prices):.0f} – {max(prices):.0f} kr (avg {sum(prices)/len(prices):.0f} kr)")
    brands = {}
    for p in unique:
        b = p.get("brand", "unknown")
        brands[b] = brands.get(b, 0) + 1
    print(f"Brands: {dict(sorted(brands.items(), key=lambda x: -x[1])[:10])}")

if __name__ == "__main__":
    main()
