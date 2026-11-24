"""Rolling-origin backtest for Isoko Smart AI.

Predicts each market's NEXT weekly price using only earlier weeks.
Models: Last price, 4-week average, 4-point trend line, Random Forest.
"""
import numpy as np
import pandas as pd

MODELS = ["Last price", "4-week average", "4-point trend line", "Random Forest"]
LAGS = 4


def weekly_prices(df):
    """One median price per crop/product/market/week (weeks start Monday)."""
    d = df[["crop_category", "product", "location", "observed_date", "price"]].copy()
    d["week"] = d["observed_date"].dt.to_period("W-SUN").dt.start_time
    return (d.groupby(["crop_category", "product", "location", "week"])["price"]
              .median().reset_index())


def _series(g):
    s = g.set_index("week")["price"].sort_index()
    full = pd.date_range(s.index.min(), s.index.max(), freq="7D")
    return s.reindex(full).ffill(limit=2).dropna()      # fill gaps of up to 2 weeks only


def _predict(train):
    y = train.to_numpy(dtype=float)
    out = {"Last price": y[-1], "4-week average": y[-LAGS:].mean()}
    x = np.arange(LAGS)
    slope, intercept = np.polyfit(x, y[-LAGS:], 1)
    out["4-point trend line"] = max(slope * LAGS + intercept, 0.0)
    out["Random Forest"] = y[-1]                          # fallback if too little history
    if len(y) - LAGS >= 6:
        try:
            from sklearn.ensemble import RandomForestRegressor
            X = np.array([y[i:i + LAGS] for i in range(len(y) - LAGS)])
            t = y[LAGS:]
            rf = RandomForestRegressor(n_estimators=100, random_state=0, n_jobs=-1)
            rf.fit(X, t)
            out["Random Forest"] = float(rf.predict(y[-LAGS:].reshape(1, -1))[0])
        except Exception:
            pass
    return out


def run_backtest(df, min_weeks=14, test_points=6):
    """One row per market series with each model's mean absolute error (RWF/kg)."""
    rows = []
    wk = weekly_prices(df)
    for (crop, prod, loc), g in wk.groupby(["crop_category", "product", "location"]):
        s = _series(g)
        if len(s) < min_weeks:
            continue
        errs = {m: [] for m in MODELS}
        for t in range(len(s) - test_points, len(s)):
            train, actual = s.iloc[:t], float(s.iloc[t])
            for m, p in _predict(train).items():
                errs[m].append(abs(p - actual))
        row = {"crop_category": crop, "product": prod, "location": loc,
               "weeks": len(s), "test_points": test_points}
        row.update({f"MAE_{m}": float(np.mean(v)) for m, v in errs.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def summarise(res):
    """Model comparison table: average error and share of series each model won."""
    if res.empty:
        return pd.DataFrame(columns=["model", "series", "mean_MAE", "median_MAE", "share_won_%"])
    cols = [f"MAE_{m}" for m in MODELS]
    winner = res[cols].idxmin(axis=1).str.replace("MAE_", "", regex=False)   # ties go to the simpler model
    out = []
    for m in MODELS:
        v = res[f"MAE_{m}"]
        out.append({"model": m, "series": len(res), "mean_MAE": round(v.mean(), 1),
                    "median_MAE": round(v.median(), 1),
                    "share_won_%": round((winner == m).mean() * 100, 1)})
    return pd.DataFrame(out)
