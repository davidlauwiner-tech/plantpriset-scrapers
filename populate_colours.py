#!/usr/bin/env python3
"""
Plantpriset — Extract colour from product names and update the colour column.
"""
import os, sys, re
from pathlib import Path
from collections import Counter
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

# Colour extraction rules — order matters, first match wins
COLOUR_RULES = [
    # Swedish colour words
    ("röd",     [r'\bröd\b', r'\brод\b', r'\brod\b', r'\bröda\b', r'\brött\b']),
    ("rosa",    [r'\brosa\b', r'\bpink\b', r'\bcerise\b', r'\bmagenta\b', r'\bfuchsia\b', r'\bapricot\b', r'\bblush\b']),
    ("orange",  [r'\borange\b', r'\bkoppar\b', r'\bcopper\b', r'\bambra\b', r'\bamber\b']),
    ("gul",     [r'\bgul\b', r'\bgula\b', r'\bgult\b', r'\byellow\b', r'\bgold\b', r'\bgolden\b', r'\bsungold\b']),
    ("vit",     [r'\bvit\b', r'\bvita\b', r'\bvitt\b', r'\bwhite\b', r'\balba\b', r'\bsilver\b', r'\bsnow\b']),
    ("blå",     [r'\bblå\b', r'\bblåa\b', r'\bblått\b', r'\bblue\b', r'\bindigo\b', r'\bsaphir\b', r'\bcobalt\b']),
    ("lila",    [r'\blila\b', r'\bpurple\b', r'\bviolet\b', r'\bpurpur\b', r'\blavendel\b']),
    ("svart",   [r'\bsvart\b', r'\bsvarta\b', r'\bblack\b', r'\bdark\b', r'\bnero\b', r'\bnoir\b']),
    ("grön",    [r'\bgrön\b', r'\bgröna\b', r'\bgrönt\b', r'\bgreen\b', r'\blime\b']),
    ("brun",    [r'\bbrun\b', r'\bbruna\b', r'\bbrown\b', r'\bchocolate\b', r'\bchoklad\b']),
    ("flerfärgad", [r'\bmix\b', r'\bmixed\b', r'\brainbow\b', r'\bparadiso mix\b', r'\bblanding\b']),
]


def extract_colour(name):
    """Extract colour from product name."""
    n = name.lower()
    for colour, patterns in COLOUR_RULES:
        for pattern in patterns:
            if re.search(pattern, n):
                return colour
    return None


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        sys.exit(1)

    # Fetch all products
    print("Fetching products...")
    products = []
    offset = 0
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/products",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params={"select": "id,name", "limit": "1000", "offset": str(offset), "order": "id.asc"},
            timeout=30,
        )
        if r.status_code != 200:
            print(f"Error: {r.status_code}")
            break
        batch = r.json()
        if not batch:
            break
        products.extend(batch)
        offset += 1000
        if len(batch) < 1000:
            break

    print(f"  {len(products)} products\n")

    # Extract colours
    updates = {}  # colour → [product_ids]
    colour_counts = Counter()
    for p in products:
        colour = extract_colour(p["name"])
        if colour:
            updates.setdefault(colour, []).append(p["id"])
            colour_counts[colour] += 1

    total_coloured = sum(len(ids) for ids in updates.values())
    print(f"  Colours found: {total_coloured} products")
    print(f"  No colour: {len(products) - total_coloured} products\n")
    print(f"  Distribution:")
    for colour, count in colour_counts.most_common():
        print(f"    {colour:15s} {count}")

    # Batch update
    print(f"\nUpdating colour column...")
    updated = 0
    for colour, product_ids in updates.items():
        for i in range(0, len(product_ids), 200):
            batch_ids = product_ids[i:i + 200]
            id_filter = ",".join(str(x) for x in batch_ids)
            r = requests.patch(
                f"{SUPABASE_URL}/rest/v1/products?id=in.({id_filter})",
                headers=HEADERS,
                json={"colour": colour},
                timeout=30,
            )
            if r.status_code in (200, 204):
                updated += len(batch_ids)
            else:
                print(f"  Error: {r.status_code} {r.text[:200]}")

    print(f"\n{'='*50}")
    print(f"COLOUR EXTRACTION COMPLETE")
    print(f"{'='*50}")
    print(f"  Updated: {updated} products with colour")


if __name__ == "__main__":
    main()
