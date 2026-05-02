# ─────────────────────────────────────────────────────────────────────────────
# insights.py — Consumer Research Insights panel
#
# One public function:
#   render_consumer_insights(df)  — renders 4-tab insights panel
#
# Tabs:
#   1. 🥇 Best Buys       — highest rated, best value, biggest savings
#   2. 💸 Price Segments  — interactive budget slider + donut chart
#   3. ⭐ Rating Analysis  — tier breakdown, social proof, price-rating correlation
#   4. 📦 Deals & Offers  — badge frequency, exchange offer stats, flash deals
# ─────────────────────────────────────────────────────────────────────────────

from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

from config import (
    COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS, COLOR_DANGER, COLOR_NEUTRAL,
    PRICE_BINS, PRICE_LABELS,
)
from utils import rating_tier


# ── Public entry point ────────────────────────────────────────────────────────

def render_consumer_insights(df: pd.DataFrame) -> None:
    """
    Render the 4-tab Consumer Research Insights section for *df*.

    Designed to be called after render_dashboard() in app.py.
    """
    st.divider()
    st.header("🔬 Consumer Research Insights")
    st.caption("Actionable buying guidance derived from scraped product data.")

    if df.empty:
        st.warning("No data to analyse.")
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "🥇 Best Buys",
        "💸 Price Segments",
        "⭐ Rating Analysis",
        "📦 Deals & Offers",
    ])

    with tab1: _tab_best_buys(df)
    with tab2: _tab_price_segments(df)
    with tab3: _tab_rating_analysis(df)
    with tab4: _tab_deals_and_offers(df)


# ── Tab 1 — Best Buys ────────────────────────────────────────────────────────

def _tab_best_buys(df: pd.DataFrame) -> None:
    st.subheader("Best Products to Buy Right Now")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**🏅 Highest Rated** *(min 100 ratings)*")
        top_rated = (
            df[df["No. of Ratings"].fillna(0) >= 100]
            .sort_values("Rating", ascending=False)
            .head(5)[["Product Name", "Price (₹)", "Rating", "No. of Ratings", "Discount (%)"]]
        )
        if not top_rated.empty:
            st.dataframe(top_rated.reset_index(drop=True), use_container_width=True)
        else:
            st.info("Not enough rated products.")

    with col_b:
        st.markdown("**💎 Best Value** *(Value Score)*")
        top_value = (
            df[df["Value Score"].notna()]
            .sort_values("Value Score", ascending=False)
            .head(5)[["Product Name", "Price (₹)", "Rating", "Value Score"]]
        )
        if not top_value.empty:
            st.dataframe(top_value.reset_index(drop=True), use_container_width=True)
        else:
            st.info("Insufficient data.")

    st.markdown("**🔥 Biggest Savings** *(₹ saved vs MRP)*")
    top_savings = (
        df[df["Savings (₹)"].fillna(0) > 0]
        .sort_values("Savings (₹)", ascending=False)
        .head(5)[["Product Name", "Price (₹)", "MRP (₹)", "Savings (₹)", "Discount (%)"]]
    )
    if not top_savings.empty:
        st.dataframe(top_savings.reset_index(drop=True), use_container_width=True)
    else:
        st.info("No MRP data found — savings cannot be calculated.")


# ── Tab 2 — Price Segments ────────────────────────────────────────────────────

