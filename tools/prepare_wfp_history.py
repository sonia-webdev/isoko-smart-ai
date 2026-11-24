"""Build the multi-year retail price history used for the seasonal-pattern page.

    python tools/prepare_wfp_history.py wfp_food_prices_rwa.csv

Source: WFP food prices for Rwanda, Humanitarian Data Exchange (CC BY-IGO). Retail prices, kg, RWF, all years.
Output: data/wfp_retail_rwa_history.csv, one row per market, commodity and month (monthly median).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_core as ic  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    w = ic.load_wfp(sys.argv[1], start="2000-01-01")
    if "pricetype" in w.columns:
        w = w[w["pricetype"].astype(str).str.lower() == "retail"]
    w["month"] = w["date"].dt.to_period("M").dt.to_timestamp()
    out = (w.groupby(["crop", "commodity", "market", "month"], as_index=False)["price"].median()
             .rename(columns={"month": "date"}).sort_values(["crop", "commodity", "market", "date"]))
    out["price"] = out["price"].round(1)
    path = os.path.join(ROOT, "data", "wfp_retail_rwa_history.csv")
    out.to_csv(path, index=False, date_format="%Y-%m-%d")
    print(f"Wrote {len(out)} rows to {path}")
    print(out.groupby("crop").agg(rows=("price", "size"), first=("date", "min"), last=("date", "max")).to_string())


if __name__ == "__main__":
    main()
