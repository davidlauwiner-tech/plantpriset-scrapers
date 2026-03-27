#!/usr/bin/env python3
"""
Plantpriset — Smart product matching v4.
 
NEW in v4: Fuzzy plant-family matching.
 
The old matcher only grouped listings with IDENTICAL normalized names.
This meant "Mejram" (Impecta, 27.90 kr) and "Mejram" (Blomsterlandet, 39.90 kr)
matched, but "Purpurmejram Herrenhausen" (Zetas, 95 kr) was isolated.
 
v4 adds a second pass that extracts the BASE PLANT NAME and matches
listings that share the same plant family + product type, while still
respecting brand, price sanity, and variety differences.
 
Key rules (carried from v3):
1. Seeds only match seeds, plants only match plants, tools only match tools
2. Different brands = no match  
3. Extreme price differences = no match
4. Generic names with big price gaps = no match
 
New in v4:
5. Extract base plant name → group by plant family
6. Match "Mejram" across retailers even if one says "Purpurmejram"
7. Detect variety names (Herrenhausen, Magnus, etc.) and match same-variety
8. Extract colour from product names for future filtering
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

# ── Swedish plant name prefixes that indicate colour/sub-type ──────────
# These get stripped to find the base plant name
COLOUR_PREFIXES = [
    "röd ", "rod ", "vit ", "gul ", "blå ", "bla ", "rosa ", "lila ",
    "blek ", "svart ", "orange ", "grön ", "gron ", "vild ", "stor ",
    "dvärg ", "dvarg ", "jätte ", "jatte ", "kryp ", "hög ", "hog ",
    "låg ", "lag ",
]

# Common variety/cultivar indicators to strip for base matching
VARIETY_PATTERN = re.compile(
    r"""(?:
        \s+(?:f1|f2|big\s*pack|perenner|annueller|, perenner|, annueller)
        |\s+(?:\d+(?:\s*(?:l|liter|cm|mm|m|m2|m²|st|pack|ml|kg|g))\b)
        |\s+(?:i\s+\d+l?\s*kruka)
        |\s+(?:certifierad|ekologisk|eko|krav)
    )""",
    re.VERBOSE | re.IGNORECASE,
)

# Known Swedish plant families → base name mapping
# This handles compound names like "Purpurmejram" → "mejram"
PLANT_COMPOUNDS = {
    "purpurmejram": "mejram",
    "citronmeliss": "meliss",
    "citrontimjan": "timjan",
    "kryddtimjan": "timjan",
    "backtimjan": "timjan",
    "fjälltimjan": "timjan",
    "bergmynta": "mynta",
    "grönmynta": "mynta",
    "chokladmynta": "mynta",
    "pepparmynta": "mynta",
    "åkermynta": "mynta",
    "vildpersilja": "persilja",
    "bladpersilja": "persilja",
    "kruspersilja": "persilja",
    "slätpersilja": "persilja",
    "körsbärstomat": "tomat",
    "cocktailtomat": "tomat",
    "bifftomat": "tomat",
    "plommontomat": "tomat",
    "druvtomat": "tomat",
    "vinbärstomat": "tomat",
    "växthustomat": "tomat",
    "ampeltomat": "tomat",
    "frilandstomat": "tomat",
    "busktomat": "tomat",
    "frilandsgurka": "gurka",
    "växthusgurka": "gurka",
    "slanggurka": "gurka",
    "inläggningsgurka": "gurka",
    "vaxböna": "böna",
    "störböna": "böna",
    "skärgårdsböna": "böna",
    "bondböna": "böna",
    "kidneybönor": "böna",
    "sojaböna": "böna",
    "trädgårdsbönor": "böna",
    "rosenpaprika": "paprika",
    "blocksallat": "sallat",
    "huvudsallat": "sallat",
    "löksallat": "sallat",
    "bindsallat": "sallat",
    "plocksallat": "sallat",
    "isbergssallat": "sallat",
    "vinterbroccoli": "broccoli",
    "purpursolhatt": "solhatt",
    "vinterlök": "lök",
    "kepalök": "lök",
    "sättlök": "lök",
    "matlök": "lök",
    "gräslök": "lök",
    "purjolök": "lök",
    "vinterlövkoja": "lövkoja",
    "sommaraster": "aster",
    "höstaster": "aster",
    "vidjehortensia": "hortensia",
    "vinteriberis": "iberis",
    "vintergröna": "vintergröna",
    "palmkål": "kål",
    "grönkål": "kål",
    "blomkål": "kål",
    "vitkål": "kål",
    "rödkål": "kål",
    "savojkål": "kål",
    "spetskål": "kål",
}


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


def extract_colour(name):
    """Extract colour from product name."""
    n = name.lower().strip()
    colours = {
        "röd": "röd", "rod": "röd", "red": "röd",
        "vit": "vit", "white": "vit",
        "gul": "gul", "yellow": "gul",
        "blå": "blå", "bla": "blå", "blue": "blå",
        "rosa": "rosa", "pink": "rosa",
        "lila": "lila", "purple": "lila",
        "orange": "orange",
        "blek": "blek",
        "svart": "svart", "black": "svart",
        "grön": "grön", "gron": "grön", "green": "grön",
        "salmon": "salmon",
        "lime": "lime",
    }
    found = []
    for keyword, colour in colours.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', n):
            if colour not in found:
                found.append(colour)
    return found[0] if found else None


def extract_variety(name):
    """Extract cultivar/variety name from a product name.
    E.g. "Solhatt Magnus" → "magnus", "Purpurmejram Herrenhausen" → "herrenhausen"
    """
    n = normalize(name)
    
    # Remove colour prefixes
    for prefix in COLOUR_PREFIXES:
        if n.startswith(prefix):
            n = n[len(prefix):]
    
    # Remove size/pack info
    n = VARIETY_PATTERN.sub("", n)
    n = re.sub(r"\s*\d+\s*$", "", n)  # trailing numbers
    n = n.strip()
    
    parts = n.split()
    if len(parts) <= 1:
        return None
    
    # The base plant is usually the first word(s), variety is the rest
    # But compound plant names need to be handled
    base = parts[0]
    if base in PLANT_COMPOUNDS:
        # "purpurmejram herrenhausen" → variety = "herrenhausen"
        return " ".join(parts[1:]) if len(parts) > 1 else None
    
    # For "röd solhatt magnus" (after colour strip) → "solhatt magnus"
    # base = "solhatt", variety = "magnus"
    if len(parts) >= 2:
        return " ".join(parts[1:])
    
    return None


def extract_base_plant(name):
    """Extract the base plant family name.
    "Purpurmejram Herrenhausen" → "mejram"
    "Röd Solhatt Magnus" → "solhatt"
    "Mejram" → "mejram"
    "Tomat Cherry Belle" → "tomat"
    """
    n = normalize(name)
    
    # Remove colour prefixes first
    for prefix in COLOUR_PREFIXES:
        if n.startswith(prefix):
            n = n[len(prefix):]
    
    # Remove size/pack/certification suffixes
    n = VARIETY_PATTERN.sub("", n)
    n = n.strip()
    
    parts = n.split()
    if not parts:
        return normalize(name)
    
    first_word = parts[0]
    
    # Check compound plant names
    if first_word in PLANT_COMPOUNDS:
        return PLANT_COMPOUNDS[first_word]
    
    # For multi-word names, the first word is usually the base plant
    return first_word


def make_slug(name, ptype):
    s = name.lower().strip()
    s = s.replace("å", "a").replace("ä", "a").replace("ö", "o")
    s = s.replace("é", "e").replace("ü", "u")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if ptype != "seed":
        s = f"{s}-{ptype}"
    return s[:300]


def detect_product_type(listing):
    """Detect if a listing is a seed, plant, or tool based on category and retailer.
    (Carried from v3 — same logic)
    """
    cat = (listing.get("category_url") or "").lower()
    name = (listing.get("name") or "").lower()
    retailer_id = listing.get("retailer_id")
    price = listing.get("price_sek") or 0
    
    seed_signals = ["/froer", "/fro/", "/fro?", "froer/", "gronsaksfroer", "blomsterfroer",
                    "kryddfroer", "angsfroer", "/froer/", "micro-leaf", "groddar"]
    tool_signals = ["/tillbehor", "/redskap", "/belysning", "/bevattning", "/krukor",
                    "/drivhus", "/vaxtskydd", "/naringstillskott", "/uppbindning",
                    "/markning", "/brickor", "/sadd-plantering", "/vaxtbelysning",
                    "/jord-godsel", "/odling-drivhus", "/tradgardstillbehor"]
    plant_signals = ["/vaxter/", "/perenner/", "/buskar/", "/trad/", "/krukvaxter/",
                     "/lokar-knolar/", "/utplanteringsvaxter/"]
    
    for s in seed_signals:
        if s in cat:
            return "seed"
    for s in tool_signals:
        if s in cat:
            return "tool"
    for s in plant_signals:
        if s in cat:
            return "plant"
    
    if retailer_id == 1:
        if "tillbehor" in cat:
            return "tool"
        return "seed"
    if retailer_id == 5:
        return "seed"
    if retailer_id == 3:
        if "/froer/" in cat:
            return "seed"
        return "tool"
    if retailer_id == 4:
        exclude_words = ["collier", "necklace", "brosch", "earring", "ring silver",
                         "ring guldpläterad", "bracelet", "ear silver", "smycke",
                         "doftljus", "handtvål", "handkräm", "handskrubb",
                         "servett", "duk ", "presentkort", "digitalt presentkort",
                         "antikljus", "ljusveke", "ljushållare", "ljushänge",
                         "ljuslykta", "stjärnljus", "toppstjärna", "adventsstjärna",
                         "adventskalender", "wreath", "bok ", "glasdekoration",
                         "jubileumsvas", "såg "]
        for w in exclude_words:
            if w in name:
                return "other"
        seed_words = ["frö", "fröer", "luktärt", "ringblomma", "vallmo", "zinnia",
                      "rosenskära", "solros", "blåklint", "krasse", "aubergine",
                      "tomat", "paprika", "chili", "gurka", "squash", "pumpa",
                      "basilika", "dill", "persilja", "koriander", "mangold",
                      "sallat", "rädisa", "morot", "ärter", "böna", "spenat",
                      "palmkål", "grönkål", "ruccola", "fänkål", "selleri",
                      "blomkål", "broccoli", "purjolök", "lök"]
        for w in seed_words:
            if w in name:
                return "seed"
        if "stor kruka" not in name and "i kruka" not in name:
            tool_words = ["kruka 'gro'", "spade", "växtnäring", "planteringsspade"]
        else:
            tool_words = ["spade", "växtnäring", "planteringsspade"]
        for w in tool_words:
            if w in name:
                return "tool"
        bulb_words = ["tulpan", "narciss", "krokus", "allium", "blåstjärna", "vårstjärna",
                      "hyacint"]
        for w in bulb_words:
            if w in name:
                return "bulb"
        if price > 500:
            return "other"
        return "plant"
    if retailer_id == 2:
        if "/froer/" in cat:
            return "seed"
        if "/tillbehor/" in cat:
            return "tool"
        if "/lokar" in cat or "/knolar" in cat or "/sattlok" in cat or "/sattpotatis" in cat:
            return "bulb"
        return "plant"
    if retailer_id == 6:
        c = cat.lower()
        if any(x in c for x in ["för hemmet", "jul >", "uteplats > utomhusmatlagning",
                                 "uteplats > utemöbler", "uteplats > uppvärmning",
                                 "servetter", "presentinslagning", "innebelysning",
                                 "högtider", "växtmöbler"]):
            return "other"
        if "fröer" in c or "grönsaker och örter" in c or "sticklingar" in c:
            return "seed"
        if "blomsterlök" in c or "potatis, lök" in c:
            return "bulb"
        if any(x in c for x in ["krukor", "krukfat", "krukvagnar", "trädgårdsskötsel",
                                 "jord, gödsel", "odlingstillbehör", "växtbelysning",
                                 "växthus", "planteringsbädd", "kompost",
                                 "uteplats > trädgårdsdekorationer", "uteplats > fågelmatning",
                                 "uteplats > trädgårdsdamm", "uteplats > gravdekorationer",
                                 "uteplats > utebelysning", "uteplats > utomhustillbehör",
                                 "gör-det-själv"]):
            return "tool"
        if "inomhusväxter" in c or "utomhusväxter" in c:
            return "plant"
        return "other"
    if retailer_id == 7:
        if name.startswith("fröer ") or name.startswith("frö "):
            return "seed"
        tool_words = ["adapter", "koppling", "slang", "bevattning", "kruka", "jord", "gödsel",
                      "redskap", "sekatör", "sax", "spade", "räfsa", "vägskran", "regulator",
                      "lampa", "belysning", "drivhus", "pallkrage", "kompost", "verktyg",
                      "fiberduk", "nät", "presenning", "odlingslåda", "thermacell",
                      "fågelmatare", "grilltillbehör", "hundleksak", "kattleksak",
                      "ampel", "underlägg", "krukfat", "spaljé", "koppel", "halsband"]
        for w in tool_words:
            if w in name:
                return "tool"
        bulb_words = ["dahlia", "tulpan", "sättlök", "sättpotatis", "gladiolus", "blomsterlök",
                      "krokus", "hyacint", "narciss"]
        for w in bulb_words:
            if w in name:
                return "bulb"
        if "fröer" in name or "frö" in name:
            return "seed"
        return "seed"
    return "seed"


def price_diff_pct(prices):
    if len(prices) < 2:
        return 0
    mn, mx = min(prices), max(prices)
    if mx == 0:
        return 0
    return (mx - mn) / mx * 100


RETAILER_BRANDS = {
    "impecta", "impecta fröhandel", "nelson garden", "weibulls", "florea",
    "zetas trädgård", "zetas", "blomsterlandet", "cramers blommor", "cramers",
    "klostra", "plantagen", "granngården",
}

def should_match(listings):
    """Determine if listings are truly the same product."""
    retailer_ids = set(l["retailer_id"] for l in listings)
    if len(retailer_ids) < 2:
        return True, 100, "single_retailer"
    
    types = set(l.get("_type") for l in listings)
    if len(types) > 1:
        return False, 0, f"type_mismatch: {types}"
    
    ptype = list(types)[0]
    
    # Brand check — only enforce for tools where brand = actual product brand (Gardena, Fiskars)
    # For seeds/plants/bulbs, "brand" is really the retailer name, so ignore it
    if ptype == "tool":
        brands = set(l.get("brand", "").strip().lower() for l in listings if l.get("brand"))
        # Filter out retailer names from brands
        real_brands = brands - RETAILER_BRANDS
        if len(real_brands) > 1:
            return False, 0, f"brand_mismatch: {real_brands}"
    
    prices = [l["price_sek"] for l in listings if l.get("price_sek") and l["price_sek"] > 0]
    if len(prices) >= 2:
        diff = price_diff_pct(prices)
        name = normalize(listings[0].get("name", ""))
        is_generic = len(name.split()) <= 2
        
        if is_generic and diff > 50:
            return False, 0, f"generic_name_price_diff_{diff:.0f}pct"
        if diff > 70:
            return False, 0, f"extreme_price_diff_{diff:.0f}pct"
        if diff > 40 and ptype == "tool" and len(set(l.get("brand","").strip().lower() for l in listings if l.get("brand")) - RETAILER_BRANDS) == 0:
            return False, 0, f"no_brand_high_price_diff_{diff:.0f}pct"
    
    return True, 85, "name_match_same_type"


def should_match_fuzzy(listings):
    """Looser matching for fuzzy/family groups — apply stricter price checks."""
    retailer_ids = set(l["retailer_id"] for l in listings)
    if len(retailer_ids) < 2:
        return True, 100, "single_retailer"
    
    types = set(l.get("_type") for l in listings)
    if len(types) > 1:
        return False, 0, f"type_mismatch: {types}"
    
    ptype = list(types)[0]
    
    # Brand check — only for tools
    if ptype == "tool":
        brands = set(l.get("brand", "").strip().lower() for l in listings if l.get("brand"))
        real_brands = brands - RETAILER_BRANDS
        if len(real_brands) > 1:
            return False, 0, f"brand_mismatch: {real_brands}"
    
    prices = [l["price_sek"] for l in listings if l.get("price_sek") and l["price_sek"] > 0]
    if len(prices) >= 2:
        diff = price_diff_pct(prices)
        # Stricter for fuzzy matches — max 60% price diff
        if diff > 60:
            return False, 0, f"fuzzy_price_diff_{diff:.0f}pct"
    
    return True, 70, "fuzzy_family_match"


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        sys.exit(1)

    # ── DRY RUN CHECK ──────────────────────────────────────────────
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("🔍 DRY RUN MODE — no data will be written\n")
    
    # ── Step 1: Fetch all listings ─────────────────────────────────
    print("Fetching listings from Supabase...")
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
    print(f"  {len(all_listings)} listings fetched")

    # ── Step 2: Detect product type ────────────────────────────────
    type_counts = defaultdict(int)
    for l in all_listings:
        l["_type"] = detect_product_type(l)
        l["_colour"] = extract_colour(l.get("name", ""))
        l["_base_plant"] = extract_base_plant(l.get("name", ""))
        l["_variety"] = extract_variety(l.get("name", ""))
        type_counts[l["_type"]] += 1
    
    print(f"  Product types: {dict(type_counts)}")

    # ── Step 3: PASS 1 — Exact name matching (same as v3) ─────────
    exact_groups = defaultdict(list)
    for l in all_listings:
        key = (normalize(l["name"]), l["_type"])
        exact_groups[key].append(l)

    matched_exact = []
    single_exact = []
    rejected_exact = []
    matched_listing_ids = set()
    
    for (name, ptype), listings in exact_groups.items():
        retailer_ids = set(l["retailer_id"] for l in listings)
        if len(retailer_ids) < 2:
            single_exact.append((name, ptype, listings))
            continue
        ok, confidence, reason = should_match(listings)
        if ok:
            matched_exact.append((name, ptype, listings, confidence, reason))
            for l in listings:
                matched_listing_ids.add(l["id"])
        else:
            rejected_exact.append((name, ptype, listings, reason))

    print(f"\n  PASS 1 (exact match):")
    print(f"    ✅ Matched: {len(matched_exact)} groups")
    print(f"    ❌ Rejected: {len(rejected_exact)} groups")
    print(f"    📦 Single-retailer: {len(single_exact)} groups")

    # ── Step 4: PASS 2 — Fuzzy plant-family matching ──────────────
    # Only for listings NOT already matched in pass 1
    unmatched = [l for l in all_listings if l["id"] not in matched_listing_ids 
                 and l["_type"] in ("seed", "plant", "bulb")]
    
    print(f"\n  PASS 2 (fuzzy family match): {len(unmatched)} unmatched plant/seed/bulb listings")
    
    # Group by (base_plant, product_type)
    family_groups = defaultdict(list)
    for l in unmatched:
        base = l["_base_plant"]
        if base and len(base) >= 3:  # skip very short base names
            key = (base, l["_type"])
            family_groups[key].append(l)
    
    matched_fuzzy = []
    rejected_fuzzy = []
    fuzzy_matched_ids = set()
    
    for (base, ptype), listings in family_groups.items():
        retailer_ids = set(l["retailer_id"] for l in listings)
        if len(retailer_ids) < 2:
            continue
        
        # Sub-group by variety if varieties exist
        # "Solhatt Magnus" and "Solhatt Cheyenne Spirit" are DIFFERENT products
        variety_subgroups = defaultdict(list)
        no_variety = []
        for l in listings:
            v = l["_variety"]
            if v and len(v) > 2:
                variety_subgroups[v].append(l)
            else:
                no_variety.append(l)
        
        # Match within each variety subgroup
        for variety, vlists in variety_subgroups.items():
            vretailers = set(l["retailer_id"] for l in vlists)
            if len(vretailers) >= 2:
                ok, confidence, reason = should_match_fuzzy(vlists)
                if ok:
                    display_name = f"{base} {variety}"
                    matched_fuzzy.append((display_name, ptype, vlists, confidence, f"fuzzy_variety:{reason}"))
                    for l in vlists:
                        fuzzy_matched_ids.add(l["id"])
                else:
                    rejected_fuzzy.append((f"{base} {variety}", ptype, vlists, reason))
        
        # Match the no-variety generics (plain "Mejram" across retailers)
        if len(no_variety) >= 2:
            nv_retailers = set(l["retailer_id"] for l in no_variety)
            if len(nv_retailers) >= 2:
                ok, confidence, reason = should_match_fuzzy(no_variety)
                if ok:
                    matched_fuzzy.append((base, ptype, no_variety, confidence, f"fuzzy_base:{reason}"))
                    for l in no_variety:
                        fuzzy_matched_ids.add(l["id"])
                else:
                    rejected_fuzzy.append((base, ptype, no_variety, reason))

    print(f"    ✅ Fuzzy matched: {len(matched_fuzzy)} new groups")
    print(f"    ❌ Fuzzy rejected: {len(rejected_fuzzy)} groups")

    # Show some examples
    if matched_fuzzy:
        print(f"\n  Sample fuzzy matches (first 10):")
        for name, ptype, listings, conf, reason in matched_fuzzy[:10]:
            retailers = set(l["retailer_id"] for l in listings)
            prices = [l["price_sek"] for l in listings if l.get("price_sek")]
            orignames = [l["name"][:40] for l in listings[:3]]
            print(f"    ✓ {name} [{ptype}] → {len(retailers)} retailers, prices={prices}")
            print(f"      From: {orignames}")

    # ── Step 5: Colour extraction stats ────────────────────────────
    colour_counts = defaultdict(int)
    for l in all_listings:
        if l["_colour"]:
            colour_counts[l["_colour"]] += 1
    if colour_counts:
        print(f"\n  Colours detected: {dict(colour_counts)}")

    # ── Summary ────────────────────────────────────────────────────
    total_multi = len(matched_exact) + len(matched_fuzzy)
    print(f"\n{'='*60}")
    print(f"  MATCHING v4 SUMMARY")
    print(f"{'='*60}")
    print(f"  Pass 1 (exact):  {len(matched_exact)} multi-retailer groups")
    print(f"  Pass 2 (fuzzy):  {len(matched_fuzzy)} new multi-retailer groups")
    print(f"  Total comparisons: {total_multi}")
    print(f"  vs v3's ~961 comparisons")
    print(f"{'='*60}")
    
    if dry_run:
        print("\n🔍 DRY RUN complete. Run without --dry-run to write to database.")
        return

    # ── Step 6: Write to database ──────────────────────────────────
    print("\nClearing old data...")
    api("DELETE", "product_listings", params={"id": "gt.0"})
    api("DELETE", "products", params={"id": "gt.0"})
    
    print("Creating matched products (exact)...")
    created_multi = 0
    linked = 0
    
    for name, ptype, listings, confidence, reason in matched_exact:
        slug = make_slug(name, ptype)
        image = next((l["image_url"] for l in listings if l.get("image_url")), "")
        latin = next((l["latin_name"] for l in listings if l.get("latin_name")), None)
        colour = next((l["_colour"] for l in listings if l.get("_colour")), None)
        
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
                print(f"  {created_multi} exact products...")

    print(f"Creating matched products (fuzzy)...")
    created_fuzzy = 0
    
    for name, ptype, listings, confidence, reason in matched_fuzzy:
        slug = make_slug(name, ptype)
        image = next((l["image_url"] for l in listings if l.get("image_url")), "")
        latin = next((l["latin_name"] for l in listings if l.get("latin_name")), None)
        
        result = api("POST", "products", data=[{
            "slug": slug, "name": name.title(), "latin_name": latin,
            "image_url": image or "", "product_type": ptype,
        }])
        if result and len(result) > 0:
            product_id = result[0]["id"]
            created_fuzzy += 1
            links = [{"product_id": product_id, "listing_id": l["id"], "match_score": confidence}
                     for l in listings]
            api("POST", "product_listings", data=links)
            linked += len(links)
            if created_fuzzy % 100 == 0:
                print(f"  {created_fuzzy} fuzzy products...")

    # Create single-retailer products (everything not yet matched)
    all_matched_ids = matched_listing_ids | fuzzy_matched_ids
    remaining = [l for l in all_listings if l["id"] not in all_matched_ids]
    
    # Group remaining by exact name + type
    remaining_groups = defaultdict(list)
    for l in remaining:
        key = (normalize(l["name"]), l["_type"])
        remaining_groups[key].append(l)
    
    print(f"Creating single-retailer products ({len(remaining_groups)})...")
    created_single = 0
    
    for (name, ptype), listings in remaining_groups.items():
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

    print(f"\n{'='*60}")
    print(f"MATCHING v4 COMPLETE")
    print(f"{'='*60}")
    print(f"  ✅ Exact multi-retailer: {created_multi}")
    print(f"  ✅ Fuzzy multi-retailer: {created_fuzzy}")
    print(f"  📦 Single-retailer: {created_single}")
    print(f"  Total products: {created_multi + created_fuzzy + created_single}")
    print(f"  Total price comparisons: {created_multi + created_fuzzy}")
    print(f"  Total links: {linked}")

if __name__ == "__main__":
    main()
