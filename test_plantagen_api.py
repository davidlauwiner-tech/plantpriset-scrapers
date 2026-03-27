import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="sv-SE")
        page = await context.new_page()
        
        api_calls = []
        async def on_response(response):
            url = response.url
            if response.status == 200:
                ct = response.headers.get("content-type", "")
                if "json" in ct and ("product" in url.lower() or "search" in url.lower() or "catalog" in url.lower() or "price" in url.lower() or "api" in url.lower()):
                    try:
                        body = await response.text()
                        api_calls.append({"url": url[:120], "size": len(body), "snippet": body[:300]})
                    except: pass
        
        page.on("response", on_response)
        
        print("=== PLANTAGEN ===")
        await page.goto("https://plantagen.se/se/vaxter/froer", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(8000)
        
        print(f"  API calls captured: {len(api_calls)}")
        for call in api_calls[:10]:
            has_price = "price" in call["snippet"].lower() or "pris" in call["snippet"].lower()
            print(f"  {'💰' if has_price else '  '} [{call['size']}b] {call['url']}")
            if has_price:
                print(f"     {call['snippet'][:200]}")
        
        # Reset for Granngården
        api_calls.clear()
        
        print("\n=== GRANNGÅRDEN ===")
        await page.goto("https://www.granngarden.se/tradgard/fro-odling/froer", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(8000)
        
        print(f"  API calls captured: {len(api_calls)}")
        for call in api_calls[:10]:
            has_price = "price" in call["snippet"].lower() or "pris" in call["snippet"].lower()
            print(f"  {'💰' if has_price else '  '} [{call['size']}b] {call['url']}")
            if has_price:
                print(f"     {call['snippet'][:200]}")
        
        await browser.close()

asyncio.run(main())
