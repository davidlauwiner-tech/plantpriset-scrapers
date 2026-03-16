import requests
import json
import re

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
})

# First get the product API to find variation codes (SKUs)
resp = session.get("https://www.nelsongarden.se/api/products/produkter/solros-p88358/")
data = resp.json()

# Extract variation codes from the response
text = json.dumps(data)
codes = re.findall(r'"variationCodes":\s*\[([^\]]+)\]', text)
print(f"Variation codes found: {codes}")

# Also find the code/contentId 
code_matches = re.findall(r'"code":\s*"(\d+)"', text)
print(f"Codes: {code_matches[:10]}")

# Now try pricing endpoints
pricing_urls = [
    "https://www.nelsongarden.se/api/pricing",
    "https://www.nelsongarden.se/api/prices",
    "https://www.nelsongarden.se/api/cart/prices",
    "https://www.nelsongarden.se/api/catalog/prices",
    "https://www.nelsongarden.se/api/market/prices",
]

for url in pricing_urls:
    for method in ["GET", "POST"]:
        try:
            if method == "GET":
                r = session.get(url, timeout=5)
            else:
                r = session.post(url, json={"codes": ["90122"]}, timeout=5)
            print(f"[{r.status_code}] {method} {url} — {r.headers.get('content-type','')[:30]}")
            if r.status_code < 500 and len(r.text) > 5:
                print(f"  {r.text[:200]}")
        except:
            pass

# Check the full HTML for any XHR/fetch calls to pricing APIs
print("\n=== Searching HTML for price API patterns ===")
resp2 = session.get("https://www.nelsongarden.se/produkter/solros-p88358/")
html = resp2.text
for pattern in ["/api/pric", "/api/cart", "/api/market", "fetchPrices", "getPrices", "loadPrices", "priceService"]:
    idx = html.find(pattern)
    if idx >= 0:
        print(f"  Found '{pattern}' at {idx}: ...{html[max(0,idx-30):idx+100]}...")
