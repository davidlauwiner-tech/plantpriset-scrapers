#!/usr/bin/env python3
"""
Plantpriset — Backfill missing images from Blomsterlandet.
Visits each listing's product_url and extracts the main product image.
Then updates both the listing and the linked product.
"""
import os, sys, re, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
BASE = "https://www.blomsterlandet.se"

HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8",
}


def extract_image(url):
    """Fetch a Blomsterlandet product page and extract the main image URL."""
    try:
        r = requests.get(url, headers=HEADERS_WEB, timeout=15)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Strategy 1: Look for catalog-images in globalassets
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if "catalog-images" in src or "product" in src.lower():
                if not src.startswith("http"):
                    src = BASE + src
                return src
        
        # Strategy 2: og:image meta tag
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            src = og["content"]
            if not src.startswith("http"):
                src = BASE + src
            return src
        
        # Strategy 3: Any large image in the product area
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if src and "globalassets" in src and "footer" not in src and "logo" not in src:
                if not src.startswith("http"):
                    src = BASE + src
                return src
        
        return None
    except Exception as e:
        return None


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        sys.exit(1)

    # Fetch Blomsterlandet listings with empty images
    print("Fetching Blomsterlandet listings with missing images...")
    listings = []
    offset = 0
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/listings",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params={
                "retailer_id": "eq.2",
                "image_url": "eq.",
                "select": "id,name,product_url",
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
        listings.extend(batch)
        offset += 1000
        if len(batch) < 1000:
            break

    print(f"  {len(listings)} listings need images\n")

    # Process each listing
    found = 0
    failed = 0
    for i, l in enumerate(listings):
        url = l.get("product_url", "")
        name = l.get("name", "?")[:45]
        print(f"  [{i+1}/{len(listings)}] {name}...", end="", flush=True)

        if not url:
            print(" NO URL")
            failed += 1
            continue

        img = extract_image(url)
        if img:
            # Update listing
            r1 = requests.patch(
                f"{SUPABASE_URL}/rest/v1/listings?id=eq.{l['id']}",
                headers=HEADERS_SB,
                json={"image_url": img},
                timeout=15,
            )
            
            # Also update any linked products that have empty image_url
            r2 = requests.get(
                f"{SUPABASE_URL}/rest/v1/product_listings?listing_id=eq.{l['id']}&select=product_id",
                headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
                timeout=15,
            )
            if r2.status_code == 200:
                for pl in r2.json():
                    requests.patch(
                        f"{SUPABASE_URL}/rest/v1/products?id=eq.{pl['product_id']}&image_url=eq.",
                        headers=HEADERS_SB,
                        json={"image_url": img},
                        timeout=15,
                    )

            found += 1
            print(f" ✓ {img[:60]}")
        else:
            failed += 1
            print(" ✗ no image found")

        # Be polite — don't hammer the site
        time.sleep(0.5)

        if (i + 1) % 100 == 0:
            print(f"\n  Progress: {found} found, {failed} failed out of {i+1}\n")

    print(f"\n{'='*50}")
    print(f"IMAGE BACKFILL COMPLETE")
    print(f"{'='*50}")
    print(f"  Found: {found}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(listings)}")


if __name__ == "__main__":
    main()
