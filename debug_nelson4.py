import requests
import json
import re

resp = requests.get("https://www.nelsongarden.se/produkter/solros-p88358/", headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
})
html = resp.text

# Find the embedded JSON data — look for large JSON blocks
# Try window.__data or similar patterns
for pattern in [r'window\.__data\s*=\s*({.+?});', r'window\.__INITIAL_STATE__\s*=\s*({.+?});', r'<script[^>]*>.*?(\{.*?"salePriceInclTax".*?\})', r'data-initial-state=["\']({.+?})["\']']:
    match = re.search(pattern, html, re.DOTALL)
    if match:
        print(f"Found pattern: {pattern[:50]}")
        print(f"Length: {len(match.group(1))}")
        try:
            data = json.loads(match.group(1))
            print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
        except:
            print(match.group(1)[:2000])
        break

# Also try to find script tags with JSON
print("\n=== Looking for script tags with product data ===")
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "html.parser")
for script in soup.find_all("script"):
    text = script.string or ""
    if "salePriceInclTax" in text or "displayPrice" in text:
        print(f"Found script with price data (length {len(text)}):")
        # Find the JSON object
        start = text.find('{')
        if start >= 0:
            print(text[start:start+2000])
        break
    if "product" in text.lower() and "price" in text.lower() and len(text) > 200:
        print(f"Found script with product+price (length {len(text)}):")
        print(text[:2000])
        break
