"""Give every market in your price file a coordinate, using the WFP market list, and update data/markets.csv.

    python tools/match_markets.py data/isoko_crop_data.csv wfp_markets_rwa.csv

A WFP coordinate is accepted ONLY when the WFP district agrees with the district in your Esoko file (the same market
name can exist in different districts: WFP's Kimironko is in Gatsibo, Esoko's is in Gasabo, Kigali). Otherwise the
market gets the average position of the WFP markets in its Esoko district, and is marked "approximate". Coordinates
already in data/markets.csv are never changed. Source: WFP market list, Humanitarian Data Exchange (CC BY-IGO).
"""
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_core as ic  # noqa: E402

KIGALI = {"nyarugenge", "gasabo", "kicukiro"}
UNKNOWN_UNIT = "administrative unit not available"
# Esoko spelling -> WFP spelling (lower case)
ALIASES = {"congonil": "congo - nil", "kicukiro-center": "kicukiro"}


def _norm(name) -> str:
    return str(name).strip().lower()


def esoko_districts(esoko: pd.DataFrame) -> pd.DataFrame:
    """One row per market in the Esoko file: location and its usual district (the file's `region` column)."""
    d = esoko.dropna(subset=["location"]).copy()
    d["location"] = d["location"].astype(str).str.strip()
    if "region" not in d.columns:
        d["region"] = ""
    rows = []
    for loc, g in d.groupby("location"):
        modes = g["region"].dropna().astype(str).str.strip().str.lower().mode()
        rows.append(dict(location=loc, district=modes.iat[0] if len(modes) else ""))
    return pd.DataFrame(rows)


def match_markets(esoko_markets: pd.DataFrame, wfp: pd.DataFrame, existing: pd.DataFrame):
    """Return (markets, report). `markets` is `existing` plus the new rows; `report` says how each market was placed."""
    wfp = wfp.copy()
    wfp["key"] = wfp["market"].map(_norm)
    wfp["district"] = wfp["admin2"].map(_norm)
    province = (wfp[wfp["district"] != UNKNOWN_UNIT].drop_duplicates("district")
                .set_index("district")["admin1"].map(_norm).to_dict())
    centre = (wfp[wfp["district"] != UNKNOWN_UNIT].groupby("district")[["latitude", "longitude"]].mean().round(3))
    by_key = {}
    for _, r in wfp.iterrows():
        by_key.setdefault(r["key"], []).append(r)

    def district_agrees(esoko_district, w):
        if w["district"] == esoko_district:
            return True
        if w["district"] in KIGALI and esoko_district in KIGALI:
            return True
        if w["district"] == UNKNOWN_UNIT:                       # WFP knows the province only
            return province.get(esoko_district) == _norm(w["admin1"])
        return False

    have = {ic._market_key(n) for n in existing["location"]}
    new_rows, report = [], []
    for _, m in esoko_markets.iterrows():
        loc, district = m["location"], _norm(m["district"])
        if ic._market_key(loc) in have:
            report.append((loc, m["district"], "already in markets.csv", ""))
            continue
        key = ALIASES.get(_norm(loc), _norm(loc))
        candidates = by_key.get(key, [])
        agreeing = [w for w in candidates if district_agrees(district, w)]
        if agreeing:
            w = agreeing[0]
            new_rows.append((loc, float(w["latitude"]), float(w["longitude"]),
                             f"WFP market list, district agrees ({w['admin2']}); district-level precision", m["district"]))
            report.append((loc, m["district"], "WFP match", f"{w['market']} ({w['admin2']})"))
        elif district in centre.index:
            lat, lon = centre.loc[district]
            why = ("WFP has a market with this name in a DIFFERENT district, so it was not used" if candidates
                   else "not in the WFP list")
            new_rows.append((loc, float(lat), float(lon),
                             "approximate: average of WFP markets in the district (" + m["district"] + ")", m["district"]))
            report.append((loc, m["district"], "district average (approximate)", why))
        else:
            report.append((loc, m["district"], "NO COORDINATE", "district not found in the WFP list: add by hand"))
    add = pd.DataFrame(new_rows, columns=["location", "lat", "lon", "coord_source", "district"])
    base = existing.copy()
    for col in ("coord_source", "district"):
        if col not in base.columns:
            base[col] = "manual" if col == "coord_source" else ""
    return (pd.concat([base, add], ignore_index=True),
            pd.DataFrame(report, columns=["location", "esoko_district", "result", "detail"]))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    esoko = pd.read_csv(sys.argv[1], low_memory=False)
    wfp = pd.read_csv(sys.argv[2])
    path = os.path.join(ROOT, "data", "markets.csv")
    markets, report = match_markets(esoko_districts(esoko), wfp, ic.load_markets(path))
    markets.to_csv(path, index=False)
    print(report["result"].value_counts().to_string())
    print("\n" + report[report["result"] != "already in markets.csv"].to_string(index=False))
    print(f"\nWrote {len(markets)} markets to {path}")


if __name__ == "__main__":
    main()
