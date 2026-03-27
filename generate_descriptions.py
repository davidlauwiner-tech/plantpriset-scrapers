#!/usr/bin/env python3
"""Generate Swedish product descriptions using Claude API."""
import os, json, time, requests
from pathlib import Path

for line in Path('.env').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())

SB = os.environ['SUPABASE_URL']
SB_KEY = os.environ['SUPABASE_SERVICE_KEY']
CLAUDE_KEY = os.environ['ANTHROPIC_API_KEY']

def sb_get(params):
    r = requests.get(f"{SB}/rest/v1/products?{params}",
        headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}"})
    return r.json() if r.ok else []

def sb_update(product_id, data):
    r = requests.patch(f"{SB}/rest/v1/products?id=eq.{product_id}",
        headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"},
        json=data)
    return r.ok

def generate_description(product):
    name = product["name"]
    latin = product.get("latin_name") or ""
    ptype = product.get("product_type", "seed")
    
    type_label = {"seed": "frö/fröpåse", "plant": "växt/planta", "bulb": "lök/knöl", "tool": "trädgårdstillbehör"}.get(ptype, "produkt")
    
    prompt = f"""Skriv en kort, informativ produktbeskrivning på svenska för en trädgårdsprodukt som säljs i svenska trädgårdsbutiker.

Produkt: {name}
{f'Latinskt namn: {latin}' if latin else ''}
Typ: {type_label}

Skriv 2-3 meningar. Inkludera:
- Vad produkten är och hur den ser ut/smakar (om frö/växt)
- Odlingstips eller användning
- Vem den passar (nybörjare/erfaren, balkong/trädgård)

Skriv BARA beskrivningen, ingen rubrik, inga bullet points. Håll det naturligt och hjälpsamt, som en kunnig trädgårdsvän som ger råd."""

    r = requests.post("https://api.anthropic.com/v1/messages", 
        headers={
            "x-api-key": CLAUDE_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30
    )
    
    if r.status_code != 200:
        print(f"  API error {r.status_code}: {r.text[:100]}")
        return None
    
    data = r.json()
    text = data["content"][0]["text"].strip()
    return text

def main():
    # Get products without descriptions, prioritize multi-retailer ones
    print("Fetching products without descriptions...")
    products = sb_get("description=is.null&select=id,name,latin_name,product_type&order=name&limit=500")
    
    print(f"Found {len(products)} products without descriptions")
    print("Generating descriptions with Claude...\n")
    
    generated = 0
    errors = 0
    
    for i, p in enumerate(products, 1):
        print(f"  [{i}/{len(products)}] {p['name'][:50]}...", end=" ")
        
        desc = generate_description(p)
        if desc:
            sb_update(p["id"], {"description": desc})
            print(f"OK ({len(desc)} chars)")
            generated += 1
        else:
            print("FAILED")
            errors += 1
        
        # Rate limit: ~50 requests/minute for Sonnet
        time.sleep(0.5)
    
    print(f"\n{'='*50}")
    print(f"Generated: {generated}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    main()
