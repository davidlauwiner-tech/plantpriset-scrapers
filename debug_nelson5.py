import requests
import json
from bs4 import BeautifulSoup

resp = requests.get("https://www.nelsongarden.se/produkter/solros-p88358/", headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
})
soup = BeautifulSoup(resp.text, "html.parser")

for script in soup.find_all("script"):
    text = script.string or ""
    if "salePriceInclTax" in text:
        # It's escaped JSON inside a script tag — unescape it
        clean = text.replace('\\"', '"').replace("\\'", "'")
        # Find the JSON start
        start = clean.find('{"apiRoute"')
        if start < 0:
            start = clean.find('{')
        # Try to parse it
        try:
            data = json.loads(clean[start:])
        except:
            # Might be wrapped — try extracting between first { and last }
            end = clean.rfind('}') + 1
            try:
                data = json.loads(clean[start:end])
            except:
                print("Could not parse JSON, showing raw keys with 'price' or 'Price':")
                import re
                for m in re.finditer(r'"(\w*[Pp]rice\w*)"[:\s]*([^,}]{1,50})', clean):
                    print(f"  {m.group(1)}: {m.group(2)}")
                for m in re.finditer(r'"(name|displayName|brand)"[:\s]*"([^"]{1,80})"', clean):
                    print(f"  {m.group(1)}: {m.group(2)}")
                exit()
        
        # If we parsed it, show the interesting fields
        props = data.get("properties", {})
        print("=== Product Data ===")
        print(f"  name: {data.get('pageHeading') or props.get('displayName')}")
        print(f"  brand: {props.get('brand')}")
        print(f"  description: {props.get('description','')[:100]}")
        
        # Look for price/variation data
        print(f"\n=== All keys with 'price' (case-insensitive) ===")
        def find_prices(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if "price" in k.lower() or "stock" in k.lower() or "sku" in k.lower():
                        print(f"  {path}.{k} = {v}")
                    find_prices(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj[:3]):
                    find_prices(item, f"{path}[{i}]")
        find_prices(data)
        break
