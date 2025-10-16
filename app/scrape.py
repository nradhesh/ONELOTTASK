# app/scrape.py
import os, json, re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from .utils import logger, retry
from .db import SessionLocal
from .services import ingest_listing
from urllib.parse import urljoin
from time import sleep
from bs4 import BeautifulSoup

# try to detect available parser; prefer lxml if installed
try:
    import lxml  # type: ignore
    _bs_parser = "lxml"
except Exception:
    _bs_parser = "html.parser"

load_dotenv()
TARGET_URL = os.getenv("TARGET_URL")
HEADLESS = os.getenv("HEADLESS", "1") == "1"
COOKIES_FILE = os.getenv("PLAYWRIGHT_COOKIES_FILE")
# allow collecting more items via env override
SCRAPE_MAX_ITEMS = int(os.getenv("SCRAPE_MAX_ITEMS", "200"))

def _get_id(url):
    m = re.search(r"/item/([^/?&]+)", url)
    return m.group(1) if m else url.split("/")[-1]

@retry(Exception, tries=3, delay=2, backoff=2)
def fetch_url_content(page, url):
    page.goto(url, timeout=60000)
    sleep(1)
    return page.content()

def scrape_marketplace():
    if not TARGET_URL:
        raise RuntimeError("TARGET_URL not set")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        if COOKIES_FILE and os.path.exists(COOKIES_FILE):
            try:
                with open(COOKIES_FILE, "r", encoding="utf-8") as fh:
                    cookies = json.load(fh)
                context.add_cookies(cookies)
            except Exception as e:
                logger.error("Failed loading cookies: %s", e)
        page = context.new_page()
        page.goto(TARGET_URL, timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        sleep(2)

        # Progressive infinite scroll until no new items appear for a few rounds or cap is reached
        urls_set = set()
        stagnant_rounds = 0
        max_rounds = 50
        while stagnant_rounds < 3 and len(urls_set) < SCRAPE_MAX_ITEMS and max_rounds > 0:
            try:
                page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            except Exception:
                pass
            # give time for network/rendering
            page.wait_for_load_state("networkidle", timeout=30000)
            sleep(1.0)
            anchors = page.query_selector_all("a[href*='/marketplace/item/'], a[href*='/item/']")
            before = len(urls_set)
            for a in anchors:
                href = a.get_attribute("href")
                if not href:
                    continue
                if href.startswith("/"):
                    href = urljoin("https://www.facebook.com", href)
                urls_set.add(href)
                if len(urls_set) >= SCRAPE_MAX_ITEMS:
                    break
            stagnant_rounds = stagnant_rounds + 1 if len(urls_set) == before else 0
            max_rounds -= 1

        urls = list(urls_set)
        logger.info("Found %d candidate urls after scrolling", len(urls))
        db = SessionLocal()
        try:
            for u in urls:
                try:
                    html = fetch_url_content(page, u)
                    # use chosen parser (lxml preferred, fallback to html.parser)
                    soup = BeautifulSoup(html, _bs_parser)
                    title = soup.find("meta", property="og:title")
                    title = title["content"].strip() if title else soup.title.string.strip() if soup.title else None
                    text_blob = soup.get_text(" ", strip=True)
                    price_m = re.search(r"([₱\$€£]|PHP)\s*([0-9,\.]+)", text_blob)
                    price = float(price_m.group(2).replace(",", "")) if price_m else None
                    currency = price_m.group(1) if price_m else None
                    year_m = re.search(r"\b(19|20)\d{2}\b", text_blob)
                    year = int(year_m.group(0)) if year_m else None
                    mileage_m = re.search(r"(\d{1,3}(?:,\d{3})+|\d{2,6})\s*(km|kilometers|kms)", text_blob, re.I)
                    mileage = int(re.sub(r"[^\d]","", mileage_m.group(1))) if mileage_m else None
                    location = None
                    loc = soup.select_one("[data-testid*='location'], [class*='location']")
                    if loc: location = loc.get_text(" ", strip=True)
                    listing_id = _get_id(u)
                    payload = {
                        "listing_id": listing_id,
                        "title": title,
                        "price": price,
                        "currency": currency,
                        "year": year,
                        "mileage": mileage,
                        "location": location,
                        "url": u,
                        "raw_json": {"snippet": str(soup)[:4000]}
                    }
                    ingest_listing(db, payload)
                except PWTimeout as e:
                    logger.warning("Timeout on %s: %s", u, e)
                except Exception as e:
                    logger.exception("Failed to scrape %s: %s", u, e)
        finally:
            db.close()
            context.close()
            browser.close()
