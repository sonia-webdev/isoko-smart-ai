"""Turn real transport quotes into data/vehicles.json, which the dashboard then uses.

    python tools/fit_transport.py data/transport_quotes.csv

Fill docs/transport_quotes_template.csv with quotes from transporters or cooperatives
(one row per quote). The rate per km is the median over your quotes for each vehicle.
"""
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_core as ic  # noqa: E402


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    fitted = ic.fit_vehicle_rates(pd.read_csv(sys.argv[1]))
    if not fitted:
        sys.exit("No usable quotes (need vehicle, capacity_kg, distance_km, total_quote_rwf).")
    path = os.path.join(ROOT, "data", "vehicles.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fitted, f, indent=2)
    for name, v in fitted.items():
        print(f"{name}: {v['rate_per_km']} RWF/km, carries {v['capacity_kg']} kg  (from {v['n_quotes']} quotes)")
    print("Saved", path, "- redeploy or restart the app to use it. Fewer than ~5 quotes per vehicle is weak evidence.")


if __name__ == "__main__":
    main()
