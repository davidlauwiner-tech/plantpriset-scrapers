import json
import re
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.impecta.se"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7",
}
CATEGORY_URLS = [
    "/sv/froer/gronsaker/bladgronsaker/sallat",
    "/sv/froer/gronsaker/bladgronsaker/spenat",
    "/sv/froer/gronsaker/bladgronsaker/persilja",
    "/sv/froer/gronsaker/bladgronsaker/dill",
    "/sv/froer/gronsaker/bladgronsaker/rucola-2",
    "/sv/froer/gronsaker/bladgronsaker/mangold",
    "/sv/froer/gronsaker/bladgronsaker/salladssenap",
    "/sv/froer/gronsaker/bladgronsaker/vintersallat",
    "/sv/froer/gronsaker/bladgronsaker/ovriga-bladgronsaker",
    "/sv/froer/gronsaker/tomat/korsbar",
    "/sv/froer/gronsaker/tomat/biff",
    "/sv/froer/gronsaker/tomat/friland",
    "/sv/froer/gronsaker/tomat/plommon",
    "/sv/froer/gronsaker/tomat/vaxthus",
    "/sv/froer/gronsaker/tomat/kruka_ampel",
    "/sv/froer/gronsaker/tomat/speciella",
    "/sv/froer/gronsaker/rotfrukter/morot",
    "/sv/froer/gronsaker/rotfrukter/rodbeta",
    "/sv/froer/gronsaker/rotfrukter/radisa",
    "/sv/froer/gronsaker/rotfrukter/palsternacka",
    "/sv/froer/gronsaker/rotfrukter/kalrot",
    "/sv/froer/gronsaker/rotfrukter/rattika",
    "/sv/froer/gronsaker/rotfrukter/majrova",
    "/sv/froer/gronsaker/rotfrukter/ovriga-rotfrukter",
    "/sv/froer/gronsaker/chilipeppar-och-paprika/chilipeppar",
    "/sv/froer/gronsaker/chilipeppar-och-paprika/paprika",
    "/sv/froer/gronsaker/gurka-och-melon/gurka",
    "/sv/froer/gronsaker/gurka-och-melon/melon",
    "/sv/froer/gronsaker/gurka-och-melon/vattenmelon",
    "/sv/froer/gronsaker/bonor-och-arter/bonor",
    "/sv/froer/gronsaker/bonor-och-arter/arter",
    "/sv/froer/gronsaker/kal-och-broccoli/broccoli",
    "/sv/froer/gronsaker/kal-och-broccoli/gronkal",
    "/sv/froer/gronsaker/kal-och-broccoli/blomkal",
    "/sv/froer/gronsaker/kal-och-broccoli/kalrabbi",
    "/sv/froer/gronsaker/kal-och-broccoli/rodkal",
    "/sv/froer/gronsaker/kal-och-broccoli/salladskal",
    "/sv/froer/gronsaker/kal-och-broccoli/spetskal",
    "/sv/froer/gronsaker/kal-och-broccoli/vitkal",
    "/sv/froer/gronsaker/kal-och-broccoli/ovriga-kalvaxter",
    "/sv/froer/gronsaker/lokvaxter/graslok",
    "/sv/froer/gronsaker/lokvaxter/purjolok",
    "/sv/froer/gronsaker/lokvaxter/salladslok",
    "/sv/froer/gronsaker/lokvaxter/gul-lok",
    "/sv/froer/gronsaker/lokvaxter/rod-lok",
    "/sv/froer/gronsaker/lokvaxter/ovriga-lokvaxter",
    "/sv/froer/gronsaker/majs",
    "/sv/froer/gronsaker/pumpa-och-squash/squash",
    "/sv/froer/gronsaker/pumpa-och-squash/myskpumpa",
    "/sv/froer/gronsaker/pumpa-och-squash/pajpumpa",
    "/sv/froer/gronsaker/pumpa-och-squash/vintersquash",
    "/sv/froer/gronsaker/pumpa-och-squash/ovriga-pumpa-och-squash",
    "/sv/froer/gronsaker/selleri",
    "/sv/froer/gronsaker/aubergin",
    "/sv/froer/gronsaker/fankal",
    "/sv/froer/gronsaker/rabarber",
    "/sv/froer/gronsaker/tomatillo",
    "/sv/froer/gronsaker/asiatiska-gronsaksvaxter",
    "/sv/froer/gronsaker/jordgubbar-och-smultron/jordgubbar",
    "/sv/froer/gronsaker/jordgubbar-och-smultron/smultron",
    "/sv/froer/gronsaker/ovriga-gronsaksvaxter",
    "/sv/froer/gronsaker/ekologiska-gronsaker",
    "/sv/froer/kryddvaxt/basilika",
    "/sv/froer/kryddvaxt/dill-2",
    "/sv/froer/kryddvaxt/koriander",
    "/sv/froer/kryddvaxt/oregano",
    "/sv/froer/kryddvaxt/persilja-2",
    "/sv/froer/kryddvaxt/rosmarin",
    "/sv/froer/kryddvaxt/timjan",
    "/sv/froer/kryddvaxt/mynta",
    "/sv/froer/kryddvaxt/anisisop",
    "/sv/froer/kryddvaxt/isop",
    "/sv/froer/kryddvaxt/kryddlok",
    "/sv/froer/kryddvaxt/kryddtagetes",
    "/sv/froer/kryddvaxt/smorgaskrasse",
    "/sv/froer/kryddvaxt/ovriga-kryddvaxter",
    "/sv/froer/perenner/flerariga-rabattvaxter",
    "/sv/froer/perenner/doftande-perenner",
    "/sv/froer/perenner/marktackande-perenner",
    "/sv/froer/perenner/flerariga-bladvaxter",
    "/sv/froer/perenner/flerariga-klattervaxter",
    "/sv/froer/perenner/flerariga-prydnadsgras",
    "/sv/froer/perenner/dammkantsvaxter",
    "/sv/froer/perenner/flerariga-skuggvaxter",
    "/sv/froer/ettariga-blommor/ettariga-rabattblommor",
    "/sv/froer/ettariga-blommor/ettariga-snittblommor",
    "/sv/froer/ettariga-blommor/ettariga-snittblommor/solros",
    "/sv/froer/ettariga-blommor/hangande-blommor",
    "/sv/froer/ettariga-blommor/sommarblomsblandningar",
    "/sv/froer/ettariga-blommor/rosenskara-och-zinnia/rosenskara",
    "/sv/froer/ettariga-blommor/rosenskara-och-zinnia/zinnia",
    "/sv/froer/ettariga-blommor/blaklint",
    "/sv/froer/ettariga-blommor/ettariga-klattervaxter/krasse",
    "/sv/froer/ettariga-blommor/ettariga-klattervaxter/luktarter-en-sommarromans",
    "/sv/froer/ettariga-blommor/doftande-ettariga-blommor",
    "/sv/froer/ettariga-blommor/krukvaxter-utomhus",
    "/sv/froer/ettariga-blommor/ettariga-bladvaxter",
    "/sv/froer/ettariga-blommor/ettariga-prydnadsgras",
    "/sv/froer/ettariga-blommor/ettariga-marktackare",
    "/sv/froer/ettariga-blommor/ekologiska-blommor",
    "/sv/froer/ettariga-blommor/atbara-ettariga-blommor",
    "/sv/froer/nordiska-vildblommor",
    "/sv/froer/dragvaxter",
    "/sv/froer/nyttovaxter/grongodslingsvaxter",
    "/sv/froer/nyttovaxter/farg-och-spanadsvaxter",
    "/sv/froer/nyttovaxter/historiska-nyttovaxter",
    "/sv/froer/medicinalvaxt",
    "/sv/froer/buskar-och-trad/barrvaxter",
    "/sv/froer/buskar-och-trad/blommande",
    "/sv/froer/buskar-och-trad/surjordsvaxter",
    "/sv/froer/buskar-och-trad/vedartade-klattervaxter",
    "/sv/froer/krukvaxter/grona-krukvaxter",
    "/sv/froer/krukvaxter/blommande-krukvaxter",
    "/sv/froer/krukvaxter/kaktusar-och-suckulenter",
    "/sv/froer/krukvaxter/klattrande-krukvaxter",
    "/sv/froer/eterneller/blommor",
    "/sv/froer/eterneller/frukter",
    "/sv/froer/eterneller/frokapslar",
    "/sv/froer/eterneller/gras",
    "/sv/tillbehor/belysning",
    "/sv/tillbehor/belysning/drivbank-inomhus",
    "/sv/tillbehor/belysning/led-ramper",
    "/sv/tillbehor/belysning/odlingsvagn",
    "/sv/tillbehor/belysning/vaxtlampor-och-armaturer",
    "/sv/tillbehor/bevattning",
    "/sv/tillbehor/bevattning/vattenkannor",
    "/sv/tillbehor/hydroponisk-odling",
    "/sv/tillbehor/krukor",
    "/sv/tillbehor/redskap",
    "/sv/tillbehor/redskap/ograsredskap",
    "/sv/tillbehor/naringstillskott",
    "/sv/tillbehor/sadd-plantering",
    "/sv/tillbehor/vaxtskydd",
    "/sv/tillbehor/markning",
    "/sv/tillbehor/brickor-trag",
    "/sv/tillbehor/drivhus",
    "/sv/tillbehor/uppbindning",
    "/sv/tillbehor/matredskap",
    "/sv/tillbehor/kompost",
]

