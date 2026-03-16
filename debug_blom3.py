import requests
from bs4 import BeautifulSoup

resp = requests.get("https://www.blomsterlandet.se/produkter/vaxter/froer/gronsaksfroer/", headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}, timeout=15)

soup = BeautifulSoup(resp.text, "html.parser")

# The cards are wrapper-big-card — let's look at one
cards = soup.select(".wrapper-big-card")
print(f"Found {len(cards)} product cards\n")

if cards:
    print("=== First card HTML ===")
    print(cards[0].prettify()[:3000])
    
    print("\n=== All elements with classes in first card ===")
    for el in cards[0].select("[class]"):
        classes = el.get("class", [])
        text = el.get_text(strip=True)[:80]
        if text:
            print(f"  <{el.name}> {' '.join(classes)[:60]:60s} → {text}")
