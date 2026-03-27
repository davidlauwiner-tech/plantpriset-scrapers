#!/usr/bin/env python3
"""
Plantpriset — Categorize remaining uncategorized products (v2).
Only updates products that currently have subcategory_id = null.
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

# ── RULES v2: broader catch-all rules for remaining products ───────────
# These run ONLY on products that weren't caught by v1.
# Order matters — first match wins.

RULES = [
    # ── BULBS (9 remaining) ──
    (20, "bulb", ["lökar", "lökar", "tulipa"]),
    (21, "bulb", ["lök", "potatis", "vitlök", "schalotten", "silverlök"]),
    (19, "bulb", ["pion", "dahlia"]),

    # ── SEEDS: Vegetables (specific first) ──
    (1,  "seed", ["tomat"]),
    (2,  "seed", ["chili", "paprika", "jalapeño", "habanero", "cayenne"]),
    (3,  "seed", ["gurka", "melon"]),
    (4,  "seed", ["sallat", "spenat", "mangold", "ruccola", "pak choi", "endiv"]),
    (5,  "seed", ["böna", "ärt", "linser"]),
    (6,  "seed", ["morot", "rädisa", "beta", "palsternacka", "selleri", "majrova", "kålrot"]),
    (7,  "seed", ["pumpa", "squash", "zucchini"]),
    (8,  "seed", ["kål", "broccoli", "blomkål"]),
    (9,  "seed", ["aubergin"]),
    (10, "seed", ["lök", "purjolök", "gräslök", "ramslök", "vitlök"]),
    (11, "seed", ["majs"]),

    # ── SEEDS: Herbs ──
    (12, "seed", ["basilika", "persilja", "dill", "koriander", "timjan", "rosmarin",
                   "oregano", "mejram", "mynta", "salvia", "citronmeliss", "dragon",
                   "fänkål", "anis", "kummin", "kyndel", "libbsticka", "ört",
                   "krasse", "isop", "malört", "lakrits"]),

    # ── SEEDS: Luktärter ──
    (14, "seed", ["luktärt"]),

    # ── SEEDS: Perennial flowers (frö) — specific names ──
    (15, "seed", ["solhatt", "echinacea", "akleja", "riddarsporre", "fingerborgsblomma",
                   "stockros", "malva", "rudbeckia", "astilbe", "flox", "iris", "pion",
                   "prästkrage", "blåklocka", "blodnäva", "geranium", "hosta",
                   "röllika", "kattmynta", "näva", "stormhatt", "alunrot", "bergenia",
                   "daggkåpa", "blåeld", "verbascum", "digitalis", "anisisop",
                   "afghanperovskia", "perovskia", "aklejruta", "ålandsrot",
                   "alchemilla", "åkervädd", "älggräs", "alpgentiana", "alpgullregn",
                   "alpmartorn", "alpros", "alruna", "trollhassel", "blålilja",
                   "funkia", "gentiana", "klocklilja", "kärleksört",
                   "fetblad", "sedum", "vinca", "iberis",
                   "binka", "blåstjärna", "brunnäva", "brunört",
                   "drakblomma", "eldkrona", "fackelblomster", "fjärilsbuske",
                   "flockblomstra", "getväppling", "gipsört", "glansnäva",
                   "gullris", "gullviva", "gullört", "gunnera", "gökblomster",
                   "hesperis", "hjärtblomma", "humle", "jordviva",
                   "kaukasisk förgätmigej", "klasefibbla", "klippros",
                   "kungsmynta", "kungsängslilja", "kärringtand", "leontopodium",
                   "liatris", "ljung", "lungört", "lysing",
                   "martorn", "murgröna", "myrlilja", "nattljus",
                   "pentstemon", "pimpinell", "prakthypericum", "präriemalva",
                   "renfana", "rosenvial", "silverax", "skogsviol",
                   "smultron", "snöbollsbuske", "solbrud", "solvända",
                   "spirea", "stenkyndel", "stjärnflocka", "strandaster",
                   "studentnejlika", "sötväppling", "tistelboll",
                   "trampört", "trollius", "tusensköna", "vallört",
                   "veronika", "vindruva", "viol", "vitplister",
                   "vädd", "ängssalvia", "ängsull", "ölandssolvända"]),

    # ── SEEDS: Annual flowers — catch-all for remaining seed types ──
    # This is BROAD: if a seed didn't match vegetables, herbs, luktärter, or perennials,
    # it's most likely an annual flower
    (13, "seed", ["ageratum", "amarant", "antirrhinum", "aster ", "begonia",
                   "bivänlig", "blåklint", "blomma", "celosia", "chrysanthemum",
                   "clarkia", "clematis frö", "coleus", "cosmos", "dahlia frö",
                   "datura", "delphinium", "dianthus", "dimorphotheca",
                   "eschscholzia", "eukalyptus", "euphorbia", "gaillardia",
                   "gazania", "godetia", "gomphrena", "gypsophila",
                   "helenium", "helianthus", "helichrysum", "helipterum",
                   "hesperis", "impatiens", "ipomea", "jordgubb",
                   "klockhyacint", "kochia", "lathyrus", "lavatera",
                   "leptosiphon", "liatris", "limonium", "linaria",
                   "lobelia", "lophospermum", "lotus", "lövkoja",
                   "lupinus", "malope", "matthiola", "mimosa",
                   "mirabilis", "nemophila", "nicotiana", "nigella",
                   "osteospermum", "papaver", "pelargon", "pensé",
                   "petunia", "phlox", "portulaca", "primula",
                   "reseda", "ricinus", "ringblomma", "rosenskära",
                   "rudbeckia", "salpiglossis", "saponaria", "scabiosa",
                   "schizanthus", "senecio", "solros", "statice",
                   "sötärt", "tagetes", "thunbergia", "tithonia",
                   "torenia", "tropaeolum", "vallmo", "verbena",
                   "vinda", "viola", "zinnia",
                   # Swedish common flower names that are likely annuals
                   "sommar", "blåeld", "borstnejlika", "eldkrona",
                   "fackelblomstera", "fingerborg", "gyllenlack",
                   "hattblomma", "honungsfacelia", "jungfrun i det gröna",
                   "kornvallmo", "krondill", "kungsljus",
                   "lejongap", "lin ", "midsommarblomster",
                   "murreva", "natt", "nattviol",
                   "prydnadsgräs", "praktsalvia", "sammet",
                   "silverek", "skäggnejlika", "snigel",
                   "stjärnhyacint", "styvmorsviol", "svärd",
                   "trumpetblomma", "ärenpris"]),

    # ── PLANTS: Indoor/tropical ──
    (18, "plant", ["aglaonema", "alokasia", "alocasia", "aloe", "anthurium",
                    "asplenium", "begonia", "bonsai", "bromeliad", "calathea",
                    "chlorophytum", "crassula", "dieffenbachia", "dracaena",
                    "epipremnum", "ficus", "fikus", "filodendron", "hedera",
                    "kalanchoe", "maranta", "monstera", "musa", "nephrolepis",
                    "orchidé", "orkidé", "pachira", "palm", "peperomia",
                    "philodendron", "pilea", "pothos", "sansevieria", "scindapsus",
                    "spathiphyllum", "strelitzia", "succulent", "syngonium",
                    "tradescantia", "zamioculcas", "i kruka", "i ampel",
                    "krukväxt", "inomhus", "ampelfackla", "ampellilja",
                    "elefantöra", "fredskalla", "gullranka", "pengaträd",
                    "svärmors", "paradisväxt"]),

    # ── PLANTS: Fruit & berries ──
    (17, "plant", ["blåbär", "hallon", "jordgubb", "vinbär", "krusbär",
                    "björnbär", "äpple", "päron", "plommon", "körsbär",
                    "fikon", "citrus", "citron", "apelsin", "lime",
                    "olivträd", "fikonträd", "vindruv"]),

    # ── PLANTS: Bushes & trees ──
    (17, "plant", ["buske", "träd", "häck", "rhododendron", "hortensia", "syren",
                    "forsythia", "spirea", "liguster", "berberis", "snöbär",
                    "kornell", "jasmin", "magnolia", "björk", "lönn", "ek",
                    "tall", "gran", "tuja", "cypress", "buxbom", "bambu",
                    "klematis", "kaprifol", "murgröna", "blåregn", "visteriavin",
                    "ros ", "rosor", "klätterros", "buskros", "parkros",
                    "dvärgbuske", "prydnadsbuske", "häckväxt",
                    "trollhassel", "benved", "måbär", "havtorn",
                    "aronia", "fläder", "vide", "pil"]),

    # ── PLANTS: Perennials (remaining plants that aren't indoor or bushes) ──
    (16, "plant", ["perenn", "lavendel", "solhatt", "echinacea", "akleja",
                    "riddarsporre", "flox", "iris", "pion", "hosta",
                    "funkia", "rudbeckia", "astilbe", "prästkrage",
                    "geranium", "näva", "blodnäva", "alunrot", "bergenia",
                    "daggkåpa", "kattmynta", "daglilja", "klocklilja",
                    "kärleksört", "stormhatt", "röllika", "veronica",
                    "salvia", "timjan", "sedum", "fetblad", "vintergröna",
                    "vinca", "iberis", "anisisop", "anisört",
                    "flocknäva", "jätteverbena", "purpurmejram",
                    "höstanemon", "kärleksblomma", "praktspira",
                    "silverax", "smultron växt", "stjärnflocka"]),

    # ── TOOLS: Watering ──
    (34, "tool", ["bevattning", "sprinkler", "vattenspridare", "vägskran",
                   "anslutning", "backventil", "antihävert", "stuprör",
                   "anläggningsrör", "micro-drip", "avslutningsring"]),
    (41, "tool", ["slang", "koppling", "vinkel", "snabbkoppling", "adapter"]),
    (44, "tool", ["vattenkanna", "spruta", "sprej"]),

    # ── TOOLS: Soil & fertilizer ──
    (35, "tool", ["jord", "dressand", "torv"]),
    (36, "tool", ["gödsel", "näring", "algomin", "jordkraft"]),

    # ── TOOLS: Pots & containers ──
    (37, "tool", ["kruka", "låda", "box ", "ampel", "fat ", "underlägg", "hängare",
                   "balkong", "pallkrage"]),

    # ── TOOLS: Greenhouse & growing ──
    (62, "tool", ["drivhus", "växthus", "miniväxthus", "förodling", "hydroponisk",
                   "plugg", "brätte", "akarina"]),

    # ── TOOLS: Lighting ──
    (40, "tool", ["belysning", "lampa", "led ", "ljus", "minilight"]),

    # ── TOOLS: Protection ──
    (38, "tool", ["avskräckning", "repellis", "skydd", "bekämpning", "snigel"]),

    # ── TOOLS: Hand tools & misc ──
    (39, "tool", ["redskap", "verktyg", "spade", "sax", "sekatör", "räfsa",
                   "handske", "knäskydd", "trädgårds"]),

    # ══ FALLBACK CATCH-ALLS ══
    # Any remaining seed → Ettåriga Blommor (13) as default
    (13, "seed", [""]),  # empty string matches everything

    # Any remaining plant → Perenner (16) as default
    (16, "plant", [""]),

    # Any remaining tool → Redskap (39) as default
    (39, "tool", [""]),

    # Any remaining bulb → Blomsterlökar (20) as default
    (20, "bulb", [""]),
]


def categorize_product(name, product_type):
    """Return subcategory_id for a product based on name + type."""
    n = name.lower()
    for subcat_id, parent_cat, keywords in RULES:
        if parent_cat != product_type:
            continue
        for kw in keywords:
            if kw == "":  # catch-all
                return subcat_id
            if kw in n:
                return subcat_id
    return None


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        sys.exit(1)

    # Fetch only uncategorized products
    print("Fetching uncategorized products...")
    products = []
    offset = 0
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/products",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params={
                "subcategory_id": "is.null",
                "select": "id,name,product_type",
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
        products.extend(batch)
        offset += 1000
        if len(batch) < 1000:
            break

    print(f"  {len(products)} uncategorized products")

    # Skip "other" type — those are non-garden products
    garden_products = [p for p in products if p["product_type"] != "other"]
    other_count = len(products) - len(garden_products)
    print(f"  Skipping {other_count} 'other' type products (non-garden items)")
    print(f"  Categorizing {len(garden_products)} garden products\n")

    # Categorize
    updates = {}
    uncategorized = 0
    for p in garden_products:
        subcat_id = categorize_product(p["name"], p["product_type"])
        if subcat_id:
            updates.setdefault(subcat_id, []).append(p["id"])
        else:
            uncategorized += 1

    categorized = sum(len(ids) for ids in updates.values())
    print(f"  Will categorize: {categorized}")
    print(f"  Still uncategorized: {uncategorized}")

    # Batch update
    print("\nUpdating subcategory_id...")
    updated = 0
    for subcat_id, product_ids in sorted(updates.items()):
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
                print(f"  Error: {r.status_code} {r.text[:200]}")

    print(f"\n{'='*50}")
    print(f"CATEGORIZATION v2 COMPLETE")
    print(f"{'='*50}")
    print(f"  Newly categorized: {updated}")
    print(f"  Skipped (other): {other_count}")
    print(f"  Still uncategorized: {uncategorized}")

    # Distribution
    print(f"\n  Distribution:")
    for subcat_id, ids in sorted(updates.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"    Subcategory {subcat_id}: {len(ids)} products")


if __name__ == "__main__":
    main()
