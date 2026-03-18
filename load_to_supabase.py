#!/usr/bin/env python3
"""Load scraped JSON into Supabase."""
import json, os, sys
from datetime import datetime
from pathlib import Path
import requests

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
OUTPUT_DIR = Path(__file__).parent / "output"

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
    sys.exit(1)

def api(method, table, data=None, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    resp = requests.request(method, url, headers=headers, json=data, timeout=30)
    if resp.status_code >= 400:
        print(f"  API Error {resp.status_code}: {resp.text[:300]}")
        return None
    try:
        return resp.json()
    except:
        return resp.text

def get_retailer_id(slug):
    result = api("GET", "retailers", params={"slug": f"eq.{slug}", "select": "id"})
    if result and len(result) > 0:
        return result[0]["id"]
    return None

def load_file(filepath):
    filepath = Path(filepath)
    print(f"\nLoading {filepath.name}...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    retailer_slug = data.get("retailer", "")
    products = data.get("products", [])
    if not retailer_slug or not products:
        print(f"  Skipping — empty")
        return 0
    retailer_id = get_retailer_id(retailer_slug)
    if not retailer_id:
        print(f"  ERROR: Retailer '{retailer_slug}' not found")
        return 0
    print(f"  Retailer: {retailer_slug} (id={retailer_id}), {len(products)} products")
    loaded = 0
    for i in range(0, len(products), 500):
        batch = products[i:i+500]
        rows = []
        for p in batch:
            url = (p.get("product_url") or "")[:1000]
            if not url:
                continue
            rows.append({
                "retailer_id": retailer_id,
                "name": (p.get("name") or "")[:500],
                "price_sek": p.get("price_sek"),
                "price_original": p.get("price_original_sek") or p.get("price_campaign_sek"),
                "product_url": url,
                "image_url": (p.get("image_url") or "")[:1000],
                "brand": (p.get("brand") or "")[:200],
                "latin_name": (p.get("latin_name") or "")[:300],
                "article_number": (p.get("article_number") or "")[:100],
                "category_url": (p.get("category_url") or "")[:500],
                "in_stock": p.get("in_stock", True),
                "properties": json.dumps(p.get("properties", [])),
                "scraped_at": p.get("scraped_at", datetime.utcnow().isoformat()),
            })
        if rows:
            result = api("POST", "listings", data=rows)
            if result is not None:
                loaded += len(rows)
                print(f"  Batch {i//500+1}: {len(rows)} rows")
            else:
                print(f"  Batch {i//500+1}: FAILED")
    print(f"  Loaded: {loaded}/{len(products)}")
    return loaded

def main():
    files = [Path(f) for f in sys.argv[1:]] if len(sys.argv) > 1 else sorted(OUTPUT_DIR.glob("*_products.json"))
    if not files:
        print(f"No JSON files in {OUTPUT_DIR}/")
        sys.exit(1)
    print(f"{'='*55}\nPLANTPRISET — Load to Supabase\n{'='*55}")
    total = sum(load_file(f) for f in files)
    print(f"\n{'='*55}\nDONE! {total} listings loaded\n{'='*55}")

if __name__ == "__main__":
    main()
