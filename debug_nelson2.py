import requests
import xml.etree.ElementTree as ET

resp = requests.get("https://www.nelsongarden.se/sitemap.xml", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
root = ET.fromstring(resp.text)
ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

urls = [url.find("s:loc", ns).text for url in root.findall("s:url", ns)]
print(f"Total URLs in sitemap: {len(urls)}")

# Find product URLs
product_urls = [u for u in urls if "/produkter/" in u or "/p/" in u or "/p" in u.split("/")[-1]]
print(f"Product URLs (/produkter/ or /p/): {len(product_urls)}")

# Show samples
print("\nFirst 20 product URLs:")
for u in product_urls[:20]:
    print(f"  {u}")

# Show URL patterns
from collections import Counter
patterns = Counter()
for u in urls:
    parts = u.replace("https://www.nelsongarden.se/", "").split("/")
    if parts[0]:
        patterns[parts[0]] += 1

print("\nURL patterns:")
for pattern, count in patterns.most_common(20):
    print(f"  {count:4d}  /{pattern}/...")
