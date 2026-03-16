import requests
import json

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
})

# First visit the product page to get cookies
session.get("https://www.nelsongarden.se/produkter/solros-p88358/")

# The embedded JSON showed apiRoute: /api/products/produkter/solros-p88358/
# Let's try that and variations
test_urls = [
    "https://www.nelsongarden.se/api/products/produkter/solros-p88358/",
    "https://www.nelsongarden.se/api/products/produkter/solros-p88358",
    "https://www.nelsongarden.se/api/products/88358",
    "https://www.nelsongarden.se/api/products?id=88358",
    # Try with market/language params
    "https://www.nelsongarden.se/api/products/produkter/solros-p88358/?market=swe&lang=sv",
    "https://www.nelsongarden.se/api/products/produkter/solros-p88358/?currency=SEK",
]

for url in test_urls:
    try:
        resp = session.get(url, timeout=10)
        ct = resp.headers.get("content-type", "")
        print(f"[{resp.status_code}] {url}")
        if resp.status_code == 200 and "json" in ct:
            data = resp.json()
            # Look for prices in the response
            text = json.dumps(data)
            if "price" in text.lower() or "Price" in text:
                # Find price fields
                import re
                for m in re.finditer(r'"(\w*[Pp]rice\w*)":\s*([0-9.]+|null)', text):
                    if m.group(2) != "null" and m.group(2) != "0.0":
                        print(f"  PRICE FOUND: {m.group(1)} = {m.group(2)}")
                if "null" in text and "price" in text.lower():
                    print(f"  (prices still null)")
            print(f"  Response size: {len(text)} bytes")
            print(f"  First 500 chars: {text[:500]}")
        elif resp.status_code == 200:
            print(f"  Content-Type: {ct}")
            print(f"  Body: {resp.text[:300]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()
