#!/usr/bin/env python3
"""
Plantpriset — Smart product matching v3.
Key rules:
1. Seeds only match seeds, plants only match plants, tools only match tools
2. Different brands = no match
3. Extreme price differences = no match
4. Generic names with big price gaps = no match
"""
import json, os, re, sys
from collections import defaultdict
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
        if "already exists" not in resp.text:
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

def make_slug(name, ptype):
    s = name.lower().strip()
    s = s.replace("å", "a").replace("ä", "a").replace("ö", "o")
    s = s.replace("é", "e").replace("ü", "u")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    # Add type suffix to avoid slug conflicts between seed and plant
    if ptype != "seed":
        s = f"{s}-{ptype}"
    return s[:300]

def detect_product_type(listing):
    """Detect if a listing is a seed, plant, or tool based on category and retailer."""
    cat = (listing.get("category_url") or "").lower()
    name = (listing.get("name") or "").lower()
    retailer_id = listing.get("retailer_id")
    price = listing.get("price_sek") or 0
    
    # Explicit category signals
    seed_signals = ["/froer", "/fro/", "/fro?", "froer/", "gronsaksfroer", "blomsterfroer",
                     "kryddfroer", "angsfroer", "/froer/", "micro-leaf", "groddar"]
    tool_signals = ["/tillbehor", "/redskap", "/belysning", "/bevattning", "/krukor",
                     "/drivhus", "/vaxtskydd", "/naringstillskott", "/uppbindning",
                     "/markning", "/brickor", "/sadd-plantering", "/vaxtbelysning",
                     "/jord-godsel", "/odling-drivhus", "/tradgardstillbehor"]
    plant_signals = ["/vaxter/", "/perenner/", "/buskar/", "/trad/", "/krukvaxter/",
                      "/lokar-knolar/", "/utplanteringsvaxter/"]
    
    # CRITICAL: Check seeds FIRST — /froer/perenner/ is seeds, not plants
    for s in seed_signals:
        if s in cat:
            return "seed"
    for s in tool_signals:
        if s in cat:
            return "tool"
    for s in plant_signals:
        if s in cat:
            return "plant"
    
    # Retailer-based defaults
    # Impecta = almost everything is seeds (except tillbehor)
    if retailer_id == 1:  # impecta
        if "tillbehor" in cat:
            return "tool"
        return "seed"
    
    # Klostra = all seeds
    if retailer_id == 5:  # klostra
        return "seed"
    
    # Cramers - check category path
    if retailer_id == 3:  # cramers
        if "/froer/" in cat:
            return "seed"
        return "tool"
    
    # Zetas - mixed (seeds, plants, tools, decor)
    if retailer_id == 4:  # zetas
        # Use name-based heuristics for Zetas
        seed_words = ["frö", "fröer", "seed", "odla"]
        for w in seed_words:
            if w in name:
                return "seed"
        # High price + plant-like name = probably a plant
        if price > 80:
            return "plant"
        return "seed"  # default for Zetas
    
    # Blomsterlandet - check category
    if retailer_id == 2:  # blomsterlandet
        if "/froer/" in cat:
            return "seed"
        if "/tillbehor/" in cat:
            return "tool"
        if "/lokar" in cat or "/knolar" in cat or "/sattlok" in cat or "/sattpotatis" in cat:
            return "bulb"
        return "plant"
    
    # Plantagen (id=6) - use Meilisearch categories
    if retailer_id == 6:
        cat_lower = cat.lower()
        if "fröer" in cat_lower or "froer" in cat_lower:
            return "seed"
        # Name-based for Plantagen
        tool_words = ["kruka", "jord", "gödsel", "redskap", "sekatör", "slang", "bevattning",
                       "lampa", "belysning", "drivhus", "pallkrage", "adapter", "koppling",
                       "regulator", "vägskran", "verktyg", "sax", "spade", "räfsa"]
        for w in tool_words:
            if w in name:
                return "tool"
        bulb_words = ["dahlia", "tulpan", "lök", "knöl", "sättlök", "sättpotatis", "gladiolus",
                       "krokus", "hyacint", "narciss", "lilja knöl"]
        for w in bulb_words:
            if w in name:
                return "bulb"
        return "plant"
    
    # Granngården (id=7) - name-based detection (no category URLs)
    if retailer_id == 7:
        # Granngården product names often start with "Fröer Nelson Garden..."
        if name.startswith("fröer ") or name.startswith("frö "):
            return "seed"
        tool_words = ["adapter", "koppling", "slang", "bevattning", "kruka", "jord", "gödsel",
                       "redskap", "sekatör", "sax", "spade", "räfsa", "vägskran", "regulator",
                       "lampa", "belysning", "drivhus", "pallkrage", "kompost", "verktyg",
                       "fiberduk", "nät", "presenning", "odlingslåda", "thermacell",
                       "fågelmatare", "grilltillbehör", "hundleksak", "kattleksak"]
        for w in tool_words:
            if w in name:
                return "tool"
        bulb_words = ["dahlia", "tulpan", "sättlök", "sättpotatis", "gladiolus", "blomsterlök",
                       "krokus", "hyacint", "narciss"]
        for w in bulb_words:
            if w in name:
                return "bulb"
        # Granngården names with "Fröer" in them are seeds
        if "fröer" in name or "frö" in name:
            return "seed"
        return "seed"  # most Granngården garden products are seeds
    
    return "seed"  # safe default

def price_diff_pct(prices):
    if len(prices) < 2:
        return 0
    mn, mx = min(prices), max(prices)
    if mx == 0:
        return 0
    return (mx - mn) / mx * 100

