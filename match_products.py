#!/usr/bin/env python3
"""
Plantpriset — Product matching engine.
Groups listings across retailers into canonical products.
"""
import json, os, re, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import requests

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

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
        print(f"  API Error {resp.status_code}: {resp.text[:200]}")
        return None
    try:
        return resp.json()
    except:
        return resp.text

def normalize(name):
    n = name.lower().strip()
    for remove in [", fröer", " fröer", " frö", ", ekologisk", ", eko", " eko",
                    " organic", ", organic", " krav", ", krav"]:
        n = n.replace(remove, "")
    n = re.sub(r"[''\"()\[\]]", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n

def make_slug(name):
    s = name.lower().strip()
    s = s.replace("å", "a").replace("ä", "a").replace("ö", "o")
    s = s.replace("é", "e").replace("ü", "u")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:300]

def main():
    # Step 1: Fetch all listings from Supabase
    print("Fetching listings from Supabase...")
    all_listings = []
    offset = 0
    while True:
        result = api("GET", "listings", params={
            "select": "id,retailer_id,name,price_sek,latin_name,image_url",
            "limit": "1000",
            "offset": str(offset),
            "order": "id.asc",
        })
        if not result or len(result) == 0:
            break
        all_listings.extend(result)
        offset += 1000
        if len(result) < 1000:
            break

    print(f"  {len(all_listings)} listings fetched")

    # Step 2: Group by normalized name
    groups = defaultdict(list)
    for listing in all_listings:
        key = normalize(listing["name"])
        groups[key].append(listing)

    # Step 3: Find multi-retailer matches
    multi = {k: v for k, v in groups.items()
             if len(set(l["retailer_id"] for l in v)) >= 2}

    print(f"  {len(groups)} unique names")
    print(f"  {len(multi)} matched across 2+ retailers")

    # Step 4: Create canonical products + link listings
    print("\nCreating canonical products...")
    created = 0
    linked = 0

    for name, listings in sorted(multi.items()):
        # Use the first listing's details for the canonical product
        first = listings[0]
        slug = make_slug(name)

        # Pick best image (prefer one that exists)
        image = next((l["image_url"] for l in listings if l.get("image_url")), "")

        # Pick latin name if any listing has one
        latin = next((l["latin_name"] for l in listings if l.get("latin_name")), None)

        # Create canonical product
        product_data = {
            "slug": slug,
            "name": name.title(),
            "latin_name": latin,
            "image_url": image or "",
        }

        result = api("POST", "products", data=[product_data])
        if result and len(result) > 0:
            product_id = result[0]["id"]
            created += 1

            # Link all listings to this product
            links = []
            for listing in listings:
                links.append({
                    "product_id": product_id,
                    "listing_id": listing["id"],
                    "match_score": 100.0,
                })

            link_result = api("POST", "product_listings", data=links)
            if link_result:
                linked += len(links)

            if created % 100 == 0:
                print(f"  {created} products created, {linked} links...")

    # Also create single-retailer products (no comparison, but still indexed)
    print("\nCreating single-retailer products...")
    singles = 0
    for name, listings in groups.items():
        if name in multi:
            continue
        first = listings[0]
        slug = make_slug(name)
        latin = next((l["latin_name"] for l in listings if l.get("latin_name")), None)
        image = next((l["image_url"] for l in listings if l.get("image_url")), "")

        product_data = {
            "slug": slug,
            "name": name.title(),
            "latin_name": latin,
            "image_url": image or "",
        }

        result = api("POST", "products", data=[product_data])
        if result and len(result) > 0:
            product_id = result[0]["id"]
            singles += 1
            links = [{"product_id": product_id, "listing_id": l["id"], "match_score": 100.0}
                     for l in listings]
            api("POST", "product_listings", data=links)
            linked += len(links)

            if singles % 500 == 0:
                print(f"  {singles} single products...")

    print(f"\n{'='*55}")
    print(f"MATCHING COMPLETE")
    print(f"{'='*55}")
    print(f"  Multi-retailer products: {created}")
    print(f"  Single-retailer products: {singles}")
    print(f"  Total products: {created + singles}")
    print(f"  Total links: {linked}")

if __name__ == "__main__":
    main()
