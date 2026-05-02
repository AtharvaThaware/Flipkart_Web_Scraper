# ─────────────────────────────────────────────────────────────────────────────
# parser.py — HTML parsing: layout detection + field extraction
#
# Responsibilities:
#   • detect_layout()    — decide list vs grid from raw HTML
#   • parse_list_card()  — extract all fields from a list-view card
#   • parse_grid_card()  — extract all fields from a grid-view card
#   • parse_page()       — top-level: parse one page's HTML → list[dict]
#
# When Flipkart rotates CSS class names, update config.py — NOT this file.
# ─────────────────────────────────────────────────────────────────────────────

import re
from bs4 import BeautifulSoup

from config import LIST_CLASSES, GRID_CLASSES
from utils  import safe_text, clean_price, parse_review_count


# ── Layout detection ──────────────────────────────────────────────────────────

def detect_layout(soup: BeautifulSoup) -> str:
    """
    Count how many list-view and grid-view containers exist on the page and
    return whichever layout has more cards.

    Returns:
        "list"  — Flipkart list layout (detailed cards with specs, exchange, warranty)
        "grid"  — Flipkart grid layout (compact image cards with fewer fields)
    """
    list_count = len(soup.find_all("div", class_=LIST_CLASSES["container"]))
    grid_count = len(soup.find_all("div", class_=GRID_CLASSES["container"]))
    return "list" if list_count >= grid_count else "grid"


# ── List layout parser ────────────────────────────────────────────────────────

def parse_list_card(card) -> dict:
    """
    Extract every available data field from a single list-layout product card.

    Fields extracted:
        Product Name, Price (₹), MRP (₹), Discount (%), Rating,
        No. of Ratings, No. of Reviews, Specs, Exchange Offer (₹),
        Offers/Badges, Warranty, Product URL
    """
    row = {}

    # ── Name ──────────────────────────────────────────────────────────────────
    row["Product Name"] = safe_text(card.find(class_=LIST_CLASSES["name"]))

    # ── Prices ────────────────────────────────────────────────────────────────
    row["Price (₹)"] = clean_price(safe_text(card.find(class_=LIST_CLASSES["price"])))
    row["MRP (₹)"]   = clean_price(safe_text(card.find(class_=LIST_CLASSES["mrp"])))

    # ── Discount % ────────────────────────────────────────────────────────────
    disc_txt = safe_text(card.find(class_=LIST_CLASSES["discount"]))
    disc_num = re.sub(r"[^\d]", "", disc_txt)
    row["Discount (%)"] = int(disc_num) if disc_num else None

    # ── Rating ────────────────────────────────────────────────────────────────
    try:
        row["Rating"] = float(safe_text(card.find(class_=LIST_CLASSES["rating"])))
    except ValueError:
        row["Rating"] = None

    # ── Ratings & Reviews count ───────────────────────────────────────────────
    # The list layout packs both into one element, e.g.:
    #   "4.41,35,727 Ratings&6,988 Reviews"
    rev_txt = safe_text(card.find(class_=LIST_CLASSES["reviews"]))
    ratings_match = re.search(r"([\d,]+)\s*Rating", rev_txt)
    reviews_match = re.search(r"([\d,]+)\s*Review", rev_txt)
    row["No. of Ratings"] = parse_review_count(ratings_match.group(1)) if ratings_match else None
    row["No. of Reviews"] = parse_review_count(reviews_match.group(1)) if reviews_match else None

    # ── Specs ─────────────────────────────────────────────────────────────────
    # Full spec string, e.g. "8 GB RAM | 128 GB ROM | Expandable Upto 1 TB | ..."
    specs_el = card.find(class_=LIST_CLASSES["specs"])
    row["Specs"] = safe_text(specs_el)

    # ── Exchange offer ────────────────────────────────────────────────────────
    # Multiple HZ0E6r spans: "Upto", "₹20,750", "Off on Exchange" — find the ₹ one
    exchange_val = None
    for el in card.find_all(class_=LIST_CLASSES["exchange"]):
        t = el.get_text(strip=True)
        if "₹" in t:
            exchange_val = clean_price(t)
            break
    row["Exchange Offer (₹)"] = exchange_val

    # ── Offers / badges ───────────────────────────────────────────────────────
    # Deduplicate and filter noise labels like "Upto" / "Off on Exchange"
    _noise = {"Upto", "Off on Exchange", ""}
    badges = list({
        el.get_text(strip=True)
        for el in card.find_all(class_=LIST_CLASSES["badge"])
        if el.get_text(strip=True) not in _noise
    })
    row["Offers/Badges"] = " | ".join(badges) if badges else "N/A"

    # ── Warranty ──────────────────────────────────────────────────────────────
    row["Warranty"] = safe_text(card.find("li", class_=LIST_CLASSES["warranty"]))

    # ── Product URL ───────────────────────────────────────────────────────────
    row["Product URL"] = _extract_link(card)

    return row


