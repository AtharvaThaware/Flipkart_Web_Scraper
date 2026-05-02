# ─────────────────────────────────────────────────────────────────────────────
# config.py — Central configuration for the Flipkart Scraper
#
# This is the ONLY file you need to edit when Flipkart rotates its CSS class
# names (which it does periodically). Every other module imports from here.
# ─────────────────────────────────────────────────────────────────────────────

# ── App metadata ──────────────────────────────────────────────────────────────
APP_TITLE   = "Flipkart Web Scraper Pro"
APP_ICON    = "🛒"
APP_CAPTION = "Dual-layout scraper with visualization dashboard & email export"

# ── Scraper defaults ──────────────────────────────────────────────────────────
DEFAULT_PAGES    = 2
MAX_PAGES        = 20
PAGE_LOAD_DELAY  = 1.5        # seconds to wait between pages
POPUP_WAIT_SECS  = 4          # seconds to wait for login popup
CARD_WAIT_SECS   = 10         # seconds to wait for product cards to appear

# ── Chrome options ─────────────────────────────────────────────────────────
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
CHROME_WINDOW_SIZE = "1920,1080"

# ── Export formats ─────────────────────────────────────────────────────────
EXPORT_FORMATS = ["Excel", "CSV", "JSON", "SQL"]

# ── Email Credentials ────────────────────────────────────────────────────────
from dotenv import load_dotenv
import os
load_dotenv()
SENDER_EMAIL = os.getenv("EMAIL_USER")
APP_PASSWORD = os.getenv("EMAIL_PASS")
# ── Email (SMTP) ──────────────────────────────────────────────────────────────
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# ── Colour palette (used in charts & UI) ─────────────────────────────────────
COLOR_PRIMARY   = "#2874F0"   # Flipkart blue
COLOR_SECONDARY = "#F59E0B"   # Amber
COLOR_SUCCESS   = "#059669"   # Green
COLOR_DANGER    = "#EF4444"   # Red
COLOR_NEUTRAL   = "#94A3B8"   # Slate

# ── Flipkart CSS class maps ───────────────────────────────────────────────────
# Last verified: May 2025
# If scraping breaks, open a Flipkart search page, right-click a product card
# → Inspect, and update the class names below to match the live HTML.

LIST_CLASSES = {
    # The outer <div> that wraps one complete list-view product card
    "container": "ZFwe0M",

    # Product fields
    "name":      "RG5Slk",   # Full product name string
    "price":     "hZ3P6w",   # Selling / discounted price  e.g. "₹22,999"
    "mrp":       "kRYCnD",   # Original MRP (strikethrough) e.g. "₹24,999"
    "discount":  "HQe8jr",   # Discount label              e.g. "8% off"
    "rating":    "MKiFS6",   # Star rating number          e.g. "4.4"

    # Reviews text contains BOTH ratings count AND reviews count:
    # e.g. "4.41,35,727 Ratings&6,988 Reviews"
    "reviews":   "a7saXW",

    # Spec bullet block  e.g. "8 GB RAM | 128 GB ROM | ..."
    "specs":     "CMXw7N",

    # Exchange offer value  e.g. "₹20,750"  (appears in multiple HZ0E6r spans)
    "exchange":  "HZ0E6r",

    # Offer / deal badge  e.g. "Bank Offer", "Super Deals"
    "badge":     "MaiFhH",

    # Warranty text inside <li>  e.g. "1 Year Warranty on Handset..."
    "warranty":  "DTBslk",
}

GRID_CLASSES = {
    # The outer <div> that wraps one complete grid-view product card
    "container": "RGLWAk",

    # Product fields
    "name":      "pIpigb",   # Product name (truncated in grid view)
    "price":     "hZ3P6w",   # Selling price  — same class as list
    "mrp":       "kRYCnD",   # Original MRP   — same class as list
    "discount":  "HQe8jr",   # Discount label — same class as list
    "rating":    "MKiFS6",   # Star rating    — same class as list

    # In grid view only the review COUNT is shown  e.g. "(2,029)"
    # (no separate ratings count)
    "reviews":   "PvbNMB",

    # Offer badge — same class as list
    "badge":     "MaiFhH",

    # Grid cards do NOT show specs, exchange offers, or warranty
}

# ── Column display order in the data table ───────────────────────────────────
COLUMNS_ORDER = [
    "Product Name",
    "Price (₹)",
    "MRP (₹)",
    "Discount (%)",
    "Savings (₹)",
    "Rating",
    "No. of Ratings",
    "No. of Reviews",
    "Value Score",
    "Specs",
    "Exchange Offer (₹)",
    "Offers/Badges",
    "Warranty",
    "Layout",
    "Product URL",
]

# ── Price segment bins used in the Consumer Insights dashboard ───────────────
PRICE_BINS   = [0, 500, 1_000, 2_000, 5_000, 10_000, 50_000, float("inf")]
PRICE_LABELS = ["<₹500", "₹500–1K", "₹1K–2K", "₹2K–5K", "₹5K–10K", "₹10K–50K", "₹50K+"]
