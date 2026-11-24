"""Isoko Smart AI - farmer dashboard.  Run:  streamlit run app.py"""
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import isoko_core as ic
import isoko_i18n as i18n
import isoko_sms

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY_CSV = os.path.join(HERE, "data", "wfp_retail_rwa_history.csv")      # many years, see tools/prepare_wfp_history.py
WFP_CSV = os.path.join(HERE, "data", "wfp_retail_rwa_2026.csv")           # retail benchmark, see tools/prepare_wfp.py
CORRECTIONS_CSV = os.path.join(HERE, "data", "kinyarwanda_corrections.csv")  # reviewer fixes, see isoko_i18n.py
REAL_CSV = os.path.join(HERE, "data", "isoko_crop_data.csv")
DEMO_CSV = os.path.join(HERE, "data", "demo_crop_data.csv")
MARKETS_CSV = os.path.join(HERE, "data", "markets.csv")
ROAD_CSV = os.path.join(HERE, "data", "road_distances.csv")      # optional, see tools/build_road_distances.py
MODEL_REPORT = os.path.join(HERE, "models", "model_report.json")   # written by tools/train_models.py
VEHICLES_JSON = os.path.join(HERE, "data", "vehicles.json")       # optional, see tools/fit_transport.py

FOREST, GREEN, CREAM, GOLD, MUTED = "#123D2A", "#23834B", "#F7F5EA", "#D6A640", "#718078"

