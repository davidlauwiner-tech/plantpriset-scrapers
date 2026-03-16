import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# SIMBADUSA - check structure
print("=== SIMBADUSA ===")
resp = requests.get("https://www.simbadusa.se/sv/articles/20/froer", headers=HEADERS, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")
print(f"Page size: {len(resp.text)} bytes")

# Count elements that contain "kr"
import re
kr_elements = soup.find_all(string=re.compile(r'\d+\s*kr'))
print(f"Elements with 'kr': {len(kr_elements)}")

# Check what contains prices
if kr_elements:
    el = kr_elements[5] if len(kr_elements) > 5 else kr_elements[0]
    parent = el.parent
    gp = parent.parent
    ggp = gp.parent if gp else None
    gggp = ggp.parent if ggp else None
    print(f"  Price text: '{el.strip()[:40]}'")
    print(f"  parent: <{parent.name}> class={parent.get('class')}")
    if gp: print(f"  grandparent: <{gp.name}> class={gp.get('class')}")
    if ggp: print(f"  ggparent: <{ggp.name}> class={ggp.get('class')}")
    if gggp: print(f"  gggparent: <{gggp.name}> class={gggp.get('class')}")

# KLOSTRA
print("\n=== KLOSTRA ===")
resp = requests.get("https://www.klostra.se/froer", headers=HEADERS, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")
print(f"Page size: {len(resp.text)} bytes")

kr_elements = soup.find_all(string=re.compile(r'\d+\s*kr'))
print(f"Elements with 'kr': {len(kr_elements)}")
for sel in [".product", "[class*='product']", "[class*='Product']", "article", ".item", "[class*='card']", ".grid-item"]:
    els = soup.select(sel)
    if els and len(els) > 3:
        print(f"Selector '{sel}': {len(els)}")

# LINDBLOMS
print("\n=== LINDBLOMS ===")
resp = requests.get("https://www.lindbloms.se/produkter/", headers=HEADERS, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")
print(f"HTTP {resp.status_code} Page size: {len(resp.text)} bytes")

kr_elements = soup.find_all(string=re.compile(r'\d+\s*kr'))
print(f"Elements with 'kr': {len(kr_elements)}")
for sel in [".product", "[class*='product']", "[class*='Product']", "article", ".item", "[class*='card']"]:
    els = soup.select(sel)
    if els and len(els) > 3:
        print(f"Selector '{sel}': {len(els)}")
