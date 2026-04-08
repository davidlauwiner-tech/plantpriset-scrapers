#!/usr/bin/env python3
"""
Plantpriset — Sync scraped JSON data into Supabase.

Reads output/*.json files and:
1. Upserts listings (creates new, updates existing by product_url)
2. Creates new products for listings that don't match existing ones
3. Links listings to products via product_listings
4. Updates prices on existing listings

Run after scraping:
    python3 sync_to_supabase.py

Or sync a single retailer:
    python3 sync_to_supabase.py zetas
"""
import os, sys, json, re, time
from pathlib import Path
from datetime import datetime
from collections import Counter

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

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

HEADERS_MINIMAL = {**HEADERS, "Prefer": "return=minimal"}

RETAILER_MAP = {
    "impecta": 1,
    "blomsterlandet": 2,
    "cramers": 3,
    "zetas": 4,
    "klostra": 5,
    "plantagen": 6,
    "granngarden": 7,
}

OUTPUT_DIR = Path(__file__).parent / "output"


def slugify(name):
    """Create URL-friendly slug from product name."""
    s = name.lower().strip()
    s = re.sub(r'[åä]', 'a', s)
    s = re.sub(r'[ö]', 'o', s)
    s = re.sub(r'[éè]', 'e', s)
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s]+', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:120]


def normalize_name(name):
    """Normalize product name for fuzzy matching across retailers."""
    import re
    s = name.lower().strip()
    # Remove quotes and special chars
    s = s.replace("'", "").replace('"', '').replace('’', '').replace('‘', '')
    s = s.replace('`', '').replace('´', '')
    # Remove " - NYHET 2026" and similar year tags
    s = re.sub(r'\s*-\s*nyhet\s*\d{4}', '', s)
    # Remove common suffixes retailers add (order matters - longer first)
    for suffix in [', sommarblomma', ', sommarblommor', ', perenner', ', ettåriga',
                   ', auberginefröer', ', bönfröer', ', fröer', ', frö',
                   ' krav-certifierad örtväxt', ' krav', ' eko', ',logisk', ' ekologisk', ' organic',
                   ' pluggplanta', ' barrotad', ' krukodlad', ' i kruka',
                   ' storportion', ' såband', ' kulturarv']:
        s = s.replace(suffix, '')
    # Remove "fröer" with or without comma/space before it
    s = s.replace(',fröer', '')  # no space variant (Klostra)
    # Remove compound fröer words
    for w in ['blomsterfröer', 'bönfröer', 'auberginefröer', 'gronsaksfröer', 'kryddfröer']:
        s = s.replace(w, '')
    # Remove "Fröer Nelson Garden" prefix (Granngården)
    s = re.sub(r'^fröer nelson garden\s+', '', s)
    # Remove trailing descriptions
    for desc in ['hydroponisk odling', 'nelson garden']:
        s = s.replace(desc, '')
    # Remove standalone "fröer" and "perenner" at end (Klostra style without comma)
    s = re.sub(r'\s+fröer\b', '', s)
    s = re.sub(r'\s+perenner\b', '', s)
    s = re.sub(r'\s+sommarblommor\b', '', s)
    s = re.sub(r'\s+sommarblomma\b', '', s)
    # Remove descriptors like "högväxande", "lågväxande"  
    s = re.sub(r'\b(högväxande|lågväxande|klättrande|krypande)\b', '', s)
    # Remove content in parentheses (e.g. "(fd Origami)", "(brittiska Amethyst)")
    s = re.sub(r'\s*\([^)]*\)', '', s)
    # Remove trailing descriptions after " - " (e.g. " - perfekt för den lilla odlingen")
    s = re.sub(r'\s*-\s*perfekt.*$', '', s)
    s = re.sub(r'\s*-\s*[a-zåäö].*$', '', s)
    # Remove F1/F2 anywhere in the name
    s = re.sub(r'\bf[12]\b', '', s)
    # Normalize common spelling variants
    s = s.replace('aubergine', 'aubergin')
    # Remove size descriptors
    for word in ['låg', 'hög', 'liten', 'stor', 'mini', 'dvärg']:
        s = re.sub(r'\b' + word + r'\b\s*', '', s)
    # Remove season descriptors (Cramers uses "Morot Sommar Rondo")
    for season in ['sommar', 'höst', 'vår', 'vinter']:
        s = re.sub(r'\b' + season + r'\b\s*', '', s)
    # Normalize common compound words with/without space
    s = s.replace('pro cut', 'procut')
    # Normalize common spelling variants across retailers
    s = s.replace('chocolat', 'chocolate')
    s = re.sub(r'\bchili\b$', '', s)  # trailing "chili" in pepper names
    s = re.sub(r'\bintred\b', '', s)  # Blomsterlandet variant suffix
    # Remove trailing comma, dash, dots
    s = re.sub(r'[,\.\-\s]+$', '', s)
    # Remove "Bamsefrö" prefix (Blomsterlandet kids range)
    s = re.sub(r'^bamsefrö\s+', '', s)
    # Remove Cramers prefix patterns like "Sallat, Plock-, "
    s = re.sub(r'^(\w+),\s+\w+-,\s*', r'\1 ', s)
    # Remove trailing ", bl.färger." and similar
    s = re.sub(r',\s*bl\..*$', '', s)
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    # Remove trailing size/pack info like "10-pack" or "0.5L"
    s = re.sub(r'\s+\d+[-.]?\d*\s*(pack|st|l|ml|kg|g|cm|mm)$', '', s)
    return s


