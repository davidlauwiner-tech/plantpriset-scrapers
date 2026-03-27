#!/usr/bin/env python3
"""
Plantpriset — Backfill missing images from Cramers Blommor.
"""
import os, sys, time
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

HEADERS_SB = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "text/html",
}


def extract_image(url):
    try:
        r = requests.get(url, headers=HEADERS_WEB, timeout=15)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Strategy 1: zoom images
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if "zoom" in src or "images/product" in src:
                if not src.startswith("http"):
                    src = "https://shop.cramersblommor.com" + src
                return src
        
        # Strategy 2: og:image
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]
        
        # Strategy 3: any product image
        for img in soup.find_all("img"):
            src = img.get("src") or ""
            if "/images/" in src and "logo" not in src and "icon" not in src and "banner" not in src:
                if not src.startswith("http"):
                    src = "https://shop.cramersblommor.com" + src
                return src
        
        return None
    except:
        return None


def main():
    print("Fetching Cramers listings with missing images...")
    listings = []
    offset = 0
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/listings",
            headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
            params={
                "retailer_id": "eq.3",
                "image_url": "eq.",
                "select": "id,name,product_url",
                "limit": "1000",
                "offset": str(offset),
                "order": "id.asc",
            },
            timeout=30,
        )
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        listings.extend(batch)
        offset += 1000
        if len(batch) < 1000:
            break

    print(f"  {len(listings)} listings need images\n")

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
            requests.patch(
                f"{SUPABASE_URL}/rest/v1/listings?id=eq.{l['id']}",
                headers=HEADERS_SB,
                json={"image_url": img},
                timeout=15,
            )
            # Update linked products too
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
            print(f" ✓")
        else:
            failed += 1
            print(" ✗")

        time.sleep(0.5)
        if (i + 1) % 100 == 0:
            print(f"\n  Progress: {found} found, {failed} failed\n")

    print(f"\n{'='*50}")
    print(f"CRAMERS IMAGE BACKFILL COMPLETE")
    print(f"  Found: {found}, Failed: {failed}")


if __name__ == "__main__":
    main()
