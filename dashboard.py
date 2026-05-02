import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Retail Sales", layout="wide")
st.title("US Retail Sales by Category")

AGGREGATE_COLS = [
    "Total Retail & Food Services",
    "Retail Only (excl. Food Services)",
    "Total excl. Motor Vehicles",
    "Total excl. Motor Vehicles & Gas",
    "Total excl. Gasoline",
    "Retail Trade (44+45)",
    "Retail Trade & Food Services",
]

try:
    df = pd.read_csv("retail_sales_by_category.csv")
    df = df.sort_values("date", ascending=False).reset_index(drop=True)
    num_cols = [c for c in df.columns if c != "date"]

    hide = {"Total Retail & Food Services", "Retail Only (excl. Food Services)"}
    individual_cols = [c for c in num_cols if c not in AGGREGATE_COLS and c not in ("Total", "Retail Only")]
    visible_aggregates = [c for c in AGGREGATE_COLS if c not in hide]

    dropdown_options = (
        ["Total", "Retail Only"]
        + visible_aggregates
        + individual_cols
    )

    tab1, tab2, tab3 = st.tabs(["Trend", "All Categories", "E-Commerce"])

    with tab1:
        selection = st.selectbox("Category", dropdown_options)

        cols_to_plot = [selection]

        trend = df[["date"] + [c for c in cols_to_plot if c in df.columns]].copy()
        trend = trend.sort_values("date").reset_index(drop=True)
        for c in cols_to_plot:
            if c in trend.columns:
                trend[c] = pd.to_numeric(trend[c], errors="coerce")
        trend["date"] = pd.to_datetime(trend["date"])

        valid_cols = [c for c in cols_to_plot if c in trend.columns]
        trend["Sales"] = trend[valid_cols].sum(axis=1)
        trend["Sales_B"] = trend["Sales"] / 1000
        trend["1Y Ago_B"] = trend["Sales_B"].shift(12)

        min_year, max_year = trend["date"].dt.year.min(), trend["date"].dt.year.max()
        default_start = max(min_year, 2021)
        start_year, end_year = st.slider("Year Range", min_year, max_year, (default_start, max_year))
        trend = trend[(trend["date"].dt.year >= start_year) & (trend["date"].dt.year <= end_year)]

        def label(v):
            if pd.isna(v):
                return ""
            return f"${v/1000:.1f}B" if v >= 1000 else f"${v:.0f}M"

        trend["3M Avg_B"] = trend["Sales_B"].rolling(3, min_periods=1).mean()
        trend["Label"] = trend["Sales"].map(label)
        trend["Avg Label"] = (trend["3M Avg_B"] * 1000).map(label)
        trend["1Y Ago Label"] = (trend["1Y Ago_B"] * 1000).map(label)

        nearest = alt.selection_point(nearest=True, on="mouseover", fields=["date"], empty=False)
        base = alt.Chart(trend).encode(x=alt.X("date:T", title="Date"))

        actual_chart = base.mark_line(opacity=0.3).encode(
            y=alt.Y("Sales_B:Q", title="Sales ($B)", axis=alt.Axis(format="$.1f")),
        )

        avg_chart = base.mark_line(strokeWidth=2.5).encode(
            y=alt.Y("3M Avg_B:Q"),
        )

        one_year_ago = base.mark_line(strokeWidth=1.5, color="red", strokeDash=[6, 3]).encode(
            y=alt.Y("1Y Ago_B:Q"),
        ).transform_filter(alt.datum["1Y Ago_B"] != None)

        selectors = base.mark_point(size=200).encode(
            opacity=alt.value(0),
            tooltip=[
                alt.Tooltip("date:T", format="%Y-%m", title="Date"),
                alt.Tooltip("Label:N", title="Sales"),
                alt.Tooltip("Avg Label:N", title="3M Avg"),
                alt.Tooltip("1Y Ago Label:N", title="1Y Ago"),
            ],
        ).add_params(nearest)

        rule = base.mark_rule(color="gray", strokeDash=[4, 4]).encode(
            x="date:T",
        ).transform_filter(nearest)

        st.altair_chart(
            alt.layer(actual_chart, avg_chart, one_year_ago, selectors, rule).properties(height=500).interactive(),
            use_container_width=True,
        )

    with tab2:
        def fmt(v):
            if pd.isna(v):
                return ""
            return f"${v/1000:.1f}B" if v >= 1000 else f"${v:.0f}M"

        display = df.copy()
        display[num_cols] = display[num_cols].map(fmt)
        st.dataframe(display, use_container_width=True, height=700)

    with tab3:
        try:
            ec = pd.read_csv("ecommerce_sales.csv")
            ec["date"] = pd.to_datetime(ec["date"], format="%Y-%m")
            col = "Electronic Shopping & Mail-Order ($M)"
            ec["Sales_B"] = ec[col] / 1000
            ec["1Y Ago_B"] = ec["Sales_B"].shift(12)

            min_y, max_y = ec["date"].dt.year.min(), ec["date"].dt.year.max()
            default_start_y = max(min_y, 2021)
            start_y, end_y = st.slider("Year Range", min_y, max_y, (default_start_y, max_y), key="ec_slider")
            ec = ec[(ec["date"].dt.year >= start_y) & (ec["date"].dt.year <= end_y)]

            ec["3M Avg_B"] = ec["Sales_B"].rolling(3, min_periods=1).mean()

            def ec_label(v):
                if pd.isna(v): return ""
                return f"${v/1000:.1f}B" if v >= 1000 else f"${v:.0f}M"

            ec["Label"] = ec[col].map(ec_label)
            ec["Avg Label"] = (ec["3M Avg_B"] * 1000).map(ec_label)
            ec["1Y Ago Label"] = (ec["1Y Ago_B"] * 1000).map(ec_label)

            ec_nearest = alt.selection_point(nearest=True, on="mouseover", fields=["date"], empty=False)
            base = alt.Chart(ec).encode(x=alt.X("date:T", title="Date"))

            actual = base.mark_line(opacity=0.3).encode(
                y=alt.Y("Sales_B:Q", title="Sales ($B)", axis=alt.Axis(format="$.1f")),
            )
            avg = base.mark_line(strokeWidth=2.5).encode(y=alt.Y("3M Avg_B:Q"))
            ec_1y = base.mark_line(strokeWidth=1.5, color="red", strokeDash=[6, 3]).encode(
                y=alt.Y("1Y Ago_B:Q"),
            ).transform_filter(alt.datum["1Y Ago_B"] != None)
            ec_selectors = base.mark_point(size=200).encode(
                opacity=alt.value(0),
                tooltip=[
                    alt.Tooltip("date:T", format="%Y-%m", title="Date"),
                    alt.Tooltip("Label:N", title="Sales"),
                    alt.Tooltip("Avg Label:N", title="3M Avg"),
                    alt.Tooltip("1Y Ago Label:N", title="1Y Ago"),
                ],
            ).add_params(ec_nearest)
            ec_rule = base.mark_rule(color="gray", strokeDash=[4, 4]).encode(
                x="date:T",
            ).transform_filter(ec_nearest)

            st.altair_chart(
                alt.layer(actual, avg, ec_1y, ec_selectors, ec_rule).properties(height=500).interactive(),
                use_container_width=True,
            )
            st.caption("Source: Census Bureau MRTS, NAICS 4541 — Electronic Shopping & Mail-Order Houses")
        except FileNotFoundError:
            st.error("ecommerce_sales.csv not found. Run retail_sales_scraper.py first.")

except FileNotFoundError:
    st.error("retail_sales_by_category.csv not found. Run retail_sales_scraper.py first.")
