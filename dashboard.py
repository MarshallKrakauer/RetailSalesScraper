import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Retail Sales", layout="wide")
st.title("US Retail Sales by Category")

CATEGORY_DESCRIPTIONS = {
    "Total": "All retail trade and food services combined.",
    "Retail Only": "All retail trade excluding food services and drinking places.",
    "Motor Vehicle & Parts Dealers": "New and used car dealers, RV dealers, motorcycle shops, and auto parts/tire stores.",
    "Auto Parts, Accessories & Tire Stores": "Stores selling auto parts, accessories, and tires — excludes new/used vehicle dealers.",
    "Furniture & Home Furnishing Stores": "Furniture, home furnishings, floor coverings, and window treatment stores.",
    "Electronics & Appliance Stores": "Household appliances, TVs, computers, cameras, and consumer electronics stores.",
    "Building Material & Garden Equipment": "Lumber yards, hardware stores, paint shops, and garden supply stores (e.g. Home Depot, Lowe's).",
    "Food & Beverage Stores": "Grocery stores, specialty food stores, beer/wine/liquor stores.",
    "Grocery Stores": "Supermarkets and other grocery stores selling a general line of food products.",
    "Health & Personal Care Stores": "Pharmacies, drugstores, optical goods, health food, and cosmetics stores.",
    "Gasoline Stations": "Establishments primarily retailing automotive fuels — may also sell convenience items.",
    "Clothing & Accessories Stores": "New clothing, shoes, jewelry, luggage, and accessory stores.",
    "Sporting Goods, Hobby, Book & Music": "Sporting goods, hobby supplies, toy stores, book stores, and musical instrument dealers.",
    "General Merchandise Stores": "Broad merchandise retailers including department stores, warehouse clubs (Costco, Target, Walmart).",
    "Department Stores": "Large stores organized into departments selling apparel, home goods, and general merchandise.",
    "Miscellaneous Store Retailers": "Florists, office supply, pet supply, art dealers, tobacco stores, and other specialty retailers.",
    "Nonstore Retailers": "Retailers with no fixed storefront — includes e-commerce, mail-order catalogs, vending machines, and door-to-door sales.",
    "Food Services & Drinking Places": "Restaurants, fast food, bars, cafeterias, food trucks, and caterers. Not traditional retail — included because Census surveys it alongside retail.",
}

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

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Trend", "All Categories", "E-Commerce", "MoM / YoY", "Volatility"])

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

    with tab4:
        raw = pd.read_csv("retail_sales_by_category.csv")
        raw = raw.sort_values("date").reset_index(drop=True)

        display_cats = ["Total", "Retail Only"] + individual_cols
        display_cats = [c for c in display_cats if c in raw.columns]

        for c in display_cats:
            raw[c] = pd.to_numeric(raw[c], errors="coerce")

        months = raw["date"].tolist()
        selected_month = st.selectbox("Month", months[::-1], index=0)
        idx = raw[raw["date"] == selected_month].index[0]

        current = raw.iloc[idx]
        prev_month = raw.iloc[idx - 1] if idx >= 1 else None
        prev_year = raw.iloc[idx - 12] if idx >= 12 else None

        rows = []
        for c in display_cats:
            mom = ((current[c] - prev_month[c]) / prev_month[c] * 100) if prev_month is not None else None
            yoy = ((current[c] - prev_year[c]) / prev_year[c] * 100) if prev_year is not None else None
            rows.append({"Category": c, "MoM %": mom, "YoY %": yoy})

        summary = pd.DataFrame(rows)

        summary["Description"] = summary["Category"].map(CATEGORY_DESCRIPTIONS).fillna("")

        def color_pct(val):
            if pd.isna(val):
                return ""
            return "background-color: #1a6fb5; color: white" if val >= 0 else "background-color: #d4641a; color: white"

        styled = (
            summary.style
            .map(color_pct, subset=["MoM %", "YoY %"])
            .format({"MoM %": "{:+.0f}%", "YoY %": "{:+.0f}%"}, na_rep="—")
        )

        st.dataframe(
            styled,
            use_container_width=True,
            height=600,
            hide_index=True,
            column_config={
                "Description": st.column_config.TextColumn("Description", width="large"),
            },
        )

    with tab5:
        raw_v = pd.read_csv("retail_sales_by_category.csv")
        raw_v = raw_v.sort_values("date").reset_index(drop=True)

        vol_cats = ["Total", "Retail Only"] + individual_cols
        vol_cats = [c for c in vol_cats if c in raw_v.columns]

        for c in vol_cats:
            raw_v[c] = pd.to_numeric(raw_v[c], errors="coerce")

        raw_v["date"] = pd.to_datetime(raw_v["date"])
        min_y = raw_v["date"].dt.year.min()
        max_y = raw_v["date"].dt.year.max()
        v_start, v_end = st.slider("Year Range", min_y, max_y, (min_y, max_y), key="vol_slider")
        raw_v = raw_v[(raw_v["date"].dt.year >= v_start) & (raw_v["date"].dt.year <= v_end)]

        rows = []
        for c in vol_cats:
            s = raw_v[c].dropna()
            mom_std = (s.pct_change() * 100).std()
            rows.append({"Category": c, "MoM Std Dev %": mom_std})

        vol_df = pd.DataFrame(rows)

        def gradient_color(col_series):
            mn, mx = col_series.min(), col_series.max()
            styles = []
            for val in col_series:
                if pd.isna(val) or mx == mn:
                    styles.append("")
                else:
                    t = (val - mn) / (mx - mn)  # 0 = least volatile, 1 = most volatile
                    r = int(26 + (1 - t) * (173 - 26))
                    g = int(111 + (1 - t) * (216 - 111))
                    b = int(181 + (1 - t) * (230 - 181))
                    text = "white" if t > 0.5 else "#333"
                    styles.append(f"background-color: rgb({r},{g},{b}); color: {text}")
            return styles

        styled_vol = (
            vol_df.style
            .apply(gradient_color, subset=["MoM Std Dev %"])
            .format({"MoM Std Dev %": "{:.1f}%"}, na_rep="—")
        )

        st.caption("Std dev of month-over-month % changes. Darker blue = more volatile.")
        st.dataframe(styled_vol, use_container_width=True, height=600, hide_index=True)

except FileNotFoundError:
    st.error("retail_sales_by_category.csv not found. Run retail_sales_scraper.py first.")
