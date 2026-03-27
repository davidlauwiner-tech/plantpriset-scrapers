#!/usr/bin/env python3
"""
Plantpriset — Generate AI descriptions for products without them.
v3: Supports parallel execution with partitions.

Usage:
  # Single tab (processes all):
  python3 generate_descriptions_v3.py

  # 3 parallel tabs:
  python3 generate_descriptions_v3.py 1 3    # Tab 1: products 1,4,7,10...
  python3 generate_descriptions_v3.py 2 3    # Tab 2: products 2,5,8,11...
  python3 generate_descriptions_v3.py 3 3    # Tab 3: products 3,6,9,12...
"""
import os, sys, time
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
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

if not all([SUPABASE_URL, SUPABASE_KEY, ANTHROPIC_KEY]):
    print("ERROR: Missing env vars. Need SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY")
    sys.exit(1)

HEADERS_ANTHROPIC = {
    "x-api-key": ANTHROPIC_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}

MAX_RETRIES = 5
BASE_DELAY = 10
MAX_DELAY = 120
BATCH_PAUSE = 1.0


def generate_description(product):
    name = product.get("name", "Okänd produkt")
    product_type = product.get("product_type", "")

    prompt = f"""Skriv en kort, informativ produktbeskrivning på svenska (max 3 meningar, ca 50-80 ord) för denna trädgårdsprodukt:

Produkt: {name}
Typ: {product_type}

Beskrivningen ska vara faktabaserad, naturlig och hjälpa en trädgårdsentusiast förstå produkten. 
Nämn användningsområde och eventuella fördelar. Skriv BARA beskrivningen, inget annat."""

    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=HEADERS_ANTHROPIC,
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60,
            )
            if r.status_code == 200:
                return r.json()["content"][0]["text"].strip()
            elif r.status_code in (529, 429):
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                print(f" ⏳ {r.status_code} waiting {delay}s...", end="", flush=True)
                time.sleep(delay)
            elif r.status_code == 400 and "credit" in r.text.lower():
                print(f" ❌ OUT OF CREDITS")
                sys.exit(1)
            else:
                print(f" ERR {r.status_code}")
                return None
        except requests.exceptions.ReadTimeout:
            delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
            print(f" ⏳ timeout, waiting {delay}s...", end="", flush=True)
            time.sleep(delay)
    return None


def main():
    # Parse partition args
    partition = 1
    total_partitions = 1
    if len(sys.argv) >= 3:
        partition = int(sys.argv[1])
        total_partitions = int(sys.argv[2])
    
    print(f"Partition {partition}/{total_partitions}")
    print("Fetching ALL products without descriptions...")
    
    all_products = []
    offset = 0
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/products",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params={
                "description": "is.null",
                "select": "id,name,product_type",
                "order": "id.asc",
                "limit": "1000",
                "offset": str(offset),
            },
            timeout=30,
        )
        if r.status_code != 200:
            print(f"Error: {r.status_code}")
            break
        batch = r.json()
        if not batch:
            break
        all_products.extend(batch)
        offset += 1000
        if len(batch) < 1000:
            break

    print(f"Total without descriptions: {len(all_products)}")

    # Pick only this partition's products
    my_products = [p for i, p in enumerate(all_products) if (i % total_partitions) == (partition - 1)]
    print(f"This partition handles: {len(my_products)} products\n")

    ok = 0
    failed = 0
    for i, p in enumerate(my_products):
        name = p.get("name", "?")
        print(f"  [{i+1}/{len(my_products)}] {name[:55]}...", end="", flush=True)

        desc = generate_description(p)
        if desc:
            r = requests.patch(
                f"{SUPABASE_URL}/rest/v1/products?id=eq.{p['id']}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                json={"description": desc},
                timeout=15,
            )
            if r.status_code in (200, 204):
                ok += 1
                print(f" OK ({len(desc)} chars)")
            else:
                failed += 1
                print(f" DB ERR {r.status_code}")
        else:
            failed += 1
            print("")

        time.sleep(BATCH_PAUSE)

    print(f"\n{'='*50}")
    print(f"PARTITION {partition}/{total_partitions} DONE")
    print(f"  OK: {ok}, Failed: {failed}")


if __name__ == "__main__":
    main()
