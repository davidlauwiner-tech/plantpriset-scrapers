import requests
import json
import re
from bs4 import BeautifulSoup

resp = requests.get("https://www.blomsterlandet.se/produkter/vaxter/froer/gronsaksfroer/", headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}, timeout=15)

soup = BeautifulSoup(resp.text, "html.parser")

for script in soup.find_all("script"):
    text = script.string or ""
    if "window.__PRELOADED_STATE__" in text:
        # Extract the JSON string
        match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*"(.+?)"\s*;', text, re.DOTALL)
        if match:
            # It's unicode-escaped
            raw = match.group(1)
            decoded = raw.encode().decode('unicode_escape')
            data = json.loads(decoded)
            
            # Find product data
            print(f"Top-level keys: {list(data.keys())}")
            
            # Look for products
            def find_products(obj, path="", depth=0):
                if depth > 4: return
                if isinstance(obj, dict):
                    # Check if this looks like a product
                    if "price" in str(obj.keys()).lower() or "productName" in str(obj.keys()):
                        print(f"\n  PRODUCT at {path}:")
                        for k, v in obj.items():
                            if not isinstance(v, (dict, list)):
                                print(f"    {k}: {v}")
                            elif isinstance(v, dict) and len(v) < 5:
                                print(f"    {k}: {v}")
                        return
                    for k, v in obj.items():
                        find_products(v, f"{path}.{k}", depth+1)
                elif isinstance(obj, list) and len(obj) > 0:
                    find_products(obj[0], f"{path}[0]", depth+1)
                    print(f"  ({len(obj)} items in {path})")
            
            find_products(data)
            break
