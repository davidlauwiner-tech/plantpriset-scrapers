#!/usr/bin/env python3
"""
Fetch seed counts from Impecta product pages and update Supabase.
Adds seed_count to the listings table for Impecta seed products.

Run once to backfill, then periodically to catch new products.
    python3 fetch_seed_counts.py
"""
import os, sys, re, time, json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

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
    "Prefer": "return=minimal",
}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept-Language": "sv-SE,sv;q=0.9",
})


def fetch_seed_count(url):
    """Fetch seed count from an Impecta product page."""
    try:
        resp = SESSION.get(url, timeout=10)
        resp.raise_for_status()
        # Look for "Portionsmängd X frö" pattern
        match = re.search(r'Portionsm.ngd.*?(\d+)\s*frö', resp.text, re.IGNORECASE | re.DOTALL)
        if match:
            return int(match[1])
        # Fallback: look for "X frö" in product info area
        soup = BeautifulSoup(resp.text, 'html.parser')
        info = soup.select_one('.productInfo, #Faktakolumn')
        if info:
            text = info.get_text()
            match2 = re.search(r'(\d+)\s*frö', text)
            if match2:
                count = int(match2[1])
                if 2 <= count <= 10000:
                    return count
        return None
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None


def get_impecta_listings_without_seed_count():
    """Get Impecta listings (retailer_id=1) that don't have seed_count yet."""
    # Get all Impecta listings where product_url contains /froer/
    url = f"{SUPABASE_URL}/rest/v1/listings"
    params = {
        "select": "id,name,product_url,quantity",
        "retailer_id": "eq.1",
        "product_url": "like.*froer*",
        "quantity": "eq.1",  # quantity=1 means "1 packet" — no seed count yet
        "limit": "500",
    }
    resp = requests.get(url, headers=HEADERS, params=params)
    if resp.status_code != 200:
        print(f"Error fetching listings: {resp.status_code} {resp.text}")
        return []
    return resp.json()


def update_listing_quantity(listing_id, seed_count):
    """Update the quantity field with the actual seed count."""
    url = f"{SUPABASE_URL}/rest/v1/listings?id=eq.{listing_id}"
    data = {"quantity": seed_count}
    resp = requests.patch(url, headers=HEADERS, json=data)
    return resp.status_code in (200, 204)


def main():
    print("Fetching Impecta seed listings without seed count...")
    listings = get_impecta_listings_without_seed_count()
    print(f"Found {len(listings)} listings to check")

    updated = 0
    skipped = 0
    errors = 0

    for i, listing in enumerate(listings, 1):
        url = listing.get("product_url", "")
        if not url or "impecta.se" not in url:
            skipped += 1
            continue

        seed_count = fetch_seed_count(url)
        if seed_count:
            success = update_listing_quantity(listing["id"], seed_count)
            if success:
                print(f"  [{i}/{len(listings)}] {listing['name']}: {seed_count} frön ✓")
                updated += 1
            else:
                errors += 1
        else:
            skipped += 1

        # Be polite
        time.sleep(1.5)

    print(f"\nDone! Updated: {updated}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    main()
