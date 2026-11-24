"""Add new prices to data/isoko_crop_data.csv safely.

    python tools/add_prices.py new_prices.csv

The new file must be a CSV with at least: observed_date, product, location, price, unit.
Columns the main file has but the new file lacks are left blank. A backup of the main file is kept.
Nothing is overwritten by accident: rows already present are skipped, and problems are listed.
"""
import argparse
import os
import shutil
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_core as ic  # noqa: E402

REQUIRED = ["observed_date", "product", "location", "price", "unit"]


def merge_prices(old: pd.DataFrame, new: pd.DataFrame):
    """Return (merged, report). Raises ValueError when the new file cannot be used."""
    missing = [c for c in REQUIRED if c not in new.columns]
    if missing:
        raise ValueError(f"The new file is missing required columns: {missing}. "
                         f"It has: {list(new.columns)}")
    new = new.copy()
    new["observed_date"] = pd.to_datetime(new["observed_date"], errors="coerce")
    new["price"] = pd.to_numeric(new["price"], errors="coerce")
    bad = new[new["observed_date"].isna() | new["price"].isna() | (new["price"] <= 0)]
    new = new.drop(bad.index)
    wrong_unit = new[new["unit"].astype(str).str.lower() != "kg"]
    new = new.drop(wrong_unit.index)

    # Duplicates are judged only on columns the new file really has (a blank 'channel' must not hide a duplicate).
    keys = [c for c in ["observed_date", "product", "location", "price", "channel"]
            if c in old.columns and c in new.columns]
    for c in old.columns:                                  # match the main file's columns
        if c not in new.columns:
            new[c] = None
    new = new[list(old.columns)]
    old = old.copy()
    old["observed_date"] = pd.to_datetime(old["observed_date"], errors="coerce")

    merged = pd.concat([old, new], ignore_index=True).drop_duplicates(subset=keys)
    report = dict(added=len(merged) - len(old), skipped_bad=len(bad), skipped_not_kg=len(wrong_unit),
                  skipped_duplicate=len(new) - (len(merged) - len(old)),
                  unknown_products=sorted(p for p in new["product"].dropna().unique() if ic.infer_crop(p) is None))
    return merged, report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("new_file")
    ap.add_argument("--target", default=os.path.join(ROOT, "data", "isoko_crop_data.csv"))
    args = ap.parse_args()

    old = pd.read_csv(args.target)
    merged, rep = merge_prices(old, pd.read_csv(args.new_file))
    shutil.copy(args.target, args.target + ".bak")
    merged.to_csv(args.target, index=False)
    print(f"Added {rep['added']} rows. Skipped: {rep['skipped_bad']} invalid, "
          f"{rep['skipped_not_kg']} not in kg, {rep['skipped_duplicate']} already present.")
    if rep["unknown_products"]:
        print("These products are not one of the project crops and will be ignored by the app:",
              rep["unknown_products"])
    print(f"Newest date now: {pd.to_datetime(merged['observed_date']).max().date()}. Backup: {args.target}.bak")


if __name__ == "__main__":
    main()
