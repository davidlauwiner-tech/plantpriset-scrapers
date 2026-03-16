import requests
from bs4 import BeautifulSoup
import re

resp = requests.get("https://www.blomsterlandet.se/produkter/vaxter/froer/gronsaksfroer/", headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}, timeout=15)

print(f"HTTP {resp.status_code} ({len(resp.text)} bytes)")

# Check for prices
prices = re.findall(r'(\d+[.,]?\d*)\s*kr', resp.text)
print(f"Prices with 'kr': {prices[:10]}")

# Check for öre-format prices
ore_prices = re.findall(r'"price":\s*(\d+)', resp.text)
print(f"JSON price fields: {ore_prices[:10]}")

soup = BeautifulSoup(resp.text, "html.parser")

# Find product-like elements
for sel in [".product", "[class*='product']", "[class*='Product']", "[class*='card']", "[class*='Card']", "[class*='item']", "article"]:
    els = soup.select(sel)
    if els and len(els) > 2:
        print(f"\nSelector '{sel}': {len(els)} elements")
        first = els[0]
        print(f"  Classes: {first.get('class')}")
        print(f"  Text: {first.get_text(strip=True)[:150]}")

# Check for JSON-LD or embedded data
for script in soup.find_all("script", type="application/ld+json"):
    print(f"\nJSON-LD: {script.string[:300] if script.string else 'empty'}")

# Check for __NEXT_DATA__ or similar
for script in soup.find_all("script"):
    text = script.string or ""
    if "price" in text.lower() and len(text) > 500:
        print(f"\nScript with price ({len(text)} bytes): {text[:400]}")
        break
