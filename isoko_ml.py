"""Isoko Smart AI - can a trained model estimate a market's price better than simple rules?

Task: for a crop at a market in a week, estimate its median price from what is known beforehand: the other
markets' average that week, this market's own earlier prices and its usual premium, its location, the month.
The model learns the RATIO to the other markets' average, so it works at any price level.

The test is fair: it trains on the earlier 70% of weeks and is scored on the later 30%, against simple rules.
Isoko uses the trained model only if it beats the best simple rule by at least `GATE_GAIN_PCT` percent.
On sparse data it usually will not, and the project then says so instead of claiming AI value.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GATE_GAIN_PCT = 10.0
MIN_MARKETS_IN_WEEK = 4


def build_dataset(df: pd.DataFrame, markets: pd.DataFrame) -> pd.DataFrame:
    """One row per crop, market and week with at least one earlier observation at that market."""
    d = df.copy()
    d["week"] = d["observed_date"].dt.to_period("W-SUN").dt.start_time
    w = (d.groupby(["crop_category", "location", "week"])["price"].median().reset_index()
           .rename(columns={"crop_category": "crop"}))
    if w.empty:
        return w
    w["wk"] = ((w["week"] - w["week"].min()).dt.days // 7).astype(int)
    g = w.groupby(["crop", "wk"])["price"]
    n = g.transform("size")
    w["loo"] = (g.transform("sum") - w["price"]) / (n - 1)           # average of the OTHER markets that week
    w = w[n >= MIN_MARKETS_IN_WEEK].sort_values(["crop", "location", "wk"]).copy()
    grp = w.groupby(["crop", "location"])
    w["prev_price"], w["prev_loo"], prev_wk = grp["price"].shift(), grp["loo"].shift(), grp["wk"].shift()
    w["age"] = w["wk"] - prev_wk
    w["rel"] = np.log(w["price"] / w["loo"])
    w["prev_rel"] = np.log(w["prev_price"] / w["prev_loo"])
    w["hist_rel"] = grp["rel"].transform(lambda x: x.shift().expanding().mean())
    w["hist_n"] = grp["rel"].transform(lambda x: x.shift().expanding().count())
    w["hist_sd"] = grp["rel"].transform(lambda x: x.shift().expanding().std()).fillna(0)
    w["mkt_rel"] = w.groupby("location")["rel"].transform(lambda x: x.shift().expanding().mean()).fillna(0)
    w["month"] = w["week"].dt.month
    m = markets.set_index("location")
    w["lat"], w["lon"] = w["location"].map(m["lat"]), w["location"].map(m["lon"])
    w = w.dropna(subset=["prev_price", "hist_rel", "lat", "lon"]).copy()
    w["target"] = w["rel"]
    return pd.concat([w, pd.get_dummies(w["crop"], prefix="c").astype(float)], axis=1)


def feature_names(data: pd.DataFrame) -> list:
    return ["prev_rel", "hist_rel", "hist_n", "hist_sd", "mkt_rel", "age", "lat", "lon", "month", "wk"] + \
           [c for c in data.columns if c.startswith("c_")]


def _models():
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    return {"Random forest (trained)": RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=0, n_jobs=-1),
            "Gradient boosting (trained)": GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05,
                                                                     subsample=0.8, random_state=0)}


def evaluate(df: pd.DataFrame, markets: pd.DataFrame, train_share: float = 0.7) -> dict:
    """Train on the earlier weeks, score on the later ones. Returns the results table and the gate decision."""
    data = build_dataset(df, markets)
    if len(data) < 200 or data["wk"].nunique() < 10:
        return dict(ok=False, reason="Not enough weekly price history to train and test a model fairly.",
                    table=pd.DataFrame(), n_train=0, n_test=0, gate_pass=False)
    cut = data["wk"].quantile(train_share)
    tr, te = data[data["wk"] <= cut], data[data["wk"] > cut]
    feats = feature_names(data)
    rows = [("Last known price at that market", te["prev_price"]),
            ("Other markets' average that week", te["loo"]),
            ("Last price moved with the other markets", te["prev_price"] * te["loo"] / te["prev_loo"])]
    for name, model in _models().items():
        model.fit(tr[feats], tr["target"])
        rows.append((name, te["loo"] * np.exp(model.predict(te[feats]))))
    table = pd.DataFrame([dict(model=n, mean_error_RWF=round(float(np.mean(np.abs(te["price"] - p))), 1),
                               kind="trained" if "trained" in n else "simple rule") for n, p in rows])
    best_rule = table[table["kind"] == "simple rule"]["mean_error_RWF"].min()
    best_ai = table[table["kind"] == "trained"]["mean_error_RWF"].min()
    gain = round((best_rule - best_ai) / best_rule * 100, 1)
    table["better_than_best_rule_%"] = ((best_rule - table["mean_error_RWF"]) / best_rule * 100).round(1)
    return dict(ok=True, table=table, n_train=len(tr), n_test=len(te), best_rule=best_rule, best_ai=best_ai,
                gain_pct=gain, gate_pass=gain >= GATE_GAIN_PCT,
                reason=("The trained model beats the best simple rule by %.1f%% (needs %.0f%%)." % (gain, GATE_GAIN_PCT)
                        if gain >= GATE_GAIN_PCT else
                        "The trained model beats the best simple rule by only %.1f%% (needs %.0f%%), so it is NOT used "
                        "for advice. More weeks of regular reports are needed." % (gain, GATE_GAIN_PCT)))


def fit_estimator(df: pd.DataFrame, markets: pd.DataFrame):
    """The random forest trained on ALL available weeks (use only if evaluate(...)['gate_pass'])."""
    data = build_dataset(df, markets)
    feats = feature_names(data)
    model = _models()["Random forest (trained)"].fit(data[feats], data["target"])
    return model, feats


# ---------------------------------------------------------------- saved training results
def data_key(df: pd.DataFrame) -> str:
    """Identifies the data a report was made from: row count and newest date."""
    return f"{len(df)}|{df['observed_date'].max():%Y-%m-%d}"


def build_report(df: pd.DataFrame, markets: pd.DataFrame) -> dict:
    """Train and test every model once and return a JSON-friendly report."""
    import backtest
    ev = evaluate(df, markets)
    res = backtest.run_backtest(df)
    summ = backtest.summarise(res)
    return dict(key=data_key(df), rows=int(len(df)), ok=bool(ev["ok"]), reason=ev["reason"],
                gate_pass=bool(ev["gate_pass"]), n_train=int(ev["n_train"]), n_test=int(ev["n_test"]),
                gain_pct=float(ev.get("gain_pct", 0.0)), gate_needed_pct=float(GATE_GAIN_PCT),
                table=ev["table"].to_dict("records") if ev["ok"] else [],
                backtest=summ.to_dict("records"), backtest_series=int(len(res)))


def save_report(report: dict, path: str) -> None:
    import json, os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def load_report(path: str, df: pd.DataFrame | None = None):
    """The saved report, or None if missing, unreadable, or made from different data than `df`."""
    import json, os
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            rep = json.load(f)
    except (OSError, ValueError):
        return None
    if df is not None and rep.get("key") != data_key(df):
        return None
    return rep
