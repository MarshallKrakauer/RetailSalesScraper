"""
Scrapes US Census Bureau Advance Monthly Retail Trade Survey (MARTS) data.
Pulls total sales by category from 1992 to present and saves to CSV.
"""

import requests
import pandas as pd

BASE_URL = "https://api.census.gov/data/timeseries/eits/marts"

CATEGORY_NAMES = {
    # Major NAICS sectors
    "441": "Motor Vehicle & Parts Dealers",
    "441X": "Auto Parts, Accessories & Tire Stores",
    "442": "Furniture & Home Furnishing Stores",
    "443": "Electronics & Appliance Stores",
    "444": "Building Material & Garden Equipment",
    "445": "Food & Beverage Stores",
    "4451": "Grocery Stores",
    "446": "Health & Personal Care Stores",
    "447": "Gasoline Stations",
    "448": "Clothing & Accessories Stores",
    "451": "Sporting Goods, Hobby, Book & Music",
    "452": "General Merchandise Stores",
    "4522": "Department Stores",
    "453": "Miscellaneous Store Retailers",
    "454": "Nonstore Retailers",
    "722": "Food Services & Drinking Places",
    # Aggregate/composite codes
    "44000": "Retail Only (excl. Food Services)",
    "44X72": "Total Retail & Food Services",
    "44Y72": "Total excl. Motor Vehicles",
    "44W72": "Total excl. Motor Vehicles & Gas",
    "44Z72": "Total excl. Gasoline",
    "44X45": "Retail Trade (44+45)",
    "44X45722": "Retail Trade & Food Services",
}

START_YEAR = 1992


def fetch_retail_data(seasonally_adjusted=False) -> pd.DataFrame:
    adj_flag = "yes" if seasonally_adjusted else "no"

    params = {
        "get": "cell_value,category_code",
        "time": f"from {START_YEAR}",
        "seasonally_adj": adj_flag,
        "geo_level_code": "US",
        "data_type_code": "SM",
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
        "time": "period",
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


TOP_LEVEL_SECTORS = [
    "Motor Vehicle & Parts Dealers",
    "Furniture & Home Furnishing Stores",
    "Electronics & Appliance Stores",
    "Building Material & Garden Equipment",
    "Food & Beverage Stores",
    "Health & Personal Care Stores",
    "Gasoline Stations",
    "Clothing & Accessories Stores",
    "Sporting Goods, Hobby, Book & Music",
    "General Merchandise Stores",
    "Miscellaneous Store Retailers",
    "Nonstore Retailers",
    "Food Services & Drinking Places",
]


MRTS_URL = "https://api.census.gov/data/timeseries/eits/mrts"


def fetch_ecommerce_data() -> pd.DataFrame:
    print("Fetching e-commerce (Electronic Shopping & Mail-Order) data from MRTS...")
    frames = []
    for start in [1992, 2019]:
        params = {
            "get": "cell_value,category_code,time_slot_id",
            "time": f"from {start}",
            "seasonally_adj": "no",
            "geo_level_code": "US",
            "data_type_code": "SM",
            "category_code": "4541",
        }
        resp = requests.get(MRTS_URL, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        frames.append(pd.DataFrame(data[1:], columns=data[0]))

    df = pd.concat(frames, ignore_index=True)
    df = df.rename(columns={"cell_value": "sales_millions", "time": "date"})
    df["sales_millions"] = pd.to_numeric(df["sales_millions"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m")
    df = df.drop_duplicates(subset="date").sort_values("date")
    df["date"] = df["date"].dt.strftime("%Y-%m")
    return df[["date", "sales_millions"]].rename(columns={"sales_millions": "Electronic Shopping & Mail-Order ($M)"})


def main():
    try:
        raw = fetch_retail_data(seasonally_adjusted=False)
    except requests.HTTPError as e:
        print(f"API request failed: {e}")
        return

    print(f"Retrieved {len(raw)} records. Processing...")

    pivot = clean_and_pivot(raw)
    pivot["Total"] = pivot["Total Retail & Food Services"]
    pivot["Retail Only"] = pivot["Retail Only (excl. Food Services)"]

    output_file = "retail_sales_by_category.csv"
    pivot.to_csv(output_file, index=False)
    print(f"Saved {len(pivot)} months to {output_file} ({pivot['date'].iloc[0]} to {pivot['date'].iloc[-1]})")

    try:
        ecomm = fetch_ecommerce_data()
        ecomm.to_csv("ecommerce_sales.csv", index=False)
        print(f"Saved {len(ecomm)} months to ecommerce_sales.csv ({ecomm['date'].iloc[0]} to {ecomm['date'].iloc[-1]})")
    except Exception as e:
        print(f"E-commerce fetch failed: {e}")


if __name__ == "__main__":
    main()
