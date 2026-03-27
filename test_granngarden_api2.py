import asyncio, json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="sv-SE")
        page = await context.new_page()
        
        price_data = []
        product_data = []
        
        async def on_response(response):
            url = response.url
            if response.status == 200 and "granngarden" in url:
                if "bestprice" in url:
                    try:
                        body = await response.text()
                        price_data.append(body[:2000])
                    except: pass
                elif "view-product-list" in url:
                    try:
                        body = await response.text()
                        product_data.append(body[:2000])
                    except: pass
        
        page.on("response", on_response)
        
        await page.goto("https://www.granngarden.se/sok?q=tomat", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)
        
        print("=== PRICE API RESPONSE ===")
        for d in price_data:
            print(d[:1000])
        
        print("\n=== PRODUCT API RESPONSE ===")
        for d in product_data:
            print(d[:1000])
        
        # Also check what the rendered product cards look like
        print("\n=== RENDERED PRODUCT CARDS ===")
        from bs4 import BeautifulSoup
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        # Find product cards
        for sel in ["[class*='product']", "[class*='Product']", "article", "[data-product]"]:
            els = soup.select(sel)
            if els and len(els) > 2:
                print(f"Selector '{sel}': {len(els)}")
                card = els[0]
                print(card.prettify()[:1500])
                break
        
        await browser.close()

asyncio.run(main())
