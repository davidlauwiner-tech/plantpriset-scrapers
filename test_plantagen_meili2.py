import requests
import json

MEILI_URL = "https://ms-a6530e77c471-12443.lon.meilisearch.io"
MEILI_KEY = "a2159774cf867351b1195f0a05a4fb9f4693c781bd3e89a3ff5e856637710594"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {MEILI_KEY}",
}

# Search for fröer with full product data
resp = requests.post(f"{MEILI_URL}/multi-search", json={
    "queries": [{
        "indexUid": "products_sv-SE",
        "q": "tomat frö",
        "limit": 5,
        "attributesToRetrieve": ["id", "title", "description", "image_url", "alias", 
                                  "sku", "discount", "market_price", "price", "categories",
                                  "brand", "in_stock", "filterable"],
    }]
}, headers=HEADERS, timeout=10)

print(f"HTTP {resp.status_code}")
data = resp.json()
hits = data.get("results", [{}])[0].get("hits", [])
total = data.get("results", [{}])[0].get("estimatedTotalHits", 0)
print(f"Hits: {len(hits)}, Total estimated: {total}")

if hits:
    print(f"\nFirst product (all fields):")
    print(json.dumps(hits[0], indent=2, ensure_ascii=False)[:2000])

# Now get total count of ALL products
print(f"\n=== Total catalog size ===")
resp2 = requests.post(f"{MEILI_URL}/multi-search", json={
    "queries": [{
        "indexUid": "products_sv-SE",
        "q": "",
        "limit": 0,
    }]
}, headers=HEADERS, timeout=10)
total_all = resp2.json().get("results", [{}])[0].get("estimatedTotalHits", 0)
print(f"Total products in Plantagen index: {total_all}")

# Search fröer specifically
resp3 = requests.post(f"{MEILI_URL}/multi-search", json={
    "queries": [{
        "indexUid": "products_sv-SE",
        "q": "",
        "limit": 3,
        "filter": "categories.lvl0 = 'Fröer'",
        "attributesToRetrieve": ["title", "market_price", "price", "alias", "sku", "brand", "categories"],
    }]
}, headers=HEADERS, timeout=10)
print(f"\nFröer category filter: HTTP {resp3.status_code}")
if resp3.status_code == 200:
    froer = resp3.json().get("results", [{}])[0]
    print(f"  Hits: {froer.get('estimatedTotalHits', '?')}")
    for h in froer.get("hits", []):
        print(f"  {h.get('title','?'):40s} {h.get('market_price','?')} kr")
