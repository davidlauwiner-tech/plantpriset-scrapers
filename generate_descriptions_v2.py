#!/usr/bin/env python3
"""
Plantpriset — Generate AI descriptions for products without them.
v2: Added retry with exponential backoff for 529 overloaded errors.

Usage:
  cd ~/Downloads/plantpriset-scrapers
  python3 generate_descriptions_v2.py

Requires .env with:
  SUPABASE_URL=https://xunlsikrzohrchtbqkcv.supabase.co
  SUPABASE_SERVICE_KEY=...
  ANTHROPIC_API_KEY=sk-ant-...
"""

import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, ANTHROPIC_KEY]):
    print("ERROR: Missing env vars. Need SUPABASE_URL, SUPABASE_SERVICE_KEY, ANTHROPIC_API_KEY")
    sys.exit(1)

HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

HEADERS_ANTHROPIC = {
    "x-api-key": ANTHROPIC_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

# ── Retry settings ──────────────────────────────────────────────
MAX_RETRIES = 5
BASE_DELAY = 10        # seconds — start with 10s for 529s
MAX_DELAY = 120        # cap at 2 minutes
BATCH_PAUSE = 1.5      # seconds between successful requests
CONSECUTIVE_FAIL_LIMIT = 10  # if 10 in a row fail, pause longer


def generate_description(product, retries=MAX_RETRIES):
    """Call Claude API to generate a Swedish product description, with retry."""
    name = product.get("name", "Okänd produkt")
    product_type = product.get("product_type", "")

    prompt = f"""Skriv en kort, informativ produktbeskrivning på svenska (max 3 meningar, ca 50-80 ord) för denna trädgårdsprodukt:

Produkt: {name}
Typ: {product_type}

Beskrivningen ska vara faktabaserad, naturlig och hjälpa en trädgårdsentusiast förstå produkten. 
Nämn användningsområde och eventuella fördelar. Skriv BARA beskrivningen, inget annat."""

    for attempt in range(retries):
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=HEADERS_ANTHROPIC,
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=60
            )

            if r.status_code == 200:
                data = r.json()
                return data["content"][0]["text"].strip()

            elif r.status_code == 529:
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                print(f"   ⏳ API overloaded (529). Waiting {delay}s before retry {attempt+1}/{retries}...")
                time.sleep(delay)
                continue

            elif r.status_code == 429:
                delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                print(f"   ⏳ Rate limited (429). Waiting {delay}s before retry {attempt+1}/{retries}...")
                time.sleep(delay)
                continue

            else:
                print(f"   API error {r.status_code}: {r.text[:100]}")
                return None

        except requests.exceptions.ReadTimeout:
            delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
            print(f"   ⏳ Timeout. Waiting {delay}s before retry {attempt+1}/{retries}...")
            time.sleep(delay)
            continue

        except Exception as e:
            print(f"   Unexpected error: {e}")
            return None

    print(f"   ❌ All {retries} retries exhausted.")
    return None


def update_description(product_id, description):
    """Write description back to Supabase."""
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/products?id=eq.{product_id}",
        headers=HEADERS_SB,
        json={"description": description}
    )
    return r.status_code in (200, 204)


def fetch_products_without_descriptions(limit=500):
    """Get products that still need descriptions."""
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/products",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        params={
            "description": "is.null",
            "select": "id,name,product_type",
            "order": "name.asc",
            "limit": limit
        }
    )
    if r.status_code == 200:
        return r.json()
    print(f"Error fetching products: {r.status_code} {r.text[:200]}")
    return []


def main():
    print("Fetching products without descriptions...")
    products = fetch_products_without_descriptions(500)
    print(f"Found {len(products)} products without descriptions\n")

    if not products:
        print("All products have descriptions!")
        return

    print("Generating descriptions with Claude (with retry on 529)...\n")

    ok = 0
    failed = 0
    consecutive_fails = 0

    for i, p in enumerate(products):
        name = p.get("name", "?")
        print(f"  [{i+1}/{len(products)}] {name[:60]}...", end="", flush=True)

        desc = generate_description(p)

        if desc:
            if update_description(p["id"], desc):
                ok += 1
                consecutive_fails = 0
                print(f" OK ({len(desc)} chars)")
            else:
                failed += 1
                consecutive_fails += 1
                print(" DB WRITE FAILED")
        else:
            failed += 1
            consecutive_fails += 1
            print("")  # newline after the retries

        # If many consecutive failures, the API is probably still recovering
        if consecutive_fails >= CONSECUTIVE_FAIL_LIMIT:
            pause = 120
            print(f"\n  ⚠️  {CONSECUTIVE_FAIL_LIMIT} consecutive failures. Pausing {pause}s...\n")
            time.sleep(pause)
            consecutive_fails = 0

        # Normal pacing between requests
        if desc:
            time.sleep(BATCH_PAUSE)

    print(f"\n{'='*50}")
    print(f"DONE: {ok} generated, {failed} failed out of {len(products)}")
    print(f"{'='*50}")

    # Check remaining
    remaining = fetch_products_without_descriptions(1)
    if remaining:
        print(f"\nStill {len(remaining)}+ products without descriptions. Run again later.")
    else:
        print("\n🎉 All products now have descriptions!")


if __name__ == "__main__":
    main()
