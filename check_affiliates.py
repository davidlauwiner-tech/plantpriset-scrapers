import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Check Granngården and Plantagen for affiliate network clues
for name, url in [
    ("Granngården", "https://www.granngarden.se/"),
    ("Plantagen", "https://plantagen.se/se"),
]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        html = resp.text.lower()
        print(f"\n=== {name} ===")
        for network in ["awin", "tradedoubler", "adtraction", "cj.com", "commission junction", 
                         "partnerads", "adservice", "tradetracker", "shareasale", "impact.com",
                         "admitad", "webgains"]:
            if network in html:
                print(f"  Found: {network}")
        # Also check for tracking pixels/scripts
        for pattern in ["aw.ds", "td.doubleclick", "track.adtraction", "cj.dotomi",
                        "prf.hn", "tracking.adtraction.com", "clk.tradedoubler"]:
            if pattern in html:
                print(f"  Tracking: {pattern}")
    except Exception as e:
        print(f"  ERROR: {e}")
