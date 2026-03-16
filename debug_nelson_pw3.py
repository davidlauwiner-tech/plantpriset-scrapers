import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="sv-SE")
        page = await context.new_page()
        
        all_responses = []
        async def on_response(response):
            url = response.url
            if "nelsongarden" in url and response.status == 200:
                ct = response.headers.get("content-type", "")
                if "json" in ct or "javascript" in ct:
                    try:
                        body = await response.text()
                        if any(x in body for x in ["price", "Price", "pris", "Pris", "SEK"]):
                            all_responses.append({"url": url, "size": len(body), "snippet": body[:400]})
                    except: pass
        
        page.on("response", on_response)
        
        # Go to homepage first to get proper cookies/market
        await page.goto("https://www.nelsongarden.se/", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Accept cookies
        try:
            btn = page.locator("button:has-text('Ok'), button:has-text('Acceptera')")
            if await btn.count() > 0:
                await btn.first.click()
                await page.wait_for_timeout(1000)
        except: pass
        
        # Now navigate to product
        await page.goto("https://www.nelsongarden.se/produkter/solros-p88358/", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)
        
        # Try to get any visible price text on the page
        all_text = await page.locator("body").inner_text()
        import re
        kr_matches = re.findall(r'(\d+[.,]?\d*)\s*kr', all_text)
        print(f"Prices in visible text: {kr_matches}")
        
        sek_matches = re.findall(r'(\d+[.,]?\d*)\s*SEK', all_text)
        print(f"SEK in visible text: {sek_matches}")
        
        # Check the ig-price elements again
        price_els = await page.locator(".ig-price").all()
        for i, el in enumerate(price_els[:8]):
            text = await el.inner_text()
            html = await el.inner_html()
            print(f"  .ig-price[{i}] text='{text.strip()}' html='{html.strip()[:100]}'")
        
        # Print captured responses
        print(f"\nCaptured {len(all_responses)} responses with price keywords:")
        for r in all_responses[:15]:
            print(f"  [{r['size']}b] {r['url'][:100]}")
            print(f"    {r['snippet'][:200]}")
            print()
        
        await browser.close()

asyncio.run(main())
