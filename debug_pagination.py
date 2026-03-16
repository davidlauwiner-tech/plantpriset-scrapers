import requests
from bs4 import BeautifulSoup

resp = requests.get("https://www.impecta.se/sv/froer/perenner/flerariga-rabattvaxter", headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
})
soup = BeautifulSoup(resp.text, "html.parser")

# Look for pagination links
print("=== Links containing 'sida' or 'page' ===")
for a in soup.select("a[href]"):
    href = a.get("href", "")
    if "sida" in href.lower() or "page" in href.lower() or "Nästa" in a.get_text():
        print(f"  href={href}  text={a.get_text(strip=True)}")

print("\n=== Text containing 'Artikel' or 'av' (item count) ===")
for el in soup.find_all(string=lambda t: t and ("Artikel" in t or " av " in t)):
    print(f"  {el.strip()[:100]}")

print("\n=== Any element with 'paginat' or 'Nästa' or 'next' ===")
for el in soup.select("[class*='paginat'], [class*='next'], [class*='Nasta']"):
    print(f"  <{el.name}> class={el.get('class')} text={el.get_text(strip=True)[:60]}")

# Also check for numbered page links like 1 2 3 4
for a in soup.select("a"):
    text = a.get_text(strip=True)
    href = a.get("href","")
    if text in ["2","3","4","5","»","Nästa"] and href:
        print(f"  PAGE LINK: text='{text}' href={href}")
