# ─────────────────────────────────────────────────────────────────────────────
# utils.py — Pure helper / utility functions
#
# No Streamlit, no Selenium, no Plotly.
# These functions are imported by every other module that needs them.
# ─────────────────────────────────────────────────────────────────────────────

import re


def clean_price(text: str) -> float | None:
    """
    Strip ₹ symbol, commas, and whitespace from a price string and return
    a float.  Returns None if the input is empty, "N/A", or not numeric.

    Examples:
        "₹22,999"  →  22999.0
        "₹1,199"   →  1199.0
        "N/A"      →  None
    """
    if not text or text.strip() in ("", "N/A"):
        return None
    cleaned = re.sub(r"[₹,\s]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_review_count(text: str) -> int | None:
    """
    Extract the first continuous run of digits from a string.

    Handles both grid format "(2,029)" and list format "1,35,727 Ratings".
    Returns None if no digits are found.

    Examples:
        "(2,029)"         →  2029
        "1,35,727 Ratings"→  135727
        "N/A"             →  None
    """
    if not text or text.strip() in ("", "N/A"):
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def safe_text(element, default: str = "N/A") -> str:
    """
    Return stripped inner text of a BeautifulSoup element, or *default* if
    the element is None.
    """
    return element.get_text(strip=True) if element else default


def compute_value_score(rating: float | None,
                        num_ratings: int | None,
                        price: float | None) -> float | None:
    """
    A simple bang-for-buck metric:

        Value Score = (Rating × No. of Ratings) / Price

    Higher is better.  Returns None if any input is missing or price is zero.
    The result is rounded to 4 decimal places.
    """
    if rating is None or num_ratings is None or not price:
        return None
    return round((rating * num_ratings) / price, 4)


def sanitize_filename(text: str) -> str:
    """
    Replace all non-word characters with underscores so a search query can
    safely be used as part of a filename.

    Example:
        "laptop bags & cases"  →  "laptop_bags___cases"
    """
    return re.sub(r"[^\w]", "_", text)


def rating_tier(rating: float) -> str:
    """
    Map a numeric rating to a human-readable tier label.

    Examples:
        4.6  →  "⭐ Excellent (4.5+)"
        4.2  →  "👍 Good (4.0–4.5)"
        3.7  →  "😐 Average (3.5–4.0)"
        3.1  →  "👎 Below Average (<3.5)"
    """
    if rating >= 4.5:
        return "⭐ Excellent (4.5+)"
    if rating >= 4.0:
        return "👍 Good (4.0–4.5)"
    if rating >= 3.5:
        return "😐 Average (3.5–4.0)"
    return "👎 Below Average (<3.5)"
