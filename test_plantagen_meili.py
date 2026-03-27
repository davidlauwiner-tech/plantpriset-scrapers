import requests
import json

# Meilisearch endpoint from intercepted calls
MEILI_URL = "https://ms-a6530e77c471-12443.lon.meilisearch.io"

# First, try to search without a key (Meilisearch public search)
# The key might be embedded in the request
resp = requests.post(f"{MEILI_URL}/multi-search", json={
    "queries": [{
        "indexUid": "products_sv-SE",
        "q": "tomat",
        "limit": 5,
    }]
}, headers={"Content-Type": "application/json"}, timeout=10)

print(f"No key: HTTP {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    hits = data.get("results", [{}])[0].get("hits", [])
    print(f"Hits: {len(hits)}")
    if hits:
        print(json.dumps(hits[0], indent=2, ensure_ascii=False)[:1000])
elif resp.status_code == 401:
    print("Need API key — let me extract it from the page")
    
    # Get the key from Plantagen's JS
    page_resp = requests.get("https://plantagen.se/se/vaxter/froer", headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }, timeout=15)
    
    import re
    # Look for Meilisearch API key in the HTML/JS
    keys = re.findall(r'(?:apiKey|searchKey|MEILI_API_KEY|meilisearch)["\s:=]+["\']([a-zA-Z0-9_-]{20,})["\']', page_resp.text)
    print(f"Found keys: {keys[:3]}")
    
    # Also look in script src URLs
    for match in re.finditer(r'["\']([^"\']*meilisearch[^"\']*)["\']', page_resp.text[:50000]):
        print(f"  Meili ref: {match.group(1)[:100]}")
