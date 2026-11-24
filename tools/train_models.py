"""Train and test every model once and save the results, so the app opens fast and shows the same numbers every time.

Run from the project folder:   python tools/train_models.py
Writes models/model_report.json. Run it again after adding new prices (the app notices when the data has changed
and recomputes on its own if the report is out of date).
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import isoko_core as ic          # noqa: E402
import isoko_ml                  # noqa: E402

REPORT = os.path.join(HERE, "models", "model_report.json")


def main(data=None, markets=None, out=REPORT):
    data = data or os.path.join(HERE, "data", "isoko_crop_data.csv")
    markets = markets or os.path.join(HERE, "data", "markets.csv")
    df = ic.load_prices(data)
    rep = isoko_ml.build_report(df, ic.load_markets(markets))
    isoko_ml.save_report(rep, out)
    print(f"Trained and tested on {rep['rows']:,} price records (newest {df['observed_date'].max():%d %b %Y}).")
    for r in rep["table"]:
        print(f"  {r['model']:<45} {r['mean_error_RWF']:>8.1f} RWF/kg  ({r['kind']})")
    print("Forecast backtest, share of market series each method won:")
    for r in rep["backtest"]:
        print(f"  {r['model']:<22} {r['share_won_%']:>5.1f}%")
    print(rep["reason"])
    print("Saved", out)


if __name__ == "__main__":
    main()
