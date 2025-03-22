import json
import asyncio
import sys
from playwright.async_api import async_playwright

SESSION_FILE = "session.json"
LOGIN_URL = "https://example.com/login"
PRODUCT_URL = "https://example.com/hidden-path"
USERNAME = "your_username"
PASSWORD = "your_password"

async def save_session(context):
    storage = await context.storage_state()
    with open(SESSION_FILE, "w") as f:
        json.dump(storage, f)

async def load_session(browser):
    try:
        with open(SESSION_FILE, "r") as f:
            storage = json.load(f)
        return await browser.new_context(storage_state=storage)
    except (FileNotFoundError, json.JSONDecodeError):
        return await browser.new_context()

async def login(page):
    await page.goto(LOGIN_URL)
    await page.fill("#username", USERNAME)
    await page.fill("#password", PASSWORD)
    await page.click("button[type='submit']")
    await page.wait_for_selector("#dashboard", timeout=10000)
    
async def navigate_wizard(page):
    await page.goto(PRODUCT_URL)
    steps = ["Select Data Source", "Choose Category", "Select View Type", "View Products"]
    for step in steps:
        await page.wait_for_selector(f"text={step}", timeout=5000)
        next_button = await page.query_selector("button:has-text('Next')")
        if next_button:
            await next_button.click()
            await asyncio.sleep(2)
    await page.wait_for_selector("text=View Products", timeout=10000)
    view_products_button = await page.query_selector("text=View Products")
    if view_products_button:
        await view_products_button.click()
    await page.wait_for_selector("table", timeout=10000)

async def extract_product_data(page):
    products = []
    while True:
        rows = await page.query_selector_all("table tbody tr")
        for row in rows:
            data = await row.evaluate("node => [...node.children].map(td => td.innerText)")
            products.append(data)
        next_button = await page.query_selector("button:has-text('Next Page')")
        if next_button and await next_button.is_enabled():
            await next_button.click()
            await page.wait_for_timeout(2000)
        else:
            break
    return products

async def main():
    try:
        import playwright
    except ModuleNotFoundError:
        print("Playwright is not installed. Installing now...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
        print("Playwright installed successfully. Please restart the script.")
        return
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await load_session(browser)
        page = await context.new_page()

        try:
            await page.goto(PRODUCT_URL)
            if await page.locator("#login-form").is_visible():
                await login(page)
                await save_session(context)

            await navigate_wizard(page)
            data = await extract_product_data(page)
            
            with open("products.json", "w") as f:
                json.dump(data, f, indent=4)
            print("Data saved to products.json")
        
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
