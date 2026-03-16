import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="sv-SE",
            extra_http_headers={"Accept-Language": "sv-SE,sv;q=0.9"}
        )
        page = await context.new_page()
        
        # Intercept all API calls to find the pricing endpoint
        api_calls = []
        async def on_response(response):
            url = response.url
            if "/api/" in url and response.status == 200:
                try:
                    body = await response.text()
                    if "price" in body.lower() and ("kr" in body or "SEK" in body or '"29"' in body or '"39"' in body):
                        api_calls.append({"url": url, "body": body[:500]})
                except: pass
        
        page.on("response", on_response)
        
        await page.goto("https://www.nelsongarden.se/produkter/solros-p88358/", wait_until="networkidle", timeout=30000)
        
        # Dismiss cookie
        try:
            btn = page.locator("button:has-text('Ok')")
            if await btn.count() > 0:
                await btn.first.click()
        except: pass
        
        # Wait longer for prices to load
        await page.wait_for_timeout(8000)
        
        # Check if prices appeared
        price_els = await page.locator(".ig-price").all()
        print(f"Price elements: {len(price_els)}")
        for el in price_els[:5]:
            text = await el.text_content()
            if text and text.strip():
                print(f"  PRICE: '{text.strip()}'")
        
        # Check all intercepted API calls
        print(f"\nAPI calls with price data: {len(api_calls)}")
        for call in api_calls[:10]:
            print(f"  URL: {call['url']}")
            print(f"  Body: {call['body'][:300]}")
            print()
        
        # Also dump ALL api calls made
        print("=== All /api/ responses captured ===")
        
        await browser.close()

asyncio.run(main())
