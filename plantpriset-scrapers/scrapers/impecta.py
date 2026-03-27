"""Impecta Fröhandel scraper — requests + BS4, with pagination."""
import time
from datetime import datetime
from .base import BaseScraper

CATEGORY_URLS = [
    "/sv/froer/gronsaker/bladgronsaker/sallat", "/sv/froer/gronsaker/bladgronsaker/spenat",
    "/sv/froer/gronsaker/bladgronsaker/persilja", "/sv/froer/gronsaker/bladgronsaker/dill",
    "/sv/froer/gronsaker/bladgronsaker/rucola-2", "/sv/froer/gronsaker/bladgronsaker/mangold",
    "/sv/froer/gronsaker/bladgronsaker/ovriga-bladgronsaker",
    "/sv/froer/gronsaker/tomat/korsbar", "/sv/froer/gronsaker/tomat/biff",
    "/sv/froer/gronsaker/tomat/friland", "/sv/froer/gronsaker/tomat/plommon",
    "/sv/froer/gronsaker/tomat/vaxthus", "/sv/froer/gronsaker/tomat/kruka_ampel",
    "/sv/froer/gronsaker/tomat/speciella",
    "/sv/froer/gronsaker/rotfrukter/morot", "/sv/froer/gronsaker/rotfrukter/rodbeta",
    "/sv/froer/gronsaker/rotfrukter/radisa", "/sv/froer/gronsaker/rotfrukter/palsternacka",
    "/sv/froer/gronsaker/rotfrukter/kalrot", "/sv/froer/gronsaker/rotfrukter/ovriga-rotfrukter",
    "/sv/froer/gronsaker/chilipeppar-och-paprika/chilipeppar",
    "/sv/froer/gronsaker/chilipeppar-och-paprika/paprika",
    "/sv/froer/gronsaker/gurka-och-melon/gurka", "/sv/froer/gronsaker/gurka-och-melon/melon",
    "/sv/froer/gronsaker/bonor-och-arter/bonor", "/sv/froer/gronsaker/bonor-och-arter/arter",
    "/sv/froer/gronsaker/kal-och-broccoli/broccoli", "/sv/froer/gronsaker/kal-och-broccoli/gronkal",
    "/sv/froer/gronsaker/kal-och-broccoli/blomkal", "/sv/froer/gronsaker/kal-och-broccoli/kalrabbi",
    "/sv/froer/gronsaker/lokvaxter/graslok", "/sv/froer/gronsaker/lokvaxter/purjolok",
    "/sv/froer/gronsaker/lokvaxter/salladslok",
    "/sv/froer/gronsaker/majs", "/sv/froer/gronsaker/pumpa-och-squash/squash",
    "/sv/froer/gronsaker/pumpa-och-squash/myskpumpa", "/sv/froer/gronsaker/pumpa-och-squash/pajpumpa",
    "/sv/froer/gronsaker/selleri", "/sv/froer/gronsaker/aubergin", "/sv/froer/gronsaker/fankal",
    "/sv/froer/gronsaker/asiatiska-gronsaksvaxter", "/sv/froer/gronsaker/ovriga-gronsaksvaxter",
    "/sv/froer/gronsaker/ekologiska-gronsaker",
    "/sv/froer/kryddvaxt/basilika", "/sv/froer/kryddvaxt/dill-2", "/sv/froer/kryddvaxt/koriander",
    "/sv/froer/kryddvaxt/oregano", "/sv/froer/kryddvaxt/persilja-2", "/sv/froer/kryddvaxt/rosmarin",
    "/sv/froer/kryddvaxt/timjan", "/sv/froer/kryddvaxt/mynta", "/sv/froer/kryddvaxt/ovriga-kryddvaxter",
    "/sv/froer/perenner/flerariga-rabattvaxter", "/sv/froer/perenner/doftande-perenner",
    "/sv/froer/perenner/marktackande-perenner", "/sv/froer/perenner/flerariga-bladvaxter",
    "/sv/froer/perenner/flerariga-klattervaxter", "/sv/froer/perenner/flerariga-prydnadsgras",
    "/sv/froer/perenner/dammkantsvaxter", "/sv/froer/perenner/flerariga-skuggvaxter",
    "/sv/froer/ettariga-blommor/ettariga-rabattblommor", "/sv/froer/ettariga-blommor/ettariga-snittblommor",
    "/sv/froer/ettariga-blommor/ettariga-snittblommor/solros",
    "/sv/froer/ettariga-blommor/hangande-blommor", "/sv/froer/ettariga-blommor/sommarblomsblandningar",
    "/sv/froer/ettariga-blommor/rosenskara-och-zinnia/rosenskara",
    "/sv/froer/ettariga-blommor/rosenskara-och-zinnia/zinnia",
    "/sv/froer/ettariga-blommor/blaklint",
    "/sv/froer/ettariga-blommor/ettariga-klattervaxter/krasse",
    "/sv/froer/ettariga-blommor/ettariga-klattervaxter/luktarter-en-sommarromans",
    "/sv/froer/ettariga-blommor/doftande-ettariga-blommor",
    "/sv/froer/ettariga-blommor/ekologiska-blommor",
    "/sv/froer/nordiska-vildblommor", "/sv/froer/dragvaxter",
    "/sv/froer/nyttovaxter/grongodslingsvaxter", "/sv/froer/medicinalvaxt",
    "/sv/froer/buskar-och-trad/blommande",
    "/sv/froer/ekologiska-froer",
    "/sv/tillbehor/belysning", "/sv/tillbehor/bevattning", "/sv/tillbehor/krukor",
    "/sv/tillbehor/redskap", "/sv/tillbehor/naringstillskott", "/sv/tillbehor/sadd-plantering",
    "/sv/tillbehor/vaxtskydd", "/sv/tillbehor/markning", "/sv/tillbehor/brickor-trag",
    "/sv/tillbehor/drivhus", "/sv/tillbehor/uppbindning",
]


