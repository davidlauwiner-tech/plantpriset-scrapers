#!/usr/bin/env python3
"""
ROLLBACK — Undo false positive miscategorizations from fix_data_quality.py

The keyword matching was too aggressive:
- "pump" matched "pumpa" (pumpkin seeds) — NOT tools!
- "slang" matched "slanggurka" (cucumber variety) — NOT tools!
- "sax" matched "Saxa" (bean/radish variety) — NOT tools!  
- "jord" matched "jordgubbe" (strawberry) — NOT tools!
- "gödsel" matched "Luktärtsgödsel" and "Lökgödsel" — these ARE tools, keep as-is
- "kruka" matched "Svartkål I Nedbrytbar Kruka" — edge case, revert

This script restores the correct categories.
"""

import os, requests
from pathlib import Path

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_KEY")
HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# Products that were CORRECTLY moved (keep these as tools):
# 98072 - Fönsteröppnare (window opener) → tool ✓
# 92959 - Luktärtsgödsel (fertilizer) → tool ✓
# 92535 - Zetas Lökgödsel (fertilizer) → tool ✓
# 97898 - Växtnäring Nelson Garden Pumpflaska 500Ml (plant nutrition pump bottle) → tool ✓

KEEP_AS_TOOL = {98072, 92959, 92535, 97898}

# All products that need to be restored to their CORRECT seed categories
RESTORE = {
    # Slanggurka (cucumber varieties) → back to subcategory 3 (Gurka & Melon)
    3: [92033, 95132, 91129, 91121, 97078, 91123, 91122, 93022, 94614, 94616, 97076, 97077],
    
    # Pumpa products → back to subcategory 7 (Pumpa & Squash)
    7: [
        94546, 91196, 91195, 91198, 91200, 97597, 93079, 93082, 93434, 94061,
        93435, 96856, 93073, 93095, 97600, 97601, 96933, 97500, 94604, 95197,
        95199, 95198, 91993, 95203, 95200, 96930, 96929, 91217, 91199, 91201,
        91202, 91216, 91214, 91887, 94252, 91968, 97604, 91197, 93078, 93075,
        93081, 93074, 93076, 93080, 93083, 93096, 93097, 93098, 93436, 93617,
        94609, 94605, 94122, 94094, 94496, 94535, 94607, 94603, 94606, 94966,
        95029, 96927, 95201, 95195, 95204, 95196, 95202, 96934, 96931, 96928,
        95194, 97598, 97599, 97605, 97388, 91218, 94608, 94495, 96854, 93616,
        96932,
    ],
    
    # Bönor with "Saxa" / "Brytböna Saxa" → back to subcategory 5 (Bönor & Ärter)
    5: [94586, 94587, 97617],
    
    # Rotfrukter / Jordgubbar with "saxa"/"jord" → back to subcategory 6 (Rotfrukter)
    6: [
        91961, 97750, 97746, 91248, 95215, 95216, 91973, 93117, 93717, 94172,
        97749, 97755, 98450,
    ],
    
    # Aubergine "Pumpkin On A Stick" → back to subcategory 9 (Aubergin)
    9: [93333, 95211],
    
    # Kål "Svartkål I Nedbrytbar Kruka" → back to subcategory 8 (Kål & Broccoli)
    8: [98838],
    
    # Ettåriga blommor "Växtnäring" false positive → this one is actually a tool, skip
    # 97898 is kept as tool
    
    # Lökväxter → back to subcategory 10
    # 92535 Lökgödsel is actually a tool, keep it
    
    # Ettåriga blommor → back to subcategory 13
    # 97898 is kept as tool
    
    # Körsbärstomater → back to subcategory 26
    26: [94242],
}

print("PLANTPRISET — ROLLBACK FALSE POSITIVES")
print("=" * 60)

total_fixed = 0
total_errors = 0

for subcategory_id, product_ids in RESTORE.items():
    print(f"\nRestoring {len(product_ids)} products to subcategory {subcategory_id}...")
    
    for pid in product_ids:
        if pid in KEEP_AS_TOOL:
            print(f"  SKIP [{pid}]: Correctly categorized as tool")
            continue
            
        r = requests.patch(
            f"{URL}/rest/v1/products?id=eq.{pid}",
            headers=HEADERS,
            json={"subcategory_id": subcategory_id, "product_type": "seed"},
        )
        if r.status_code < 300:
            total_fixed += 1
        else:
            total_errors += 1
            print(f"  ERROR [{pid}]: {r.status_code} {r.text}")

print(f"\n{'=' * 60}")
print(f"ROLLBACK COMPLETE")
print(f"  Restored: {total_fixed}")
print(f"  Errors: {total_errors}")
print(f"  Kept as tool: {len(KEEP_AS_TOOL)}")
print(f"{'=' * 60}")

# Verify
print("\nVerifying pumpa count in subcategory 7...")
r = requests.head(
    f"{URL}/rest/v1/products?subcategory_id=eq.7&select=id&limit=1",
    headers={
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Prefer": "count=exact",
        "Range": "0-0",
    },
)
count = r.headers.get("content-range", "?/?").split("/")[-1]
print(f"  Pumpa & Squash products: {count}")

print("\nVerifying slanggurka in subcategory 3...")
r = requests.head(
    f"{URL}/rest/v1/products?subcategory_id=eq.3&select=id&limit=1",
    headers={
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Prefer": "count=exact",
        "Range": "0-0",
    },
)
count = r.headers.get("content-range", "?/?").split("/")[-1]
print(f"  Gurka & Melon products: {count}")