# ── Grid layout parser ────────────────────────────────────────────────────────

def parse_grid_card(card) -> dict:
    """
    Extract available data fields from a single grid-layout product card.

    Grid cards show fewer fields than list cards — no specs, no exchange
    offers, no warranty, and only a combined review count (not split into
    ratings vs reviews).
    """
    row = {}

    # ── Name ──────────────────────────────────────────────────────────────────
    row["Product Name"] = safe_text(card.find(class_=GRID_CLASSES["name"]))

    # ── Prices ────────────────────────────────────────────────────────────────
    row["Price (₹)"] = clean_price(safe_text(card.find(class_=GRID_CLASSES["price"])))
    row["MRP (₹)"]   = clean_price(safe_text(card.find(class_=GRID_CLASSES["mrp"])))

    # ── Discount % ────────────────────────────────────────────────────────────
    disc_txt = safe_text(card.find(class_=GRID_CLASSES["discount"]))
    disc_num = re.sub(r"[^\d]", "", disc_txt)
    row["Discount (%)"] = int(disc_num) if disc_num else None

    # ── Rating ────────────────────────────────────────────────────────────────
    try:
        row["Rating"] = float(safe_text(card.find(class_=GRID_CLASSES["rating"])))
    except ValueError:
        row["Rating"] = None

    # ── Review count ──────────────────────────────────────────────────────────
    # Grid shows only "(2,029)" — treated as No. of Ratings
    row["No. of Ratings"] = parse_review_count(
        safe_text(card.find(class_=GRID_CLASSES["reviews"]))
    )
    row["No. of Reviews"] = None      # not shown separately in grid view

    # ── Fields not available in grid view ─────────────────────────────────────
    row["Specs"]             = "N/A"
    row["Exchange Offer (₹)"] = None
    row["Warranty"]          = "N/A"

    # ── Offers / badges ───────────────────────────────────────────────────────
    badges = list({
        el.get_text(strip=True)
        for el in card.find_all(class_=GRID_CLASSES["badge"])
        if el.get_text(strip=True)
    })
    row["Offers/Badges"] = " | ".join(badges) if badges else "N/A"

    # ── Product URL ───────────────────────────────────────────────────────────
    row["Product URL"] = _extract_link(card)

    return row


# ── Page-level entry point ────────────────────────────────────────────────────

def parse_page(html: str) -> tuple[list[dict], str]:
    """
    Parse all product cards from one page's raw HTML.

    Automatically detects whether the page uses list or grid layout.

    Args:
        html:  Raw HTML string from driver.page_source

    Returns:
        (rows, layout)
            rows   — list of product dicts ready to become DataFrame rows
            layout — "list" or "grid"
    """
    soup   = BeautifulSoup(html, "html.parser")
    layout = detect_layout(soup)

    if layout == "list":
        cards  = soup.find_all("div", class_=LIST_CLASSES["container"])
        # Only keep cards that actually have a product name
        rows   = [
            parse_list_card(c)
            for c in cards
            if c.find(class_=LIST_CLASSES["name"])
        ]
    else:
        cards  = soup.find_all("div", class_=GRID_CLASSES["container"])
        rows   = [
            parse_grid_card(c)
            for c in cards
            if c.find(class_=GRID_CLASSES["name"])
        ]

    # Tag each row with its layout so downstream code can distinguish them
    for row in rows:
        row["Layout"] = layout.capitalize()

    return rows, layout


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_link(card) -> str:
    """
    Find the product detail page URL inside a card.

    Prefers links whose href contains "/p/" (Flipkart product URL pattern).
    Falls back to the first <a> tag if no "/p/" link exists.
    Prepends the Flipkart base URL for relative hrefs.
    """
    link_el = card.find("a", href=lambda h: h and "/p/" in h)
    if not link_el:
        link_el = card.find("a", href=True)
    if not link_el:
        return "N/A"

    href = link_el["href"]
    return ("https://www.flipkart.com" + href) if href.startswith("/") else href