def parse_price(text):
    if not text: return None
    cleaned = re.sub(r'[^\d.,]', '', text.strip()).replace(",", ".")
    try: return float(cleaned)
    except: return None

def extract_product(card, cat_url):
    p = {"retailer": "impecta", "category_url": cat_url}
    art_id = card.get("data-id")
    if art_id: p["article_number"] = art_id
    name_el = card.select_one(".PT_Beskr")
    if name_el: p["name"] = name_el.get_text(strip=True)
    link = card.select_one("a.box")
    if link:
        href = link.get("href", "")
        if href: p["product_url"] = f"{BASE_URL}{href}" if not href.startswith("http") else href
    price_el = card.select_one(".PT_PrisNormal")
    if price_el: p["price_sek"] = parse_price(price_el.get_text())
    camp_el = card.select_one(".PT_PrisKampanj")
    if camp_el:
        p["price_campaign_sek"] = parse_price(camp_el.get_text())
        if p.get("price_campaign_sek"): p["price_sek"] = p["price_campaign_sek"]
    ord_el = card.select_one(".PT_PrisOrdinarie, .PrisORD, .ordPrice")
    if ord_el: p["price_original_sek"] = parse_price(ord_el.get_text())
    img = card.select_one(".PT_Bild img")
    if img:
        src = img.get("src", "")
        if src: p["image_url"] = f"{BASE_URL}{src}" if not src.startswith("http") else src
    props = []
    if card.select_one(".pv1"): props.append("ekologisk")
    if card.select_one(".pv2"): props.append("kulturarv")
    icon_new = card.select_one(".icon.new")
    if icon_new and icon_new.get_text(strip=True): props.append("nyhet")
    icon_offer = card.select_one(".icon.offer")
    if icon_offer and icon_offer.get_text(strip=True): props.append("erbjudande")
    p["properties"] = props
    btn = card.select_one(".buy-button")
    if btn:
        classes = " ".join(btn.get("class", []))
        p["in_stock"] = "sid_1" in classes
    p["scraped_at"] = datetime.utcnow().isoformat()
    return p

