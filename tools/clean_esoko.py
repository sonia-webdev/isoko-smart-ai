"""Clean a raw Esoko price download into data/isoko_crop_data.csv, and write a quality report.

    python tools/clean_esoko.py raw_esoko.csv

Keeps only your 7 crops (beans, cassava, Irish potatoes, maize, rice, sweet potatoes, tomatoes) in kg and RWF, from
1 May 2026, adds `crop_category`, removes exact duplicates and trims market names.
No price is changed or deleted for being unusual: prices far outside the usual range for their product get
`price_flag = "unusually_high"` or `"unusually_low"` so that you can look at them yourself.
Writes data/isoko_crop_data.csv and data/quality_report.csv.
"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_core as ic  # noqa: E402

DEDUP_KEYS = ["observed_date", "product", "location", "price", "channel"]


def flag_unusual(df: pd.DataFrame, min_group: int = 30) -> pd.Series:
    """'unusually_high' / 'unusually_low' by the 1.5 x IQR rule within each product (groups of 30+ prices only)."""
    flag = pd.Series("", index=df.index)
    for _, g in df.groupby("product"):
        if len(g) < min_group:
            continue
        q1, q3 = g["price"].quantile([0.25, 0.75])
        spread = q3 - q1
        flag.loc[g.index[g["price"] > q3 + 1.5 * spread]] = "unusually_high"
        flag.loc[g.index[g["price"] < q1 - 1.5 * spread]] = "unusually_low"
    return flag


def clean_raw(raw: pd.DataFrame, start: str = ic.WINDOW_START):
    """Return (clean, report). report is a table of steps with the number of rows left and removed."""
    steps = []

    def step(name, before, after):
        steps.append(dict(step=name, rows_before=before, rows_after=after, rows_removed=before - after))

    df = raw.copy()
    n = len(df)
    df["crop_category"] = df["product"].map(ic.infer_crop)
    df = df.dropna(subset=["crop_category"])
    step("keep the 7 project crops (drops flour, leaves, fresh and green beans, soya, sweet pepper, other foods)", n, len(df))

    n = len(df)
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["observed_date"] = pd.to_datetime(df["observed_date"], errors="coerce")
    df = df.dropna(subset=["price", "observed_date", "location", "product"])
    df = df[df["price"] > 0]
    step("valid date, market, product and a price above zero", n, len(df))

    n = len(df)
    df = df[df["unit"].astype(str).str.lower() == "kg"]
    if "currency" in df.columns:
        df = df[df["currency"].astype(str).str.upper() == "RWF"]
    step("price per kg in RWF", n, len(df))

    n = len(df)
    df = df[df["observed_date"] >= pd.Timestamp(start)]
    step(f"from {start} onward", n, len(df))

    n = len(df)
    df["location"] = df["location"].astype(str).str.strip()
    keys = [k for k in DEDUP_KEYS if k in df.columns]
    df = df.drop_duplicates(subset=keys)
    step("remove exact duplicates (same date, product, market, price and channel)", n, len(df))

    df = df.sort_values(["crop_category", "product", "location", "observed_date"]).reset_index(drop=True)
    df["price_flag"] = flag_unusual(df)
    df["observed_date"] = df["observed_date"].dt.strftime("%Y-%m-%d")
    first = ["observed_date", "crop_category", "product", "unit", "channel", "location", "region", "price",
             "currency", "source", "scraped_at", "price_flag"]
    df = df[[c for c in first if c in df.columns] + [c for c in df.columns if c not in first]]
    return df.drop(columns=[c for c in ("variety", "grade") if c in df.columns and df[c].isna().all()]), pd.DataFrame(steps)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    raw = pd.read_csv(sys.argv[1], low_memory=False)
    clean, report = clean_raw(raw)
    out_dir = os.path.join(ROOT, "data")
    clean.to_csv(os.path.join(out_dir, "isoko_crop_data.csv"), index=False)
    summary = (clean.groupby("crop_category").agg(rows=("price", "size"), products=("product", "nunique"),
               markets=("location", "nunique"), newest=("observed_date", "max"),
               flagged=("price_flag", lambda s: int((s != "").sum()))).reset_index())
    report.to_csv(os.path.join(out_dir, "quality_report.csv"), index=False)
    print(report.to_string(index=False))
    print()
    print(summary.to_string(index=False))
    print(f"\nWrote {len(clean):,} rows to {out_dir}/isoko_crop_data.csv")


if __name__ == "__main__":
    main()
