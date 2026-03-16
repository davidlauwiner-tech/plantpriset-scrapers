import requests
from bs4 import BeautifulSoup
import re

resp = requests.get("https://www.blomsterlandet.se/produkter/vaxter/froer/gronsaksfroer/", headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Check for links wrapping the cards
cards = soup.select(".wrapper-big-card")
print(f"Cards: {len(cards)}")
card = cards[0]

# Check parent for link
parent = card.parent
print(f"Parent tag: <{parent.name}> class={parent.get('class')}")
if parent.name == "a":
    print(f"  href: {parent.get('href')}")

# Check for links inside or around
links = card.find_parents("a")
if links:
    print(f"Wrapping <a>: {links[0].get('href')}")

# Look for links near the card
prev = card.find_previous("a")
if prev:
    print(f"Previous <a>: {prev.get('href','')[:80]}")

# Let's look at a wider context — get the full card container
container = card.parent
print(f"\nContainer HTML (first 500):")
print(str(container)[:500])

# Also check how many total products the page claims to have
page_text = soup.get_text()
count_match = re.search(r'(\d+)\s*(produkter|resultat|träffar|artiklar)', page_text)
if count_match:
    print(f"\nProduct count text: {count_match.group()}")

# Check for category links we should scrape
print("\n=== Category links under /froer/ ===")
for a in soup.select("a[href*='/froer/']"):
    href = a.get("href","")
    text = a.get_text(strip=True)
    if text and "/froer/" in href and len(text) < 40:
        print(f"  {text:30s} → {href}")