def guess_product_type(product):
    """Guess product type from tags, category, or name."""
    name = product.get("name", "").lower()
    tags = [t.lower() for t in product.get("tags", [])]
    ptype = product.get("product_type", "").lower()
    cat_url = product.get("category_url", "").lower()

    # Plantagen-specific: use their category hierarchy (most reliable)
    if "utomhusväxter" in cat_url:
        return "plant"
    if "inomhusväxter" in cat_url and ("gröna växter" in cat_url or "blommande växter" in cat_url):
        return "plant"
    if "trädgårdsskötsel" in cat_url or "maskiner" in cat_url:
        return "tool"
    if "krukor" in cat_url or "krukfat" in cat_url:
        return "tool"
    if "jord, gödsel" in cat_url or "toppdekoration" in cat_url:
        return "tool"
    if "odla > odlingstillbehör" in cat_url or "odla > växtbelysning" in cat_url or "odla > växthus" in cat_url or "odla > planteringsbädd" in cat_url:
        return "tool"
    if "snittblommor" in cat_url or "blomstergrupper" in cat_url or "gör-det-själv" in cat_url:
        return "other"

    # Check tags first
    if any(t in tags for t in ["fröer", "seeds", "frö"]):
        return "seed"
    if any(t in tags for t in ["växter", "plants", "perenner", "buskar"]):
        return "plant"
    if any(t in tags for t in ["lökar", "bulbs", "knölar"]):
        return "bulb"

    # Check category URL
    if "/froer/" in cat_url or "/fro/" in cat_url:
        return "seed"
    if "/vaxter/" in cat_url or "/plantor/" in cat_url:
        return "plant"
    if "/lokar/" in cat_url or "/knolar/" in cat_url:
        return "bulb"

    # Check product type field
    if any(w in ptype for w in ["perenn", "buske", "träd", "plant", "ros"]):
        return "plant"
    if any(w in ptype for w in ["frö", "seed"]):
        return "seed"
    if any(w in ptype for w in ["lök", "knöl", "bulb", "dahlia", "tulpan"]):
        return "bulb"

    # Check name
    if any(w in name for w in ["frö ", "fröer", "frön", "såband"]):
        return "seed"
    if any(w in name for w in ["jord", "gödsel", "kruka", "bevattning", "redskap", "sax", "spade"]):
        return "tool"

    return "other"


def api_get(path, params=None):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}", headers=HEADERS, params=params or {}, timeout=30)
    if r.status_code == 200:
        return r.json()
    return []


def api_patch(path, data):
    for attempt in range(3):
        try:
            r = requests.patch(f"{SUPABASE_URL}/rest/v1/{path}", headers=HEADERS_MINIMAL, json=data, timeout=15)
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout, requests.exceptions.Timeout):
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return None
    return r.status_code in (200, 204)


def api_post(path, data):
    for attempt in range(3):
        try:
            r = requests.post(f"{SUPABASE_URL}/rest/v1/{path}", headers=HEADERS, json=data, timeout=15)
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout, requests.exceptions.Timeout):
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return None
    if r.status_code in (200, 201):
        return r.json()
    return None


def load_existing_listings(retailer_id):
    """Load all existing listings for a retailer, keyed by product_url."""
    listings = {}
    offset = 0
    while True:
        batch = api_get("listings", {
            "retailer_id": f"eq.{retailer_id}",
            "select": "id,product_url,price_sek,name",
            "limit": "1000",
            "offset": str(offset),
            "order": "id.asc",
        })
        if not batch:
            break
        for l in batch:
            listings[l["product_url"]] = l
        offset += 1000
        if len(batch) < 1000:
            break
    return listings


def load_existing_products():
    """Load all products keyed by name (lowercase) for matching."""
    products = {}
    offset = 0
    while True:
        batch = api_get("products", {
            "select": "id,name,slug",
            "limit": "1000",
            "offset": str(offset),
            "order": "id.asc",
        })
        if not batch:
            break
        for p in batch:
            products[p["name"].lower().strip()] = p
        offset += 1000
        if len(batch) < 1000:
            break
    # Also index by normalized name for fuzzy matching
    for name_key, prod in list(products.items()):
        norm = normalize_name(prod["name"])
        if norm not in products:
            products[norm] = prod
    return products
    return products


