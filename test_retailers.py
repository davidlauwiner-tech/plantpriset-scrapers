import requests
import re

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

retailers = [
    ("Wexthuset", "https://www.wexthuset.com/froer-lokar/froer"),
    ("Plantagen", "https://plantagen.se/se/vaxter/froer"),
    ("Granngården", "https://www.granngarden.se/tradgard/fro-odling"),
    ("Cramers", "https://shop.cramersblommor.com/froer/"),
    ("Simbadusa", "https://www.simbadusa.se/sv/articles/20/froer"),
    ("Lindbloms", "https://www.lindbloms.se/"),
    ("Klostra", "https://www.klostra.se/froer"),
    ("Zetas", "https://zetas.se/"),
    ("Runåbergs", "https://www.runabergs.se/"),
    ("Örtagården", "https://www.ortagarden.se/"),
]

for name, url in retailers:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        prices = re.findall(r'(\d+)[.,]?\d*\s*kr', resp.text)
        has_prices = len(prices) > 3
        size = len(resp.text)
        print(f"{'✅' if has_prices else '❌'} {name:15s} HTTP {resp.status_code} {size:>8} bytes  prices={len(prices):>3}")
    except Exception as e:
        print(f"❌ {name:15s} ERROR: {e}")
