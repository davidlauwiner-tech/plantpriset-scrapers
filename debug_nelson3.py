import requests

# Nelson Garden product URLs contain an ID like p88358, p90336
# Let's check if there's an API endpoint that serves product data as JSON

test_urls = [
    # Try common API patterns
    "https://www.nelsongarden.se/api/products/88358",
    "https://www.nelsongarden.se/api/product/88358",
    "https://www.nelsongarden.se/api/v1/products/88358",
    "https://www.nelsongarden.se/api/catalog/products/88358",
    # Episerver/Optimizely patterns (from their robots.txt blocking /episerver)
    "https://www.nelsongarden.se/api/content/produkter/solros-p88358",
    # Try fetching product page with JSON accept header
    "https://www.nelsongarden.se/produkter/solros-p88358/",
]

headers_json = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}
headers_html = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

for url in test_urls:
    try:
        resp = requests.get(url, headers=headers_json, timeout=10, allow_redirects=False)
        content_type = resp.headers.get("content-type", "")
        print(f"[{resp.status_code}] {content_type[:40]:40s} {url}")
        if "json" in content_type:
            print(f"  JSON! {resp.text[:300]}")
    except Exception as e:
        print(f"[ERR] {url} - {e}")

# Also check if the HTML page has embedded JSON (Next.js __NEXT_DATA__ or similar)
print("\n=== Checking for embedded JSON in HTML ===")
resp = requests.get("https://www.nelsongarden.se/produkter/solros-p88358/", headers=headers_html, timeout=10)
html = resp.text
for marker in ["__NEXT_DATA__", "window.__data", "application/ld+json", "product", "Price", "price"]:
    idx = html.find(marker)
    if idx >= 0:
        print(f"  Found '{marker}' at position {idx}")
        print(f"  Context: ...{html[max(0,idx-20):idx+200]}...")
        print()