def _tab_price_segments(df: pd.DataFrame) -> None:
    st.subheader("Products by Budget Range")
    price_df = df[df["Price (₹)"].notna()].copy()

    if price_df.empty:
        st.info("No price data available.")
        return

    min_p = int(price_df["Price (₹)"].min())
    max_p = int(price_df["Price (₹)"].max())

    budget = st.slider(
        "Your Budget (₹)",
        min_value=min_p,
        max_value=max_p,
        value=(min_p, min_p + (max_p - min_p) // 2),
    )

    filtered = (
        price_df[price_df["Price (₹)"].between(budget[0], budget[1])]
        .sort_values("Rating", ascending=False)
    )
    st.write(f"**{len(filtered)} products** in ₹{budget[0]:,} – ₹{budget[1]:,} range")

    if not filtered.empty:
        cols_show = [c for c in [
            "Product Name", "Price (₹)", "Rating",
            "Discount (%)", "No. of Ratings", "Product URL",
        ] if c in filtered.columns]
        st.dataframe(filtered[cols_show].reset_index(drop=True), use_container_width=True)

    # Segment donut
    price_df["Segment"] = pd.cut(price_df["Price (₹)"], bins=PRICE_BINS, labels=PRICE_LABELS)
    seg_counts = price_df["Segment"].value_counts().sort_index()
    if not seg_counts.empty:
        fig = px.pie(
            values=seg_counts.values,
            names=seg_counts.index,
            hole=0.45,
            template="plotly_white",
            color_discrete_sequence=px.colors.sequential.Blues_r,
        )
        fig.update_layout(title="Product Distribution by Price Segment", height=350)
        st.plotly_chart(fig, use_container_width=True)


# ── Tab 3 — Rating Analysis ───────────────────────────────────────────────────

def _tab_rating_analysis(df: pd.DataFrame) -> None:
    st.subheader("What Ratings Tell You")
    rated = df[df["Rating"].notna() & df["No. of Ratings"].notna()].copy()

    if rated.empty:
        st.info("No rating data available.")
        return

    # Rating tier breakdown
    rated["Tier"] = rated["Rating"].apply(rating_tier)
    tier_counts   = rated["Tier"].value_counts()

    c1, c2 = st.columns([1, 2])
    with c1:
        st.dataframe(tier_counts.rename("Count").reset_index(), use_container_width=True)
    with c2:
        fig = px.pie(
            values=tier_counts.values,
            names=tier_counts.index,
            hole=0.4,
            template="plotly_white",
            color_discrete_sequence=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_NEUTRAL, COLOR_DANGER],
        )
        fig.update_layout(height=280, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    # Social proof table
    st.markdown("**Products with Most Social Proof** *(Rating × No. of Ratings)*")
    rated["Social Proof"] = (rated["Rating"] * rated["No. of Ratings"]).round(0).astype(int)
    social = rated.nlargest(8, "Social Proof")[
        ["Product Name", "Price (₹)", "Rating", "No. of Ratings", "Social Proof"]
    ]
    st.dataframe(social.reset_index(drop=True), use_container_width=True)

    # Price-rating correlation callout
    corr = rated["Price (₹)"].corr(rated["Rating"])
    if abs(corr) > 0.3:
        direction = "positively" if corr > 0 else "negatively"
        note = "more expensive ≈ better rated" if corr > 0 else "price does not guarantee quality here"
        st.info(f"📊 Price & Rating are **{direction} correlated** (r = {corr:.2f}) — {note}.")
    else:
        st.info(
            f"📊 Price & Rating show **weak correlation** (r = {corr:.2f}) — "
            f"good deals exist across all price points."
        )


# ── Tab 4 — Deals & Offers ────────────────────────────────────────────────────

def _tab_deals_and_offers(df: pd.DataFrame) -> None:
    st.subheader("Active Deals & Best Discount Windows")

    d1, d2 = st.columns(2)

    with d1:
        st.markdown("**🎁 Offer Badges Found**")
        all_badges = []
        for b in df["Offers/Badges"].dropna():
            all_badges.extend([x.strip() for x in b.split("|") if x.strip()])

        badge_counts = Counter(all_badges)
        if badge_counts:
            badge_df = (
                pd.DataFrame(badge_counts.items(), columns=["Badge", "Count"])
                .sort_values("Count", ascending=False)
            )
            fig = px.bar(
                badge_df, x="Count", y="Badge",
                orientation="h",
                color="Count",
                color_continuous_scale="Blues",
                template="plotly_white",
                height=280,
            )
            fig.update_layout(yaxis_title="", coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No badge / offer data found.")

    with d2:
        st.markdown("**💱 Exchange Offer Analysis**")
        exc_df = df[df["Exchange Offer (₹)"].notna()]
        if not exc_df.empty:
            st.metric("Avg Exchange Value", f"₹{exc_df['Exchange Offer (₹)'].mean():,.0f}")
            st.metric("Max Exchange Value", f"₹{exc_df['Exchange Offer (₹)'].max():,.0f}")
            fig = px.histogram(
                exc_df, x="Exchange Offer (₹)",
                color_discrete_sequence=[COLOR_SUCCESS],
                template="plotly_white",
                height=200,
            )
            fig.update_layout(bargap=0.1, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No exchange offer data (only available in list layout).")

    st.markdown("**⚡ Flash / Hot / Super Deals**")
    deal_df = df[
        df["Offers/Badges"].str.contains(
            "Deal|Flash|Hot|Super|Limited", case=False, na=False
        )
    ]
    if not deal_df.empty:
        cols = [c for c in [
            "Product Name", "Price (₹)", "Rating",
            "Discount (%)", "Offers/Badges", "Product URL",
        ] if c in deal_df.columns]
        st.dataframe(deal_df[cols].reset_index(drop=True), use_container_width=True)
    else:
        st.info("No special deal badges found in this search.")
