#!/usr/bin/env python3
"""
Plantpriset — Data Quality Fixes
Run from ~/Downloads/plantpriset-scrapers/

Fixes:
1. Miscategorized products (e.g. window opener in Tomater)
2. "Högväxandea" typo in product names
3. Scans for other obvious miscategorizations
"""

import os, json, requests
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not URL or not KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
    exit(1)

HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

HEADERS_COUNT = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Prefer": "count=exact",
    "Range": "0-0",
}


def fix_miscategorized():
    """Fix products that are clearly in the wrong category."""
    print("\n" + "=" * 60)
    print("FIX 1: Miscategorized products")
    print("=" * 60)

    fixes = [
        # (product_id, correct_subcategory_id, correct_product_type, reason)
        (98072, 62, "tool", "Fönsteröppnare is greenhouse equipment, not a tomato seed"),
    ]

    # Also scan for non-seed items categorized as seeds
    # Look for products with "tool" keywords in seed categories (subcategory_id 1-15, 26-33)
    seed_subcats = list(range(1, 16)) + list(range(26, 34))
    tool_keywords = [
        "öppnare", "slang", "kruka", "spade", "sax", "redskap",
        "bevattning", "gödsel", "jord", "odlingslåda", "drivhus",
        "termometer", "handske", "pump", "timer", "belysning",
        "pallkrage", "kompost", "spruta", "vagn",
    ]

    print("\nScanning for tools hiding in seed categories...")
    for subcat_id in seed_subcats:
        r = requests.get(
            f"{URL}/rest/v1/products?subcategory_id=eq.{subcat_id}&select=id,name,subcategory_id,product_type",
            headers={**HEADERS, "Prefer": "return=representation"},
        )
        if r.status_code != 200:
            continue
        for p in r.json():
            name_lower = p["name"].lower()
            for kw in tool_keywords:
                if kw in name_lower:
                    print(f"  SUSPECT: [{p['id']}] \"{p['name']}\" in subcategory {p['subcategory_id']}")
                    # Auto-fix: move to generic tools category (39=Redskap) unless we have a better match
                    fixes.append((p["id"], 62, "tool", f"Contains tool keyword '{kw}'"))
                    break

    # Also look for seed products in tool categories (34-68)
    tool_subcats = list(range(34, 69))
    seed_keywords = ["frö", "frön", "tomat ", "gurka ", "chili ", "paprika ", "sallat "]

    print("\nScanning for seeds hiding in tool categories...")
    for subcat_id in tool_subcats:
        r = requests.get(
            f"{URL}/rest/v1/products?subcategory_id=eq.{subcat_id}&select=id,name,subcategory_id,product_type",
            headers={**HEADERS, "Prefer": "return=representation"},
        )
        if r.status_code != 200:
            continue
        for p in r.json():
            name_lower = p["name"].lower()
            for kw in seed_keywords:
                if kw in name_lower and p["product_type"] != "seed":
                    print(f"  SUSPECT: [{p['id']}] \"{p['name']}\" in tool subcategory {p['subcategory_id']}")
                    break

    # Apply fixes
    fixed = 0
    for pid, new_subcat, new_type, reason in fixes:
        r = requests.patch(
            f"{URL}/rest/v1/products?id=eq.{pid}",
            headers=HEADERS,
            json={"subcategory_id": new_subcat, "product_type": new_type},
        )
        if r.status_code < 300:
            fixed += 1
            print(f"  FIXED [{pid}]: → subcategory {new_subcat}, type={new_type} ({reason})")
        else:
            print(f"  ERROR [{pid}]: {r.status_code} {r.text}")

    print(f"\n  Total fixed: {fixed}")


