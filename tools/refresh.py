"""Weekly refresh: add new Esoko prices, rebuild the web data, and report how fresh and reliable the data is.

    python tools/refresh.py new_prices.csv            add prices, rebuild everything the web app and API read
    python tools/refresh.py                           only rebuild and print the data health report
    python tools/refresh.py new_prices.csv --train    also retrain and test the models (takes several minutes)

The new file needs the columns observed_date, product, location, price, unit (prices in kg). Duplicates, bad rows and
anything not in kg are skipped, and a backup of the main file is kept (data/isoko_crop_data.csv.bak).
"""
import argparse
import collections
import json
import os
import shutil
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import add_prices          # noqa: E402
import export_web_data     # noqa: E402

DATA = os.path.join(ROOT, "data")
PRICES = os.path.join(DATA, "isoko_crop_data.csv")
WEB_DATA = os.path.join(DATA, "web_data.json")


def health(web: dict) -> dict:
    """How trustworthy today's advice is: reliability counts, and which markets are quiet (the ones to chase)."""
    counts = collections.Counter()
    last_seen = {}
    for crop in web["cur"].values():
        for rows in crop.values():
            for loc, _price, _days, last, _old, rel in rows:
                counts[rel] += 1
                last_seen[loc] = max(last, last_seen.get(loc, ""))
    asof = pd.Timestamp(web["meta"]["asof"])
    quiet = sorted(((int((asof - pd.Timestamp(d)).days), m) for m, d in last_seen.items()), reverse=True)
    return dict(latest=web["meta"]["asof"], records=web["meta"]["records"],
                reliability={k: counts.get(k, 0) for k in ("High", "Medium", "Low")},
                quiet_markets=[dict(market=m, days_since_last_report=d) for d, m in quiet[:10]])


def refresh(new_csv=None, train=False, target=PRICES, out_web=WEB_DATA):
    report = {}
    if new_csv:
        try:
            new = pd.read_csv(new_csv)
        except Exception as exc:
            raise ValueError(f"The new file could not be read as a CSV: {exc}")
        first_time = not os.path.exists(target)
        old = new.iloc[0:0] if first_time else pd.read_csv(target)      # the very first file becomes the main file
        merged, rep = add_prices.merge_prices(old, new)
        if not first_time:
            shutil.copy(target, target + ".bak")
        merged.to_csv(target, index=False)
        report["added"] = rep
    web = export_web_data.build(target, os.path.join(DATA, "markets.csv"), os.path.join(DATA, "road_distances.csv"),
                                os.path.join(ROOT, "models", "model_report.json"))
    tmp = out_web + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(web, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, out_web)                                         # readers never see a half-written file
    if train:
        import train_models
        train_models.main()
    report["health"] = health(web)
    report["models_stale"] = bool(new_csv) and not train
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("new_file", nargs="?")
    ap.add_argument("--train", action="store_true")
    a = ap.parse_args()
    try:
        r = refresh(a.new_file, a.train)
    except ValueError as exc:
        sys.exit(f"Could not refresh: {exc}")
    if "added" in r:
        x = r["added"]
        print(f"Added {x['added']} rows. Skipped: {x['skipped_bad']} invalid, {x['skipped_not_kg']} not in kg, "
              f"{x['skipped_duplicate']} already present.")
        if x["unknown_products"]:
            print("Not one of the project crops (ignored):", x["unknown_products"])
    h = r["health"]
    print(f"Data to {h['latest']}, {h['records']:,} records. Reliability of today's market prices: {h['reliability']}")
    print("Quietest markets (chase these for fresh reports):")
    for q in h["quiet_markets"]:
        print(f"  {q['market']:<20} last report {q['days_since_last_report']} days before the newest data")
    if r["models_stale"]:
        print("The saved model results are out of date; run with --train when convenient (takes several minutes).")
    print("Web data written to", WEB_DATA)


if __name__ == "__main__":
    main()