def find_or_create_product(scraped, existing_products):
    """Find matching product or create new one."""
    name = scraped["name"].strip()
    name_lower = name.lower()

    # Exact match
    if name_lower in existing_products:
        return existing_products[name_lower]["id"]

    # Normalized match (strips quotes, suffixes, etc.)
    norm = normalize_name(name)
    if norm in existing_products:
        return existing_products[norm]["id"]

    # Create new product
    slug = slugify(name)
    product_type = guess_product_type(scraped)
    
    new_product = {
        "name": name,
        "slug": slug,
        "product_type": product_type,
        "image_url": scraped.get("image_url", ""),
    }

    result = api_post("products", new_product)
    if result and isinstance(result, list) and len(result) > 0:
        pid = result[0]["id"]
        existing_products[name_lower] = {"id": pid, "name": name, "slug": slug}
        return pid

    return None


def sync_retailer(retailer_slug, products_data):
    """Sync all products from one retailer JSON into Supabase."""
    retailer_id = RETAILER_MAP.get(retailer_slug)
    if not retailer_id:
        print(f"  Unknown retailer: {retailer_slug}")
        return

    scraped_products = products_data.get("products", [])
    print(f"  {len(scraped_products)} scraped products")

    # Load existing data
    print(f"  Loading existing listings...")
    existing_listings = load_existing_listings(retailer_id)
    print(f"  {len(existing_listings)} existing listings")

    stats = Counter()

    for i, sp in enumerate(scraped_products):
        url = sp.get("product_url", "")
        name = sp.get("name", "").strip()
        price = sp.get("price_sek")
        
        if not url or not name or not price:
            stats["skipped"] += 1
            continue

        if url in existing_listings:
            # UPDATE existing listing
            existing = existing_listings[url]
            old_price = existing.get("price_sek")
            update_data = {
                "price_sek": price,
                "in_stock": sp.get("in_stock", True),
                            }
            # Update image if we have a better one
            img = sp.get("image_url", "")
            if img:
                update_data["image_url"] = img

            # Only call API if price actually changed
            if old_price != price:
                api_patch(f"listings?id=eq.{existing['id']}", update_data)
                if old_price and old_price != price:
                    stats["price_changed"] += 1
                else:
                    stats["updated_img"] += 1
            else:
                stats["unchanged"] += 1
        else:
            # NEW listing — insert
            listing_data = {
                "name": name,
                "retailer_id": retailer_id,
                "product_url": url,
                "price_sek": price,
                "image_url": sp.get("image_url", ""),
                "in_stock": sp.get("in_stock", True),
                            }
            result = api_post("listings", listing_data)
            if result and isinstance(result, list):
                listing_id = result[0]["id"]
                stats["new_listing"] += 1

                # Find or create product and link
                product_id = find_or_create_product(sp, existing_products)
                if product_id:
                    # Check if link exists
                    existing_link = api_get("product_listings", {
                        "product_id": f"eq.{product_id}",
                        "listing_id": f"eq.{listing_id}",
                        "select": "id",
                        "limit": "1",
                    })
                    if not existing_link:
                        api_post("product_listings", {
                            "product_id": product_id,
                            "listing_id": listing_id,
                        })
                        stats["new_link"] += 1

                    # Update product image if it's empty
                    api_patch(
                        f"products?id=eq.{product_id}&image_url=eq.",
                        {"image_url": sp.get("image_url", "")}
                    )
            else:
                stats["insert_failed"] += 1

        if (i + 1) % 200 == 0:
            print(f"    ... {i+1}/{len(scraped_products)} processed")

    return stats


def main():
    global existing_products

    # Which retailers to sync
    requested = sys.argv[1:] if len(sys.argv) > 1 else list(RETAILER_MAP.keys())

    print(f"{'='*55}")
    print(f"PLANTPRISET — Sync to Supabase")
    print(f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Retailers: {', '.join(requested)}")
    print(f"{'='*55}")

    # Load all existing products once
    print(f"\nLoading existing products...")
    existing_products = load_existing_products()
    print(f"  {len(existing_products)} products in database\n")

    total_stats = Counter()

    for retailer_slug in requested:
        json_path = OUTPUT_DIR / f"{retailer_slug}_products.json"
        if not json_path.exists():
            print(f"\n--- {retailer_slug.upper()} ---")
            print(f"  No JSON file found at {json_path}")
            continue

        print(f"\n--- {retailer_slug.upper()} ---")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        stats = sync_retailer(retailer_slug, data)
        if stats:
            total_stats += stats
            print(f"  Results: {dict(stats)}")

    print(f"\n{'='*55}")
    print(f"SYNC COMPLETE")
    print(f"{'='*55}")
    print(f"  New listings:    {total_stats.get('new_listing', 0)}")
    print(f"  Price changes:   {total_stats.get('price_changed', 0)}")
    print(f"  Unchanged:       {total_stats.get('unchanged', 0)}")
    print(f"  New links:       {total_stats.get('new_link', 0)}")
    print(f"  Skipped:         {total_stats.get('skipped', 0)}")
    print(f"  Insert failed:   {total_stats.get('insert_failed', 0)}")


if __name__ == "__main__":
    main()
