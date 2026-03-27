#!/usr/bin/env python3
"""
Plantpriset — Auto-assign subcategory_id to products based on name matching.
Run after match_products_v4.py to populate subcategory pages.
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

# ── Subcategory rules: (subcategory_id, parent_category, keywords) ─────
# Order matters — first match wins. More specific rules come first.
RULES = [
    # SEEDS — Tomato subtypes (must be before generic "tomater")
    (26, "seed", ["körsbärstomat", "cherry tomat"]),
    (27, "seed", ["bifftomat"]),
    (28, "seed", ["cocktailtomat"]),
    (29, "seed", ["plommontomat", "roma tomat", "san marzano"]),
    (30, "seed", ["busktomat"]),
    (31, "seed", ["ampeltomat", "hängtomat"]),
    (32, "seed", ["dvärg tomat", "dvärgtom", "micro tom"]),
    (33, "seed", ["specialtomat", "indigo", "svart tomat"]),
    (1,  "seed", ["tomat", "tomato"]),  # generic tomato catch-all

    # SEEDS — Vegetables
    (2,  "seed", ["chili", "paprika", "jalapeño", "habanero", "cayenne", "carolina reaper", "bhut jolokia", "scotch bonnet"]),
    (3,  "seed", ["gurka", "melon", "vattenmelon", "honungsmelon", "cantaloupe"]),
    (4,  "seed", ["sallat", "spenat", "mangold", "ruccola", "rucola", "pak choi", "mache", "endiv", "cikoria"]),
    (5,  "seed", ["böna", "bonor", "ärt", "ärter", "sockerärt", "brytböna", "skärböna", "störböna", "bondböna", "kidneyböna", "sojaböna"]),
    (6,  "seed", ["morot", "rädisa", "beta", "rödbeta", "palsternacka", "rotselleri", "majrova", "kålrot", "jordärtskocka", "pepparrot"]),
    (7,  "seed", ["pumpa", "squash", "zucchini", "butternut", "spaghettipumpa", "halloweenpumpa"]),
    (8,  "seed", ["kål", "broccoli", "blomkål", "vitkål", "rödkål", "savojkål", "spetskål", "grönkål", "palmkål", "brysselkål"]),
    (9,  "seed", ["aubergin", "äggplanta"]),
    (10, "seed", ["lök", "purjolök", "gräslök", "schalottenlök", "vinterlök", "kepalök", "rödlök", "silverlök", "vitlök", "ramslök"]),
    (11, "seed", ["majs", "sockermajs", "popcornmajs"]),

    # SEEDS — Herbs
    (12, "seed", ["basilika", "persilja", "dill", "koriander", "timjan", "rosmarin", "oregano",
                   "mejram", "mynta", "salvia", "citronmeliss", "dragon", "fänkål", "anis",
                   "kummin", "kyndel", "libbsticka", "krasse", "koriander", "lagerblad",
                   "lavendel fröer", "ört"]),

    # SEEDS — Flowers
    (14, "seed", ["luktärt"]),
    (15, "seed", ["solhatt", "echinacea", "akleja", "riddarsporre", "fingerborgsblomma",
                   "stockros", "malva", "rudbeckia", "astilbe", "flox", "iris", "pion",
                   "prästkrage", "blåklocka", "blodnäva", "geranium", "funkia", "hosta",
                   "röllika", "kattmynta", "näva", "stormhatt", "alunrot", "bergenia",
                   "daggkåpa", "blåeld", "verbascum", "digitalis"]),
    (13, "seed", ["zinnia", "cosmos", "rosenskära", "ringblomma", "vallmo", "solros",
                   "blåklint", "lejongap", "lobelia", "petunia", "tagetes", "dahlia frö",
                   "penséer", "begonia frö", "verbena", "celosia", "amarant", "klockia",
                   "clarkia", "godetia", "heliotrop", "aster", "krysantemum", "blomman för dagen",
                   "prydnadsgräs frö", "sötärt", "praktsalvia", "nicotiana", "blomstertobak",
                   "blomsterlin", "blomsterkörvel", "blomstermorot", "fjärilsbuske frö",
                   "doftwicke", "gyllenlack", "lövkoja", "vinda", "ipomea"]),

    # PLANTS
    (16, "plant", ["perenn", "lavendel", "solhatt", "echinacea", "akleja", "riddarsporre",
                    "flox", "iris", "pion", "hosta", "funkia", "rudbeckia", "astilbe",
                    "prästkrage", "geranium", "näva", "blodnäva", "alunrot", "bergenia",
                    "daggkåpa", "kattmynta", "daglilja", "klocklilja", "kärleksört",
                    "stormhatt", "röllika", "verbena", "veronica", "salvia", "timjan",
                    "sedum", "fetblad", "vintergröna", "vinca", "iberis",
                    "flocknäva", "jätteverbena", "purpurmejram"]),
    (17, "plant", ["buske", "träd", "rhododendron", "hortensia", "syren", "forsythia",
                    "spirea", "häck", "liguster", "berberis", "snöbär", "kornell",
                    "jasmin", "magnolia", "körsbär", "äppelträd", "päronträd", "plommonträd",
                    "björk", "lönn", "ek", "tall", "gran", "tuja", "cypress", "buxbom",
                    "klätterväxt", "klematis", "kaprifol", "murgröna", "vin"]),
    (18, "plant", ["krukväxt", "inomhus", "monstera", "philodendron", "pothos", "orkidé",
                    "palm", "fikus", "succulent", "kaktus", "kalanchoe", "begonia"]),

    # BULBS
    (19, "bulb",  ["dahlia"]),
    (20, "bulb",  ["tulpan", "krokus", "narciss", "hyacint", "snödroppe", "blåstjärna",
                    "vårstjärna", "allium", "iris lökar", "lilja lökar", "gladiolus",
                    "anemone", "ranunkel", "vildtulpan"]),
    (21, "bulb",  ["sättpotatis", "sättlök", "vinterlök"]),

    # TOOLS — Watering subtypes
    (42, "tool",  ["droppbevattning", "droppslang", "dripline"]),
    (43, "tool",  ["bevattningsdator", "timer", "bevattningsur"]),
    (44, "tool",  ["vattenkanna", "sprej", "spruta", "trädgårdsprej"]),
    (45, "tool",  ["semesterbevattning"]),
    (46, "tool",  ["regntunna", "regnvattentunna"]),
    (41, "tool",  ["slang", "koppling", "vinkelkoppling", "snabbkoppling", "slanghållare"]),
    (34, "tool",  ["bevattning", "vattenspridare", "vattensprinkler", "sprinkler"]),

    # TOOLS — Soil subtypes
    (47, "tool",  ["blomjord"]),
    (48, "tool",  ["grönsaksjord", "tomatjord"]),
    (49, "tool",  ["såjord"]),
    (50, "tool",  ["planteringsjord"]),
    (51, "tool",  ["surjord", "rhododendronjord", "orkidéjord", "kaktusjord", "citrusjord"]),
    (52, "tool",  ["perlit", "leca", "vermikulit", "lecakulor", "kokosfiber", "biokol"]),
    (35, "tool",  ["jord"]),  # generic soil catch-all

    # TOOLS — Fertilizer subtypes
    (53, "tool",  ["universalgödsel", "universell näring", "allround"]),
    (55, "tool",  ["flytande näring", "flytande gödsel", "pumpflaska"]),
    (54, "tool",  ["tomatgödsel", "rosgödsel", "gräsmattegödsel", "hortensiago", "rhododendrongödsel"]),
    (56, "tool",  ["organisk", "bonbio", "ekologisk gödsel", "hönsgödsel", "kogödsel"]),
    (57, "tool",  ["kompost", "bokashi"]),
    (36, "tool",  ["gödsel", "näring", "växtnäring", "jordkraft"]),  # generic fertilizer

    # TOOLS — Pots & containers
    (61, "tool",  ["ampel", "hängande kruka", "hängampel"]),
    (60, "tool",  ["pallkrage", "odlingslåda"]),
    (58, "tool",  ["innekruka"]),
    (59, "tool",  ["utekruka"]),
    (37, "tool",  ["kruka", "krukfat", "underlägg", "odlings"]),

    # TOOLS — Plant protection
    (63, "tool",  ["insekt", "bladlus", "snigel", "nematod", "biologisk bekämpning"]),
    (64, "tool",  ["viltskydd", "rådjur", "hjort", "fågelskydd", "nät", "fiberduk"]),
    (65, "tool",  ["ogräs", "ogräsmedel"]),
    (38, "tool",  ["växtskydd", "bekämpning"]),

    # TOOLS — Hand tools
    (67, "tool",  ["sekatör", "sax", "trädgårdssax", "grensax"]),
    (66, "tool",  ["spade", "hacka", "grep", "skyffel"]),
    (68, "tool",  ["räfsa", "kratta"]),
    (39, "tool",  ["redskap", "verktyg", "handske"]),

    # TOOLS — Lighting & greenhouse
    (40, "tool",  ["växtbelysning", "växtlampa", "växtarmatur", "led lampa", "led-ramp", "odlingslampa", "grow"]),
    (62, "tool",  ["drivhus", "växthus", "miniväxthus", "förodling", "pluggbrätte", "såbrätte", "driv"]),
]


def categorize_product(name, product_type):
    """Return subcategory_id for a product based on name + type."""
    n = name.lower()
    for subcat_id, parent_cat, keywords in RULES:
        if parent_cat != product_type:
            continue
        for kw in keywords:
            if kw in n:
                return subcat_id
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
            params={"select": "id,name,product_type", "limit": "1000", "offset": str(offset), "order": "id.asc"},
            timeout=30,
        )
        if r.status_code != 200:
            print(f"Error: {r.status_code} {r.text[:200]}")
            break
        batch = r.json()
        if not batch:
            break
        products.extend(batch)
        offset += 1000
        if len(batch) < 1000:
            break

    print(f"  {len(products)} products fetched")

    # Categorize
    updates = {}  # subcat_id → [product_ids]
    uncategorized = 0
    for p in products:
        subcat_id = categorize_product(p["name"], p.get("product_type", "seed"))
        if subcat_id:
            updates.setdefault(subcat_id, []).append(p["id"])
        else:
            uncategorized += 1

    categorized = sum(len(ids) for ids in updates.values())
    print(f"  Categorized: {categorized}")
    print(f"  Uncategorized: {uncategorized}")

    # Batch update by subcategory
    print("\nUpdating subcategory_id...")
    updated = 0
    for subcat_id, product_ids in sorted(updates.items()):
        # Update in batches of 200 IDs
        for i in range(0, len(product_ids), 200):
            batch_ids = product_ids[i:i+200]
            id_filter = ",".join(str(x) for x in batch_ids)
            r = requests.patch(
                f"{SUPABASE_URL}/rest/v1/products?id=in.({id_filter})",
                headers=HEADERS,
                json={"subcategory_id": subcat_id},
                timeout=30,
            )
            if r.status_code in (200, 204):
                updated += len(batch_ids)
            else:
                print(f"  Error updating subcat {subcat_id}: {r.status_code} {r.text[:200]}")

        if updated % 500 < 200:
            print(f"  {updated} products updated...")

    print(f"\n{'='*50}")
    print(f"CATEGORIZATION COMPLETE")
    print(f"{'='*50}")
    print(f"  Updated: {updated}")
    print(f"  Uncategorized: {uncategorized}")

    # Show distribution
    print(f"\n  Distribution:")
    for subcat_id, ids in sorted(updates.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"    Subcategory {subcat_id}: {len(ids)} products")


if __name__ == "__main__":
    main()
