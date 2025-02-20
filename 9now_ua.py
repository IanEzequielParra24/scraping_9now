import asyncio
import json
import time
import psutil
import pandas as pd
import aiohttp
from datetime import datetime
from urllib.parse import urlparse
from playwright.async_api import async_playwright

CSV_FILE = "/home/ian/Escritorio/examen python/urls.cvs"
OUTPUT_FILE = "extracted_9now.json"
TAB_OUTPUT_FILE = "tabs.json"
SCREENSHOT_FILE = "screenshot.png"
BASE_URL = "https://www.9now.com.au/"

def normalize_url(url):
    return url.strip().lower() if url else ""

def extract_data_recursive(data, extracted_data):
    if isinstance(data, dict):
        if "cards" in data:
            for card in data["cards"]:
                desc_text = card.get("description", {}).get("text", "")
                new_title = card.get("title", {}).get("text", "")
                tertiary = card.get("tertiaryContent", {})
                channel = ""
                hour = ""
                if tertiary:
                    metadata = tertiary.get("metadata", [])
                    if metadata:
                        channel = metadata[0].get("text", "")
                    if len(metadata) > 1:
                        hour = metadata[1].get("text", "")
                secondary = card.get("secondaryTitle", {})
                gender = ""
                if secondary:
                    metadata_sec = secondary.get("metadata", [])
                    if metadata_sec:
                        gender = metadata_sec[0].get("text", "")
                img_set = card.get("cardImage", {}).get("default", {}).get("srcset", "")
                buttons = card.get("secondaryActions", {}).get("buttons", [])
                if buttons:
                    actions = buttons[0].get("actions", {})
                    on_click = actions.get("onClick", [])
                    if on_click:
                        destination_uri = on_click[0].get("data", {}).get("destinationUri", "")
                        if destination_uri:
                            full_dest_url = BASE_URL + destination_uri if destination_uri.startswith("/") else destination_uri
                            norm_dest = normalize_url(full_dest_url)
                            for entry in extracted_data:
                                norm_href = normalize_url(entry.get("url", ""))
                                if norm_dest in norm_href or norm_href in norm_dest:
                                    entry["description"] = desc_text
                                    entry["channel"] = channel
                                    entry["gender"] = gender
                                    entry["hour"] = hour
                                    entry["img"] = img_set
                                    entry["title"] = new_title
        for key, value in data.items():
            extract_data_recursive(value, extracted_data)
    elif isinstance(data, list):
        for item in data:
            extract_data_recursive(item, extracted_data)

