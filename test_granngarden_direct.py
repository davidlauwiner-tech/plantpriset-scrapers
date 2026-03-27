import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
})

# First visit the site to get cookies + verification token
resp = session.get("https://www.granngarden.se/sok?q=tomat", timeout=15)
print(f"Page: HTTP {resp.status_code} ({len(resp.text)} bytes)")

# Check for verification token in cookies or HTML
import re
token_match = re.search(r'__RequestVerificationToken["\s]*value="([^"]+)"', resp.text)
if token_match:
    print(f"Token found in HTML: {token_match.group(1)[:50]}...")

# Check cookies
for name, val in session.cookies.items():
    if "verif" in name.lower() or "token" in name.lower() or "csrf" in name.lower():
        print(f"Cookie: {name}={val[:50]}...")

# Try the price API directly  
price_resp = session.get("https://www.granngarden.se/api/price/bestprice?productNumbers=1265771,2001355", timeout=10)
print(f"\nPrice API: HTTP {price_resp.status_code}")
if price_resp.status_code == 200:
    import json
    data = price_resp.json()
    for p in data.get("prices", []):
        print(f"  {p.get('productNumber')}: {p.get('price')} kr ({p.get('formattedPrice')})")

# Try the search results page - does it have product data in HTML?
from bs4 import BeautifulSoup
soup = BeautifulSoup(resp.text, "html.parser")
cards = soup.select(".product-card")
print(f"\nProduct cards in HTML: {len(cards)}")
if cards:
    card = cards[0]
    name = card.select_one(".product-card__name")
    link = card.select_one("a")
    print(f"  Name: {name.get_text(strip=True) if name else '?'}")
    print(f"  Link: {link.get('href','?') if link else '?'}")