st.set_page_config(page_title="Isoko Smart AI", page_icon="🌾", layout="wide")
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; }}
.stApp {{ background: {CREAM}; }}
[data-testid="stSidebar"] {{ background: {FOREST}; }}
[data-testid="stSidebar"] * {{ color: #fff !important; }}
h1, h2, h3 {{ color: {FOREST} !important; }}
.answer {{ background:#fff; border-left:6px solid {GREEN}; border-radius:10px; padding:18px 22px; margin:8px 0 18px; }}
.answer.stay {{ border-left-color:{GOLD}; }}
.answer h3 {{ margin:0 0 6px; font-size:1.35rem; }}
.answer p {{ margin:0; color:#26352C; font-size:1.02rem; }}
.hero {{ background:{FOREST}; border-radius:14px; padding:30px 34px; margin:4px 0 20px; }}
.hero h2 {{ color:#fff !important; margin:0 0 8px; font-size:2rem; }}
.hero p {{ color:#DDEBE1; margin:0; font-size:1.1rem; line-height:1.5; }}
.card {{ background:#fff; border-radius:12px; padding:16px 20px; height:100%; border-top:4px solid {GOLD}; }}
.card h4 {{ margin:0 0 6px; color:{FOREST}; }}
.card p {{ margin:0; color:#26352C; }}
.badge {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:.82rem; font-weight:700; }}
.b-High {{ background:#DDF0E2; color:#14532D; }} .b-Medium {{ background:#FBF0CC; color:#7A5B00; }}
.b-Low {{ background:#F8DADA; color:#8B1A1A; }}
/* Keep the page sharp: Streamlit fades elements while the script reruns, which looks like blur. */
[data-stale="true"] {{ opacity: 1 !important; filter: none !important; }}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load():
    path = REAL_CSV if os.path.exists(REAL_CSV) else DEMO_CSV
    roads = ic.load_road_distances(ROAD_CSV) if os.path.exists(ROAD_CSV) else {}
    return ic.load_prices(path), ic.load_markets(MARKETS_CSV), path == DEMO_CSV, roads, ic.load_vehicles(VEHICLES_JSON)


df, markets, using_demo, road_km, VEHICLES = load()
if df.empty:
    st.error("No prices found from 1 May 2026 onward. Check data/isoko_crop_data.csv.")
    st.stop()

if "region" not in df.columns:                      # the demonstration file has no district column
    df["region"] = ""
asof = df["observed_date"].max()
i18n.apply_corrections(CORRECTIONS_CSV)

st.sidebar.markdown("## 🌾 Isoko Smart AI")
st.sidebar.info("New interface: stop this and run  python start.py  (or double-click start_isoko.bat) to open the new React interface with the vehicle transport options.")
st.sidebar.caption("Know the market. Choose wisely. Earn more.")
lang = {"English": "en", "Kinyarwanda": "rw"}[st.sidebar.radio("Language / Ururimi", ["English", "Kinyarwanda"],
                                                                 horizontal=True)]
T = lambda key, **kw: i18n.t(lang, key, **kw)
VIEW_PAGES = {"home": ["home"], "farmer": ["sell", "trends", "sms"], "gov": ["overview", "season", "markets", "data"]}
view = st.sidebar.radio(T("view_label"), list(VIEW_PAGES), key="view", format_func=lambda k: T(f"view_{k}"))
if view == "home":
    page = "home"
else:
    page = st.sidebar.radio(T("section"), VIEW_PAGES[view], key=f"page_{view}", format_func=lambda k: T(f"page_{k}"))


def open_view(name):
    """Button callback: jump from the Home page to a dashboard."""
    st.session_state["view"] = name


st.sidebar.markdown("---")
st.sidebar.caption(f"Prices from {df['observed_date'].min():%d %b %Y} to {asof:%d %b %Y}")

st.title("Isoko Smart AI")
if using_demo:
    st.warning("DEMONSTRATION DATA: these prices are synthetic and must not be used for real decisions. "
               "Add data/isoko_crop_data.csv to use verified prices.")
age = ic.data_age_days(df)
if not using_demo and age > 14:
    st.warning(f"The newest price in the data is {age} days old ({asof:%d %b %Y}). "
               "Check current prices locally before you travel.")


def pick_product(key):
    crops = sorted(df["crop_category"].unique())
    c1, c2 = st.columns(2)
    crop = c1.selectbox(T("crop"), crops, key=f"crop_{key}", format_func=lambda c: i18n.crop_name(lang, c))
    products = (df[df["crop_category"] == crop].groupby("product").size()
                .sort_values(ascending=False).index.tolist())
    product = c2.selectbox(T("product"), products, key=f"prod_{key}")
    return crop, product


# ---------------------------------------------------------------- Home (landing page)
if page == "home":
    st.markdown(f"<div class='hero'><h2>{T('home_tag')}</h2><p>{T('home_lead')}</p></div>", unsafe_allow_html=True)
    b1, b2, _ = st.columns([1, 1, 1])
    b1.button("🧑‍🌾 " + T("home_go_farmer"), on_click=open_view, args=("farmer",), use_container_width=True)
    b2.button("🏛️ " + T("home_go_gov"), on_click=open_view, args=("gov",), use_container_width=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(T("home_n_records"), f"{len(df):,}")
    k2.metric(T("home_n_markets"), df["location"].nunique())
    k3.metric(T("home_n_crops"), df["crop_category"].nunique())
    k4.metric(T("home_n_latest"), f"{asof:%d %b %Y}")

    # a live example, worked out from the data exactly as the farmer page does it
    try:
        ex_crop = df["crop_category"].value_counts().index[0]
        ex_product = df[df["crop_category"] == ex_crop]["product"].value_counts().index[0]
        origin_names = set(markets["location"])
        ex_origin = "Nyabugogo" if "Nyabugogo" in origin_names else sorted(origin_names)[0]
        ex_cp = ic.trusted_only(ic.current_prices(df, ex_crop, ex_product, asof=asof), ex_origin)
        ex_rec = ic.recommend(ic.rank_markets(ic.add_distance(ex_cp, markets, ex_origin, road_km=road_km), 500))
    except Exception:
        ex_rec = None
    if ex_rec is not None:
        st.markdown("### " + T("home_example_title"))
        st.caption(T("home_example_intro", origin=ex_origin, qty=500, product=i18n.crop_name(lang, ex_crop)))
        ex = i18n.advice(lang, ex_rec, 500)
        st.markdown(f"<div class='{'answer' if ex['kind'] == 'sell' else 'answer stay'}'><h3>{ex['headline']}</h3>"
                    f"<p>{ex['body']} <span class='badge b-{ex['level']}'>{ex['badge']}</span></p></div>",
                    unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='card'><h4>{T('home_for_farmer_title')}</h4><p>{T('home_for_farmer')}</p></div>",
                unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><h4>{T('home_for_gov_title')}</h4><p>{T('home_for_gov')}</p></div>",
                unsafe_allow_html=True)
    st.markdown("### " + T("home_problem_title"))
    st.write(T("home_problem"))
    st.markdown("### " + T("home_how_title"))
    for k in ("home_step1", "home_step2", "home_step3"):
        st.write(T(k))
    st.markdown("### " + T("home_honest_title"))
    st.write(T("home_honest"))
    st.caption(T("home_pick"))

# ---------------------------------------------------------------- Where to sell
elif page == "sell":
    st.subheader(T("sell_title"))
    crop, product = pick_product("sell")
    c1, c2 = st.columns(2)
    qty = c1.number_input(T("qty"), min_value=10, max_value=100000, value=500, step=50)
    origin = c2.selectbox(T("origin"), sorted(markets["location"]))

    with st.expander(T("tx_title")):
        method = st.radio(T("tx_how"), [T("tx_simple"), T("tx_vehicle")], horizontal=True)
        simple = method == T("tx_simple")
        if simple:
            rate = st.slider(T("tx_rate"), 0.0, 2.0, ic.DEFAULT_RATE, 0.05, help=T("tx_rate_help"))
            trip = 0
        else:
            vehicle = st.selectbox(T("tx_vehicle_pick"), list(VEHICLES) + ["My own quote"], index=list(VEHICLES).index("Pickup / small van") if "Pickup / small van" in VEHICLES else 0,
                                   format_func=lambda v: T("tx_own_quote") if v == "My own quote" else v)
            d = VEHICLES.get(vehicle, next(iter(VEHICLES.values())))
            v1, v2 = st.columns(2)
            capacity = v1.number_input(T("tx_capacity"), 10, 50000, int(d["capacity_kg"]), 50,
                                       key=f"cap_{vehicle}")
            veh_rate = v2.number_input(T("tx_per_km"), 0, 20000, int(d["rate_per_km"]), 50,
                                       key=f"rate_{vehicle}", help=T("tx_per_km_help"))
            round_trip = st.checkbox(T("tx_round"), value=True)
            trip, fee, loss = 0, 0.0, 0.0
            if d.get("n_quotes"):
                st.caption(f"Vehicle figures come from {d['n_quotes']} real transport quotes. "
                           "Your own quote may differ, so you can change them.")
            else:
                st.caption(T("tx_defaults"))
        window = st.slider(T("tx_window"), 7, 30, 14)
        safer = st.checkbox(T("tx_safer"), value=True, help=T("tx_safer_help"))

    cp = ic.current_prices(df, crop, product, asof=asof, window_days=window)
    if cp.empty:
        st.info(T("no_recent"))
        st.stop()
    if safer:
        cp = ic.trusted_only(cp, origin)
    with_dist = ic.add_distance(cp, markets, origin, road_km=road_km)
    if simple:
        ranker = lambda k: ic.rank_markets(with_dist, qty, rate * k, trip * k)
    else:
        ranker = lambda k: ic.rank_markets_vehicle(with_dist, qty, capacity, veh_rate, round_trip, trip, fee, loss,
                                                   cost_scale=k)
    ranked = ranker(1.0)
    rec = ic.recommend(ranked)

    if rec is None:
        st.info(T("no_distance"))
    else:
        best = rec["best"]
        adv = i18n.advice(lang, rec, qty)
        cls = "answer" if adv["kind"] == "sell" else "answer stay"
        st.markdown(f"<div class='{cls}'><h3>{adv['headline']}</h3><p>{adv['body']} "
                    f"<span class='badge b-{adv['level']}'>{adv['badge']}</span></p></div>",
                    unsafe_allow_html=True)
        if best["reliability"] == "Low":
            st.warning(T("warn_low", market=best["location"]))

        # Does the advice survive a wrong transport assumption?
        stab = ic.best_market_stability(ranker)
        if stab["stable"]:
            st.caption("✅ " + T("stable_ok"))
        else:
            st.warning("⚠️ " + T("stable_warn"))
        with st.expander(T("stab_title")):
            rows = []
            for scale, v in stab["by_scale"].items():
                rows.append({T("stab_col_cost"): f"{scale:g}x",
                             T("stab_col_best"): T("stab_none") if v is None else v["best"],
                             T("stab_col_worth"): "-" if v is None else (T("yes") if v["worthwhile"] else T("no"))})
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    top = ranked.dropna(subset=["net_return"]).head(10).iloc[::-1]
    fig = go.Figure(go.Bar(x=top["net_return"], y=top["location"], orientation="h",
                           marker_color=[GREEN if i == len(top) - 1 else "#9DBFA9" for i in range(len(top))],
                           hovertemplate="%{y}: %{x:,.0f} RWF<extra></extra>"))
    fig.update_layout(height=60 + 34 * len(top), margin=dict(l=0, r=10, t=10, b=0),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(size=14), xaxis_title=T("chart_income"))
    st.plotly_chart(fig, use_container_width=True)

    ranked = ranked.copy()
    ranked["why"] = ic.explain_ranking(ranked, rec, lang=lang)
    cols = ["rank", "location", "price", "distance_km", "distance_source", "transport_cost"]
    if not simple:
        cols += ["trips"]
    cols += ["net_return", "last_date", "reliability", "data_status"]
    show = ranked[cols].copy()
    show["last_date"] = show["last_date"].dt.strftime("%d %b %Y")
    st.dataframe(show, hide_index=True, use_container_width=True, column_config={
        "rank": T("col_rank"), "location": T("col_market"),
        "price": st.column_config.NumberColumn(T("col_price"), format="%.0f"),
        "distance_km": st.column_config.NumberColumn(T("col_distance"), format="%.0f"),
        "distance_source": T("col_distance_type"),
        "transport_cost": st.column_config.NumberColumn(T("col_transport"), format="%.0f"),
        "trips": st.column_config.NumberColumn(T("col_trips"), format="%d"),
        "net_return": st.column_config.NumberColumn(T("col_income"), format="%.0f"),
        "last_date": T("col_date"), "reliability": T("col_reliability"), "data_status": T("col_data")})
    st.markdown("#### " + T("col_why"))
    for r_ in ranked.dropna(subset=["net_return"]).head(10).itertuples():
        st.markdown(f"**{r_.rank}. {r_.location}** — {r_.why}")
    n_road = int((ranked["distance_source"] == "road").sum())
    st.caption(f"Distance type: 'road' is a real road distance ({n_road} of {len(ranked)} markets here); 'estimate' is "
               f"straight-line distance x {ic.ROAD_FACTOR}. Markets with no coordinates are listed but not ranked. "
               "Prices are farmgate prices reported by Esoko Rwanda; they are estimates, not guarantees.")

# ---------------------------------------------------------------- Trends
elif page == "trends":
    st.subheader("Price trend")
    crop, product = pick_product("trend")
    locs = ["All markets (median)"] + sorted(df[(df["crop_category"] == crop) & (df["product"] == product)]["location"].unique())
    loc = st.selectbox("Market", locs)
    series = ic.weekly_series(df, crop, product, None if loc.startswith("All") else loc)
    if series.empty:
        st.info("No data for this selection.")
        st.stop()
    fig = go.Figure(go.Scatter(x=series.index, y=series.values, mode="lines+markers",
                               line=dict(color=GREEN, width=2.5), name="Weekly median"))
    gate = ic.forecast_gate(series)
    if gate["show"]:
        nxt = series.index[-1] + pd.Timedelta(days=7)
        fig.add_trace(go.Scatter(x=[nxt], y=[gate["forecast"]], mode="markers",
                                 marker=dict(color=GOLD, size=12, symbol="diamond"),
                                 error_y=dict(type="constant", value=gate["typical_error"]), name="Next-week estimate"))
    fig.update_layout(height=420, margin=dict(l=0, r=10, t=10, b=0), yaxis_title="RWF per kg",
                      font=dict(size=14), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    sig = ic.trend_signal(series)
    words = {"rising": "going up", "falling": "going down", "steady": "steady", "unknown": "not enough data to judge"}
    pct = f" ({sig['pct']:+.0f}% over the last 2 weeks vs the 4 before)" if sig["pct"] is not None else ""
    st.markdown(f"**Recent movement:** prices are {words[sig['direction']]}{pct}.")
    if gate["show"]:
        st.success(f"Next-week estimate: about {gate['forecast']:,.0f} RWF/kg, give or take {gate['typical_error']:,.0f}. "
                   f"In testing this beat 'same as last week' (average error {gate['mae_trend']:,.0f} vs {gate['mae_last']:,.0f}). "
                   "It is an estimate, not a guaranteed price.")
    else:
        st.info(f"No forecast shown. {gate['reason']}")

# ---------------------------------------------------------------- Government: national overview
elif page == "overview":
    st.subheader(T("gov_title"))
    st.caption(T("gov_caption"))
    g1, g2, g3, g4 = st.columns(4)
    g1.metric(T("home_n_records"), f"{len(df):,}")
    g2.metric(T("home_n_markets"), df["location"].nunique())
    g3.metric(T("home_n_crops"), df["crop_category"].nunique())
    g4.metric(T("home_n_latest"), f"{asof:%d %b %Y}")
    pm = ic.pattern_2026(df)
    if pm.empty:
        st.info("No monthly prices to show.")
    else:
        story = ic.price_story(pm, df)
        st.markdown("#### In plain words")
        for line in ic.plain_words(story):
            st.markdown("- " + line)
        last = pm.sort_values("month").groupby("crop").tail(1).dropna(subset=["spread_pct"])
        if len(last):
            st.markdown("#### " + T("gov_gap_title"))
            fig = go.Figure(go.Bar(x=last["crop"], y=last["spread_pct"], marker_color=GOLD,
                                   hovertemplate="%{x}: %{y:.0f}%<extra></extra>"))
            fig.update_layout(height=320, margin=dict(l=0, r=10, t=10, b=0), yaxis_title=T("gov_col_gap"),
                              font=dict(size=14), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(T("gov_gap_help"))
            show = last[["crop", "month", "median_price", "markets", "spread_pct"]].copy()
            show["month"] = show["month"].dt.strftime("%b %Y")
            st.dataframe(show, hide_index=True, use_container_width=True, column_config={
                "crop": T("gov_col_crop"), "month": T("gov_col_month"),
                "median_price": st.column_config.NumberColumn(T("gov_col_median"), format="%.0f"),
                "markets": T("gov_col_markets"),
                "spread_pct": st.column_config.NumberColumn(T("gov_col_gap"), format="%.0f")})
    st.markdown("#### " + T("gov_cov_title"))
    seen = df.groupby("location")["observed_date"].max()
    n_stale = int((seen < asof - pd.Timedelta(days=30)).sum())
    (st.warning if n_stale else st.success)(
        T("gov_cov_stale", n=n_stale, total=len(seen)) if n_stale else T("gov_cov_ok", total=len(seen)))

# ---------------------------------------------------------------- Government: market comparison
elif page == "markets":
    st.subheader(T("mk_title"))
    st.caption(T("mk_caption"))
    crop, product = pick_product("mk")
    sub = df[(df["crop_category"] == crop) & (df["product"] == product)
             & (df["observed_date"] > asof - pd.Timedelta(days=30))]
    if sub.empty:
        st.info(T("mk_none"))
    else:
        tbl = (sub.groupby("location").agg(district=("region", "first"), price=("price", "median"),
                                           reports=("price", "count"), last=("observed_date", "max")).reset_index())
        national = float(tbl["price"].median())
        tbl["vs"] = (tbl["price"] / national - 1) * 100
        tbl = tbl.sort_values("price", ascending=False)
        tbl["last"] = tbl["last"].dt.strftime("%d %b %Y")
        st.dataframe(tbl, hide_index=True, use_container_width=True, column_config={
            "location": T("mk_col_market"), "district": T("mk_col_district"),
            "price": st.column_config.NumberColumn(T("mk_col_median"), format="%.0f"),
            "reports": T("mk_col_reports"), "last": T("mk_col_last"),
            "vs": st.column_config.NumberColumn(T("mk_col_vs"), format="%+.0f")})
        st.download_button(T("mk_download"), tbl.to_csv(index=False).encode("utf-8"),
                           file_name=f"isoko_markets_{product}.csv".replace(" ", "_"), mime="text/csv")
    st.markdown("#### " + T("mk_cov_table"))
    cov = (df.groupby("location").agg(district=("region", "first"), crops=("crop_category", "nunique"),
                                      records=("price", "count"), last=("observed_date", "max"))
           .reset_index().sort_values("records", ascending=False))
    cov["last"] = cov["last"].dt.strftime("%d %b %Y")
    st.dataframe(cov, hide_index=True, use_container_width=True, column_config={
        "location": T("mk_col_market"), "district": T("mk_col_district"), "crops": T("mk_col_crops"),
        "records": T("mk_col_records"), "last": T("mk_col_last")})
    st.download_button(T("mk_download") + " ", cov.to_csv(index=False).encode("utf-8"),
                       file_name="isoko_market_coverage.csv", mime="text/csv", key="cov_dl")

# ---------------------------------------------------------------- Data and trust
elif page == "data":
    st.subheader("Data and trust")
    a, b, c = st.columns(3)
    a.metric("Price records used", f"{len(df):,}")
    b.metric("Markets", df["location"].nunique())
    c.metric("Latest price date", f"{asof:%d %b %Y}")
    st.markdown("**Rule:** only prices from 1 May 2026 onward are used, in kg, in RWF.")
    summary = (df.groupby("crop_category").agg(records=("price", "count"), markets=("location", "nunique"),
                                               products=("product", "nunique"), latest=("observed_date", "max"))
               .reset_index())
    summary["latest"] = summary["latest"].dt.strftime("%d %b %Y")
    st.dataframe(summary, hide_index=True, use_container_width=True)
    if os.path.exists(WFP_CSV) and not using_demo:
        bench = ic.retail_benchmark(df, ic.load_wfp(WFP_CSV))
        st.markdown("**Retail benchmark:** Esoko farmgate prices against WFP retail prices for the same months.")
        st.dataframe(bench, hide_index=True, use_container_width=True, column_config={
            "crop": "Crop", "months_compared": "Months compared", "esoko_markets": "Esoko markets",
            "esoko_farmgate_median": st.column_config.NumberColumn("Esoko farmgate median (RWF/kg)", format="%.0f"),
            "wfp_markets": "WFP markets",
            "wfp_retail_median": st.column_config.NumberColumn("WFP retail median (RWF/kg)", format="%.0f"),
            "retail_minus_farmgate": st.column_config.NumberColumn("Retail minus farmgate", format="%.0f"),
            "retail_premium_pct": st.column_config.NumberColumn("Retail above farmgate (%)", format="%.0f"),
            "note": "Note"})
        st.caption("Retail prices are normally higher than farmgate prices. WFP source: Humanitarian Data Exchange, "
                   "licence CC BY-IGO. A large gap, or retail below farmgate, means the products may not match.")
    with st.expander("AI model check: can a trained model estimate a market's price?"):
        @st.cache_data(show_spinner="Training and testing the models (run tools/train_models.py once to skip this)...")
        def ml_report(_df, _markets, key):
            import isoko_ml
            saved = isoko_ml.load_report(MODEL_REPORT, _df)        # trained earlier by tools/train_models.py
            return saved if saved is not None else isoko_ml.build_report(_df, _markets)
        res = ml_report(df, markets, (len(df), str(asof)))
        if not res["ok"]:
            st.info(res["reason"])
        else:
            st.markdown(f"Two models were **trained** on the earlier weeks ({res['n_train']:,} market-weeks) and tested on "
                        f"the later weeks ({res['n_test']:,}), against simple rules. Lower error is better.")
            st.dataframe(pd.DataFrame(res["table"]).rename(columns={
                "model": "Method", "mean_error_RWF": "Average error (RWF/kg)", "kind": "Type",
                "better_than_best_rule_%": "Better than best rule (%)"}), hide_index=True, use_container_width=True)
            (st.success if res["gate_pass"] else st.warning)(res["reason"])
            if res.get("backtest"):
                st.markdown(f"**Next-week forecast test** ({res['backtest_series']} market series): share of series where each "
                            "method had the smallest error.")
                st.dataframe(pd.DataFrame(res["backtest"])[["model", "mean_MAE", "share_won_%"]].rename(columns={
                    "model": "Method", "mean_MAE": "Average error (RWF/kg)", "share_won_%": "Series won (%)"}),
                    hide_index=True, use_container_width=True)
            st.caption("Isoko uses a trained model for advice only if it clearly beats the simple rules.")

    st.markdown("**Data status:** " + ", ".join(f"{k}: {v:,}" for k, v in df["data_status"].value_counts().items()))
    miss = ic.missing_coordinates(df, markets)
    if miss:
        st.warning(f"{len(miss)} markets have prices but no coordinates, so they are not ranked: " + ", ".join(miss)
                   + ". Add them to data/markets.csv.")
    share = ic.cross_crop_identical_share(df)
    if share is not None:
        if share >= 0.5:
            st.warning(f"Source check: on {share:.0%} of market-days, every crop had exactly the same price. The source "
                       "may report one price per market, not per crop. Compare markets for one crop; do not "
                       "compare crops with each other.")
        else:
            st.markdown(f"**Source check:** on {share:.0%} of market-days, every crop had exactly the same price "
                        "(low, so the source appears to report separate prices per crop).")
    st.markdown(f"**Road distances:** {len({frozenset(k) for k in road_km})} market pairs with real road distances; "
                "all other distances are straight-line estimates.")
    st.markdown("**Limits:** one source (Esoko Rwanda, farmgate prices); transport costs are planning figures, so the "
                "advice page shows whether the best market changes if they are wrong; forecasts appear only when "
                "they beat a simple baseline in testing.")

# ---------------------------------------------------------------- Seasonal patterns (planners, government)
elif page == "season":
    st.subheader(T("page_season"))
    st.caption("For planners and government: how each crop's price moved month by month in 2026, from May onward, "
               "and how far apart markets are. Source: Esoko Rwanda farmgate prices.")
    pm = ic.pattern_2026(df)
    if pm.empty:
        st.info("No monthly prices to show.")
        st.stop()
    summary = ic.pattern_summary(pm)
    story = ic.price_story(pm, df)
    raw = ic.monthly_farmgate(df)
    thin = raw[raw["markets"] < 5]
    if len(thin):
        st.caption("Left out because fewer than 5 markets reported: " + ", ".join(
            sorted({f"{r.crop} {r.month:%b}" for r in thin.itertuples()})) + ".")
    st.markdown("#### In plain words")
    for line in ic.plain_words(story):
        st.markdown("- " + line)
    st.dataframe(story.rename(columns={
        "crop": "Crop", "first_month": "From", "last_month": "To", "price_first": "Price at start (RWF/kg)",
        "price_last": "Latest price (RWF/kg)", "change_pct": "Change (%)", "direction": "Direction",
        "same_market_change_pct": "Change, same markets only (%)", "same_markets": "Markets in both months",
        "evidence": "How sure"}), use_container_width=True, hide_index=True)
    st.caption("Change (%) = how much dearer (+) or cheaper (-) the crop is now than in the first month. "
               "'Same markets only' repeats the comparison with only the markets that reported in both months, so it is not "
               "fooled when different markets report. 'How sure': Good = 8 or more markets in both months, "
               "Limited = 3 to 7, Weak = fewer than 3.")
    crops_pm = sorted(pm["crop"].unique())
    crop = st.selectbox("Crop", crops_pm, format_func=lambda c: f"{c} ({i18n.crop_name(lang, c)})", key="season_crop")
    g = pm[pm["crop"] == crop].sort_values("month")
    row = summary[summary["crop"] == crop].iloc[0]
    labels = [m.strftime("%b") + (" (part)" if p_ else "") for m, p_ in zip(g["month"], g["partial"])]
    colors = [GREEN if m.strftime("%b") == row["cheapest_month"] else GOLD if m.strftime("%b") == row["dearest_month"]
              else "#9bb8a5" for m in g["month"]]
    st.markdown("#### Median price each month")
    fig = go.Figure(go.Bar(x=labels, y=g["median_price"], marker_color=colors, name="Median price"))
    fig.update_layout(height=360, margin=dict(l=0, r=10, t=10, b=0), yaxis_title="RWF per kg (median of markets)",
                      font=dict(size=14), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
    direction = "up" if row["change_pct"] > 0 else "down" if row["change_pct"] < 0 else "unchanged"
    st.markdown(f"**{crop}** was cheapest in **{row['cheapest_month']}** and dearest in **{row['dearest_month']}**, "
                f"about **{row['peak_above_low_pct']:.0f}%** higher at the peak. From {row['first_month']} "
                f"({row['price_first']:,} RWF/kg) to {row['last_month']} ({row['price_last']:,} RWF/kg) the price went "
                f"{direction} **{abs(row['change_pct']):.0f}%**.")
    if g["partial"].any():
        st.caption("Months marked (part) have data for only part of the month.")

    st.markdown("#### All crops at a glance")
    st.dataframe(summary.rename(columns={
        "crop": "Crop", "first_month": "From", "last_month": "To", "cheapest_month": "Cheapest month",
        "dearest_month": "Dearest month", "price_first": "Price at start (RWF/kg)", "price_last": "Latest price (RWF/kg)",
        "change_pct": "Change since start (%)", "peak_above_low_pct": "Peak above low (%)", "months": "Months",
        "min_markets": "Fewest markets in a month"}), use_container_width=True, hide_index=True)

    st.markdown("#### All crops together")
    shown = st.selectbox("Show prices as", ["Actual price (RWF per kg)", "Change since the first month (%)"], key="season_mode")
    actual = shown.startswith("Actual")
    col = "median_price" if actual else "change_pct_may"
    fig2 = go.Figure()
    for c_, gg in pm.groupby("crop"):
        gg = gg.sort_values("month")
        fig2.add_trace(go.Scatter(x=[m.strftime("%b") for m in gg["month"]], y=gg[col], mode="lines+markers", name=c_))
    fig2.update_layout(height=420, margin=dict(l=0, r=10, t=10, b=0),
                       yaxis_title="RWF per kg (median of markets)" if actual else "% dearer (+) or cheaper (-) than in the first month",
                       font=dict(size=14), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)
    z = pm.pivot(index="crop", columns="month", values="index_may")
    txt = pm.pivot(index="crop", columns="month", values=col).round(0)
    fig3 = go.Figure(go.Heatmap(z=z.values, x=[m.strftime("%b") for m in z.columns], y=list(z.index),
                                colorscale="RdYlGn_r", zmid=100, zmin=60, zmax=140,
                                text=(txt.fillna(0).astype(int).astype(str) if actual else txt.fillna(0).map(lambda v: f"{v:+.0f}%")).values,
                                texttemplate="%{text}",
                                showscale=False))
    fig3.update_layout(height=60 + 46 * len(z), margin=dict(l=0, r=10, t=10, b=0), font=dict(size=14),
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.markdown("**Month-by-month grid** " + ("(numbers are RWF per kg; " if actual else "(numbers are the % change since the first month; ") +
                "colour: green = cheaper than May, red = dearer than May)")
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("#### Markets in each month")
    m2 = pm[pm["crop"] == crop].copy()
    m2["month"] = m2["month"].dt.strftime("%b %Y")
    st.dataframe(m2.drop(columns=["crop", "index_may", "change_pct_may", "partial"]).rename(columns={
        "month": "Month", "median_price": "Median price (RWF/kg)", "markets": "Markets reporting",
        "reports": "Reports", "spread_pct": "Gap between dearer and cheaper markets (%)"}),
        use_container_width=True, hide_index=True)
    st.caption("The gap compares the dearer and cheaper markets (90th and 10th percentile of market medians) and is shown "
               "only when at least 5 markets reported. A wide gap means farmers in some markets are paid much less.")
    st.download_button("Download the 2026 monthly table (CSV)", pm.to_csv(index=False).encode("utf-8"),
                       file_name="isoko_monthly_2026.csv", mime="text/csv")
    with st.expander("How to read this, and its limits"):
        st.markdown("- This covers **May 2026 onward only**. It shows what happened this year; it cannot prove a "
                    "repeating seasonal pattern, because that needs several years.\n"
                    "- Prices are farmgate prices reported by Esoko. In some months few markets reported, see the "
                    "table above.\n"
                    "- A month with data for only part of the month is marked (part).\n"
                    "- Source: Esoko Rwanda.")

# ---------------------------------------------------------------- SMS demo
elif page == "sms":
    st.subheader(T("page_sms"))
    st.caption("A farmer with any phone texts a short message and gets a short reply, in English or Kinyarwanda. "
               "This is a demonstration: no real SMS is sent.")
    st.markdown("**Type your message the way you would text it, then press Enter.**")
    st.caption("Write a short command or a normal sentence, in Kinyarwanda or English. For example: `GURISHA IBISHYIMBO IBIRO 500 NYABUGOGO`, `Ndashaka kugurisha ibishyimbo ibiro 500 i Nyabugogo. Nabigurisha he?`, `I want to sell 300 kg of rice at Huye` or `Ibijumba bigura angahe?`. The reply comes back in the language you wrote.")
    msg = st.text_input("Your message", value="", placeholder="GURISHA IBISHYIMBO IBIRO 500 NYABUGOGO",
                        key="sms_free_text")
    if msg.strip():
        res = isoko_sms.handle_sms(msg, df, markets, road_km)
        st.markdown("**Reply:**")
        st.code(res["reply"], language=None)
        st.caption(f"{res['length']} characters, {res['segments']} SMS (one SMS holds 160 characters).")
    else:
        st.info("Waiting for your message. Type a message above.")
    with st.expander("How to write a message"):
        st.markdown("- `SELL <crop> <kg> <market>` or `GURISHA <igihingwa> IBIRO <kg> <isoko>`\n"
                    "- `PRICE <crop>` or `IGICIRO <igihingwa>`\n"
                    "- `HELP` or `UBUFASHA`\n\n"
                    "Crops: beans (ibishyimbo), cassava (imyumbati), potatoes (ibirayi), maize (ibigori), "
                    "rice (umuceri), sweet potatoes (ibijumba), tomatoes (inyanya).")
