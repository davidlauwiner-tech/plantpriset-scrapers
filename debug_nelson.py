import requests

# Check if Nelson has a sitemap we can use
for url in [
    "https://www.nelsongarden.se/sitemap.xml",
    "https://www.nelsongarden.se/robots.txt",
]:
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        print(f"\n=== {url} === HTTP {resp.status_code}")
        print(resp.text[:2000])
    except Exception as e:
        print(f"\n=== {url} === ERROR: {e}")
