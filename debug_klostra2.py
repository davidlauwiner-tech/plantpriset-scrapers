import requests
from bs4 import BeautifulSoup

resp = requests.get("https://www.klostra.se/froer", headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")
cards = soup.select(".product")
print(f"Cards: {len(cards)}")
if cards:
    print(cards[0].prettify()[:2000])
