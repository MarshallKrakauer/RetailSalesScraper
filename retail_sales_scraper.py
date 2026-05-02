"""
Scrapes US Census Bureau Advance Monthly Retail Trade Survey (MARTS) data.
Pulls total sales by category from 1992 to present and saves to CSV.
"""

import requests
import pandas as pd

BASE_URL = "https://api.census.gov/data/timeseries/eits/marts"

CATEGORY_NAMES = {
    "441": "Motor Vehicle & Parts Dealers",
    "442": "Furniture & Home Furnishing Stores",
    "443": "Electronics & Appliance Stores",
    "444": "Building Material & Garden Equipment",
    "445": "Food & Beverage Stores",
    "446": "Health & Personal Care Stores",
    "447": "Gasoline Stations",
    "448": "Clothing & Accessories Stores",
    "451": "Sporting Goods, Hobby, Book & Music",
    "452": "General Merchandise Stores",
    "453": "Miscellaneous Store Retailers",
    "454": "Nonstore Retailers",
    "722": "Food Services & Drinking Places",
    "44X45": "Total Retail Trade",
    "44X45722": "Total Retail Trade & Food Services",
}

START_YEAR = 1992


def fetch_retail_data(seasonally_adjusted=False) -> pd.DataFrame:
    adj_flag = "yes" if seasonally_adjusted else "no"

    params = {
        "get": "cell_value,error_data,category_code,time_slot_id",
        "for": "us:*",
        "time": f"from {START_YEAR}",
        "seasonally_adj": adj_flag,
        "geo_level_code": "US",
    }

    print(f"Fetching {'seasonally adjusted' if seasonally_adjusted else 'unadjusted'} data from Census Bureau MARTS API...")
    response = requests.get(BASE_URL, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()
    headers = data[0]
    rows = data[1:]

    df = pd.DataFrame(rows, columns=headers)
    return df


def clean_and_pivot(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={
        "cell_value": "sales_millions",
        "category_code": "category_code",
        "time_slot_id": "period",
    })

    df["sales_millions"] = pd.to_numeric(df["sales_millions"], errors="coerce")
    df["period"] = pd.to_datetime(df["period"], format="%Y-%m")

    df["category_name"] = df["category_code"].map(CATEGORY_NAMES).fillna(df["category_code"])

    df = df.sort_values("period")

    pivot = df.pivot_table(
        index="period",
        columns="category_name",
        values="sales_millions",
        aggfunc="first",
    )
    pivot.index.name = "date"
    pivot.columns.name = None
    pivot = pivot.reset_index()
    pivot["date"] = pivot["date"].dt.strftime("%Y-%m")

    return pivot


def main():
    try:
        raw = fetch_retail_data(seasonally_adjusted=False)
    except requests.HTTPError as e:
        print(f"API request failed: {e}")
        return

    print(f"Retrieved {len(raw)} records. Processing...")

    pivot = clean_and_pivot(raw)

    output_file = "retail_sales_by_category.csv"
    pivot.to_csv(output_file, index=False)

    print(f"Saved {len(pivot)} months of data to {output_file}")
    print(f"Date range: {pivot['date'].iloc[0]} to {pivot['date'].iloc[-1]}")
    print(f"Categories: {[c for c in pivot.columns if c != 'date']}")


if __name__ == "__main__":
    main()
