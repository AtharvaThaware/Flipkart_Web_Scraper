# ─────────────────────────────────────────────────────────────────────────────
# app.py — Streamlit entry point
#
# This file is intentionally thin.  It only:
#   1. Configures the Streamlit page
#   2. Renders the sidebar (inputs)
#   3. Initialises session state
#   4. Calls the scraper when the user clicks "Start Scraping"
#   5. Renders the data table, download button, email panel
#   6. Delegates charts → dashboard.py
#   7. Delegates insights → insights.py
#
# Run with:
#   streamlit run app.py
# ─────────────────────────────────────────────────────────────────────────────

import smtplib
import streamlit as st

from config     import (
    APP_TITLE, APP_ICON, APP_CAPTION,
    EXPORT_FORMATS, DEFAULT_PAGES, MAX_PAGES,
    COLUMNS_ORDER, SENDER_EMAIL, APP_PASSWORD,
)
from scraper    import scrape_flipkart
from exporter   import build_export, send_email_with_attachment
from dashboard  import render_dashboard
from insights   import render_consumer_insights


# ─────────────────────────────────────────────────────────────────────────────
# Page config (must be the very first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(f"""
## {APP_ICON} {APP_TITLE}

{APP_CAPTION}

🔍 **Scrape real-time Flipkart data**  
📊 **Analyze trends & insights instantly**  
📤 **Export or email results in one click**
""")

st.divider()

st.markdown("""
<style>
    .metric-card {
        background: #f0f7ff;
        border-left: 4px solid #2874F0;
        padding: 1rem;
        border-radius: 6px;
        margin-bottom: 0.5rem;
    }
    .stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.title(f"{APP_ICON} {APP_TITLE}")
st.caption(APP_CAPTION)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — Scraping options
# ─────────────────────────────────────────────────────────────────────────────
st.sidebar.header("🔍 Scraping Options")

search_query    = st.sidebar.text_input("Product Name", placeholder="e.g. earbuds, laptop...")
pages_to_scrape = st.sidebar.slider("Pages to Scrape", 1, MAX_PAGES, DEFAULT_PAGES)
file_type       = st.sidebar.selectbox("Export Format", EXPORT_FORMATS)
start_scraping  = st.sidebar.button("🚀 Start Scraping", use_container_width=True)

# ── Email settings ────────────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.header("📧 Email Settings")

# sender_email   = st.sidebar.text_input("Your Gmail Address")
# app_password   = st.sidebar.text_input(
#     "App Password", type="password",
#     help="Generate at myaccount.google.com → Security → App Passwords",
# )
receiver_email = st.sidebar.text_input("Recipient Email")
subject        = st.sidebar.text_input("Subject", value="Flipkart Scrape Results")
message_body   = st.sidebar.text_area(
    "Message Body",
    value="Hi,\n\nPlease find the scraped Flipkart data attached.",
)


# ─────────────────────────────────────────────────────────────────────────────
# Session state — persists data across Streamlit reruns
# ─────────────────────────────────────────────────────────────────────────────
for key in ("df", "export_bytes", "export_filename", "export_mime"):
    if key not in st.session_state:
        st.session_state[key] = None


# ─────────────────────────────────────────────────────────────────────────────
# Scraping trigger
# ─────────────────────────────────────────────────────────────────────────────
if start_scraping:
    if not search_query.strip():
        st.error("⚠️ Please enter a product name before scraping.")
    else:
        with st.spinner("🔍 Opening browser and scraping Flipkart…"):
            df, layouts = scrape_flipkart(search_query.strip(), pages_to_scrape)

        if df.empty:
            st.error("❌ No products found. Try a different query or increase pages.")
        else:
            st.session_state.df = df

            layout_str = " + ".join(sorted(layouts))
            st.success(
                f"✅ Scraped **{len(df)} products** "
                f"({layout_str} layout{'s' if len(layouts) > 1 else ''} detected)"
            )

            # Build export once and store in session so reruns don't re-compute
            export_bytes, export_filename, export_mime = build_export(
                df, file_type, search_query.strip()
            )
            st.session_state.export_bytes    = export_bytes
            st.session_state.export_filename = export_filename
            st.session_state.export_mime     = export_mime


# ─────────────────────────────────────────────────────────────────────────────
# Results — data table, download, email
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.df is not None:
    df = st.session_state.df

    # ── Data table ────────────────────────────────────────────────────────────
    st.subheader(f"📋 Product Data ({len(df)} items)")
    ordered_cols = [c for c in COLUMNS_ORDER if c in df.columns]
    st.dataframe(df[ordered_cols], use_container_width=True, height=350)

    # ── Download + Email row ──────────────────────────────────────────────────
    col_dl, col_mail = st.columns([1, 2])

    with col_dl:
        st.download_button(
            label=f"⬇️ Download {file_type}",
            data=st.session_state.export_bytes,
            file_name=st.session_state.export_filename,
            mime=st.session_state.export_mime or "application/octet-stream",
            use_container_width=True,
        )

    with col_mail:
        with st.expander("📧 Send via Email"):
            if st.button("Send Email with Attachment", use_container_width=True):
                if not all([SENDER_EMAIL, APP_PASSWORD, receiver_email]):
                    st.warning("⚠️ Fill in all three email fields in the sidebar first.")
                else:
                    try:
                        with st.spinner("Sending email…"):
                            send_email_with_attachment(
                                from_addr=SENDER_EMAIL,
                                password=APP_PASSWORD,
                                to_addr=receiver_email,
                                subj=subject or f"Flipkart: {search_query}",
                                body=message_body,
                                attachment_bytes=st.session_state.export_bytes,
                                attachment_name=st.session_state.export_filename,
                            )
                        st.success("✅ Email sent successfully!")

                    except smtplib.SMTPAuthenticationError:
                        st.error(
                            "❌ Authentication failed. Make sure you are using a "
                            "**Gmail App Password** (not your regular Gmail password). "
                            "Generate one at: myaccount.google.com → Security → App Passwords"
                        )
                    except Exception as e:
                        st.error(f"❌ Email failed: {e}")

    # ── Visualisation dashboard ───────────────────────────────────────────────
    render_dashboard(df)

    # ── Consumer research insights ────────────────────────────────────────────
    render_consumer_insights(df)

st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
### 👨‍💻 About This Project

This is a **Flipkart Web Scraper & Analytics Dashboard** that extracts real-time product data and provides actionable insights using interactive visualizations.

---

### 🚀 Features
- Multi-page scraping using Selenium  
- Data cleaning & transformation with Pandas  
- Interactive dashboards with Plotly  
- Export to Excel, CSV, JSON, SQL  
- Email integration  

---

### 📬 Contact Me
**Atharva Thaware**  
- 🔗 LinkedIn: https://www.linkedin.com/in/atharva-thaware-aa7794250/  
- 💻 GitHub: https://github.com/AtharvaThaware 

---

### 📂 Source Code
👉 https://github.com/AtharvaThaware/Flipkart-Web-Scraper

---

### 🛠 Tech Stack
Python • Selenium • Streamlit • Pandas • Plotly
""")
