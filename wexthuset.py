import os, time, re, requests
from playwright.sync_api import sync_playwright
from base_scraper import BaseScraper

class WexthusetScraper(BaseScraper):
    retailer_slug = "wexthuset"
    retailer_name = "Wexthuset"
    retailer_url = "https://www.wexthuset.com"

    def run(self):
        print(f"=== {self.retailer_name} Scraper ===")
        plants = self.get_all_plants()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()

            # Debug: test one search and print structure
            print("\n--- DEBUG: Testing search for 'lavendel' ---")
            page.goto("https://www.wexthuset.com/search?q=lavendel", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Print page title
            print(f"Page title: {page.title()}")
            print(f"URL: {page.url}")
            
            # Print all links that look like products
            links = page.query_selector_all("a[href*='/froer'], a[href*='/vaxter'], a[href*='/perenn']")
            print(f"Product-like links found: {len(links)}")
            for link in links[:5]:
                print(f"  - {link.get_attribute('href')} | {link.inner_text()[:50]}")
            
            # Print page source snippet
            content = page.content()
            print(f"\nPage length: {len(content)} chars")
            
            # Look for price patterns
            prices = re.findall(r'(\d{2,4})\s*kr', content)
            print(f"Price mentions found: {prices[:10]}")
            
            # Look for JSON data
            json_matches = re.findall(r'"name":"([^"]{3,50})"', content)
            print(f"JSON name fields: {json_matches[:10]}")

            browser.close()

if __name__ == "__main__":
    WexthusetScraper().run()
