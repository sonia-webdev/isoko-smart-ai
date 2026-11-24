"""Isoko Smart AI - core logic (no Streamlit here, so it can be tested alone).

Design rules taken from the project report:
  * only recent prices are used (default window starts 1 May 2026);
  * every result carries its data date and a reliability label;
  * demonstration data is always labelled as such;
  * a forecast is shown only if it beats the "last price" baseline in a backtest.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

WINDOW_START = "2026-05-01"     # prices before this date are ignored
ROAD_FACTOR = 1.3               # road distance ~ 1.3 x straight line (used only when no real road distance is known)
DEFAULT_RATE = 0.20             # RWF per kg per km (assumption - validate with farmers)

# Vehicle options for the transport calculator. These are PLANNING DEFAULTS, not measured values:
# replace them with real local quotes (see README, "Replacing the transport assumptions").
VEHICLES = {
    "Motorbike":          {"capacity_kg": 100,  "rate_per_km": 150},
    "Car (saloon)":       {"capacity_kg": 300,  "rate_per_km": 300},
    "Pickup / small van": {"capacity_kg": 1000, "rate_per_km": 500},
    "Truck":              {"capacity_kg": 5000, "rate_per_km": 1200},
}

# Other spellings of the same market (lower case). Butare is the old name of Huye town.
MARKET_ALIASES = {"butare": "huye"}

# Rules that turn a product name into one of the project's crops (first match wins, so "sweet potato" is tested
# before plain "potato"). Names that look like a crop but are a different product are left out on purpose:
# flour, bran, leaves, fresh/green beans, soya beans, sweet pepper.
CROP_RULES = [
    (r"sweet[\s\-_]*potato", "Sweet Potatoes"),
    (r"potato|irish", "Irish Potatoes"),
    (r"\bbean", "Beans"),
    (r"cassava", "Cassava"),
    (r"maize", "Maize"),
    (r"\brice\b", "Rice"),
    (r"tomato", "Tomatoes"),
]
CROP_EXCLUDE = ("flour", "bran", "leaves", "leaf", "soya", "soy", "green", "fresh", "pepper", "powder", "oil")


def infer_crop(product) -> str | None:
    """Crop for a product name such as 'Tomatos' or 'Irish- Potato- Kirundo' (None if not a project crop)."""
    import re
    name = str(product).lower()
    if any(word in name for word in CROP_EXCLUDE):
        return None
    for pattern, crop in CROP_RULES:
        if re.search(pattern, name):
            return crop
    return None


# WFP commodity names ("Beans (dry)", "Rice (imported, Tanzanian)") follow the same rules.
def wfp_to_crop(commodity) -> str | None:
    """Project crop for a WFP commodity name ('Beans (dry)' -> Beans), or None."""
    return infer_crop(commodity)


def load_wfp(path: str, start: str = WINDOW_START) -> pd.DataFrame:
    """WFP (Humanitarian Data Exchange) Rwanda food prices, reduced to the project's crops:
    kg only, RWF only, from `start` onward, with a `crop` column. These are RETAIL prices."""
    w = pd.read_csv(path, low_memory=False)
    w = w[~w["date"].astype(str).str.startswith("#")]                # HDX files have a '#date' tag row under the header
    w["date"] = pd.to_datetime(w["date"], errors="coerce")
    w["price"] = pd.to_numeric(w["price"], errors="coerce")
    w = w.dropna(subset=["date", "price", "market", "commodity"])
    if "unit" in w.columns:
        w = w[w["unit"].astype(str).str.upper() == "KG"]
    if "currency" in w.columns:
        w = w[w["currency"].astype(str).str.upper() == "RWF"]
    w = w[(w["date"] >= pd.Timestamp(start)) & (w["price"] > 0)].copy()
    if "crop" not in w.columns:
        w["crop"] = w["commodity"].map(wfp_to_crop)
    return w.dropna(subset=["crop"]).reset_index(drop=True)


def _market_key(name) -> str:
    key = str(name).strip().lower()
    return MARKET_ALIASES.get(key, key)


# --------------------------------------------------------------------------
# 1. Loading and cleaning
# --------------------------------------------------------------------------
def clean_prices(df: pd.DataFrame, start: str = WINDOW_START) -> pd.DataFrame:
    df = df.copy()
    # Raw scraped files have no crop_category column: work it out from the product name.
    if "crop_category" not in df.columns:
        df["crop_category"] = df["product"].map(infer_crop)
    else:
        df["crop_category"] = df["crop_category"].fillna(df["product"].map(infer_crop))
    df["observed_date"] = pd.to_datetime(df["observed_date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["observed_date", "price", "crop_category", "product", "location"])
    df = df[df["price"] > 0]
    if "unit" in df.columns:
        df = df[df["unit"].astype(str).str.lower() == "kg"]
    df = df[df["observed_date"] >= pd.Timestamp(start)]
    df["location"] = df["location"].astype(str).str.strip()
    source = df["source"].astype(str) if "source" in df.columns else pd.Series("unknown", index=df.index)
    df["data_status"] = np.where(source.str.contains("demo", case=False), "demonstration", "verified")
    keys = [c for c in ["observed_date", "product", "location", "price", "channel"] if c in df.columns]
    return df.drop_duplicates(subset=keys).reset_index(drop=True)


def load_prices(path: str, start: str = WINDOW_START) -> pd.DataFrame:
    return clean_prices(pd.read_csv(path), start)


def load_markets(path: str) -> pd.DataFrame:
    m = pd.read_csv(path)
    m["location"] = m["location"].astype(str).str.strip()
    return m


# --------------------------------------------------------------------------
# 2. Current price per market
# --------------------------------------------------------------------------
def reliability(days_with_price: int, days_old: int, stale: bool) -> str:
    if stale or days_old > 14 or days_with_price < 2:
        return "Low"
    if days_with_price >= 4 and days_old <= 7:
        return "High"
    return "Medium"


def current_prices(df, crop, product, asof=None, window_days=14, stale_days=30) -> pd.DataFrame:
    cols = ["location", "price", "days_with_price", "last_date", "days_old",
            "stale", "reliability", "data_status"]
    d = df[(df["crop_category"] == crop) & (df["product"] == product)]
    if d.empty:
        return pd.DataFrame(columns=cols)
    asof = pd.Timestamp(asof) if asof is not None else d["observed_date"].max()
    rows = []
    for loc, g in d[d["observed_date"] <= asof].groupby("location"):
        last = g["observed_date"].max()
        age = int((asof - last).days)
        if age > stale_days:
            continue
        recent = g[g["observed_date"] > asof - pd.Timedelta(days=window_days)]
        stale = recent.empty
        use = g[g["observed_date"] == last] if stale else recent
        n_days = int(use["observed_date"].nunique())
        status = "demonstration" if (use["data_status"] == "demonstration").any() else "verified"
        rows.append(dict(location=loc, price=float(use["price"].median()),
                         days_with_price=n_days, last_date=last, days_old=age,
                         stale=stale, reliability=reliability(n_days, age, stale),
                         data_status=status))
    return pd.DataFrame(rows, columns=cols)


def trusted_only(cp: pd.DataFrame, origin: str, min_days: int = 2) -> pd.DataFrame:
    """Drop markets whose price rests on a single report day, so one lucky high price cannot win the ranking.
    The farmer's own market always stays (it is the comparison point). If fewer than two other markets remain,
    nothing is dropped, because advice from nothing is worse than cautious advice."""
    if cp.empty:
        return cp
    keep = (cp["days_with_price"] >= min_days) | (cp["location"].map(_market_key) == _market_key(origin))
    return cp[keep] if int((keep & (cp["location"].map(_market_key) != _market_key(origin))).sum()) >= 2 else cp


# --------------------------------------------------------------------------
# 3. Distance, transport and net return
# --------------------------------------------------------------------------
def fit_vehicle_rates(quotes: pd.DataFrame) -> dict:
    """Turn real transport quotes into vehicle settings.

    quotes needs: vehicle, capacity_kg, distance_km, total_quote_rwf and (optional) round_trip (yes/no).
    rate_per_km = quote / (distance x legs), taking the median over the quotes for each vehicle."""
    q = quotes.dropna(subset=["vehicle", "capacity_kg", "distance_km", "total_quote_rwf"]).copy()
    q = q[(q["distance_km"] > 0) & (q["total_quote_rwf"] > 0)]
    if "round_trip" in q.columns:
        legs = np.where(q["round_trip"].astype(str).str.strip().str.lower().isin(["yes", "y", "true", "1"]), 2, 1)
    else:
        legs = 1
    q["rate"] = q["total_quote_rwf"] / (q["distance_km"] * legs)
    out = {}
    for vehicle, g in q.groupby("vehicle"):
        out[str(vehicle)] = {"capacity_kg": int(round(g["capacity_kg"].median())),
                             "rate_per_km": int(round(g["rate"].median())), "n_quotes": int(len(g))}
    return out


def load_vehicles(path: str | None) -> dict:
    """Default vehicles, overridden by data/vehicles.json (made by tools/fit_transport.py) when it exists."""
    import json
    import os
    vehicles = {k: dict(v) for k, v in VEHICLES.items()}
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            vehicles.update(json.load(f))
    return vehicles


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def load_road_distances(path: str) -> dict:
    """Real road distances between markets: CSV with columns origin, destination, km.
    Returns {(origin, destination): km} in lower case. Build the file with tools/build_road_distances.py."""
    d = pd.read_csv(path)
    out = {}
    for o, t, km in zip(d["origin"], d["destination"], d["km"]):
        out[(_market_key(o), _market_key(t))] = float(km)
    return out


def add_distance(prices: pd.DataFrame, markets: pd.DataFrame, origin: str,
                 road_factor: float = ROAD_FACTOR, road_km: dict | None = None) -> pd.DataFrame:
    """Add distance_km and distance_source ('road' = real road distance, 'estimate' = straight line x factor)."""
    m = markets.assign(_k=markets["location"].map(_market_key)).drop_duplicates("_k").set_index("_k")
    origin_key = _market_key(origin)
    o = m.loc[origin_key]
    road_km = road_km or {}
    out = prices.copy()

    def dist(loc):
        key = _market_key(loc)
        if key == origin_key:
            return 0.0, "same market"
        known = road_km.get((origin_key, key), road_km.get((key, origin_key)))
        if known is not None:
            return round(float(known), 1), "road"
        if key not in m.index:
            return np.nan, "unknown"
        t = m.loc[key]
        return round(haversine_km(o["lat"], o["lon"], t["lat"], t["lon"]) * road_factor, 1), "estimate"

    pairs = out["location"].map(dist)
    out["distance_km"] = pairs.map(lambda p: p[0])
    out["distance_source"] = pairs.map(lambda p: p[1])
    return out


def rank_markets(prices: pd.DataFrame, quantity_kg: float, rate_per_kg_km: float = DEFAULT_RATE,
                 fixed_trip_cost: float = 0.0) -> pd.DataFrame:
    """Net return = Q x (P - T) - F, where T = rate x distance.
    F (fixed trip cost, e.g. vehicle hire) is charged only for markets away from home."""
    out = prices.copy()
    out["transport_per_kg"] = out["distance_km"] * rate_per_kg_km
    away = out["distance_km"] > 0
    out["gross_revenue"] = quantity_kg * out["price"]
    out["transport_cost"] = quantity_kg * out["transport_per_kg"] + np.where(away, fixed_trip_cost, 0.0)
    out["net_return"] = out["gross_revenue"] - out["transport_cost"]
    out = out.sort_values("net_return", ascending=False, na_position="last").reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def rank_markets_vehicle(prices: pd.DataFrame, quantity_kg: float, capacity_kg: float, rate_per_km: float,
                         round_trip: bool = True, fixed_trip_cost: float = 0.0,
                         market_fee_per_kg: float = 0.0, loss_pct_per_100km: float = 0.0,
                         cost_scale: float = 1.0) -> pd.DataFrame:
    """Vehicle-based net return.

    * trips = ceil(quantity / vehicle capacity); each trip pays rate_per_km for every km driven
      (twice the distance if the vehicle must come back) plus the fixed cost per trip;
    * loss_pct_per_100km of the load is lost (spoilage, shrinkage) per 100 km driven one way;
    * market_fee_per_kg is paid on the kilograms actually sold.
    cost_scale multiplies the transport costs (used by the stability check). Same output columns as
    rank_markets, plus trips, loss_kg and other_costs, so the dashboard can show either."""
    out = prices.copy()
    dist = out["distance_km"]
    away = dist > 0
    trips = max(int(math.ceil(quantity_kg / capacity_kg)), 1)
    legs = 2 if round_trip else 1
    drive = trips * legs * dist * rate_per_km * cost_scale
    fixed = np.where(away, trips * fixed_trip_cost * cost_scale, 0.0)
    loss_frac = np.clip(loss_pct_per_100km / 100.0 * dist / 100.0, 0.0, 0.9)
    sold_kg = quantity_kg * (1 - loss_frac)
    out["trips"] = np.where(away, trips, 0)
    out["transport_cost"] = drive + fixed
    out["transport_per_kg"] = out["transport_cost"] / quantity_kg
    out["gross_revenue"] = quantity_kg * out["price"]
    out["loss_kg"] = quantity_kg - sold_kg
    out["other_costs"] = out["loss_kg"] * out["price"] + market_fee_per_kg * sold_kg
    out["net_return"] = out["gross_revenue"] - out["transport_cost"] - out["other_costs"]
    out = out.sort_values("net_return", ascending=False, na_position="last").reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def explain_ranking(ranked: pd.DataFrame, rec: dict | None, min_gain_pct: float = 5.0, lang: str = "en") -> pd.Series:
    """One plain sentence per market: why it is recommended, or why it is not. Index matches `ranked`.
    The wording comes from isoko_i18n, so it can be shown in English or Kinyarwanda."""
    import isoko_i18n as i18n
    T = lambda key, **kw: i18n.t(lang, key, **kw)
    why = pd.Series("", index=ranked.index, dtype=object)
    missing_text = T("why_missing")
    if rec is None:
        return why.where(ranked["net_return"].notna(), missing_text)
    best, base = rec["best"], rec["baseline"]
    m = lambda x: f"{x:,.0f}"
    for i, r in ranked.iterrows():
        name = str(r["location"])
        if pd.isna(r["net_return"]):
            why[i] = missing_text
            continue
        note = T("why_note_low") if r["reliability"] == "Low" else ""
        km = f"{r['distance_km']:.0f}"
        gap = best["net_return"] - r["net_return"]
        if name == base["location"] and name == best["location"]:
            why[i] = T("why_home_best", gain=f"{min_gain_pct:g}", note=note)
        elif name == best["location"]:
            if rec["worthwhile"]:
                why[i] = T("why_best_rec", transport=m(r["transport_cost"]), km=km, net=m(r["net_return"]),
                           uplift=m(rec["uplift"]), pct=f"{rec['uplift_pct']:.0f}", base=base["location"], note=note)
            else:
                why[i] = T("why_best_not", pct=f"{rec['uplift_pct']:.0f}", base=base["location"],
                           gain=f"{min_gain_pct:g}", note=note)
        elif name == base["location"]:
            why[i] = T("why_home", net=m(r["net_return"]), best=best["location"], diff=m(gap), note=note)
        elif r["price"] > best["price"]:
            why[i] = T("why_more_price", price=m(r["price"]), best_price=m(best["price"]), km=km,
                       transport=m(r["transport_cost"]), gap=m(gap), best=best["location"], note=note)
        elif r["price"] < best["price"] and r["transport_cost"] < best["transport_cost"]:
            why[i] = T("why_closer", km=km, price=m(r["price"]), best_price=m(best["price"]), gap=m(gap),
                       best=best["location"], note=note)
        elif r["price"] < best["price"]:
            why[i] = T("why_less_price", price=m(r["price"]), best_price=m(best["price"]), km=km,
                       transport=m(r["transport_cost"]), gap=m(gap), best=best["location"], note=note)
        else:
            why[i] = T("why_same_price", best=best["location"], km=km, gap=m(gap), note=note)
    return why


def best_market_stability(rank_fn, scales=(0.5, 1.0, 1.5, 2.0)) -> dict:
    """Does the advice survive a wrong transport assumption?

    rank_fn(scale) must return a ranked table in which transport costs are multiplied by `scale`.
    Returns the best market for every scale and whether it is the same one as at scale 1.0."""
    scales = tuple(sorted(set(scales) | {1.0}))
    by_scale = {}
    for s in scales:
        rec = recommend(rank_fn(s))
        by_scale[s] = None if rec is None else dict(best=str(rec["best"]["location"]),
                                                    worthwhile=bool(rec["worthwhile"]),
                                                    baseline=str(rec["baseline"]["location"]))
    base = by_scale[1.0]
    if base is None:
        return dict(by_scale=by_scale, stable=False, same_share=0.0, base_best=None)
    same = [s for s, v in by_scale.items() if v and v["best"] == base["best"]
            and v["worthwhile"] == base["worthwhile"]]
    return dict(by_scale=by_scale, stable=len(same) == len(scales),
                same_share=len(same) / len(scales), base_best=base["best"])


def recommend(ranked: pd.DataFrame, min_gain_pct: float = 5.0) -> dict | None:
    known = ranked.dropna(subset=["net_return"])
    if known.empty:
        return None
    best = known.iloc[0]
    home = known[known["distance_km"] == 0]
    base = home.iloc[0] if not home.empty else known.sort_values("distance_km").iloc[0]
    uplift = float(best["net_return"] - base["net_return"])
    pct = uplift / base["net_return"] * 100 if base["net_return"] else 0.0
    worthwhile = best["location"] != base["location"] and pct >= min_gain_pct
    return dict(best=best, baseline=base, uplift=uplift, uplift_pct=pct, worthwhile=worthwhile)


# --------------------------------------------------------------------------
# 4. Trends and the honest forecast
# --------------------------------------------------------------------------
def weekly_series(df, crop, product, location: str | None = None) -> pd.Series:
    d = df[(df["crop_category"] == crop) & (df["product"] == product)].copy()
    if location:
        d = d[d["location"] == location]
    if d.empty:
        return pd.Series(dtype=float)
    d["week"] = d["observed_date"].dt.to_period("W-SUN").dt.start_time
    if location:
        s = d.groupby("week")["price"].median()
    else:
        s = d.groupby(["week", "location"])["price"].median().groupby("week").median()
    return s.sort_index()


def trend_signal(series: pd.Series, recent: int = 2, base: int = 4, threshold: float = 0.05) -> dict:
    s = series.dropna()
    if len(s) < recent + base:
        return dict(direction="unknown", pct=None)
    now = s.iloc[-recent:].median()
    before = s.iloc[-(recent + base):-recent].median()
    pct = (now - before) / before
    direction = "rising" if pct > threshold else "falling" if pct < -threshold else "steady"
    return dict(direction=direction, pct=float(pct * 100))


def forecast_gate(series: pd.Series, min_points: int = 12, test_points: int = 8,
                  trend_points: int = 4, margin: float = 0.9) -> dict:
    """Show a forecast only if a 4-point trend line beats 'same as last week' in a backtest."""
    vals = series.dropna().to_numpy(float)
    if len(vals) < min_points:
        return dict(show=False, reason=f"Only {len(vals)} weekly prices; at least {min_points} are needed.")
    e_last, e_trend = [], []
    for i in range(max(trend_points, len(vals) - test_points), len(vals)):
        hist = vals[:i]
        slope, icpt = np.polyfit(np.arange(trend_points), hist[-trend_points:], 1)
        e_trend.append(abs(vals[i] - (icpt + slope * trend_points)))
        e_last.append(abs(vals[i] - hist[-1]))
    mae_last, mae_trend = float(np.mean(e_last)), float(np.mean(e_trend))
    if mae_last == 0 or mae_trend > margin * mae_last:
        return dict(show=False, mae_last=mae_last, mae_trend=mae_trend,
                    reason="A trend forecast did not beat 'same as last week' in testing, "
                           "so the last price is the best guide.")
    slope, icpt = np.polyfit(np.arange(trend_points), vals[-trend_points:], 1)
    return dict(show=True, forecast=float(icpt + slope * trend_points), typical_error=mae_trend,
                mae_last=mae_last, mae_trend=mae_trend, reason="Trend forecast beat the baseline in testing.")


# --------------------------------------------------------------------------
# 4b. Seasonal patterns (for planners and government)
# --------------------------------------------------------------------------
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def seasonal_index(hist: pd.DataFrame, min_points: int = 10, min_years: int = 3) -> pd.DataFrame:
    """How prices move through the calendar year, from many years of WFP monthly RETAIL prices.

    Each market-and-commodity series is divided by its own centred 12-month average, so inflation, a rising or
    falling trend, product mix and market mix do not pass for seasonality. The median across series gives one value
    per crop, year and month; the typical value across years is the index (100 = the average month).
    Only crops with all 12 months and at least `min_years` years are returned.
    Columns: crop, month (1-12), index, low, high (middle half of years), years, series."""
    h = hist.copy()
    h["date"] = pd.to_datetime(h["date"])
    parts = []
    for _, g in h.groupby(["crop", "commodity", "market"]):
        s = g.groupby("date")["price"].median()
        s = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="MS"))
        m12 = s.rolling(12, min_periods=min_points).mean()
        centred = (m12.shift(-6) + m12.shift(-5)) / 2               # 2x12 centred moving average
        r = (s / centred).dropna()
        if len(r):
            parts.append(pd.DataFrame({"crop": g["crop"].iloc[0], "date": r.index, "ratio": r.values}))
    if not parts:
        return pd.DataFrame(columns=["crop", "month", "index", "low", "high", "years", "series"])
    r = pd.concat(parts)
    r["year"], r["month"] = r["date"].dt.year, r["date"].dt.month
    ym = r.groupby(["crop", "year", "month"], as_index=False).agg(ratio=("ratio", "median"), series=("ratio", "size"))
    out = (ym.groupby(["crop", "month"]).agg(index=("ratio", "median"), low=("ratio", lambda x: x.quantile(.25)),
                                             high=("ratio", lambda x: x.quantile(.75)),
                                             years=("year", "nunique"), series=("series", "sum")).reset_index())
    good = out.groupby("crop").agg(n=("month", "nunique"), y=("years", "min"))
    out = out[out["crop"].isin(good[(good["n"] == 12) & (good["y"] >= min_years)].index)].copy()
    scale = 100 / out.groupby("crop")["index"].transform("mean")
    for c in ("index", "low", "high"):
        out[c] = out[c] * scale
    return out.reset_index(drop=True)


def seasonal_summary(si: pd.DataFrame, hist: pd.DataFrame) -> pd.DataFrame:
    """One line per crop: cheapest and dearest month, the size of the swing, and how much history supports it."""
    rows = []
    hy = pd.to_datetime(hist["date"]).dt.year
    for crop, g in si.groupby("crop"):
        lo, hi = g.loc[g["index"].idxmin()], g.loc[g["index"].idxmax()]
        yrs = hy[hist["crop"] == crop]
        rows.append(dict(crop=crop, cheapest_month=MONTH_NAMES[int(lo["month"]) - 1],
                         dearest_month=MONTH_NAMES[int(hi["month"]) - 1],
                         swing_pct=round((hi["index"] / lo["index"] - 1) * 100, 1),
                         years_used=int(g["years"].min()), first_year=int(yrs.min()), last_year=int(yrs.max()),
                         evidence="good" if g["years"].min() >= 5 else "limited"))
    return pd.DataFrame(rows)


def monthly_farmgate(df: pd.DataFrame, min_markets: int = 5) -> pd.DataFrame:
    """Esoko farmgate prices by calendar month (2026 only, so this is NOT a seasonal pattern yet).
    spread_pct = gap between the dearer and cheaper markets (90th vs 10th percentile of market medians)."""
    d = df.copy()
    d["month"] = d["observed_date"].dt.to_period("M").dt.to_timestamp()
    mm = d.groupby(["crop_category", "month", "location"], as_index=False)["price"].median()
    rows = []
    for (crop, month), g in mm.groupby(["crop_category", "month"]):
        med = float(g["price"].median())
        spread = None
        if len(g) >= min_markets and med > 0:
            spread = round((g["price"].quantile(.9) - g["price"].quantile(.1)) / med * 100, 1)
        rows.append(dict(crop=crop, month=month, median_price=round(med), markets=len(g),
                         reports=int(((d["crop_category"] == crop) & (d["month"] == month)).sum()), spread_pct=spread))
    return pd.DataFrame(rows).sort_values(["crop", "month"]).reset_index(drop=True)


def pattern_2026(df: pd.DataFrame, min_markets: int = 5) -> pd.DataFrame:
    """Month-by-month movement of each crop in the Esoko data (2026, from May onward).
    median_price: median across markets of each market's monthly median. index_may: that price as a percentage of
    the first month (May = 100). partial: the last month if data stops well before month end.
    A month in which fewer than `min_markets` markets reported a crop is left out: one market is not a national price.
    This describes what happened this year; seven months of one year cannot prove a seasonal pattern."""
    mf = monthly_farmgate(df)
    if mf.empty:
        return mf.assign(index_may=[], partial=[], change_pct_may=[])
    mf = mf[mf["markets"] >= min_markets].copy()
    if mf.empty:
        return mf.assign(index_may=[], partial=[], change_pct_may=[])
    last = df["observed_date"].max()
    mf["partial"] = (mf["month"] == last.to_period("M").to_timestamp()) & (last.day < (last + pd.offsets.MonthEnd(0)).day - 5)
    base = mf.groupby("crop")["median_price"].transform("first")
    mf["index_may"] = (mf["median_price"] / base * 100).round(1)
    mf["change_pct_may"] = (mf["index_may"] - 100).round(1)          # +53 means 53% dearer than in May
    return mf


def pattern_summary(pm: pd.DataFrame) -> pd.DataFrame:
    """One line per crop: cheapest and dearest month so far, change since the first month, and the latest month."""
    rows = []
    for crop, g in pm.groupby("crop"):
        g = g.sort_values("month")
        lo, hi, first, last = g.loc[g["median_price"].idxmin()], g.loc[g["median_price"].idxmax()], g.iloc[0], g.iloc[-1]
        rows.append(dict(crop=crop, first_month=first["month"].strftime("%b"), last_month=last["month"].strftime("%b"),
                         cheapest_month=lo["month"].strftime("%b"), dearest_month=hi["month"].strftime("%b"),
                         price_first=int(first["median_price"]), price_last=int(last["median_price"]),
                         change_pct=round((last["median_price"] / first["median_price"] - 1) * 100, 1),
                         peak_above_low_pct=round((hi["median_price"] / lo["median_price"] - 1) * 100, 1),
                         months=len(g), min_markets=int(g["markets"].min())))
    return pd.DataFrame(rows)


def price_story(pm: pd.DataFrame, df: pd.DataFrame, steady_pct: float = 10.0) -> pd.DataFrame:
    """The plain facts per crop: price at the start, latest price, change, direction, and a like-for-like check.
    same_market_change_pct compares the first and the latest month using ONLY markets that reported in both, so a
    change in WHICH markets reported cannot pass for a change in price. `evidence` says how far to trust it."""
    d = df.copy()
    d["month"] = d["observed_date"].dt.to_period("M").dt.to_timestamp()
    mm = d.groupby(["crop_category", "month", "location"])["price"].median().reset_index()
    rows = []
    for crop, g in pm.groupby("crop"):
        g = g.sort_values("month")
        first, last = g.iloc[0], g.iloc[-1]
        ch = (last["median_price"] / first["median_price"] - 1) * 100
        piv = mm[mm["crop_category"] == crop].pivot(index="location", columns="month", values="price")
        both = piv[[first["month"], last["month"]]].dropna() if len(g) > 1 else piv.iloc[0:0]
        same = None if len(both) < 3 else round((both.iloc[:, 1].median() / both.iloc[:, 0].median() - 1) * 100, 1)
        n = int(len(both))
        rows.append(dict(crop=crop, first_month=first["month"].strftime("%b"), last_month=last["month"].strftime("%b"),
                         price_first=int(first["median_price"]), price_last=int(last["median_price"]),
                         change_pct=round(ch, 1),
                         direction="Rising" if ch >= steady_pct else "Falling" if ch <= -steady_pct else "About the same",
                         same_market_change_pct=same, same_markets=n,
                         evidence="Good" if n >= 8 else "Limited" if n >= 3 else "Weak"))
    return pd.DataFrame(rows)


def plain_words(story: pd.DataFrame) -> list:
    """A few sentences a farmer or an official can read without knowing any statistics."""
    if story.empty:
        return []
    out = []
    top = story.loc[story["price_last"].idxmax()]
    low = story.loc[story["price_last"].idxmin()]
    out.append(f"**Highest price per kg now:** {top['crop']}, {top['price_last']:,} RWF (in {top['last_month']}). "
                f"**Lowest:** {low['crop']}, {low['price_last']:,} RWF.")
    up = story.loc[story["change_pct"].idxmax()]
    out.append(f"**Rose the most since {up['first_month']}:** {up['crop']}, from {up['price_first']:,} to "
               f"{up['price_last']:,} RWF per kg ({up['change_pct']:+.0f}%).")
    down = story[story["change_pct"] < 0]
    if len(down):
        dn = down.loc[down["change_pct"].idxmin()]
        out.append(f"**Fell:** {dn['crop']}, from {dn['price_first']:,} to {dn['price_last']:,} RWF per kg ({dn['change_pct']:+.0f}%).")
    if top["crop"] != up["crop"]:
        out.append(f"A high price is not the same as a rise: {top['crop']} costs the most per kg but "
                   f"{'rose only ' + format(top['change_pct'], '+.0f') + '%' if top['change_pct'] > 0 else 'did not rise'}, "
                   f"while {up['crop']} rose the fastest.")
    return out


# --------------------------------------------------------------------------
# 5. Data-trust diagnostics
# --------------------------------------------------------------------------
def missing_coordinates(df: pd.DataFrame, markets: pd.DataFrame) -> list[str]:
    known = {_market_key(l) for l in markets["location"]}
    return sorted(l for l in df["location"].unique() if _market_key(l) not in known)


def retail_benchmark(esoko: pd.DataFrame, wfp: pd.DataFrame) -> pd.DataFrame:
    """Compare Esoko FARMGATE medians with WFP RETAIL medians, crop by crop.

    Only the months for which WFP has a price are used, so both sides describe the same period.
    The two sources measure different things (farmgate vs retail), so a retail price above the
    farmgate price is expected; this is a sanity check, not a like-for-like comparison."""
    wfp = wfp.assign(month=wfp["date"].dt.to_period("M"))
    esoko = esoko.assign(month=esoko["observed_date"].dt.to_period("M"))
    rows = []
    for crop in sorted(esoko["crop_category"].unique()):
        w = wfp[wfp["crop"] == crop]
        row = dict(crop=crop, months_compared=0, esoko_markets=0, esoko_farmgate_median=np.nan,
                   wfp_markets=0, wfp_retail_median=np.nan, retail_minus_farmgate=np.nan,
                   retail_premium_pct=np.nan, note="")
        if w.empty:
            row["note"] = "no WFP price per kg in this period"
            rows.append(row)
            continue
        months = set(w["month"])
        e = esoko[(esoko["crop_category"] == crop) & esoko["month"].isin(months)]
        row.update(months_compared=len(months), wfp_markets=int(w["market"].nunique()),
                   wfp_retail_median=float(w["price"].median()))
        if e.empty:
            row["note"] = "no Esoko price in the WFP months"
        else:
            e_med = float(e["price"].median())
            row.update(esoko_markets=int(e["location"].nunique()), esoko_farmgate_median=e_med,
                       retail_minus_farmgate=row["wfp_retail_median"] - e_med,
                       retail_premium_pct=(row["wfp_retail_median"] - e_med) / e_med * 100)
            if row["retail_premium_pct"] < 0:
                row["note"] = "retail below farmgate: check that the products match"
            elif len(months) < 3:
                row["note"] = "only %d month(s) of WFP data" % len(months)
        rows.append(row)
    return pd.DataFrame(rows)


def data_age_days(df: pd.DataFrame, today=None) -> int:
    """Days between the newest price and today (the dashboard warns when this is large)."""
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.today().normalize()
    return int((today - df["observed_date"].max()).days)


def cross_crop_identical_share(df: pd.DataFrame) -> float | None:
    """Share of market-days where every crop reported the same price (possible source artefact)."""
    g = df.groupby(["location", "observed_date", "crop_category"])["price"].median().reset_index()
    per = g.groupby(["location", "observed_date"])["price"].agg(["nunique", "count"])
    per = per[per["count"] >= 3]
    return None if per.empty else float((per["nunique"] == 1).mean())
