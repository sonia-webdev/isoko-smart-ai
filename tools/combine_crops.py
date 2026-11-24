"""Combine one price CSV per crop (or any mix of Esoko CSVs) into the single file the project reads.

    python tools/combine_crops.py beans.csv cassava.csv rice.csv ...   ->  data/isoko_crop_data.csv

Each file needs at least: observed_date, product, location, price, unit (other Esoko columns are kept).
Common alternative column names are understood (date, market, name, ...). The crop of a row comes from its product
name, never from the file name, so a file with the wrong name cannot put a price under the wrong crop.
Rows that are not one of your 7 crops are counted and left to the normal cleaning, which drops them.
Exact duplicates across files (same date, product, market, price, channel) are removed.
"""
import os
import re
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_core as ic  # noqa: E402

ALIASES = {"date": "observed_date", "observed": "observed_date", "market": "location", "market_name": "location",
           "product_name": "product", "commodity": "product", "name": "product", "price_rwf": "price",
           "unit_of_measure": "unit"}
REQUIRED = ["observed_date", "product", "location", "price", "unit"]
DEDUP_KEYS = ["observed_date", "product", "location", "price", "channel"]



def read_one(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False, encoding="utf-8-sig")
    df.columns = [ALIASES.get(re.sub(r"[\s\-]+", "_", str(c).strip().lower()), re.sub(r"[\s\-]+", "_", str(c).strip().lower()))
                  for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"{os.path.basename(path)} is missing the columns {missing}. It has: {list(df.columns)}")
    return df


def combine(paths):
    """(combined raw rows, report table, list of problems). Files that cannot be read are listed, not fatal."""
    frames, rows, problems = [], [], []
    for path in paths:
        name = os.path.basename(path)
        try:
            df = read_one(path)
        except Exception as exc:                                       # a bad file must not stop the others
            problems.append(f"{name}: {exc}")
            continue
        crop = df["product"].map(ic.infer_crop)
        kg = df["unit"].astype(str).str.lower().eq("kg")
        found = ", ".join(sorted(crop.dropna().unique())) or "none"
        rows.append(dict(file=name, rows=len(df), crop_rows=int(crop.notna().sum()), kg_rows=int((crop.notna() & kg).sum()),
                         crops_found=found,
                         first_date=pd.to_datetime(df["observed_date"], errors="coerce").min(),
                         last_date=pd.to_datetime(df["observed_date"], errors="coerce").max()))
        if crop.notna().sum() == 0:
            problems.append(f"{name}: no row matches one of your 7 crops (check the product column).")
        df["source_file"] = name
        frames.append(df)
    if not frames:
        return pd.DataFrame(), pd.DataFrame(rows), problems
    allrows = pd.concat(frames, ignore_index=True)
    keys = [k for k in DEDUP_KEYS if k in allrows.columns]
    before = len(allrows)
    allrows = allrows.drop_duplicates(subset=keys).reset_index(drop=True)
    if before - len(allrows):
        problems.append(f"{before - len(allrows):,} duplicate rows (same date, product, market, price and channel) were removed.")
    return allrows.drop(columns=["source_file"]), pd.DataFrame(rows), problems


def crops_covered(clean: pd.DataFrame) -> dict:
    """{crop: rows} for the 7 crops after cleaning; a missing crop has 0."""
    counts = clean["crop_category"].value_counts().to_dict() if len(clean) else {}
    return {c: int(counts.get(c, 0)) for c in sorted(set(ic.CROP_RULES_NAMES))} if hasattr(ic, "CROP_RULES_NAMES") else \
           {c: int(counts.get(c, 0)) for c in ["Beans", "Cassava", "Irish Potatoes", "Maize", "Rice", "Sweet Potatoes", "Tomatoes"]}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    combined, report, problems = combine(sys.argv[1:])
    print(report.to_string(index=False))
    for p in problems:
        print("NOTE:", p)
    if combined.empty:
        sys.exit("Nothing to write.")
    out = os.path.join(ROOT, "data", "isoko_crop_data.csv")
    combined.to_csv(out, index=False)
    print(f"Wrote {len(combined):,} rows to {out}")
    print("Crops after cleaning:", crops_covered(ic.clean_prices(combined)))


if __name__ == "__main__":
    main()
