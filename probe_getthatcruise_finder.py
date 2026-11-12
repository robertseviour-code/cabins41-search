"""Diagnostic browser probe for the interactive Get That Cruise finder.

This is intentionally *not* a production scraper. It records the network
requests made when the solo-fare filter is clicked and when more results load.
No external requests are made beyond browsing the supplier's public website.
Run manually: pip install playwright; playwright install chromium;
python probe_getthatcruise_finder.py
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.getthatcruise.co.uk/cruises"
OUT = Path("getthatcruise_finder_probe.json")


async def main():
    requests = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("request", lambda req: requests.append({
            "method": req.method,
            "url": req.url,
            "resource_type": req.resource_type,
        }) if req.resource_type in ("fetch", "xhr") else None)
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        initial = await page.locator("body").inner_text()
        # Click only the actual filter control, not arbitrary matching text.
        chip = page.get_by_text("Solo fare published", exact=False).first
        if await chip.count() == 0:
            raise RuntimeError("Solo filter not found; inspect finder manually")
        await chip.click(timeout=10000)
        await page.wait_for_timeout(1500)
        filtered = await page.locator("body").inner_text()
        show_more = page.get_by_text("Show 24 more", exact=False).first
        more_present = await show_more.count() > 0
        if more_present:
            await show_more.click(timeout=10000)
            await page.wait_for_timeout(1500)
        after_more = await page.locator("body").inner_text()
        OUT.write_text(json.dumps({
            "initial_excerpt": initial[:1500],
            "filtered_excerpt": filtered[:1500],
            "after_more_excerpt": after_more[:1500],
            "filter_applied": initial != filtered,
            "more_button_found": more_present,
            "network_requests": requests,
        }, indent=2), encoding="utf-8")
        print("Diagnostic saved to", OUT)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
