"""Export the real data as one compact JSON file for the React dashboard (web/index.html).

Run from the project folder:   python tools/export_web_data.py
Everything in the file is computed by isoko_core from the real Esoko prices; nothing is invented.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import pandas as pd              # noqa: E402
import isoko_core as ic          # noqa: E402
import isoko_i18n as i18n        # noqa: E402


def build(data_csv, markets_csv, road_csv=None, report_json=None):
    df = ic.load_prices(data_csv)
    markets = ic.load_markets(markets_csv)
    roads = ic.load_road_distances(road_csv) if road_csv and os.path.exists(road_csv) else {}
    asof = df["observed_date"].max()
    if "region" not in df.columns:
        df["region"] = ""
    district = df.groupby("location")["region"].first().to_dict()

    cur, series = {}, {}
    for crop, g in df.groupby("crop_category"):
        for product in g["product"].unique():
            cp = ic.current_prices(df, crop, product, asof=asof)
            if cp.empty:
                continue
            cur.setdefault(crop, {})[product] = [
                [r.location, round(r.price, 1), int(r.days_with_price), f"{r.last_date:%Y-%m-%d}", int(r.days_old),
                 r.reliability] for r in cp.itertuples()]
            s = ic.weekly_series(df, crop, product)
            if len(s):
                series.setdefault(crop, {})[product] = [[f"{d:%Y-%m-%d}", round(float(v), 1)] for d, v in s.items()]
    # product with most records first, per crop
    order = {c: g["product"].value_counts().index.tolist() for c, g in df.groupby("crop_category")}

    locs = sorted({r[0] for c in cur.values() for p in c.values() for r in p})
    dist = {}
    for origin in markets["location"]:
        d = ic.add_distance(pd.DataFrame({"location": locs}), markets, origin, road_km=roads)
        dist[origin] = {r.location: [None if pd.isna(r.distance_km) else float(r.distance_km), r.distance_source[0]]
                        for r in d.itertuples()}

    pm = ic.pattern_2026(df)
    story = ic.price_story(pm, df) if len(pm) else pd.DataFrame()
    month = [[r.crop, f"{r.month:%Y-%m}", float(r.median_price), int(r.markets), int(r.reports),
              None if pd.isna(r.spread_pct) else float(r.spread_pct), bool(r.partial)] for r in pm.itertuples()]
    story_rows = [] if story.empty else json.loads(story.to_json(orient="records"))
    cov = (df.groupby("location").agg(district=("region", "first"), crops=("crop_category", "nunique"),
                                      records=("price", "count"), last=("observed_date", "max")).reset_index())
    cov["last"] = cov["last"].dt.strftime("%Y-%m-%d")
    ml = None
    if report_json and os.path.exists(report_json):
        with open(report_json, encoding="utf-8") as fh:
            rep = json.load(fh)
        ml = {k: rep.get(k) for k in ("gate_pass", "gain_pct", "gate_needed_pct", "reason", "table", "backtest")}
    return dict(
        meta=dict(records=int(len(df)), markets=int(df["location"].nunique()), crops=int(df["crop_category"].nunique()),
                  first=f"{df['observed_date'].min():%Y-%m-%d}", asof=f"{asof:%Y-%m-%d}"),
        crops=order, cur=cur, series=series, dist=dist, district=district, month=month, story=story_rows,
        coverage=json.loads(cov.to_json(orient="records")), ml=ml,
        rate=ic.DEFAULT_RATE, vehicles=ic.load_vehicles(os.path.join(HERE, "data", "vehicles.json")), strings=i18n.STR, cropnames=i18n.CROPS)


if __name__ == "__main__":
    out = build(os.path.join(HERE, "data", "isoko_crop_data.csv"), os.path.join(HERE, "data", "markets.csv"),
                os.path.join(HERE, "data", "road_distances.csv"), os.path.join(HERE, "models", "model_report.json"))
    path = os.path.join(HERE, "web", "data.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("Wrote", path, os.path.getsize(path) // 1024, "KB")
