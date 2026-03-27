import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="sv-SE")
        page = await context.new_page()
        
        all_calls = []
        async def on_response(response):
            url = response.url
            if response.status == 200:
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    try:
                        body = await response.text()
                        all_calls.append({
                            "url": url,
                            "size": len(body),
                            "body": body[:2000],
                            "method": response.request.method,
                        })
                    except: pass
        
        page.on("response", on_response)
        
        print("=== PLANTAGEN — Loading page + scrolling ===")
        await page.goto("https://plantagen.se/se/vaxter/froer", wait_until="networkidle", timeout=30000)
        
        # Accept cookies
        try:
            btn = page.locator("#onetrust-accept-btn-handler, button:has-text('Acceptera')")
            if await btn.count() > 0:
                await btn.first.click()
                await page.wait_for_timeout(2000)
        except: pass
        
        # Scroll down to trigger lazy loading
        for i in range(3):
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(2000)
        
        await page.wait_for_timeout(3000)
        
        print(f"\n  Total API calls: {len(all_calls)}")
        for call in all_calls:
            has_price = any(x in call["body"].lower() for x in ["price", "pris", "amount", "cost"])
            has_product = any(x in call["body"].lower() for x in ["product", "name", "title", "frö"])
            flag = ""
            if has_price: flag += "💰"
            if has_product: flag += "📦"
            if flag:
                print(f"\n  {flag} {call['method']} {call['url'][:100]}")
                print(f"     Size: {call['size']}b")
                print(f"     {call['body'][:400]}")
        
        await browser.close()

asyncio.run(main())
