import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="sv-SE")
        page = await context.new_page()
        
        all_calls = []
        async def on_request(request):
            url = request.url
            if "granngarden" in url and ("api" in url or "product" in url or "search" in url or "sok" in url or "catalog" in url):
                all_calls.append({
                    "method": request.method,
                    "url": url,
                    "headers": {k:v for k,v in request.headers.items() if 'auth' in k.lower() or 'key' in k.lower() or 'token' in k.lower()},
                    "body": (request.post_data or "")[:300],
                })
        
        page.on("request", on_request)
        
        # Try the search page instead — that usually loads products
        await page.goto("https://www.granngarden.se/sok?q=tomat", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)
        
        # Also try scrolling
        for i in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await page.wait_for_timeout(1500)
        
        print(f"API calls: {len(all_calls)}")
        for call in all_calls:
            print(f"\n  {call['method']} {call['url'][:120]}")
            if call['headers']:
                print(f"  Auth: {call['headers']}")
            if call['body']:
                print(f"  Body: {call['body'][:200]}")
        
        # Check if prices are in the rendered HTML
        import re
        content = await page.content()
        prices = re.findall(r'(\d+)[,.]?\d*\s*(?:kr|:-)', content)
        print(f"\nPrices in rendered HTML: {len(prices)}")
        if prices:
            print(f"  Sample: {prices[:10]}")
        
        await browser.close()

asyncio.run(main())
