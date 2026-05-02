# ─────────────────────────────────────────────────────────────────────────────
# scraper.py — Browser automation & multi-page scraping orchestration
#
# Responsibilities:
#   • get_chrome_driver()   — configure & launch headless Chrome
#   • close_popup()         — dismiss the Flipkart login popup
#   • scrape_flipkart()     — loop over pages, collect rows, return DataFrame
#
# This module contains ALL Selenium code. If you switch to Playwright or
# requests+BS4, only this file changes.
# ─────────────────────────────────────────────────────────────────────────────

import time
import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui    import WebDriverWait
from selenium.webdriver.support       import expected_conditions as EC

from config  import (
    CHROME_USER_AGENT, CHROME_WINDOW_SIZE,
    PAGE_LOAD_DELAY, POPUP_WAIT_SECS, CARD_WAIT_SECS,
    LIST_CLASSES, GRID_CLASSES,
)
from parser  import parse_page
from utils   import compute_value_score


# ── Driver setup ──────────────────────────────────────────────────────────────

def get_chrome_driver() -> webdriver.Chrome:
    """
    Build and return a headless Chrome WebDriver with anti-detection options.

    Key options:
        --headless              Run without a visible window
        --no-sandbox            Required inside Docker / CI environments
        --disable-dev-shm-usage Prevents crashes in low-memory containers
        user-agent              Mimic a real desktop browser to avoid 403 blocks
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument(f"--window-size={CHROME_WINDOW_SIZE}")
    options.add_argument(f"user-agent={CHROME_USER_AGENT}")
    return webdriver.Chrome(options=options)


# ── Popup handler ─────────────────────────────────────────────────────────────

def close_popup(driver: webdriver.Chrome) -> None:
    """
    Try to click Flipkart's login popup close button (✕).

    The popup appears only on the first page load for a session, so this is
    called once after navigating to page 1.  Failures are silently swallowed
    — if the popup isn't present, no action is needed.
    """
    try:
        btn = WebDriverWait(driver, POPUP_WAIT_SECS).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'✕')]")
            )
        )
        btn.click()
        time.sleep(1)
    except Exception:
        pass   # No popup — that's fine


# ── Main scraper ──────────────────────────────────────────────────────────────

def scrape_flipkart(query: str, pages: int) -> tuple[pd.DataFrame, set[str]]:
    """
    Scrape *pages* pages of Flipkart search results for *query*.

    Steps per page:
        1. Navigate to the search URL
        2. On page 1: dismiss the login popup
        3. Wait for product cards to appear in the DOM
        4. Pass page_source to parser.parse_page()
        5. Append parsed rows to the collection

    After all pages:
        • Deduplicate on (Product Name, Price)
        • Compute Savings (₹) and Value Score derived columns

    Args:
        query:   URL-encoded product search term (e.g. "earbuds", "laptop")
        pages:   Number of result pages to scrape (1–20)

    Returns:
        (df, layouts_seen)
            df            — cleaned Pandas DataFrame of all products
            layouts_seen  — set of layout strings e.g. {"List"} or {"Grid"}
    """
    driver       = get_chrome_driver()
    all_rows     = []
    layouts_seen = set()

    # Streamlit progress bar — visible to the user during scraping
    progress = st.progress(0, text="Starting browser…")

    try:
        for page_num in range(1, pages + 1):
            progress.progress(
                page_num / pages,
                text=f"Scraping page {page_num} of {pages}…"
            )

            url = f"https://www.flipkart.com/search?q={query}&page={page_num}"
            driver.get(url)

            # Dismiss popup on the very first page only
            if page_num == 1:
                close_popup(driver)

            # Wait until at least one product card is present
            _wait_for_cards(driver)

            rows, layout = parse_page(driver.page_source)
            all_rows.extend(rows)
            layouts_seen.add(layout.capitalize())

            time.sleep(PAGE_LOAD_DELAY)   # Be polite to Flipkart's servers

    finally:
        driver.quit()
        progress.empty()

    # ── Build DataFrame ───────────────────────────────────────────────────────
    if not all_rows:
        return pd.DataFrame(), layouts_seen

    df = pd.DataFrame(all_rows)

    # Remove exact duplicates (same name + same price)
    df.drop_duplicates(subset=["Product Name", "Price (₹)"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # ── Derived columns ───────────────────────────────────────────────────────
    # Savings = how much you save vs original MRP
    df["Savings (₹)"] = (df["MRP (₹)"] - df["Price (₹)"]).clip(lower=0)

    # Value Score = (Rating × No. of Ratings) / Price — higher = better value
    df["Value Score"] = df.apply(
        lambda r: compute_value_score(r["Rating"], r["No. of Ratings"], r["Price (₹)"]),
        axis=1,
    )

    return df, layouts_seen


# ── Internal helper ───────────────────────────────────────────────────────────

def _wait_for_cards(driver: webdriver.Chrome) -> None:
    """
    Block until either list-layout or grid-layout product cards appear in the
    DOM, or until CARD_WAIT_SECS seconds elapse.

    Uses a lambda condition because WebDriverWait doesn't natively support
    OR-style element checks.
    """
    try:
        WebDriverWait(driver, CARD_WAIT_SECS).until(
            lambda d: (
                d.find_elements(By.CLASS_NAME, LIST_CLASSES["container"]) or
                d.find_elements(By.CLASS_NAME, GRID_CLASSES["container"])
            )
        )
    except Exception:
        pass   # Timeout — parse whatever is on the page anyway
