import os, re, time, requests
from datetime import datetime
from supabase import create_client

class BaseScraper:
    retailer_slug = ""
    retailer_name = ""
    retailer_url = ""

    def __init__(self):
        self.api_url = os.environ.get("API_URL", "https://web-production-cc863.up.railway.app")
        self.supabase = create_client(os.environ.get("SUPABASE_URL",""), os.environ.get("SUPABASE_KEY",""))
        self.retailer_id = self._get_or_create_retailer()

    def _get_or_create_retailer(self):
        r = self.supabase.table("retailers").select("id").eq("slug", self.retailer_slug).execute()
        if r.data: return r.data[0]["id"]
        return self.supabase.table("retailers").insert({"slug":self.retailer_slug,"name":self.retailer_name,"url":self.retailer_url,"is_active":True,"data_source":"scraper"}).execute().data[0]["id"]

    def get_all_plants(self):
        plants, page = [], 1
        while True:
            r = requests.get(f"{self.api_url}/plants", params={"limit":100,"page":page}).json()
            batch = r.get("plants", [])
            if not batch: break
            plants.extend(batch)
            if len(plants) >= r.get("total", 0): break
            page += 1
        print(f"Fetched {len(plants)} plants")
        return plants

    def parse_price(self, s):
        if not s: return None
        m = re.search(r"(\d+[,.]?\d*)", s.replace("\xa0","").replace(" ",""))
        return float(m.group(1).replace(",",".")) if m else None

    def upsert_listing(self, plant_id, product):
        try:
            ex = self.supabase.table("listings").select("id").eq("plant_id",plant_id).eq("retailer_id",self.retailer_id).eq("product_url",product["url"]).execute()
            data = {"plant_id":plant_id,"retailer_id":self.retailer_id,"price_sek":product["price"],"product_url":product["url"],"in_stock":product.get("in_stock",True),"unit_type":product.get("unit_type","st"),"quantity":product.get("quantity",1),"last_updated":datetime.utcnow().isoformat()}
            if ex.data: self.supabase.table("listings").update(data).eq("id",ex.data[0]["id"]).execute()
            else: self.supabase.table("listings").insert(data).execute()
            print(f"    ✓ {product.get('name','?')} — {product['price']} kr")
        except Exception as e:
            print(f"    ✗ {e}")

    def search(self, plant): raise NotImplementedError

    def run(self):
        print(f"=== {self.retailer_name} Scraper ===")
        plants = self.get_all_plants()
        for i, plant in enumerate(plants):
            print(f"\n[{i+1}/{len(plants)}] {plant.get('common_name_sv') or plant.get('slug')}")
            try:
                products = self.search(plant)
                if products:
                    for p in sorted(products, key=lambda x: x.get("price") or 9999)[:3]:
                        self.upsert_listing(plant["id"], p)
                else: print("  No results")
            except Exception as e: print(f"  Error: {e}")
            time.sleep(2)