async def fetch_data():
    try:
        async with aiohttp.ClientSession() as session:
            url_home = "https://api.9now.com.au/web/home-page"
            headers_home = {
                "accept": "application/json",
                "accept-language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7,es-419;q=0.6",
                "if-none-match": 'W/"31989-sqpXGRIHBTNYtIRvCkd+fkoyQxY"',
                "origin": "https://www.9now.com.au",
                "referer": "https://www.9now.com.au/",
                "priority": "u=1, i",
                "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Linux"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            }
            async with session.get(url_home, headers=headers_home) as response_home:
                response_home.raise_for_status()
                response_home_json = await response_home.json()
                tabs = [tab['id'] for tab in response_home_json['data']['getHomePage']['sections']['content']['tabs'] if 'Tab' in tab['id']]
                final_data = []
                for tab in tabs:
                    url_tab = f"https://api.9now.com.au/web/tab-by-id?device=web&variables=%7B%22elementType%22%3A%22TAB%22%2C%22dynamicElementId%22%3A%22{tab}%22%2C%22region%22%3A%22overseas%22%7D&token="
                    async with session.get(url_tab, headers=headers_home) as response_tab:
                        response_tab.raise_for_status()
                        data_tab = await response_tab.json()
                        tab_data = next(item for item in response_home_json['data']['getHomePage']['sections']['content']['tabs'] if item['id'] == tab)
                        combined_data = {**tab_data, **data_tab}
                        final_data.append(combined_data)
                with open(TAB_OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(final_data, f, indent=4)
                return final_data
    except aiohttp.ClientError as e:
        print(f"Hubo un error en fetch_data: {e}")
        return []

async def scrape_9now(url, url_type, tabs_data):
    start_time = time.time()
    process = psutil.Process()
    print(f"🔍 Scrapeando: {url} ({url_type})")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        extracted_data = []
        api_responses = []

        def handle_response(response):
            if response.request.resource_type == "xhr":
                if "tab-by-id" in response.url and "device=web" in response.url:
                    asyncio.create_task(process_response(response))

        async def process_response(response):
            try:
                if response.status == 200:
                    data = await response.json()
                    if "getElementById" in json.dumps(data):
                        api_responses.append({"url": response.url, "data": data})
                        print(f"✅ API Capturada: {response.url}")
            except Exception as e:
                print(f"⚠ Error en API {response.url}: {e}")

        page.on("response", handle_response)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            for _ in range(30):
                await page.evaluate("window.scrollBy(0, 900)")
                await asyncio.sleep(2)
            await asyncio.sleep(5)
        except Exception as e:
            print(f"⚠ Error al cargar la página: {e}")
            await browser.close()
            return

        async def extract_live():
            try:
                section = await page.query_selector('section[class="sc-f1737771-0 cQYcvW"] section.sc-f1737771-2.jppAqW')
                if section:
                    img_el = await section.query_selector('img.sc-2818d18f-0.hxlXSY.sc-fc3d43dd-0.jPEqae')
                    title = await img_el.get_attribute("alt") if img_el else ""
                    img = await img_el.get_attribute("src") if img_el else ""
                    channel_el = await section.query_selector('div.sc-8bd455a9-4.eJrbpf svg')
                    channel = await channel_el.get_attribute("aria-label") if channel_el else ""
                    finish_el = await section.query_selector('span.sc-be2dc1e9-1.igltsg.sdui_inline_text_and_icon_element span')
                    finish = await finish_el.inner_text() if finish_el else ""
                    spans = await section.query_selector_all('span.sc-be2dc1e9-1.eUEJCz.sdui_inline_text_and_icon_element')
                    gender = await spans[2].inner_text() if len(spans) >= 3 else ""
                    next_text = await spans[1].inner_text() if len(spans) >= 2 else ""
                    duration = await spans[3].inner_text() if len(spans) >= 1 else ""
                    class_el = await section.query_selector('span.sc-be2dc1e9-1.lijJix.sdui_inline_text_and_icon_element')
                    classification = await class_el.inner_text() if class_el else ""
                    desc_el = await section.query_selector('p.sc-6a24f417-2.hdqhbR')
                    description = await desc_el.inner_text() if desc_el else ""
                    href_el = await section.query_selector("a")
                    href = await href_el.get_attribute("href") if href_el else ""
                    full_url = BASE_URL + href if href and href.startswith("/") else href
                    data = {
                        "category": "Live_TV",
                        "title": title,
                        "img": img,
                        "channel": channel,
                        "finish": finish,
                        "gender": gender,
                        "next": next_text,
                        "duration": duration,
                        "classification": classification,
                        "description": description,
                        "url": full_url
                    }
                    extracted_data.append(data)
            except Exception as e:
                print(f"⚠ Error al extraer Live TV: {e}")

        async def extract_featured_data():
            try:
                sections = await page.query_selector_all('section[id="Tab-0"]')
                for sec in sections:
                    cat_el = await sec.query_selector('h2.sc-a20f8d3e-1.sc-60747d80-0.ixmMiH.cKSuqW.tab_title')
                    cat = await cat_el.inner_text() if cat_el else ""
                    articles = await sec.query_selector_all('article.sdui_card.primary-card-view')
                    for art in articles:
                        title_el = await art.query_selector('div.sdui_card__primary_title')
                        hor_el = await art.query_selector('.schedule-time')
                        tv_el = await art.query_selector('.program-name')
                        chan_el = await art.query_selector('.channel-name')
                        dur_el = await art.query_selector('.duration')
                        fin_el = await art.query_selector('.end-time')
                        img_el = await art.query_selector('img.sc-2818d18f-0.hxlXSY.sdui_card__image')
                        href_el = await art.query_selector("a")
                        title = await title_el.inner_text() if title_el else ""
                        hor = await hor_el.inner_text() if hor_el else ""
                        tv = await tv_el.inner_text() if tv_el else ""
                        chan = await chan_el.inner_text() if chan_el else ""
                        dur = await dur_el.inner_text() if dur_el else ""
                        fin = await fin_el.inner_text() if fin_el else ""
                        img = await img_el.get_attribute("src") if img_el else ""
                        href = await href_el.get_attribute("href") if href_el else ""
                        full_url = BASE_URL + href if href and href.startswith("/") else href
                        entry = {
                            "category": cat,
                            "title": title,
                            "horario": hor,
                            "tv": tv,
                            "channel": chan,
                            "duracion": dur,
                            "finalizacion": fin,
                            "img": img,
                            "url": full_url
                        }
                        extracted_data.append(entry)
            except Exception as e:
                print(f"⚠ Error al extraer Featured: {e}")

        async def extract_live_channels():
            try:
                section = await page.query_selector('section[id="LIVE_CHANNELS_LISTINGS_LIST"]')
                if section:
                    cat_el = await section.query_selector('h2')
                    cat = await cat_el.inner_text() if cat_el else ""
                    cards = await section.query_selector_all('div.sdui_card__wrapper')
                    for card in cards:
                        a_el = await card.query_selector("a")
                        href = await a_el.get_attribute("href") if a_el else ""
                        full_url = BASE_URL + href if href and href.startswith("/") else href
                        title_el = await card.query_selector('span')
                        title = await title_el.inner_text() if title_el else ""
                        extracted_data.append({"category": cat, "title": title, "url": full_url})
            except Exception as e:
                print(f"⚠ Error al extraer Live Channels Listings: {e}")

        async def extract_tab4_data():
            try:
                sections = await page.query_selector_all('section[id^="Tab-"]')
                for sec in sections:
                    cat_el = await sec.query_selector('h2')
                    cat = await cat_el.inner_text() if cat_el else ""
                    cards = await sec.query_selector_all('div[data-testid^="Card-"]')
                    for card in cards:
                        a_el = await card.query_selector("a")
                        href = await a_el.get_attribute("href") if a_el else ""
                        full_url = BASE_URL + href if href and href.startswith("/") else href
                        title_el = await card.query_selector('span')
                        title = await title_el.inner_text() if title_el else ""
                        extracted_data.append({"category": cat, "title": title, "url": full_url})
            except Exception as e:
                print(f"⚠ Error al extraer Tab 4: {e}")

        async def extract_cat_data():
            try:
                sections = await page.query_selector_all('div[class="singleCategoryPage__results"]')
                for sec in sections:
                    cat_el = await sec.query_selector('h1')
                    cat = await cat_el.inner_text() if cat_el else ""
                    cards = await sec.query_selector_all('ul li')
                    for card in cards:
                        a_el = await card.query_selector("a")
                        href = await a_el.get_attribute("href") if a_el else ""
                        full_url = BASE_URL + href if href and href.startswith("/") else href
                        title_el = await card.query_selector('h3')
                        title = await title_el.inner_text() if title_el else ""
                        extracted_data.append({"category": cat, "title": title, "url": full_url})
            except Exception as e:
                print(f"⚠ Error al extraer Categorías: {e}")

        await asyncio.gather(
            extract_live(),
            extract_featured_data(),
            extract_live_channels(),
            extract_tab4_data(),
            extract_cat_data()
        )
        await asyncio.sleep(3)

        async def extract_from_api():
            for api in api_responses:
                try:
                    cards = api["data"].get("data", {}).get("getElementById", {}).get("cards", [])
                    for card in cards:
                        try:
                            buttons = card.get("secondaryActions", {}).get("buttons", [])
                            if buttons:
                                actions = buttons[0].get("actions", {})
                                on_click = actions.get("onClick", [])
                                if on_click:
                                    destination_uri = on_click[0].get("data", {}).get("destinationUri", "")
                                    if destination_uri:
                                        full_dest_url = BASE_URL + destination_uri if destination_uri.startswith("/") else destination_uri
                                        print("API destination URL:", full_dest_url)
                        except Exception as inner_e:
                            print(f"⚠ Error procesando card de API: {inner_e}")
                except Exception as e:
                    print(f"⚠ Error extrayendo datos de la API: {e}")

        await extract_from_api()

        extract_data_recursive(tabs_data, extracted_data)

        await page.screenshot(path=SCREENSHOT_FILE, full_page=True)
        print(f"📸 Captura de pantalla guardada en {SCREENSHOT_FILE}")
        await browser.close()
        extracted_data.sort(key=lambda x: x.get("category", ""))
        end_time = time.time()
        exec_time = end_time - start_time
        process.cpu_percent(interval=None)
        end_time = time.time()
        exec_time = end_time - start_time
        cpu_end = process.cpu_percent(interval=1) 
        ram_usage = process.memory_info().rss / (1024 * 1024)  
        execution_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {"url": url, 
                "url_type": url_type,
                "execution_date": execution_date,
                "execution_time": f"{exec_time:.2f} segundos",
                "cpu_usage": f"{cpu_end:.2f}%",
                "ram_usage": f"{ram_usage:.2f} MB",
                "data": extracted_data}

async def main():
    tabs_data = await fetch_data()
    for tab in tabs_data:
    
        df = pd.read_csv(CSV_FILE)
    all_data = [await scrape_9now(row["url"], row["url_type"], tabs_data) for _, row in df.iterrows()]
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4)
    print(f"📂 Datos guardados en {OUTPUT_FILE}")

asyncio.run(main())
