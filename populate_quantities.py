#!/usr/bin/env python3
"""
Plantpriset — Extract quantity/pack info from listing names and URLs.
Updates the quantity field on listings where pack sizes are detected.
"""
import os, sys, re
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

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# Patterns to detect quantity in names and URLs
QUANTITY_PATTERNS = [
    # "6-pack", "6 pack", "6-p", "6 st", "6st"
    (r'(\d+)\s*-?\s*pack', int),
    (r'(\d+)\s*-?\s*st\b', int),
    (r'(\d+)\s*-?\s*p\b', int),
    # "x3", "x 6"
    (r'x\s*(\d+)\b', int),
    # Swedish: "3 lökar", "6 knölar", "10 frön"
    (r'(\d+)\s*lökar', int),
    (r'(\d+)\s*knölar', int),
    (r'(\d+)\s*frön', int),
    (r'(\d+)\s*pluggplantor', int),
    (r'(\d+)\s*plantor', int),
    # Weight-based (bags of soil, fertilizer)
    (r'(\d+)\s*kg\b', None),  # Skip weight-based, not quantity
    (r'(\d+)\s*liter\b', None),
    (r'(\d+)\s*[lL]\b', None),
]


def extract_quantity(name, url):
    """Extract quantity from product name or URL. Returns quantity or 1."""
    text = (name + " " + url).lower()
    
    for pattern, converter in QUANTITY_PATTERNS:
        match = re.search(pattern, text)
        if match and converter:
            qty = converter(match.group(1))
            if 2 <= qty <= 100:  # Reasonable range for plant packs
                return qty
    
    return 1


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        sys.exit(1)

    print("Fetching all listings...")
    listings = []
    offset = 0
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/listings",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params={
                "select": "id,name,product_url",
                "limit": "1000",
                "offset": str(offset),
                "order": "id.asc",
            },
            timeout=30,
        )
        if r.status_code != 200:
            print(f"Error: {r.status_code}")
            break
        batch = r.json()
        if not batch:
            break
        listings.extend(batch)
        offset += 1000
        if len(batch) < 1000:
            break

    print(f"  {len(listings)} listings\n")

    # Extract quantities
    updates = []
    qty_distribution = {}
    for l in listings:
        qty = extract_quantity(l["name"], l["product_url"])
        if qty > 1:
            updates.append((l["id"], qty))
            qty_distribution[qty] = qty_distribution.get(qty, 0) + 1

    print(f"Found {len(updates)} listings with quantity > 1:")
    for qty, count in sorted(qty_distribution.items()):
        print(f"  {qty}-pack: {count} listings")

    # Show some examples
    print(f"\nExamples:")
    for lid, qty in updates[:15]:
        l = next(x for x in listings if x["id"] == lid)
        print(f"  [{qty}st] {l['name'][:50]}")

    # Update database
    print(f"\nUpdating {len(updates)} listings...")
    updated = 0
    for lid, qty in updates:
        r = requests.patch(
            f"{SUPABASE_URL}/rest/v1/listings?id=eq.{lid}",
            headers=HEADERS,
            json={"quantity": qty},
            timeout=15,
        )
        if r.status_code in (200, 204):
            updated += 1
        else:
            print(f"  Error updating {lid}: {r.status_code}")

    print(f"\n{'='*50}")
    print(f"QUANTITY EXTRACTION COMPLETE")
    print(f"  Updated: {updated} listings with pack quantities")
    print(f"  Remaining: {len(listings) - updated} listings at quantity=1")


if __name__ == "__main__":
    main()
