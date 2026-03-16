import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("https://www.nelsongarden.se/produkter/solros-p88358/", wait_until="networkidle", timeout=30000)
        
        # Try to dismiss cookie banner
        try:
            btn = page.locator("button:has-text('Ok'), button:has-text('Godkänn'), button:has-text('Acceptera')")
            if await btn.count() > 0:
                await btn.first.click()
                await page.wait_for_timeout(1000)
        except: pass
        
        await page.wait_for_timeout(3000)
        
        # Get all text that looks like a price
        content = await page.content()
        
        import re
        prices = re.findall(r'(\d+[.,]?\d*)\s*kr', content)
        print(f"Prices found in rendered page: {prices}")
        
        # Look for price elements
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")
        
        # Find elements with price-like content
        for el in soup.find_all(string=re.compile(r'\d+.*kr')):
            parent = el.parent
            print(f"  <{parent.name}> class={parent.get('class')} → {el.strip()[:80]}")
        
        # Also check for specific price classes
        for selector in [".price", "[class*='price']", "[class*='Price']", "[data-price]"]:
            els = soup.select(selector)
            if els:
                print(f"\n  Selector '{selector}' matched {len(els)} elements:")
                for el in els[:5]:
                    print(f"    <{el.name}> class={el.get('class')} text={el.get_text(strip=True)[:60]}")
        
        await browser.close()

asyncio.run(main())
