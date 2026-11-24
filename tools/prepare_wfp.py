"""Shrink a WFP Rwanda food price download to the small file the project uses as a retail benchmark.

    python tools/prepare_wfp.py wfp_food_prices_rwa.csv

Source: WFP food prices for Rwanda, Humanitarian Data Exchange (data.humdata.org/dataset/wfp-food-prices-for-rwanda),
licence Creative Commons Attribution for Intergovernmental Organisations. Keep that credit in your report.
Output: data/wfp_retail_rwa_2026.csv (kg prices in RWF from 1 May 2026, your crops only).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_core as ic  # noqa: E402

KEEP = ["date", "admin1", "admin2", "market", "commodity", "crop", "unit", "pricetype", "currency", "price"]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    w = ic.load_wfp(sys.argv[1])
    w = w[[c for c in KEEP if c in w.columns]].sort_values(["crop", "market", "date"])
    w["source"] = "WFP via HDX (CC BY-IGO), retail"
    out = os.path.join(ROOT, "data", "wfp_retail_rwa_2026.csv")
    w.to_csv(out, index=False, date_format="%Y-%m-%d")
    print(f"Wrote {len(w)} rows to {out}")
    print(w.groupby("crop").agg(rows=("price", "size"), markets=("market", "nunique"),
                                last=("date", "max")).to_string())


if __name__ == "__main__":
    main()
