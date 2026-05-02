# ─────────────────────────────────────────────────────────────────────────────
# dashboard.py — Visualisation dashboard (Plotly charts)
#
# One public function:
#   render_dashboard(df)  — renders all charts into the active Streamlit page
#
# All chart functions are private (_prefix) so only render_dashboard is the
# entry point from app.py.  Add new charts here without touching app.py.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from config import COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS


# ── Public entry point ────────────────────────────────────────────────────────

def render_dashboard(df: pd.DataFrame) -> None:
    """
    Render the full visualisation dashboard for *df*.

    Sections:
        • KPI summary row    (5 headline metrics)
        • Row 1: Price histogram  +  Rating histogram
        • Row 2: Price vs Rating scatter  +  Top 10 discounted (bar)
        • Row 3: Reviews vs Price scatter  +  Top 10 Value Score (bar)
        • Row 4: MRP vs Selling Price grouped bar (full width)
    """
    st.divider()
    st.header("📊 Visualisation Dashboard")

    _render_kpis(df)
    st.divider()

    c1, c2 = st.columns(2)
    with c1: _chart_price_distribution(df)
    with c2: _chart_rating_distribution(df)

    c3, c4 = st.columns(2)
    with c3: _chart_price_vs_rating(df)
    with c4: _chart_top_discounts(df)

    c5, c6 = st.columns(2)
    with c5: _chart_reviews_vs_price(df)
    with c6: _chart_top_value_score(df)

    _chart_mrp_vs_price(df)


# ── KPI strip ─────────────────────────────────────────────────────────────────

def _render_kpis(df: pd.DataFrame) -> None:
    """Five headline metric boxes."""
    numeric = df[df["Price (₹)"].notna()]
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Products Found",  len(df))
    col2.metric(
        "Avg Price",
        f"₹{numeric['Price (₹)'].mean():,.0f}" if not numeric.empty else "–",
    )
    col3.metric(
        "Avg Rating",
        f"{df['Rating'].dropna().mean():.2f}" if df["Rating"].notna().any() else "–",
    )
    col4.metric(
        "Avg Discount",
        f"{df['Discount (%)'].dropna().mean():.1f}%" if df["Discount (%)"].notna().any() else "–",
    )
    col5.metric(
        "Avg Savings",
        f"₹{df['Savings (₹)'].dropna().mean():,.0f}" if df["Savings (₹)"].notna().any() else "–",
    )


# ── Individual chart functions ────────────────────────────────────────────────

def _chart_price_distribution(df: pd.DataFrame) -> None:
    st.subheader("💰 Price Distribution")
    numeric = df[df["Price (₹)"].notna()]
    if numeric.empty:
        st.info("No price data available.")
        return
    fig = px.histogram(
        numeric, x="Price (₹)", nbins=20,
        color_discrete_sequence=[COLOR_PRIMARY],
        template="plotly_white",
    )
    fig.update_layout(bargap=0.1, showlegend=False, height=350)
    st.plotly_chart(fig, use_container_width=True)


def _chart_rating_distribution(df: pd.DataFrame) -> None:
    st.subheader("⭐ Rating Distribution")
    rated = df[df["Rating"].notna()]
    if rated.empty:
        st.info("No rating data available.")
        return
    fig = px.histogram(
        rated, x="Rating", nbins=15,
        color_discrete_sequence=[COLOR_SECONDARY],
        template="plotly_white",
    )
    fig.update_layout(bargap=0.1, showlegend=False, height=350)
    st.plotly_chart(fig, use_container_width=True)


def _chart_price_vs_rating(df: pd.DataFrame) -> None:
    st.subheader("🎯 Price vs Rating")
    scatter_df = df[df["Price (₹)"].notna() & df["Rating"].notna()].copy()
    if scatter_df.empty:
        st.info("Insufficient data for scatter plot.")
        return

    has_reviews  = scatter_df["No. of Ratings"].notna().any()
    has_discount = scatter_df["Discount (%)"].notna().any()

    fig = px.scatter(
        scatter_df,
        x="Price (₹)", y="Rating",
        size="No. of Ratings" if has_reviews  else None,
        color="Discount (%)"  if has_discount else None,
        hover_name="Product Name",
        color_continuous_scale="Blues",
        template="plotly_white",
        height=380,
    )
    fig.update_traces(marker=dict(opacity=0.8, line=dict(width=0.5, color="white")))
    st.plotly_chart(fig, use_container_width=True)


def _chart_top_discounts(df: pd.DataFrame) -> None:
    st.subheader("🏷️ Top 10 Discounted Products")
    disc_df = df[df["Discount (%)"].notna()].nlargest(10, "Discount (%)")
    if disc_df.empty:
        st.info("No discount data available.")
        return
    fig = px.bar(
        disc_df,
        x="Discount (%)",
        y=disc_df["Product Name"].str[:35],
        orientation="h",
        color="Discount (%)",
        color_continuous_scale="Blues",
        template="plotly_white",
        height=380,
    )
    fig.update_layout(yaxis_title="", showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)


def _chart_reviews_vs_price(df: pd.DataFrame) -> None:
    st.subheader("📣 Reviews vs Price")
    rev_df = df[df["No. of Ratings"].notna() & df["Price (₹)"].notna()]
    if rev_df.empty:
        st.info("No review data available.")
        return
    fig = px.scatter(
        rev_df,
        x="Price (₹)", y="No. of Ratings",
        hover_name="Product Name",
        color="Rating",
        color_continuous_scale="RdYlGn",
        template="plotly_white",
        height=350,
    )
    fig.update_traces(marker=dict(size=8, opacity=0.75))
    st.plotly_chart(fig, use_container_width=True)


def _chart_top_value_score(df: pd.DataFrame) -> None:
    st.subheader("🏆 Top 10 by Value Score")
    st.caption("Value Score = (Rating × No. of Ratings) / Price — higher = better bang-for-buck")
    vs_df = df[df["Value Score"].notna()].nlargest(10, "Value Score")
    if vs_df.empty:
        st.info("Insufficient data for Value Score.")
        return
    fig = px.bar(
        vs_df,
        x="Value Score",
        y=vs_df["Product Name"].str[:35],
        orientation="h",
        color="Value Score",
        color_continuous_scale="Greens",
        template="plotly_white",
        height=350,
    )
    fig.update_layout(yaxis_title="", showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)


def _chart_mrp_vs_price(df: pd.DataFrame) -> None:
    st.subheader("📉 Selling Price vs MRP — Top 15 Products")
    cmp_df = df[df["MRP (₹)"].notna() & df["Price (₹)"].notna()].head(15).copy()
    if cmp_df.empty:
        st.info("No MRP data available for comparison.")
        return

    short_names = cmp_df["Product Name"].str[:30]
    fig = go.Figure()
    fig.add_bar(name="MRP (₹)",           x=short_names, y=cmp_df["MRP (₹)"],   marker_color="#CBD5E1")
    fig.add_bar(name="Selling Price (₹)", x=short_names, y=cmp_df["Price (₹)"], marker_color=COLOR_PRIMARY)
    fig.update_layout(
        barmode="overlay",
        template="plotly_white",
        height=380,
        xaxis_tickangle=-30,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)