def fix_typos():
    """Fix 'Högväxandea' → 'Högväxande' in product names and slugs."""
    print("\n" + "=" * 60)
    print("FIX 2: 'Högväxandea' typo")
    print("=" * 60)

    # Get all affected products
    r = requests.get(
        f"{URL}/rest/v1/products?name=ilike.*xandea*&select=id,name,slug",
        headers={**HEADERS, "Prefer": "return=representation"},
    )
    if r.status_code != 200:
        print(f"  ERROR fetching: {r.status_code} {r.text}")
        return

    products = r.json()
    print(f"  Found {len(products)} products with 'Högväxandea' typo")

    fixed = 0
    for p in products:
        new_name = p["name"].replace("Högväxandea", "Högväxande")
        new_slug = p["slug"].replace("hogvaxandea", "hogvaxande") if p.get("slug") else None

        update = {"name": new_name}
        if new_slug and new_slug != p.get("slug"):
            update["slug"] = new_slug

        r = requests.patch(
            f"{URL}/rest/v1/products?id=eq.{p['id']}",
            headers=HEADERS,
            json=update,
        )
        if r.status_code < 300:
            fixed += 1
            if fixed <= 5:
                print(f"  FIXED: \"{p['name']}\" → \"{new_name}\"")
        else:
            print(f"  ERROR [{p['id']}]: {r.status_code} {r.text}")

    if fixed > 5:
        print(f"  ... and {fixed - 5} more")
    print(f"\n  Total fixed: {fixed}")


def fix_other_typos():
    """Fix other common typos found in product names."""
    print("\n" + "=" * 60)
    print("FIX 3: Other name issues")
    print("=" * 60)

    typo_patterns = [
        # (search_pattern, old_text, new_text, description)
        ("*Högväxandea*", "Högväxandea", "Högväxande", "already handled above"),
        ("*Salladstomat*", None, None, "check only"),
    ]

    # Check for trailing "a" on other descriptors (common Klostra scraper issue)
    # e.g. "Kulturarva" instead of "Kulturarv"
    for suffix in ["Kulturarva", "Lågväxandea", "Medelhöga"]:
        search = suffix.lower().replace("ä", "*").replace("ö", "*")
        r = requests.get(
            f"{URL}/rest/v1/products?name=ilike.*{suffix[:6]}*&select=id,name&limit=5",
            headers={**HEADERS, "Prefer": "return=representation"},
        )
        if r.status_code == 200 and r.json():
            for p in r.json():
                if suffix in p["name"]:
                    print(f"  FOUND TYPO: [{p['id']}] \"{p['name']}\"")

    # Check for duplicate-looking products (same base name, different suffixes)
    print("\n  Checking for potential duplicates in tomater (subcategory 1)...")
    r = requests.get(
        f"{URL}/rest/v1/products?subcategory_id=eq.1&select=id,name&order=name",
        headers={**HEADERS, "Prefer": "return=representation"},
    )
    if r.status_code == 200:
        products = r.json()
        seen_bases = {}
        for p in products:
            # Normalize: strip "Tomat ", ", Högväxande", "F1", etc.
            base = (
                p["name"]
                .replace("Tomat ", "")
                .replace(", Högväxande", "")
                .replace(" Högväxande", "")
                .replace(", Kruktomat", "")
                .replace(", Dwarftomat", "")
                .replace(", Salladstomat", "")
                .replace(" - Kulturarv", "")
                .replace(", Kulturarv", "")
                .replace(" - Nyhet 2026", "")
                .strip()
            )
            if base in seen_bases:
                seen_bases[base].append(p)
            else:
                seen_bases[base] = [p]

        dupes = {k: v for k, v in seen_bases.items() if len(v) > 1}
        if dupes:
            print(f"  Found {len(dupes)} potential duplicate groups:")
            for base, prods in list(dupes.items())[:10]:
                names = [p["name"] for p in prods]
                print(f"    \"{base}\": {names}")
            if len(dupes) > 10:
                print(f"    ... and {len(dupes) - 10} more groups")
        else:
            print("  No obvious duplicates found.")


def summary():
    """Print current database stats."""
    print("\n" + "=" * 60)
    print("DATABASE SUMMARY")
    print("=" * 60)

    for label, query in [
        ("Total products", "products?select=id"),
        ("Products with descriptions", "products?description=not.is.null&select=id"),
        ("Products missing descriptions", "products?description=is.null&select=id"),
        ("Total listings", "listings?select=id"),
        ("Product-listing matches", "product_listings?select=id"),
    ]:
        r = requests.head(
            f"{URL}/rest/v1/{query}&limit=1",
            headers=HEADERS_COUNT,
        )
        count = r.headers.get("content-range", "?/?").split("/")[-1]
        print(f"  {label}: {count}")


if __name__ == "__main__":
    print("PLANTPRISET DATA QUALITY FIXES")
    print("=" * 60)
    fix_miscategorized()
    fix_typos()
    fix_other_typos()
    summary()
    print("\nDone!")
