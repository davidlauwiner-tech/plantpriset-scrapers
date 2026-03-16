import requests
import json
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# === ZETAS (Shopify?) ===
print("=== ZETAS ===")
for url in ["https://zetas.se/products.json?limit=3", "https://zetas.se/collections/all/products.json?limit=3"]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        print(f"[{resp.status_code}] {url}")
        if resp.status_code == 200 and "json" in resp.headers.get("content-type",""):
            data = resp.json()
            products = data.get("products", [])
            print(f"  Products: {len(products)}")
            if products:
                p = products[0]
                price = p.get("variants", [{}])[0].get("price", "?")
                print(f"  Example: {p.get('title')} — {price} SEK")
    except Exception as e:
        print(f"  {e}")

# === CRAMERS ===
print("\n=== CRAMERS ===")
resp = requests.get("https://shop.cramersblommor.com/froer/", headers=HEADERS, timeout=30)
soup = BeautifulSoup(resp.text, "html.parser")

# Try various product selectors
for sel in [".product-item", ".product-card", "li.product", ".productItem", 
            "[class*='roduct']", "article", ".item-box", ".product-box"]:
    els = soup.select(sel)
    if els and len(els) > 5:
        print(f"Selector '{sel}': {len(els)} elements")
        card = els[0]
        print(f"  HTML preview: {card.prettify()[:1500]}")
        print(f"\n  Elements with text:")
        for el in card.select("[class]"):
            text = el.get_text(strip=True)[:80]
            if text:
                print(f"    <{el.name}> class={el.get('class')} → {text}")
        break
