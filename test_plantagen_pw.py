import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # === PLANTAGEN ===
        print("=== PLANTAGEN ===")
        await page.goto("https://plantagen.se/se/vaxter/froer", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)
        
        # Accept cookies
        try:
            btn = page.locator("button:has-text('Acceptera'), button:has-text('Godkänn'), #onetrust-accept-btn-handler")
            if await btn.count() > 0:
                await btn.first.click()
                await page.wait_for_timeout(2000)
        except: pass
        
        content = await page.content()
        import re
        prices = re.findall(r'(\d+)[,.]?\d*\s*(?:kr|:-)', content)
        print(f"  Prices found: {len(prices)}")
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")
        
        # Find product elements
        for sel in [".product", "[class*='product']", "[class*='Product']", "article", "[class*='card']", "[class*='Card']", "[class*='tile']", "[class*='Tile']"]:
            els = soup.select(sel)
            if els and len(els) > 3:
                print(f"  Selector '{sel}': {len(els)} elements")
        
        # Find price patterns
        for el in soup.find_all(string=re.compile(r'\d+\s*(?:kr|:-)')):
            parent = el.parent
            if parent:
                print(f"  Price: '{el.strip()[:40]}' in <{parent.name}> class={parent.get('class')}")
                break

        # === GRANNGÅRDEN ===
        print("\n=== GRANNGÅRDEN ===")
        await page.goto("https://www.granngarden.se/tradgard/fro-odling/froer", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)
        
        try:
            btn = page.locator("button:has-text('Acceptera'), button:has-text('Godkänn'), #onetrust-accept-btn-handler")
            if await btn.count() > 0:
                await btn.first.click()
                await page.wait_for_timeout(2000)
        except: pass
        
        content = await page.content()
        prices = re.findall(r'(\d+)[,.]?\d*\s*(?:kr|:-)', content)
        print(f"  Prices found: {len(prices)}")
        
        soup = BeautifulSoup(content, "html.parser")
        for sel in [".product", "[class*='product']", "[class*='Product']", "article", "[class*='card']", "[class*='Card']", "[class*='tile']"]:
            els = soup.select(sel)
            if els and len(els) > 3:
                print(f"  Selector '{sel}': {len(els)} elements")
        
        for el in soup.find_all(string=re.compile(r'\d+\s*(?:kr|:-)')):
            parent = el.parent
            if parent:
                print(f"  Price: '{el.strip()[:40]}' in <{parent.name}> class={parent.get('class')}")
                break
        
        await browser.close()

asyncio.run(main())