class ImpectaScraper(BaseScraper):
    retailer_slug = "impecta"
    base_url = "https://www.impecta.se"

    def extract_product(self, card, cat_url):
        p = {"retailer": self.retailer_slug, "category_url": cat_url}
        art_id = card.get("data-id")
        if art_id:
            p["article_number"] = art_id
        name_el = card.select_one(".PT_Beskr")
        if name_el:
            p["name"] = name_el.get_text(strip=True)
        link = card.select_one("a.box")
        if link:
            href = link.get("href", "")
            if href:
                p["product_url"] = f"{self.base_url}{href}" if not href.startswith("http") else href
        price_el = card.select_one(".PT_PrisNormal")
        if price_el:
            p["price_sek"] = self.parse_price(price_el.get_text())
        camp_el = card.select_one(".PT_PrisKampanj")
        if camp_el:
            cp = self.parse_price(camp_el.get_text())
            if cp:
                p["price_campaign_sek"] = cp
                p["price_sek"] = cp
        ord_el = card.select_one(".PT_PrisOrdinarie, .PrisORD, .ordPrice")
        if ord_el:
            p["price_original_sek"] = self.parse_price(ord_el.get_text())
        img = card.select_one(".PT_Bild img")
        if img:
            src = img.get("src", "")
            if src:
                p["image_url"] = f"{self.base_url}{src}" if not src.startswith("http") else src
        props = []
        if card.select_one(".pv1"): props.append("ekologisk")
        if card.select_one(".pv2"): props.append("kulturarv")
        p["properties"] = props
        btn = card.select_one(".buy-button")
        if btn:
            classes = " ".join(btn.get("class", []))
            p["in_stock"] = "sid_1" in classes
        p["scraped_at"] = datetime.utcnow().isoformat()
        return p

    def scrape_category(self, cat_url):
        products = []
        page_num = 1
        while True:
            url = f"{self.base_url}{cat_url}"
            if page_num > 1:
                url += f"?page={page_num}"
            try:
                soup, _ = self.get_page(url)
                cards = soup.select(".PT_Wrapper")
                if not cards:
                    break
                for card in cards:
                    prod = self.extract_product(card, cat_url)
                    if prod.get("name") and prod.get("price_sek"):
                        products.append(prod)
                next_link = soup.select_one(f'a[href*="page={page_num + 1}"]')
                if next_link:
                    page_num += 1
                    time.sleep(self.delay)
                else:
                    break
            except Exception as e:
                print(f"    ERROR page {page_num}: {e}")
                break
        return products, page_num

    def scrape(self):
        all_products = []
        for i, cat in enumerate(CATEGORY_URLS, 1):
            products, pages = self.scrape_category(cat)
            pg = f" ({pages}p)" if pages > 1 else ""
            print(f"  [{i}/{len(CATEGORY_URLS)}] {cat} → {len(products)}{pg}")
            all_products.extend(products)
            time.sleep(self.delay)
        return all_products