def should_match(listings):
    """Determine if listings are truly the same product."""
    retailer_ids = set(l["retailer_id"] for l in listings)
    if len(retailer_ids) < 2:
        return True, 100, "single_retailer"
    
    # Rule 1: Product types must match
    types = set(l.get("_type") for l in listings)
    if len(types) > 1:
        return False, 0, f"type_mismatch: {types}"
    
    # Rule 2: Brand consistency
    brands = set(l.get("brand", "").strip().lower() for l in listings if l.get("brand"))
    if len(brands) > 1:
        return False, 0, f"brand_mismatch: {brands}"
    
    # Rule 3: Price sanity
    prices = [l["price_sek"] for l in listings if l.get("price_sek") and l["price_sek"] > 0]
    if len(prices) >= 2:
        diff = price_diff_pct(prices)
        name = normalize(listings[0].get("name", ""))
        is_generic = len(name.split()) <= 2
        
        if is_generic and diff > 50:
            return False, 0, f"generic_name_price_diff_{diff:.0f}pct"
        if diff > 70:
            return False, 0, f"extreme_price_diff_{diff:.0f}pct"
        if diff > 40 and len(brands) == 0:
            return False, 0, f"no_brand_high_price_diff_{diff:.0f}pct"
    
    if len(brands) == 1:
        return True, 95, "same_brand_same_type"
    return True, 80, "name_match_same_type"

def main():
    # Clear old data
    print("Clearing old product matches...")
    api("DELETE", "product_listings", params={"id": "gt.0"})
    api("DELETE", "products", params={"id": "gt.0"})
    
    # Fetch listings
    print("Fetching listings...")
    all_listings = []
    offset = 0
    while True:
        result = api("GET", "listings", params={
            "select": "id,retailer_id,name,price_sek,latin_name,image_url,brand,article_number,category_url",
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
    print(f"  {len(all_listings)} listings")

    # Detect product type for each listing
    type_counts = defaultdict(int)
    for l in all_listings:
        l["_type"] = detect_product_type(l)
        type_counts[l["_type"]] += 1
    
    print(f"  Product types: {dict(type_counts)}")

    # Group by normalized name + product type (this is the key change!)
    groups = defaultdict(list)
    for l in all_listings:
        key = (normalize(l["name"]), l["_type"])
        groups[key].append(l)

    # Smart matching
    matched_groups = []
    rejected = []
    single_groups = []
    
    for (name, ptype), listings in groups.items():
        retailer_ids = set(l["retailer_id"] for l in listings)
        if len(retailer_ids) < 2:
            single_groups.append((name, ptype, listings))
            continue
        
        ok, confidence, reason = should_match(listings)
        if ok:
            matched_groups.append((name, ptype, listings, confidence, reason))
        else:
            rejected.append((name, ptype, listings, reason))

    print(f"\n  Multi-retailer groups: {len(matched_groups) + len(rejected)}")
    print(f"  ✅ Matched: {len(matched_groups)}")
    print(f"  ❌ Rejected: {len(rejected)}")
    print(f"  Single-retailer: {len(single_groups)}")
    
    if rejected:
        print(f"\n  Sample rejected (first 15):")
        for name, ptype, listings, reason in rejected[:15]:
            prices = [l["price_sek"] for l in listings if l.get("price_sek")]
            types = set(l.get("_type") for l in listings)
            brands = set(l.get("brand","?") for l in listings if l.get("brand"))
            print(f"    ✗ {name} [{ptype}]")
            print(f"      {reason} | prices={prices} brands={brands} types={types}")

    # Create products
    print(f"\nCreating matched products...")
    created_multi = 0
    linked = 0

    for name, ptype, listings, confidence, reason in matched_groups:
        slug = make_slug(name, ptype)
        image = next((l["image_url"] for l in listings if l.get("image_url")), "")
        latin = next((l["latin_name"] for l in listings if l.get("latin_name")), None)

        result = api("POST", "products", data=[{
            "slug": slug, "name": name.title(), "latin_name": latin,
            "image_url": image or "", "product_type": ptype,
        }])
        if result and len(result) > 0:
            product_id = result[0]["id"]
            created_multi += 1
            links = [{"product_id": product_id, "listing_id": l["id"], "match_score": confidence}
                     for l in listings]
            api("POST", "product_listings", data=links)
            linked += len(links)
            if created_multi % 100 == 0:
                print(f"  {created_multi} matched products...")

    print(f"\nCreating single-retailer products...")
    created_single = 0
    for name, ptype, listings in single_groups:
        slug = make_slug(name, ptype)
        image = next((l["image_url"] for l in listings if l.get("image_url")), "")
        latin = next((l["latin_name"] for l in listings if l.get("latin_name")), None)

        result = api("POST", "products", data=[{
            "slug": slug, "name": name.title(), "latin_name": latin,
            "image_url": image or "", "product_type": ptype,
        }])
        if result and len(result) > 0:
            product_id = result[0]["id"]
            created_single += 1
            links = [{"product_id": product_id, "listing_id": l["id"], "match_score": 100.0}
                     for l in listings]
            api("POST", "product_listings", data=links)
            linked += len(links)
            if created_single % 500 == 0:
                print(f"  {created_single} single products...")

    print(f"\n{'='*55}")
    print(f"SMART MATCHING v3 COMPLETE")
    print(f"{'='*55}")
    print(f"  ✅ Multi-retailer (price comparison): {created_multi}")
    print(f"  ❌ Rejected false matches: {len(rejected)}")
    print(f"  📦 Single-retailer: {created_single}")
    print(f"  Total products: {created_multi + created_single}")
    print(f"  Total links: {linked}")

if __name__ == "__main__":
    main()
