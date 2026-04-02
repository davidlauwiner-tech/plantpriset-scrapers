#!/usr/bin/env python3
"""
Plantpriset — Merge Duplicate Products

For each group of duplicates:
1. Pick the "best" product (shortest clean name, has image, has description)
2. Move all product_listings from losers to the winner
3. Delete the loser products

Run with --dry-run first to preview, then without to execute.
"""

import os, re, sys, requests
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
H_COUNT = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Prefer": "count=exact", "Range": "0-0"}


def normalize(name):
    n = name.strip()
    for suffix in [
        ", Högväxande", " Högväxande", ", Lågväxande", " Lågväxande",
        ", Kruktomat", ", Dwarftomat", ", Salladstomat", ", Piennolotomat",
        ", Vinbärstomat", ", Vintertomat",
        " - Kulturarv", ", Kulturarv",
        " - Nyhet 2026", ", Nyhet 2026",
        ", Squash",
    ]:
        n = n.replace(suffix, "")
    n = re.sub(r"^Fröer Nelson Garden\s+", "", n)
    n = re.sub(r",?\s*Big Pack$", "", n)
    n = n.replace("Högväxandea", "Högväxande")
    n = " ".join(n.split())
    return n


def pick_winner(products):
    """Pick the best product to keep from a group of duplicates."""
    scored = []
    for p in products:
        score = 0
        name = p["name"]
        # Prefer shorter names (less suffix clutter)
        score -= len(name) * 0.1
        # Prefer names WITHOUT "Fröer Nelson Garden" prefix
        if not name.startswith("Fröer Nelson Garden"):
            score += 10
        # Prefer products with images
        if p.get("image_url"):
            score += 5
        # Prefer products with descriptions
        if p.get("description"):
            score += 5
        # Prefer products with latin names
        if p.get("latin_name"):
            score += 3
        # Prefer products with a subcategory
        if p.get("subcategory_id"):
            score += 2
        # Penalize "Big Pack" variants
        if "Big Pack" in name:
            score -= 15
        # Penalize "Nyhet 2026" variants
        if "Nyhet 2026" in name:
            score -= 5
        scored.append((score, p))
    
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


# Fetch all products with descriptions
print("Fetching all products...")
all_products = []
offset = 0
while True:
    r = requests.get(
        f"{URL}/rest/v1/products?select=id,name,slug,subcategory_id,product_type,image_url,description,latin_name&order=name&limit=1000&offset={offset}",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
    )
    batch = r.json()
    if not batch:
        break
    all_products.extend(batch)
    offset += 1000

print(f"Total products: {len(all_products)}")

# Group by normalized name
groups = {}
for p in all_products:
    key = normalize(p["name"]).lower()
    if key not in groups:
        groups[key] = []
    groups[key].append(p)

dupes = {k: v for k, v in groups.items() if len(v) > 1}
print(f"Duplicate groups: {len(dupes)}")
print(f"Products to merge away: {sum(len(v) - 1 for v in dupes.values())}")

if DRY_RUN:
    print("\n*** DRY RUN — no changes will be made ***\n")

# Process each duplicate group
merged = 0
errors = 0
listings_moved = 0

for key, products in sorted(dupes.items()):
    winner = pick_winner(products)
    losers = [p for p in products if p["id"] != winner["id"]]
    
    if DRY_RUN:
        print(f"\n\"{key}\":")
        print(f"  KEEP: [{winner['id']}] {winner['name']}")
        for l in losers:
            print(f"  DROP: [{l['id']}] {l['name']}")
        continue
    
    for loser in losers:
        # 1. Move product_listings from loser to winner
        # First check if winner already has listings from the same retailer
        r = requests.get(
            f"{URL}/rest/v1/product_listings?product_id=eq.{loser['id']}&select=id,listing_id,match_score",
            headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
        )
        loser_pls = r.json() if r.status_code == 200 else []
        
        for pl in loser_pls:
            # Check if winner already has this listing
            r2 = requests.get(
                f"{URL}/rest/v1/product_listings?product_id=eq.{winner['id']}&listing_id=eq.{pl['listing_id']}&select=id",
                headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
            )
            existing = r2.json() if r2.status_code == 200 else []
            
            if existing:
                # Winner already has this listing, delete the loser's link
                requests.delete(
                    f"{URL}/rest/v1/product_listings?id=eq.{pl['id']}",
                    headers=H,
                )
            else:
                # Move the listing to the winner
                r3 = requests.patch(
                    f"{URL}/rest/v1/product_listings?id=eq.{pl['id']}",
                    headers=H,
                    json={"product_id": winner["id"]},
                )
                if r3.status_code < 300:
                    listings_moved += 1
                else:
                    print(f"  ERROR moving listing {pl['id']}: {r3.status_code} {r3.text}")
                    errors += 1
        
        # 2. If winner is missing image/description/latin_name, take from loser
        updates = {}
        if not winner.get("image_url") and loser.get("image_url"):
            updates["image_url"] = loser["image_url"]
            winner["image_url"] = loser["image_url"]
        if not winner.get("description") and loser.get("description"):
            updates["description"] = loser["description"]
            winner["description"] = loser["description"]
        if not winner.get("latin_name") and loser.get("latin_name"):
            updates["latin_name"] = loser["latin_name"]
            winner["latin_name"] = loser["latin_name"]
        
        if updates:
            requests.patch(
                f"{URL}/rest/v1/products?id=eq.{winner['id']}",
                headers=H,
                json=updates,
            )
        
        # 3. Delete the loser product
        r4 = requests.delete(
            f"{URL}/rest/v1/products?id=eq.{loser['id']}",
            headers=H,
        )
        if r4.status_code < 300:
            merged += 1
        else:
            print(f"  ERROR deleting [{loser['id']}] {loser['name']}: {r4.status_code} {r4.text}")
            errors += 1

if not DRY_RUN:
    print(f"\n{'='*60}")
    print(f"MERGE COMPLETE")
    print(f"  Products merged away: {merged}")
    print(f"  Listings moved: {listings_moved}")
    print(f"  Errors: {errors}")
    print(f"{'='*60}")
    
    # Verify counts
    r = requests.head(f"{URL}/rest/v1/products?select=id&limit=1", headers=H_COUNT)
    count = r.headers.get("content-range", "?/?").split("/")[-1]
    print(f"\n  Products remaining: {count}")
    
    r = requests.head(f"{URL}/rest/v1/product_listings?select=id&limit=1", headers=H_COUNT)
    count = r.headers.get("content-range", "?/?").split("/")[-1]
    print(f"  Product-listings remaining: {count}")
