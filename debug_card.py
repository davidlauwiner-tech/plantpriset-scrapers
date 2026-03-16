import requests
from bs4 import BeautifulSoup

resp = requests.get("https://www.impecta.se/sv/froer/kryddvaxt/timjan", headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
})
soup = BeautifulSoup(resp.text, "html.parser")
cards = soup.select(".PT_Wrapper")
print(f"Found {len(cards)} cards\n")
if cards:
    card = cards[0]
    print("=== RAW HTML of first card ===")
    print(card.prettify()[:3000])
    print("\n=== All classes in card ===")
    for el in card.select("[class]"):
        print(f"  <{el.name}> classes={el.get('class')}")
        text = el.get_text(strip=True)[:80]
        if text:
            print(f"    text: {text}")
