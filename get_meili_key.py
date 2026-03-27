import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        captured_headers = []
        async def on_request(request):
            if "meilisearch" in request.url:
                captured_headers.append({
                    "url": request.url,
                    "headers": dict(request.headers),
                    "body": request.post_data or "",
                })
        
        page.on("request", on_request)
        
        await page.goto("https://plantagen.se/se", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)
        
        print(f"Meilisearch requests captured: {len(captured_headers)}")
        for req in captured_headers:
            print(f"\n  URL: {req['url'][:100]}")
            print(f"  Auth header: {req['headers'].get('authorization', 'none')}")
            print(f"  X-Meili-API-Key: {req['headers'].get('x-meilisearch-api-key', 'none')}")
            # Show all headers that might be auth
            for k, v in req['headers'].items():
                if any(x in k.lower() for x in ['auth', 'key', 'token', 'meili']):
                    print(f"  {k}: {v}")
            print(f"  Body: {req['body'][:200]}")
        
        await browser.close()

asyncio.run(main())