def scrape_category(session, cat_url):
    """Scrape all pages of a category."""
    products = []
    page_num = 1
    while True:
        url = f"{BASE_URL}{cat_url}"
        if page_num > 1:
            url += f"?page={page_num}"
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(".PT_Wrapper")
            if not cards:
                break
            for card in cards:
                prod = extract_product(card, cat_url)
                if prod.get("name") and prod.get("price_sek"):
                    products.append(prod)
            # Check if there's a next page
            next_link = soup.select_one(f'a[href*="page={page_num + 1}"]')
            if next_link:
                page_num += 1
                time.sleep(1.5)
            else:
                break
        except Exception as e:
            print(f"    ERROR page {page_num}: {e}")
            break
    return products, page_num

def main():
    print("=" * 55)
    print("PLANTPRISET — Impecta Scraper (with pagination)")
    print("=" * 55)
    print(f"Categories: {len(CATEGORY_URLS)}")
    session = requests.Session()
    session.headers.update(HEADERS)
    print("Getting cookies...")
    session.get(BASE_URL, timeout=15)
    time.sleep(1)

    all_products = []
    for i, cat in enumerate(CATEGORY_URLS, 1):
        products, pages = scrape_category(session, cat)
        page_info = f" ({pages} pages)" if pages > 1 else ""
        print(f"[{i}/{len(CATEGORY_URLS)}] {cat} → {len(products)} products{page_info}")
        all_products.extend(products)
        time.sleep(1.5)

    # Deduplicate by product_url
    seen = set()
    unique = []
    for p in all_products:
        key = p.get("product_url", p.get("name", ""))
        if key not in seen:
            seen.add(key)
            unique.append(p)

    with open("impecta_products.json", "w", encoding="utf-8") as f:
        json.dump({
            "retailer": "impecta",
            "scraped_at": datetime.utcnow().isoformat(),
            "total_products": len(unique),
            "categories_scraped": len(CATEGORY_URLS),
            "products": unique,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*55}")
    print(f"DONE! {len(unique)} unique products → impecta_products.json")
    prices = [p["price_sek"] for p in unique if p.get("price_sek")]
    if prices:
        print(f"Prices: {min(prices):.0f} – {max(prices):.0f} kr (avg {sum(prices)/len(prices):.0f} kr)")
    in_stock = sum(1 for p in unique if p.get("in_stock"))
    print(f"In stock: {in_stock}/{len(unique)}")
    campaign = sum(1 for p in unique if p.get("price_campaign_sek"))
    eko = sum(1 for p in unique if "ekologisk" in p.get("properties", []))
    print(f"On sale: {campaign} | Ekologisk: {eko}")

if __name__ == "__main__":
    main()
