/* Isoko Smart AI - React dashboard. Reads data.json made by tools/export_web_data.py (real Esoko prices). */
const { useState, useMemo, useEffect } = React;

/* ------------------------------------------------------------------ text */
const MONTHS = {
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
  rw: ["Mut", "Gas", "Wer", "Mat", "Gic", "Kam", "Nya", "Kan", "Nze", "Ukw", "Ugu", "Ukb"],
};
const UI = {
  en: {
    nav_home: "Home", nav_farmer: "Farmer", nav_gov: "Government",
    brand_tag: "Know the market. Choose wisely. Earn more.",
    sub_sell: "Where to sell", sub_trends: "Price trends", sub_board: "Price board",
    sub_overview: "National overview", sub_monthly: "Monthly movement", sub_markets: "Market comparison", sub_trust: "Data and trust",
    hero_kicker: "Rwanda crop prices, made useful",
    hero_cta_farmer: "I am a farmer", hero_cta_gov: "I work in government",
    live_title: "Prices today", live_sub: "Median farmgate price across markets that reported in the last 14 days",
    per_kg: "RWF per kg", markets_n: "{n} markets", range: "Range",
    pick_crop: "Crop", pick_product: "Variety", pick_origin: "Where are you now?", pick_qty: "Quantity (kg)",
    rate: "Transport cost (RWF per kg per km)", safer: "Ignore markets with one report only",
    adv_title: "Our advice", income_chart: "Income after transport, by market (RWF)",
    rank_title: "All markets, best first", why_title: "Why this market, or why not",
    stab_title: "Does the advice survive a wrong transport cost?", stab_cost: "Transport cost", stab_best: "Best market", stab_worth: "Worth the trip",
    col_market: "Market", col_price: "Price (RWF/kg)", col_km: "Distance (km)", col_transport: "Transport (RWF)", col_income: "Income (RWF)",
    col_trust: "Trust", col_district: "District", col_reports: "Report days", col_last: "Last price", col_vs: "Against median",
    road: "road", estimate: "estimate", same: "own market",
    trend_title: "Price trend", trend_market: "Weekly median across markets",
    trend_up: "Prices are going up", trend_down: "Prices are going down", trend_steady: "Prices are steady", trend_unknown: "Not enough weeks to judge a direction",
    trend_pct: "{pct}% over the last 2 weeks compared with the 4 before",
    no_forecast: "No next-week forecast is shown. In testing it did not beat \"same as last week\", so showing it would mislead.",
    sms_title: "No smartphone? Use SMS", sms_body: "Text a short command and get a reply of 160 characters or fewer, in English or Kinyarwanda. Example:",
    sms_note: "SMS is a working prototype in the Streamlit app. A live number needs an SMS provider.",
    kpi_records: "Price records", kpi_markets: "Markets", kpi_crops: "Crops", kpi_latest: "Latest price",
    story_title: "What happened to prices", story_sub: "Median farmgate price, first month to latest month",
    rising: "Rising", falling: "Falling", steady: "Steady", since: "since {m}", how_sure: "How sure", ev_Good: "Good", ev_Limited: "Limited", ev_Weak: "Weak",
    monthly_title: "Month by month, 2026", monthly_sub: "Median price of all reporting markets. May to latest month.",
    partial: "partial month", all_crops: "All crops together", copy_csv: "Copy table as CSV", copied: "Copied",
    col_month: "Month", col_median: "Median (RWF/kg)", col_nm: "Markets", col_rep: "Reports", col_gap: "Gap (%)",
    mk_cov_title: "Reports by market, all crops", crops_n: "Crops", records_n: "Records",
    ml_title: "Do trained AI models beat simple rules?", ml_method: "Method", ml_err: "Average error (RWF/kg)", ml_type: "Type", ml_vs: "Against best rule",
    bt_title: "Next-week forecast test", bt_won: "Series won (%)",
    limits_title: "Limits you should know",
    lim1: "One source: Esoko Rwanda farmgate prices, from May 2026. Some markets report rarely.",
    lim2: "Transport costs are planning figures. The advice page tests whether the answer changes if they are wrong.",
    lim3: "The monthly view shows what happened in 2026. It cannot prove a seasonal pattern, which needs several years.",
    footer_src: "Prices: Esoko Rwanda farmgate reports. Data from {a} to {b}.",
    tx_quotes: "Vehicle figures come from {n} real transport quotes. Your own quote may differ, so you can change them.", tx_trips: "This load needs {n} trips.",
    sub_sms: "SMS",
    sms_h: "Try the SMS service", sms_p: "Type a message the way a farmer would text it, in English or Kinyarwanda.", sms_ph: "GURISHA IBISHYIMBO IBIRO 500 NYABUGOGO",
    sms_send: "Send", sms_reply: "Reply", sms_chars: "{n} characters, {s} SMS", sms_off: "The SMS service answers only when this page is served by the Isoko server (server.py).",
    sms_ex: "Examples",
    fb_q: "Was this advice useful?", fb_yes: "Yes", fb_no: "No", fb_thanks: "Thank you. Your answer was saved.", fb_off: "Thank you. (Answers are saved only when the Isoko server is running.)",
    stale_banner: "Prices are {n} days old (newest {date}). Check today's price at the market before you travel.",
    loading: "Loading prices...", load_fail: "The price file could not be loaded.",
    theme: "Theme", ev_note: "Evidence",
    ask_gov: "Open government dashboard", ask_farm: "Open farmer dashboard", try_it: "Try it with your own crop",
    ex_for: "Example: a farmer at {origin} with {qty} kg of {crop}", unranked: "Not ranked: no known distance",
    quality_title: "How far can you trust this?",
    q_gate: "Trained models are used only when they beat the best simple rule by {n}% or more.",
  },
  rw: {
    nav_home: "Ahabanza", nav_farmer: "Umuhinzi", nav_gov: "Leta",
    brand_tag: "Menya isoko. Hitamo neza. Ungukire.",
    sub_sell: "Aho kugurisha", sub_trends: "Uko ibiciro bihinduka", sub_board: "Ibiciro by'uyu munsi",
    sub_overview: "Incamake y'igihugu", sub_monthly: "Ukwezi ku kwezi", sub_markets: "Kugereranya amasoko", sub_trust: "Amakuru no kwizerwa",
    hero_kicker: "Ibiciro by'ibihingwa mu Rwanda, bifite akamaro",
    hero_cta_farmer: "Ndi umuhinzi", hero_cta_gov: "Nkorera Leta",
    live_title: "Ibiciro by'uyu munsi", live_sub: "Igiciro rwagati ku muhanda mu masoko yatanze amakuru mu minsi 14 ishize",
    per_kg: "FRW ku kilo", markets_n: "Amasoko {n}", range: "Hagati ya",
    pick_crop: "Igihingwa", pick_product: "Ubwoko", pick_origin: "Ubu uri he?", pick_qty: "Ingano (kg)",
    rate: "Igiciro cy'ubwikorezi (FRW ku kilo ku kilometero)", safer: "Ntiharebwe amasoko afite raporo imwe gusa",
    adv_title: "Inama yacu", income_chart: "Inyungu nyuma y'ubwikorezi, ku isoko (FRW)",
    rank_title: "Amasoko yose, ahambere hejuru", why_title: "Impamvu iri soko, cyangwa impamvu atari ryo",
    stab_title: "Inama ihinduka iyo ubwikorezi butari bwo?", stab_cost: "Ubwikorezi", stab_best: "Isoko ryiza", stab_worth: "Bikwiye urugendo",
    col_market: "Isoko", col_price: "Igiciro (FRW/kg)", col_km: "Intera (km)", col_transport: "Ubwikorezi (FRW)", col_income: "Inyungu (FRW)",
    col_trust: "Kwizerwa", col_district: "Akarere", col_reports: "Iminsi", col_last: "Igiciro cya nyuma", col_vs: "Ugereranyije n'igiciro rwagati",
    road: "umuhanda", estimate: "igereranyo", same: "isoko ryawe",
    trend_title: "Uko igiciro gihinduka", trend_market: "Igiciro rwagati cy'icyumweru mu masoko yose",
    trend_up: "Ibiciro biri kuzamuka", trend_down: "Ibiciro biri kumanuka", trend_steady: "Ibiciro biracyari bimwe", trend_unknown: "Nta byumweru bihagije byo kumenya icyerekezo",
    trend_pct: "{pct}% mu byumweru 2 bishize ugereranyije n'ibya 4 byabanje",
    no_forecast: "Nta igereranya ry'icyumweru gitaha ryerekanwa. Mu bipimo ntiryatsinze \"nk'icyumweru gishize\", bityo kuryerekana byayobya.",
    sms_title: "Nta telefone igezweho? Koresha SMS", sms_body: "Ohereza itegeko rigufi ubone igisubizo kitarenza inyuguti 160, mu Kinyarwanda cyangwa mu Cyongereza. Urugero:",
    sms_note: "SMS ni igerageza rikora muri porogaramu ya Streamlit. Nimero ya nyayo isaba umutanga serivisi wa SMS.",
    kpi_records: "Ibiciro byanditswe", kpi_markets: "Amasoko", kpi_crops: "Ibihingwa", kpi_latest: "Igiciro cya vuba",
    story_title: "Uko ibiciro byagenze", story_sub: "Igiciro rwagati ku muhanda, kuva ukwezi kwa mbere kugeza ukwa vuba",
    rising: "Birazamuka", falling: "Biramanuka", steady: "Biracyari bimwe", since: "kuva muri {m}", how_sure: "Kwizerwa", ev_Good: "Hejuru", ev_Limited: "Hagati", ev_Weak: "Hasi",
    monthly_title: "Ukwezi ku kwezi, 2026", monthly_sub: "Igiciro rwagati cy'amasoko yose yatanze amakuru. Kuva muri Gicurasi.",
    partial: "ukwezi kudashize", all_crops: "Ibihingwa byose hamwe", copy_csv: "Kopera imbonerahamwe (CSV)", copied: "Byakoporowe",
    col_month: "Ukwezi", col_median: "Rwagati (FRW/kg)", col_nm: "Amasoko", col_rep: "Ibyanditswe", col_gap: "Itandukaniro (%)",
    mk_cov_title: "Amakuru ku isoko, ibihingwa byose", crops_n: "Ibihingwa", records_n: "Ibyanditswe",
    ml_title: "Moderi zatojwe zitsinda amategeko yoroshye?", ml_method: "Uburyo", ml_err: "Ikosa rya rusange (FRW/kg)", ml_type: "Ubwoko", ml_vs: "Ugereranyije n'itegeko ryiza",
    bt_title: "Ikizamini cy'igereranya ry'icyumweru gitaha", bt_won: "Ibyatsinzwe (%)",
    limits_title: "Aho bigarukira",
    lim1: "Isoko rimwe ry'amakuru: ibiciro bya Esoko Rwanda, kuva muri Gicurasi 2026. Amasoko amwe atanga amakuru gake.",
    lim2: "Ibiciro by'ubwikorezi ni ibigereranyo. Urupapuro rw'inama rugerageza niba igisubizo cyahinduka iyo bitari byo.",
    lim3: "Ibisubizo by'amezi byerekana ibyabaye muri 2026. Ntibishobora kwemeza ibihe bisubiramo, bisaba imyaka myinshi.",
    footer_src: "Ibiciro: raporo za Esoko Rwanda. Amakuru kuva {a} kugeza {b}.",
    tx_quotes: "Ibiciro by'ibinyabiziga bivuye ku biciro nyakuri {n} by'ubwikorezi. Igiciro cyawe gishobora gutandukana, bityo urashobora kubihindura.", tx_trips: "Uyu mutwaro ukeneye ingendo {n}.",
    sub_sms: "SMS",
    sms_h: "Gerageza serivisi ya SMS", sms_p: "Andika ubutumwa nk'uko umuhinzi yabwandika kuri telefone, mu Kinyarwanda cyangwa mu Cyongereza.", sms_ph: "GURISHA IBISHYIMBO IBIRO 500 NYABUGOGO",
    sms_send: "Ohereza", sms_reply: "Igisubizo", sms_chars: "Inyuguti {n}, SMS {s}", sms_off: "Serivisi ya SMS ikora gusa iyo uru rupapuro rutangwa na seriveri ya Isoko (server.py).",
    sms_ex: "Ingero",
    fb_q: "Iyi nama yaragufashije?", fb_yes: "Yego", fb_no: "Oya", fb_thanks: "Murakoze. Igisubizo cyanyu cyabitswe.", fb_off: "Murakoze. (Ibisubizo bibikwa gusa iyo seriveri ya Isoko iri gukora.)",
    stale_banner: "Ibiciro bimaze iminsi {n} (ibya vuba: {date}). Subiza ku isoko urebe igiciro cy'uyu munsi mbere yo gutega.",
    loading: "Biri gushakwa...", load_fail: "Ibiciro ntibyabashije gufungurwa.",
    theme: "Insanganyamatsiko", ev_note: "Ibimenyetso",
    ask_gov: "Fungura urubuga rwa Leta", ask_farm: "Fungura urubuga rw'umuhinzi", try_it: "Gerageza n'igihingwa cyawe",
    ex_for: "Urugero: umuhinzi i {origin} ufite ibiro {qty} bya {crop}", unranked: "Ntiriringanywa: intera ntizwi",
    quality_title: "Wakwizera amakuru angana ate?",
    q_gate: "Moderi zatojwe zikoreshwa gusa iyo zitsinze itegeko ryoroshye ryiza kuri {n}% cyangwa hejuru.",
  },
};

/* ------------------------------------------------------------------ helpers */
const num = (n) => Math.round(n).toLocaleString("en-US");
const fill = (s, v = {}) => String(s || "").replace(/\{(\w+)\}/g, (_, k) => (v[k] === undefined ? "{" + k + "}" : v[k]));
const med = (a) => { const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const dateOf = (iso, lang) => { const [y, m, d] = iso.split("-").map(Number); return `${d} ${MONTHS[lang][m - 1]} ${y}`; };
const monthOf = (iso, lang) => { const [y, m] = iso.split("-").map(Number); return `${MONTHS[lang][m - 1]}`; };
const niceTicks = (lo, hi, n = 5) => {
  if (hi === lo) hi = lo + 1;
  const raw = (hi - lo) / n, p = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / p;
  const step = (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p;
  const a = Math.floor(lo / step) * step, out = [];
  for (let v = a; v <= hi + step * 0.999; v += step) out.push(Math.round(v * 1e6) / 1e6);
  return out;
};

/* ------------------------------------------------------------------ the advice engine (same maths as isoko_core.py) */
/* tx is either a number (RWF per kg per km) or { capacity, perKm, round } for a vehicle (trips x distance x cost per km) */
const VEH_NAMES = {
  en: { "Motorbike": "Motorbike", "Car (saloon)": "Car", "Pickup / small van": "Pickup / van", "Truck": "Truck", own: "My own quote" },
  rw: { "Motorbike": "Moto", "Car (saloon)": "Imodoka", "Pickup / small van": "Pikipu / imodoka ntoya", "Truck": "Ikamyo", own: "Igiciro cyanjye bwite" },
};
function transportCost(tx, qty, km, scale) {
  if (typeof tx === "number") return { cost: qty * tx * scale * km, trips: km > 0 ? 1 : 0 };
  const trips = Math.max(Math.ceil(qty / tx.capacity), 1);
  return { cost: km > 0 ? trips * (tx.round ? 2 : 1) * km * tx.perKm * scale : 0, trips: km > 0 ? trips : 0 };
}
function rankMarkets(D, crop, product, origin, qty, tx, safer, scale = 1) {
  let rows = ((D.cur[crop] || {})[product] || []).map(([loc, price, days, last, old, rel]) => ({ loc, price, days, last, old, rel }));
  const dm = D.dist[origin] || {};
  const info = (r) => dm[r.loc];
  if (safer) {
    const keep = rows.filter((r) => r.days >= 2 || (info(r) && info(r)[0] === 0));
    const others = keep.filter((r) => !(info(r) && info(r)[0] === 0)).length;
    if (others >= 2) rows = keep;
  }
  rows = rows.map((r) => {
    const d = info(r), km = d && d[0] != null ? d[0] : null;
    const src = !d || km == null ? "unknown" : d[1] === "s" ? "same" : d[1] === "r" ? "road" : "estimate";
    const t = km == null ? null : transportCost(tx, qty, km, scale);
    return { ...r, km, src, transport: t && t.cost, trips: t && t.trips, net: km == null ? null : qty * r.price - t.cost };
  });
  rows.sort((a, b) => (b.net ?? -Infinity) - (a.net ?? -Infinity));
  rows.forEach((r, i) => (r.rank = i + 1));
  return rows;
}
function recommend(rows) {
  const known = rows.filter((r) => r.net != null);
  if (!known.length) return null;
  const best = known[0];
  const home = known.filter((r) => r.km === 0);
  const base = home[0] || [...known].sort((a, b) => a.km - b.km)[0];
  const uplift = best.net - base.net;
  const pct = base.net ? (uplift / base.net) * 100 : 0;
  return { best, base, uplift, pct, worthwhile: best.loc !== base.loc && pct >= 5 };
}
function stability(D, crop, product, origin, qty, tx, safer) {
  const by = {}, scales = [0.5, 1, 1.5, 2];
  scales.forEach((s) => {
    const rec = recommend(rankMarkets(D, crop, product, origin, qty, tx, safer, s));
    by[s] = rec && { best: rec.best.loc, worthwhile: rec.worthwhile };
  });
  const b = by[1];
  const stable = !!b && scales.every((s) => by[s] && by[s].best === b.best && by[s].worthwhile === b.worthwhile);
  return { by, stable };
}
function whyText(S, rows, rec) {
  const T = (k, v) => fill(S[k], v);
  const m = num;
  return rows.map((r) => {
    if (r.net == null) return T("why_missing");
    const { best, base } = rec;
    const note = r.rel === "Low" ? S.why_note_low : "";
    const km = Math.round(r.km), gap = best.net - r.net;
    if (r.loc === base.loc && r.loc === best.loc) return T("why_home_best", { gain: 5, note });
    if (r.loc === best.loc) return rec.worthwhile
      ? T("why_best_rec", { transport: m(r.transport), km, net: m(r.net), uplift: m(rec.uplift), pct: Math.round(rec.pct), base: base.loc, note })
      : T("why_best_not", { pct: Math.round(rec.pct), base: base.loc, gain: 5, note });
    if (r.loc === base.loc) return T("why_home", { net: m(r.net), best: best.loc, diff: m(gap), note });
    if (r.price > best.price) return T("why_more_price", { price: m(r.price), best_price: m(best.price), km, transport: m(r.transport), gap: m(gap), best: best.loc, note });
    if (r.price < best.price && r.transport < best.transport) return T("why_closer", { km, price: m(r.price), best_price: m(best.price), gap: m(gap), best: best.loc, note });
    if (r.price < best.price) return T("why_less_price", { price: m(r.price), best_price: m(best.price), km, transport: m(r.transport), gap: m(gap), best: best.loc, note });
    return T("why_same_price", { best: best.loc, km, gap: m(gap), note });
  });
}
function adviceText(D, lang, rec, qty) {
  const S = D.strings[lang], money = (x) => `${num(x)} ${lang === "rw" ? "FRW" : "RWF"}`;
  const level = rec.best.rel, badge = fill(S.badge, { level: S["level_" + level] });
  if (rec.worthwhile) return { kind: "sell", level, badge, head: fill(S.head_sell, { market: rec.best.loc }),
    body: fill(S.body_sell, { net: money(rec.best.net), qty: num(qty), uplift: money(rec.uplift), pct: Math.round(rec.pct), base: rec.base.loc, price: money(rec.best.price), date: dateOf(rec.best.last, lang) }) };
  return { kind: "stay", level, badge, head: fill(S.head_stay, { market: rec.base.loc }),
    body: fill(S.body_stay, { net: money(rec.base.net), qty: num(qty), price: money(rec.base.price) }) };
}
function cropBoard(D) {
  return Object.keys(D.crops).map((crop) => {
    const products = D.crops[crop].filter((p) => (D.cur[crop] || {})[p]);
    const product = products[0];
    const rows = product ? D.cur[crop][product] : [];
    const prices = rows.map((r) => r[1]);
    return { crop, product, n: rows.length, median: prices.length ? med(prices) : null, lo: prices.length ? Math.min(...prices) : null, hi: prices.length ? Math.max(...prices) : null };
  });
}
function trendSignal(vals) {
  if (vals.length < 6) return { dir: "unknown", pct: null };
  const now = med(vals.slice(-2)), before = med(vals.slice(-6, -2)), pct = ((now - before) / before) * 100;
  return { dir: pct > 5 ? "up" : pct < -5 ? "down" : "steady", pct };
}
const toCsv = (rows) => rows.map((r) => r.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");

/* ------------------------------------------------------------------ illustrations (original artwork) */
const CROP_TINT = { Beans: "#F3DDD3", Cassava: "#EADFCB", "Irish Potatoes": "#F2E6C4", Maize: "#FFF0B0", Rice: "#F4EBC8", "Sweet Potatoes": "#E9D6EC", Tomatoes: "#FAD9D3" };
function CropArtIcon({ crop, size = 56 }) {
  const art = {
    Beans: <g><path d="M14 38c-4-10 2-22 14-24 8-1 12 6 8 14-4 9-16 17-22 10z" fill="#9B3A2E" /><path d="M30 46c-2-9 4-20 14-24 8-3 12 5 8 12-5 9-18 17-22 12z" fill="#B9503F" /><ellipse cx="25" cy="25" rx="3" ry="1.6" fill="#E9B7A8" transform="rotate(-30 25 25)" /><ellipse cx="42" cy="33" rx="3" ry="1.6" fill="#EBC1B3" transform="rotate(-30 42 33)" /></g>,
    Rice: <g><path d="M20 54c0-18 4-32 20-42" stroke="#6E8F3A" strokeWidth="3" fill="none" strokeLinecap="round" />{[[26, 40], [30, 32], [36, 25], [41, 18], [24, 46], [33, 40], [39, 32], [44, 25]].map(([x, y], i) => <ellipse key={i} cx={x} cy={y} rx="3.2" ry="6" fill="#E2B93B" transform={`rotate(${35 + (i % 4) * 6} ${x} ${y})`} />)}</g>,
    Cassava: <g><path d="M12 50c6-18 20-34 40-38 4 8-2 20-14 30-8 7-20 11-26 8z" fill="#8A5A36" /><path d="M16 49c6-12 17-25 33-32" stroke="#B88A5E" strokeWidth="2.5" fill="none" strokeLinecap="round" /><circle cx="52" cy="12" r="3" fill="#EFE3CF" /></g>,
    "Irish Potatoes": <g><ellipse cx="25" cy="36" rx="15" ry="12" fill="#C49A55" transform="rotate(-15 25 36)" /><ellipse cx="42" cy="30" rx="12" ry="10" fill="#D5AE68" transform="rotate(20 42 30)" />{[[20, 33], [29, 40], [38, 27], [46, 32]].map(([x, y], i) => <circle key={i} cx={x} cy={y} r="1.6" fill="#7C5A28" />)}</g>,
    Maize: <g><path d="M32 8c9 6 13 18 11 34-2 8-6 12-11 14-5-2-9-6-11-14C19 26 23 14 32 8z" fill="#F2C200" />{[18, 26, 34, 42].map((y) => <path key={y} d={`M22 ${y}h20`} stroke="#C79A00" strokeWidth="1.4" />)}{[26, 32, 38].map((x) => <path key={x} d={`M${x} 14v38`} stroke="#C79A00" strokeWidth="1.4" />)}<path d="M32 58C18 54 10 40 12 26c8 4 14 12 16 24zM32 58c14-4 22-18 20-32-8 4-14 12-16 24z" fill="#3E8E4F" /></g>,
    "Sweet Potatoes": <g><path d="M8 40c4-12 18-18 34-14 8 2 14 8 14 14-2 8-14 10-26 8-12-1-24-2-22-8z" fill="#9A4F86" /><path d="M14 40c8-6 22-8 34-4" stroke="#C487B5" strokeWidth="2.4" fill="none" strokeLinecap="round" /><circle cx="46" cy="38" r="1.6" fill="#6C3260" /></g>,
    Tomatoes: <g><circle cx="32" cy="36" r="19" fill="#D8412F" /><ellipse cx="25" cy="29" rx="5" ry="3" fill="#EF7B6B" transform="rotate(-30 25 29)" /><path d="M32 18l-6 6 6-2 6 2-6-6zM32 18l-9-2 7 5zM32 18l9-2-7 5z" fill="#3E8E4F" stroke="#3E8E4F" strokeWidth="1.5" strokeLinejoin="round" /></g>,
  }[crop];
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} role="img" aria-label={crop} style={{ flex: "none" }}>
      <rect width="64" height="64" rx="16" fill={CROP_TINT[crop] || "#E6EEE6"} />
      {art}
    </svg>
  );
}

const PHOTO = { Beans: "beans", Cassava: "cassava", "Irish Potatoes": "irish_potatoes", Maize: "maize", Rice: "rice", "Sweet Potatoes": "sweet_potatoes", Tomatoes: "tomatoes" };
/* real photographs of the crops (web/img); the drawn icon is the fallback if a photo is missing */
function CropIcon({ crop, size = 56 }) {
  const [bad, setBad] = useState(false);
  if (bad || !PHOTO[crop]) return <CropArtIcon crop={crop} size={size} />;
  return <img src={`img/${PHOTO[crop]}.jpg`} alt={crop} width={size} height={size} loading="lazy" onError={() => setBad(true)}
    style={{ width: size, height: size, borderRadius: Math.round(size * 0.25), objectFit: "cover", flex: "none", background: "#F6EFD9" }} />;
}
function CropPhoto({ crop, className }) {
  const [bad, setBad] = useState(false);
  if (bad || !PHOTO[crop]) return <div className={className} style={{ display: "flex", alignItems: "center", justifyContent: "center", background: CROP_TINT[crop] || "#E6EEE6" }}><CropArtIcon crop={crop} size={64} /></div>;
  return <img src={`img/${PHOTO[crop]}.jpg`} alt={crop} loading="lazy" onError={() => setBad(true)} className={className} style={{ objectFit: "cover", background: "#F6EFD9" }} />;
}

function HillsArt() {
  const hill = (y, c, k) => <path key={k} d={`M0 ${y} C 90 ${y - 46}, 170 ${y + 8}, 260 ${y - 30} S 420 ${y - 54}, 520 ${y - 14} S 640 ${y - 40}, 720 ${y - 8} V 360 H 0 Z`} fill={c} />;
  const rows = (y, c, n) => Array.from({ length: n }, (_, i) => <path key={i} d={`M${40 + i * 18} ${y + i * 11} q 170 -34 360 -6`} stroke={c} strokeWidth="2" fill="none" opacity="0.55" strokeLinecap="round" />);
  return (
    <svg viewBox="0 0 720 360" className="w-full h-auto block" role="img" aria-label="Terraced hills with three markets joined by a route" preserveAspectRatio="xMidYMax slice">
      <circle cx="590" cy="82" r="42" fill="#F2C200" />
      <circle cx="590" cy="82" r="62" fill="#F2C200" opacity=".16" />
      {hill(190, "#1B5E3C", 1)}
      {rows(190, "#2C8554", 4)}
      {hill(240, "#17503A", 2)}
      {rows(246, "#3A9A63", 4)}
      {hill(300, "#10382A", 3)}
      <path className="route" d="M120 292 C 220 230, 300 262, 380 214 S 520 170, 610 196" stroke="#F2C200" strokeWidth="3.5" fill="none" strokeDasharray="2 9" strokeLinecap="round" />
      {[[120, 292, "#fff"], [380, 214, "#fff"], [610, 196, "#F2C200"]].map(([x, y, c], i) => (
        <g key={i}><circle cx={x} cy={y} r={i === 2 ? 15 : 11} fill={c} opacity=".25" /><circle cx={x} cy={y} r={i === 2 ? 8 : 6} fill={c} stroke="#0E2A1F" strokeWidth="2" /></g>
      ))}
    </svg>
  );
}
function Logo({ size = 30 }) {
  return (
    <svg viewBox="0 0 40 40" width={size} height={size} aria-hidden="true">
      <rect width="40" height="40" rx="11" fill="#1E7A4C" />
      <path d="M0 29c6-9 13-8 19-3s13 4 21-4v18H0z" fill="#0E2A1F" />
      <circle cx="29" cy="12" r="5" fill="#F2C200" />
      <path d="M12 26c1-7 5-11 11-12-1 7-5 11-11 12z" fill="#fff" />
    </svg>
  );
}

/* ------------------------------------------------------------------ charts */
const axisText = { fontSize: 11, fill: "var(--muted)", fontFamily: "Inter, system-ui, sans-serif" };
function HBars({ items, unit, highlight }) {
  const W = 640, left = 130, right = 70, rowH = 30, top = 6, H = top + items.length * rowH + 22;
  const max = Math.max(...items.map((d) => d.value), 1), ticks = niceTicks(0, max, 4), top2 = ticks[ticks.length - 1];
  const x = (v) => left + (v / top2) * (W - left - right);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={unit}>
      {ticks.map((t) => <g key={t}><line x1={x(t)} x2={x(t)} y1={top} y2={H - 20} stroke="var(--line)" /><text x={x(t)} y={H - 6} textAnchor="middle" style={axisText}>{t >= 1000 ? num(t / 1000) + "k" : t}</text></g>)}
      {items.map((d, i) => {
        const y = top + i * rowH;
        return (
          <g key={d.label}>
            <text x={left - 8} y={y + 18} textAnchor="end" style={{ ...axisText, fontSize: 12, fill: "var(--ink)" }}>{d.label.length > 17 ? d.label.slice(0, 16) + "…" : d.label}</text>
            <rect x={left} y={y + 5} width={Math.max(x(d.value) - left, 2)} height={18} rx="4" fill={d.label === highlight ? "var(--leaf)" : "var(--bar)"} />
            <text x={x(d.value) + 6} y={y + 18} style={{ ...axisText, fill: "var(--ink)" }}>{d.text ?? num(d.value)}</text>
          </g>
        );
      })}
    </svg>
  );
}
function LineChart({ series, unit, h = 260, dates = false, lang }) {
  /* series: [{name,color,points:[[x,y]]}], x is a number (ordinal) with optional labels */
  const W = 640, L = 52, R = 14, T = 14, B = 28;
  const all = series.flatMap((s) => s.points), xs = all.map((p) => p[0]), ys = all.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), yt = niceTicks(Math.min(...ys) * 0.96, Math.max(...ys) * 1.04, 4);
  const y0 = yt[0], y1 = yt[yt.length - 1];
  const X = (v) => L + ((v - x0) / Math.max(x1 - x0, 1)) * (W - L - R), Y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (h - T - B);
  const xt = niceTicks(x0, x1, 5).filter((v) => v >= x0 && v <= x1);
  return (
    <svg viewBox={`0 0 ${W} ${h}`} className="w-full h-auto" role="img" aria-label={unit}>
      {yt.map((t) => <g key={t}><line x1={L} x2={W - R} y1={Y(t)} y2={Y(t)} stroke="var(--line)" /><text x={L - 8} y={Y(t) + 4} textAnchor="end" style={axisText}>{num(t)}</text></g>)}
      {xt.map((t) => <text key={t} x={X(t)} y={h - 8} textAnchor="middle" style={axisText}>{dates ? dates(t) : t}</text>)}
      {series.map((s) => {
        const d = s.points.map((p, i) => `${i ? "L" : "M"}${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(" ");
        const last = s.points[s.points.length - 1];
        return (
          <g key={s.name}>
            {s.area && <path d={`${d} L${X(last[0])} ${h - B} L${X(s.points[0][0])} ${h - B} Z`} fill={s.color} opacity=".10" />}
            <path d={d} fill="none" stroke={s.color} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
            <circle cx={X(last[0])} cy={Y(last[1])} r="4.5" fill={s.color} stroke="var(--surface)" strokeWidth="2" />
          </g>
        );
      })}
    </svg>
  );
}
function Columns({ items, unit, h = 240 }) {
  const W = 640, L = 52, R = 10, T = 22, B = 36, max = Math.max(...items.map((d) => d.value), 1), yt = niceTicks(0, max, 4), y1 = yt[yt.length - 1];
  const bw = Math.min(56, ((W - L - R) / items.length) * 0.62), step = (W - L - R) / items.length;
  const Y = (v) => T + (1 - v / y1) * (h - T - B);
  return (
    <svg viewBox={`0 0 ${W} ${h}`} className="w-full h-auto" role="img" aria-label={unit}>
      {yt.map((t) => <g key={t}><line x1={L} x2={W - R} y1={Y(t)} y2={Y(t)} stroke="var(--line)" /><text x={L - 8} y={Y(t) + 4} textAnchor="end" style={axisText}>{num(t)}</text></g>)}
      {items.map((d, i) => {
        const cx = L + step * i + step / 2;
        return (
          <g key={d.label}>
            <rect x={cx - bw / 2} y={Y(d.value)} width={bw} height={h - B - Y(d.value)} rx="4" fill={d.color || "var(--bar)"} opacity={d.faint ? 0.55 : 1} />
            <text x={cx} y={Y(d.value) - 6} textAnchor="middle" style={{ ...axisText, fill: "var(--ink)" }}>{d.text ?? num(d.value)}</text>
            <text x={cx} y={h - 14} textAnchor="middle" style={axisText}>{d.label}</text>
          </g>
        );
      })}
    </svg>
  );
}

/* ------------------------------------------------------------------ small UI parts */
const cx = (...a) => a.filter(Boolean).join(" ");
function Card({ className, children, ...p }) { return <section {...p} className={cx("rounded-2xl border", /\bbg-/.test(className || "") ? "" : "bg-surface", /\bborder-/.test(className || "") ? "" : "border-line", className)}>{children}</section>; }
function Pill({ tone = "leaf", children }) {
  const t = { leaf: "bg-leafsoft text-leaf", sun: "bg-sunsoft text-ink", bad: "bg-badsoft text-bad", sky: "bg-skysoft text-sky" }[tone];
  return <span className={cx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold", t)}>{children}</span>;
}
const relTone = { High: "leaf", Medium: "sun", Low: "bad" };
function Field({ id, label, children }) {
  return <div className="flex flex-col gap-1.5"><label htmlFor={id} className="text-sm font-medium text-ink">{label}</label>{children}</div>;
}
const inputCls = "w-full rounded-xl border border-line bg-surface px-3 py-2.5 text-ink text-[15px] focus:outline-none focus:ring-2 focus:ring-leaf";
function Tabs({ items, value, onChange }) {
  return (
    <div role="tablist" className="flex gap-1 overflow-x-auto rounded-xl bg-leafsoft p-1 w-fit max-w-full">
      {items.map(([k, label]) => (
        <button key={k} role="tab" aria-selected={value === k} onClick={() => onChange(k)}
          className={cx("whitespace-nowrap rounded-lg px-3.5 py-2 text-sm font-semibold transition", value === k ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink")}>{label}</button>
      ))}
    </div>
  );
}
function Stat({ label, value, sub }) {
  return (
    <div className="rounded-2xl bg-surface border border-line p-4">
      <div className="text-xs uppercase tracking-wide text-muted font-semibold">{label}</div>
      <div className="font-display text-3xl font-bold text-ink mt-1 tabular-nums">{value}</div>
      {sub && <div className="text-sm text-muted mt-0.5">{sub}</div>}
    </div>
  );
}
function CopyBtn({ rows, tr }) {
  const [done, setDone] = useState(false);
  const go = () => {
    const text = toCsv(rows);
    const ok = () => { setDone(true); setTimeout(() => setDone(false), 1800); };
    try { navigator.clipboard.writeText(text).then(ok, () => {}); } catch (e) { /* no clipboard here */ }
  };
  return <button onClick={go} className="rounded-lg border border-line px-3 py-1.5 text-sm font-medium text-ink hover:bg-leafsoft">{done ? tr("copied") : tr("copy_csv")}</button>;
}
function DataTable({ head, rows, className }) {
  return (
    <div className={cx("overflow-x-auto rounded-xl border border-line", className)}>
      <table className="w-full min-w-[520px] text-sm">
        <thead><tr className="bg-leafsoft text-left text-xs uppercase tracking-wide text-muted">{head.map((h, i) => <th key={i} className="px-3 py-2.5 font-semibold whitespace-nowrap">{h}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i} className="border-t border-line">{r.map((c, j) => <td key={j} className="px-3 py-2.5 tabular-nums align-top">{c}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ pages */
function Home({ D, lang, tr, go }) {
  const S = D.strings[lang], board = useMemo(() => cropBoard(D), [D]);
  const ex = useMemo(() => {
    const origin = D.dist["Nyabugogo"] ? "Nyabugogo" : Object.keys(D.dist)[0];
    const tries = [...board].sort((a, b) => b.n - a.n).map((c) => {
      const rec = recommend(rankMarkets(D, c.crop, c.product, origin, 500, D.rate, true));
      return rec && { crop: c.crop, origin, rec };
    }).filter(Boolean);
    const pick = tries.find((t) => t.rec.worthwhile && t.rec.best.rel !== "Low") || tries[0];   // prefer an example with trustworthy data
    return pick && { ...pick, adv: adviceText(D, lang, pick.rec, 500) };
  }, [D, board, lang]);
  const cropLabel = (c) => (lang === "rw" ? D.cropnames[c] || c : c);
  return (
    <div>
      <div className="bg-hero text-white">
        <div className="gutter mx-auto max-w-6xl grid md:grid-cols-2 gap-8 items-center py-12 md:py-16">
          <div className="min-w-0">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold tracking-wide text-sun"><span className="h-1.5 w-1.5 rounded-full bg-sun" />{tr("hero_kicker")}</div>
            <h1 className="font-display text-4xl sm:text-5xl font-extrabold leading-[1.05] mt-4 text-balance">{S.home_tag}</h1>
            <p className="mt-5 text-lg text-white/80 max-w-xl">{S.home_lead}</p>
            <div className="mt-7 flex flex-wrap gap-3">
              <button onClick={() => go("farmer")} className="rounded-xl bg-sun px-5 py-3 font-bold text-[#10261C] hover:brightness-105">{tr("hero_cta_farmer")}</button>
              <button onClick={() => go("gov")} className="rounded-xl border border-white/30 px-5 py-3 font-semibold text-white hover:bg-white/10">{tr("hero_cta_gov")}</button>
            </div>
          </div>
          <div className="min-w-0 rounded-3xl overflow-hidden bg-[#0A2219] ring-1 ring-white/10"><HillsArt /></div>
        </div>
        <div className="border-t border-white/10">
          <div className="gutter mx-auto max-w-6xl grid grid-cols-2 md:grid-cols-4 gap-y-4 py-5">
            {[[tr("kpi_records"), num(D.meta.records)], [tr("kpi_markets"), D.meta.markets], [tr("kpi_crops"), D.meta.crops], [tr("kpi_latest"), dateOf(D.meta.asof, lang)]].map(([l, v]) => (
              <div key={l}><div className="font-display text-2xl font-bold tabular-nums">{v}</div><div className="text-xs uppercase tracking-wide text-white/60">{l}</div></div>
            ))}
          </div>
        </div>
      </div>

      <div className="gutter mx-auto max-w-6xl py-12 space-y-14">
        <div>
          <h2 className="font-display text-2xl font-bold text-ink">{tr("live_title")}</h2>
          <p className="text-muted mt-1">{tr("live_sub")}</p>
          <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3">
            {board.map((b) => (
              <button key={b.crop} onClick={() => go("farmer", { crop: b.crop })} className="text-left rounded-2xl bg-surface border border-line p-4 hover:border-leaf transition">
                <CropPhoto crop={b.crop} className="w-full h-28 rounded-xl" />
                <div className="mt-3 font-semibold text-ink">{cropLabel(b.crop)}</div>
                <div className="font-display text-2xl font-bold text-ink tabular-nums">{b.median ? num(b.median) : "-"} <span className="text-xs font-medium text-muted">{tr("per_kg")}</span></div>
                <div className="text-xs text-muted mt-1">{fill(tr("markets_n"), { n: b.n })}{b.lo != null && <> · {num(b.lo)}-{num(b.hi)}</>}</div>
              </button>
            ))}
            <div className="rounded-2xl bg-leafsoft p-4 flex flex-col justify-between">
              <div className="text-sm text-ink">{tr("try_it")}</div>
              <button onClick={() => go("farmer")} className="mt-3 rounded-lg bg-leaf px-3 py-2 text-sm font-bold text-white">{tr("ask_farm")}</button>
            </div>
          </div>
        </div>

        {ex && (
          <div className="grid lg:grid-cols-5 gap-6 items-stretch">
            <div className="lg:col-span-2 min-w-0">
              <h2 className="font-display text-2xl font-bold text-ink">{S.home_example_title}</h2>
              <p className="text-muted mt-2">{fill(tr("ex_for"), { origin: ex.origin, qty: 500, crop: cropLabel(ex.crop) })}</p>
              <p className="mt-4 text-ink">{S.home_problem}</p>
            </div>
            <div className="lg:col-span-3 min-w-0"><AdviceBox adv={ex.adv} className="lg:h-full" /></div>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-5">
          <Card className="p-6"><div className="text-xs font-bold uppercase tracking-wide text-leaf">{S.home_for_farmer_title}</div><p className="mt-2 text-ink">{S.home_for_farmer}</p><button onClick={() => go("farmer")} className="mt-4 text-leaf font-semibold">{tr("ask_farm")} →</button></Card>
          <Card className="p-6"><div className="text-xs font-bold uppercase tracking-wide text-sky">{S.home_for_gov_title}</div><p className="mt-2 text-ink">{S.home_for_gov}</p><button onClick={() => go("gov")} className="mt-4 text-sky font-semibold">{tr("ask_gov")} →</button></Card>
        </div>

        <div>
          <h2 className="font-display text-2xl font-bold text-ink">{S.home_how_title}</h2>
          <div className="mt-5 grid md:grid-cols-3 gap-4">
            {["home_step1", "home_step2", "home_step3"].map((k) => {
              const [head, ...rest] = S[k].split(":");
              return <Card key={k} className="p-5"><div className="font-display text-lg font-bold text-ink">{head.replace(/^\d\.\s*/, "")}</div><p className="mt-1.5 text-muted">{rest.join(":").trim()}</p></Card>;
            })}
          </div>
        </div>

        <Card className="p-6 md:p-8 bg-sunsoft border-transparent">
          <h2 className="font-display text-2xl font-bold text-ink">{S.home_honest_title}</h2>
          <p className="mt-2 text-ink max-w-3xl">{S.home_honest}</p>
          {D.ml && <p className="mt-3 text-sm text-ink">{fill(tr("q_gate"), { n: D.ml.gate_needed_pct })} {D.ml.reason}</p>}
        </Card>
      </div>
    </div>
  );
}

function AdviceBox({ adv, className }) {
  const sell = adv.kind === "sell";
  return (
    <div className={cx("rounded-2xl p-6", className, sell ? "bg-leafsoft" : "bg-sunsoft")}>
      <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-muted"><span className={cx("h-2 w-2 rounded-full", sell ? "bg-leaf" : "bg-sun")} />Isoko</div>
      <h3 className="font-display text-2xl font-bold text-ink mt-2">{adv.head}</h3>
      <p className="mt-2 text-ink leading-relaxed">{adv.body}</p>
      <div className="mt-3"><Pill tone={relTone[adv.level]}>{adv.badge}</Pill></div>
    </div>
  );
}

function Sell({ D, lang, tr, preset }) {
  const S = D.strings[lang];
  const crops = Object.keys(D.crops);
  const [crop, setCrop] = useState(preset && crops.includes(preset) ? preset : "Beans");
  const products = D.crops[crop].filter((p) => (D.cur[crop] || {})[p]);
  const [product, setProduct] = useState(products[0]);
  useEffect(() => { setProduct(D.crops[crop].filter((p) => (D.cur[crop] || {})[p])[0]); }, [crop]);
  const origins = Object.keys(D.dist).sort();
  const [origin, setOrigin] = useState(origins.includes("Nyabugogo") ? "Nyabugogo" : origins[0]);
  const [qty, setQty] = useState(500);
  const [rate, setRate] = useState(D.rate);
  const [safer, setSafer] = useState(true);
  const vehicles = D.vehicles || {};
  const vnames = Object.keys(vehicles);
  const [method, setMethod] = useState("simple");
  const [veh, setVeh] = useState(vnames.includes("Pickup / small van") ? "Pickup / small van" : vnames[0]);
  const base = vehicles[veh] || { capacity_kg: 1000, rate_per_km: 500 };
  const [cap, setCap] = useState(null), [perKm, setPerKm] = useState(null), [roundTrip, setRoundTrip] = useState(true);
  useEffect(() => { setCap(null); setPerKm(null); }, [veh]);
  const capacity = Math.max(10, Number(cap ?? base.capacity_kg) || 10), perKmV = Math.max(0, Number(perKm ?? base.rate_per_km) || 0);
  const tx = method === "simple" ? rate : { capacity, perKm: perKmV, round: roundTrip };
  const vLabel = (v) => (VEH_NAMES[lang] || VEH_NAMES.en)[v] || v;
  const prod = products.includes(product) ? product : products[0];
  const q = Math.max(10, Number(qty) || 10);
  const rows = useMemo(() => rankMarkets(D, crop, prod, origin, q, tx, safer), [D, crop, prod, origin, q, method, rate, capacity, perKmV, roundTrip, safer]);
  const rec = useMemo(() => recommend(rows), [rows]);
  const stab = useMemo(() => stability(D, crop, prod, origin, q, tx, safer), [D, crop, prod, origin, q, method, rate, capacity, perKmV, roundTrip, safer]);
  const why = useMemo(() => (rec ? whyText(S, rows, rec) : []), [S, rows, rec]);
  const adv = rec && adviceText(D, lang, rec, q);
  const cropLabel = (c) => (lang === "rw" ? D.cropnames[c] || c : c);
  const top = rows.filter((r) => r.net != null).slice(0, 8);
  return (
    <div className="grid lg:grid-cols-[340px_minmax(0,1fr)] gap-6 items-start">
      <Card className="p-5 space-y-4 lg:sticky lg:top-24">
        <div>
          <div className="text-sm font-medium text-ink mb-2">{tr("pick_crop")}</div>
          <div className="grid grid-cols-4 gap-2">
            {crops.map((c) => (
              <button key={c} onClick={() => setCrop(c)} aria-pressed={crop === c} title={cropLabel(c)}
                className={cx("rounded-xl p-1.5 border-2 transition", crop === c ? "border-leaf bg-leafsoft" : "border-transparent hover:bg-leafsoft")}>
                <CropIcon crop={c} size={44} />
              </button>
            ))}
          </div>
          <div className="mt-2 font-semibold text-ink">{cropLabel(crop)}</div>
        </div>
        {products.length > 1 && (
          <Field id="product" label={tr("pick_product")}>
            <select id="product" className={inputCls} value={prod} onChange={(e) => setProduct(e.target.value)}>{products.map((p) => <option key={p}>{p}</option>)}</select>
          </Field>
        )}
        <Field id="origin" label={tr("pick_origin")}>
          <select id="origin" className={inputCls} value={origin} onChange={(e) => setOrigin(e.target.value)}>{origins.map((o) => <option key={o}>{o}</option>)}</select>
        </Field>
        <Field id="qty" label={tr("pick_qty")}>
          <input id="qty" type="number" min="10" step="50" className={inputCls} value={qty} onChange={(e) => setQty(e.target.value)} />
        </Field>
        <div className="space-y-3 rounded-xl border border-line p-3">
          <div className="text-sm font-semibold text-ink">{S.tx_title}</div>
          <div role="group" aria-label={S.tx_how} className="flex rounded-lg bg-leafsoft p-1 text-sm">
            {[["simple", S.tx_simple], ["vehicle", S.tx_vehicle]].map(([k, l]) => (
              <button key={k} onClick={() => setMethod(k)} aria-pressed={method === k} className={cx("flex-1 rounded-md px-2 py-1.5 font-semibold", method === k ? "bg-surface text-ink shadow-sm" : "text-muted")}>{l}</button>
            ))}
          </div>
          {method === "simple" ? (
            <Field id="rate" label={`${S.tx_rate}: ${rate.toFixed(2)}`}>
              <input id="rate" type="range" min="0" max="2" step="0.05" value={rate} onChange={(e) => setRate(Number(e.target.value))} className="w-full accent-[var(--leaf)]" />
              <span className="text-xs text-muted">{S.tx_rate_help}</span>
            </Field>
          ) : (
            <>
              <Field id="veh" label={S.tx_vehicle_pick}>
                <select id="veh" className={inputCls} value={veh} onChange={(e) => setVeh(e.target.value)}>{vnames.map((v) => <option key={v} value={v}>{vLabel(v)}</option>)}</select>
              </Field>
              <div className="grid grid-cols-2 gap-2">
                <Field id="cap" label={S.tx_capacity}><input id="cap" type="number" min="10" step="50" className={inputCls} value={cap ?? base.capacity_kg} onChange={(e) => setCap(e.target.value)} /></Field>
                <Field id="perkm" label={S.tx_per_km}><input id="perkm" type="number" min="0" step="50" className={inputCls} value={perKm ?? base.rate_per_km} onChange={(e) => setPerKm(e.target.value)} /></Field>
              </div>
              <label className="flex items-start gap-2 text-sm text-ink"><input type="checkbox" checked={roundTrip} onChange={(e) => setRoundTrip(e.target.checked)} className="mt-0.5 h-4 w-4 accent-[var(--leaf)]" />{S.tx_round}</label>
              <p className="text-xs text-muted">{base.n_quotes ? fill(tr("tx_quotes"), { n: base.n_quotes }) : S.tx_defaults}</p>
              <p className="text-xs text-ink">{S.tx_per_km_help} {Math.ceil(q / capacity) > 1 && fill(tr("tx_trips"), { n: Math.ceil(q / capacity) })}</p>
            </>
          )}
        </div>
        <label className="flex items-start gap-2 text-sm text-ink"><input type="checkbox" checked={safer} onChange={(e) => setSafer(e.target.checked)} className="mt-0.5 h-4 w-4 accent-[var(--leaf)]" />{tr("safer")}</label>
      </Card>

      <div className="space-y-6 min-w-0">
        {!rec ? <Card className="p-6 text-ink">{S.no_recent}</Card> : (
          <>
            <AdviceBox adv={adv} />
            <Feedback tr={tr} kind="advice" crop={crop} market={rec.best.loc} lang={lang} />
            {rec.best.rel === "Low" && <div className="rounded-xl bg-badsoft text-bad px-4 py-3 text-sm font-medium">{fill(S.warn_low, { market: rec.best.loc })}</div>}
            <div className={cx("rounded-xl px-4 py-3 text-sm font-medium", stab.stable ? "bg-leafsoft text-leaf" : "bg-sunsoft text-ink")}>{stab.stable ? "✓ " + S.stable_ok : "! " + S.stable_warn}</div>
            <Card className="p-5">
              <h3 className="font-display text-lg font-bold text-ink mb-3">{tr("income_chart")}</h3>
              <HBars items={top.map((r) => ({ label: r.loc, value: r.net, text: num(r.net) }))} unit={tr("income_chart")} highlight={rec.best.loc} />
            </Card>
            <Card className="p-5">
              <h3 className="font-display text-lg font-bold text-ink mb-3">{tr("rank_title")}</h3>
              <DataTable head={["#", tr("col_market"), tr("col_price"), tr("col_km"), tr("col_transport"), tr("col_income"), tr("col_trust")]}
                rows={rows.map((r) => [r.rank, <span className="font-semibold text-ink">{r.loc}</span>, num(r.price),
                  r.km == null ? tr("unranked") : <>{num(r.km)} <span className="text-xs text-muted">{tr(r.src)}</span></>,
                  r.transport == null ? "-" : <>{num(r.transport)}{method === "vehicle" && r.trips > 0 && <span className="text-xs text-muted"> ({r.trips}×)</span>}</>, r.net == null ? "-" : <b>{num(r.net)}</b>, <Pill tone={relTone[r.rel]}>{S["level_" + r.rel]}</Pill>])} />
            </Card>
            <Card className="p-5">
              <h3 className="font-display text-lg font-bold text-ink mb-3">{tr("why_title")}</h3>
              <ul className="space-y-2.5">
                {rows.filter((r) => r.net != null).slice(0, 8).map((r, i) => <li key={r.loc} className="text-sm text-ink"><b>{r.rank}. {r.loc}</b> — {why[rows.indexOf(r)]}</li>)}
              </ul>
            </Card>
            <Card className="p-5">
              <h3 className="font-display text-lg font-bold text-ink mb-3">{tr("stab_title")}</h3>
              <DataTable head={[tr("stab_cost"), tr("stab_best"), tr("stab_worth")]}
                rows={Object.entries(stab.by).map(([s, v]) => [`${s}x`, v ? v.best : "-", v ? (v.worthwhile ? S.yes : S.no) : "-"])} />
            </Card>
          </>
        )}
        <Card className="p-5 bg-skysoft border-transparent">
          <h3 className="font-display text-lg font-bold text-ink">{tr("sms_title")}</h3>
          <p className="text-sm text-ink mt-1">{tr("sms_body")}</p>
          <code className="mt-2 inline-block rounded-lg bg-surface px-3 py-2 text-sm text-ink">GURISHA IBISHYIMBO IBIRO 500 NYABUGOGO</code>
          <p className="text-xs text-muted mt-2">{tr("sms_note")}</p>
        </Card>
      </div>
    </div>
  );
}

function Feedback({ tr, kind, crop, market, lang }) {
  const [state, setState] = useState(null);
  const send = (useful) => {
    fetch("api/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ useful, kind, crop, market, lang }) })
      .then((r) => setState(r.ok ? "saved" : "off")).catch(() => setState("off"));
  };
  if (state) return <p className="text-sm text-muted">{state === "saved" ? tr("fb_thanks") : tr("fb_off")}</p>;
  return (
    <div className="flex flex-wrap items-center gap-3 text-sm text-ink">
      <span className="font-medium">{tr("fb_q")}</span>
      <button onClick={() => send(true)} className="rounded-lg border border-line px-3 py-1.5 font-semibold hover:bg-leafsoft">{"👍 " + tr("fb_yes")}</button>
      <button onClick={() => send(false)} className="rounded-lg border border-line px-3 py-1.5 font-semibold hover:bg-badsoft">{"👎 " + tr("fb_no")}</button>
    </div>
  );
}

function StaleBanner({ D, tr, lang }) {
  const age = Math.floor((Date.now() - Date.parse(D.meta.asof)) / 864e5);
  if (!(age > 7)) return null;
  return <div role="status" className="rounded-xl bg-sunsoft text-ink px-4 py-3 text-sm font-medium">{"! " + fill(tr("stale_banner"), { n: age, date: dateOf(D.meta.asof, lang) })}</div>;
}

function Sms({ D, lang, tr }) {
  const [text, setText] = useState("");
  const [out, setOut] = useState(null);
  const [busy, setBusy] = useState(false);
  const examples = ["GURISHA IBISHYIMBO IBIRO 500 NYABUGOGO", "Ndashaka kugurisha ibigori ibiro 300 i Musanze", "PRICE RICE", "HELP"];
  const send = (msg) => {
    const m = (msg ?? text).trim(); if (!m) return;
    setBusy(true);
    fetch("api/sms?format=json", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: m }) })
      .then((r) => (r.ok ? r.json() : Promise.reject())).then((j) => setOut({ ok: true, ...j })).catch(() => setOut({ ok: false }))
      .finally(() => setBusy(false));
  };
  return (
    <Card className="p-5 max-w-2xl">
      <h3 className="font-display text-lg font-bold text-ink">{tr("sms_h")}</h3>
      <p className="text-sm text-muted mt-1">{tr("sms_p")}</p>
      <form className="mt-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <label htmlFor="smsText" className="sr-only">SMS</label>
        <input id="smsText" className={inputCls} value={text} placeholder={tr("sms_ph")} onChange={(e) => setText(e.target.value)} maxLength={300} />
        <button type="submit" disabled={busy} className="rounded-xl bg-leaf px-5 py-2.5 font-bold text-white disabled:opacity-60">{tr("sms_send")}</button>
      </form>
      <div className="mt-3 flex flex-wrap gap-2 items-center"><span className="text-xs text-muted">{tr("sms_ex")}:</span>
        {examples.map((x) => <button key={x} onClick={() => { setText(x); send(x); }} className="rounded-full border border-line px-3 py-1 text-xs text-ink hover:bg-leafsoft">{x}</button>)}
      </div>
      {out && (out.ok
        ? <div className="mt-4 rounded-2xl bg-skysoft p-4"><div className="text-xs font-bold uppercase tracking-wide text-muted">{tr("sms_reply")}</div><p className="mt-1 text-ink text-lg">{out.reply}</p><p className="mt-2 text-xs text-muted">{fill(tr("sms_chars"), { n: out.length, s: out.segments })}</p></div>
        : <p className="mt-4 text-sm text-muted">{tr("sms_off")}</p>)}
    </Card>
  );
}

function Trends({ D, lang, tr }) {
  const crops = Object.keys(D.series);
  const [crop, setCrop] = useState(crops.includes("Beans") ? "Beans" : crops[0]);
  const prods = Object.keys(D.series[crop]).sort((a, b) => D.series[crop][b].length - D.series[crop][a].length);
  const [prod, setProd] = useState(prods[0]);
  useEffect(() => { setProd(Object.keys(D.series[crop]).sort((a, b) => D.series[crop][b].length - D.series[crop][a].length)[0]); }, [crop]);
  const p = prods.includes(prod) ? prod : prods[0], s = D.series[crop][p];
  const t0 = Date.parse(s[0][0]), pts = s.map(([d, v]) => [(Date.parse(d) - t0) / 6048e5, v]);
  const sig = trendSignal(s.map((x) => x[1]));
  const label = { up: "trend_up", down: "trend_down", steady: "trend_steady", unknown: "trend_unknown" }[sig.dir];
  const tone = { up: "sun", down: "sky", steady: "leaf", unknown: "sun" }[sig.dir];
  const dates = (w) => { const d = new Date(t0 + w * 6048e5); return `${d.getUTCDate()} ${MONTHS[lang][d.getUTCMonth()]}`; };
  const cropLabel = (c) => (lang === "rw" ? D.cropnames[c] || c : c);
  return (
    <div className="space-y-5">
      <div className="grid sm:grid-cols-2 gap-4 max-w-xl">
        <Field id="tc" label={tr("pick_crop")}><select id="tc" className={inputCls} value={crop} onChange={(e) => setCrop(e.target.value)}>{crops.map((c) => <option key={c} value={c}>{cropLabel(c)}</option>)}</select></Field>
        <Field id="tp" label={tr("pick_product")}><select id="tp" className={inputCls} value={p} onChange={(e) => setProd(e.target.value)}>{prods.map((x) => <option key={x}>{x}</option>)}</select></Field>
      </div>
      <Card className="p-5">
        <div className="flex flex-wrap items-center gap-3 mb-3"><h3 className="font-display text-lg font-bold text-ink">{tr("trend_title")}</h3><Pill tone={tone}>{tr(label)}</Pill></div>
        <p className="text-sm text-muted mb-3">{tr("trend_market")} · {tr("per_kg")}</p>
        <LineChart series={[{ name: p, color: "var(--leaf)", points: pts, area: true }]} unit={tr("per_kg")} dates={dates} lang={lang} />
        {sig.pct != null && <p className="mt-3 text-sm text-ink">{fill(tr("trend_pct"), { pct: (sig.pct >= 0 ? "+" : "") + sig.pct.toFixed(0) })}</p>}
        <p className="mt-2 text-sm text-muted">{tr("no_forecast")}</p>
      </Card>
    </div>
  );
}

function Board({ D, lang, tr, go }) {
  const board = useMemo(() => cropBoard(D), [D]);
  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {board.map((b) => (
        <Card key={b.crop} className="p-5 flex items-center gap-4">
          <CropIcon crop={b.crop} size={88} />
          <div className="min-w-0">
            <div className="font-semibold text-ink">{lang === "rw" ? D.cropnames[b.crop] : b.crop}</div>
            <div className="font-display text-2xl font-bold text-ink tabular-nums">{b.median ? num(b.median) : "-"} <span className="text-xs text-muted font-medium">{tr("per_kg")}</span></div>
            <div className="text-xs text-muted">{fill(tr("markets_n"), { n: b.n })} · {tr("range")} {num(b.lo)}-{num(b.hi)}</div>
          </div>
        </Card>
      ))}
    </div>
  );
}

const PALETTE = ["#1E7A4C", "#0B78B0", "#C98A00", "#B5473A", "#7A4FA3", "#2B8F8F", "#6B7A2A"];
function Overview({ D, lang, tr }) {
  const S = D.strings[lang];
  const dirKey = (d) => ({ Rising: "rising", Falling: "falling" }[d] || "steady");
  const last = useMemo(() => {
    const m = {};
    D.month.forEach((r) => { if (r[5] != null && (!m[r[0]] || r[1] > m[r[0]][1])) m[r[0]] = r; });
    return Object.values(m);
  }, [D]);
  const stale = D.coverage.filter((c) => c.last < new Date(Date.parse(D.meta.asof) - 30 * 864e5).toISOString().slice(0, 10)).length;
  const cropLabel = (c) => (lang === "rw" ? D.cropnames[c] || c : c);
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label={tr("kpi_records")} value={num(D.meta.records)} /><Stat label={tr("kpi_markets")} value={D.meta.markets} />
        <Stat label={tr("kpi_crops")} value={D.meta.crops} /><Stat label={tr("kpi_latest")} value={dateOf(D.meta.asof, lang)} />
      </div>
      <div>
        <h3 className="font-display text-xl font-bold text-ink">{tr("story_title")}</h3>
        <p className="text-sm text-muted">{tr("story_sub")}</p>
        <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {D.story.map((s) => {
            const k = dirKey(s.direction), tone = { rising: "bad", falling: "sky", steady: "leaf" }[k];
            return (
              <Card key={s.crop} className="p-4">
                <div className="flex items-center gap-3"><CropIcon crop={s.crop} size={44} /><div className="min-w-0"><div className="font-semibold text-ink">{cropLabel(s.crop)}</div><Pill tone={tone}>{tr(k)} {s.change_pct > 0 ? "+" : ""}{Math.round(s.change_pct)}%</Pill></div></div>
                <div className="mt-3 text-sm text-ink tabular-nums">{num(s.price_first)} → <b>{num(s.price_last)}</b> <span className="text-muted">{tr("per_kg")}</span></div>
                <div className="text-xs text-muted mt-1">{fill(tr("since"), { m: s.first_month })} · {tr("how_sure")}: {tr("ev_" + s.evidence)}</div>
              </Card>
            );
          })}
        </div>
      </div>
      {last.length > 0 && (
        <Card className="p-5">
          <h3 className="font-display text-lg font-bold text-ink">{S.gov_gap_title}</h3>
          <p className="text-sm text-muted mb-3">{S.gov_gap_help}</p>
          <HBars items={last.map((r) => ({ label: cropLabel(r[0]), value: r[5], text: Math.round(r[5]) + "%" }))} unit="%" highlight={[...last].sort((a, b) => b[5] - a[5])[0] && cropLabel([...last].sort((a, b) => b[5] - a[5])[0][0])} />
        </Card>
      )}
      <div className={cx("rounded-xl px-4 py-3 text-sm font-medium", stale ? "bg-sunsoft text-ink" : "bg-leafsoft text-leaf")}>
        {stale ? fill(S.gov_cov_stale, { n: stale, total: D.coverage.length }) : fill(S.gov_cov_ok, { total: D.coverage.length })}
      </div>
    </div>
  );
}

function Monthly({ D, lang, tr }) {
  const crops = [...new Set(D.month.map((r) => r[0]))];
  const [crop, setCrop] = useState(crops.includes("Rice") ? "Rice" : crops[0]);
  const rows = D.month.filter((r) => r[0] === crop).sort((a, b) => (a[1] < b[1] ? -1 : 1));
  const lo = Math.min(...rows.map((r) => r[2])), hi = Math.max(...rows.map((r) => r[2]));
  const cropLabel = (c) => (lang === "rw" ? D.cropnames[c] || c : c);
  const months = [...new Set(D.month.map((r) => r[1]))].sort();
  const series = crops.map((c, i) => ({ name: c, color: PALETTE[i % PALETTE.length], points: D.month.filter((r) => r[0] === c).sort((a, b) => (a[1] < b[1] ? -1 : 1)).map((r) => [months.indexOf(r[1]), r[2]]) }));
  const csv = [[tr("pick_crop"), tr("col_month"), tr("col_median"), tr("col_nm"), tr("col_rep"), tr("col_gap")], ...D.month.map((r) => [r[0], r[1], r[2], r[3], r[4], r[5] ?? ""])];
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2" role="group">
        {crops.map((c) => <button key={c} onClick={() => setCrop(c)} aria-pressed={crop === c} className={cx("flex items-center gap-2 rounded-full border px-2.5 py-1.5 text-sm font-medium", crop === c ? "border-leaf bg-leafsoft text-ink" : "border-line text-muted hover:text-ink")}><CropIcon crop={c} size={22} />{cropLabel(c)}</button>)}
      </div>
      <Card className="p-5">
        <h3 className="font-display text-lg font-bold text-ink">{tr("monthly_title")} · {cropLabel(crop)}</h3>
        <p className="text-sm text-muted mb-3">{tr("monthly_sub")} {tr("per_kg")}.</p>
        <Columns unit={tr("per_kg")} items={rows.map((r) => ({ label: monthOf(r[1], lang) + (r[6] ? "*" : ""), value: r[2], faint: r[6], color: r[2] === lo ? "var(--sky)" : r[2] === hi ? "var(--sun)" : "var(--bar)" }))} />
        {rows.some((r) => r[6]) && <p className="text-xs text-muted mt-1">* {tr("partial")}</p>}
      </Card>
      <Card className="p-5">
        <h3 className="font-display text-lg font-bold text-ink mb-3">{tr("all_crops")}</h3>
        <LineChart series={series} unit={tr("per_kg")} dates={(i) => (months[Math.round(i)] ? monthOf(months[Math.round(i)], lang) : "")} lang={lang} />
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">{series.map((s) => <span key={s.name} className="inline-flex items-center gap-1.5 text-sm text-ink"><span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />{cropLabel(s.name)}</span>)}</div>
      </Card>
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3"><h3 className="font-display text-lg font-bold text-ink">{cropLabel(crop)}</h3><CopyBtn rows={csv} tr={tr} /></div>
        <DataTable head={[tr("col_month"), tr("col_median"), tr("col_nm"), tr("col_rep"), tr("col_gap")]} rows={rows.map((r) => [monthOf(r[1], lang) + (r[6] ? "*" : ""), num(r[2]), r[3], r[4], r[5] == null ? "-" : Math.round(r[5]) + "%"])} />
      </Card>
    </div>
  );
}

function Markets({ D, lang, tr }) {
  const crops = Object.keys(D.crops);
  const [crop, setCrop] = useState("Beans");
  const prods = D.crops[crop].filter((p) => (D.cur[crop] || {})[p]);
  const [prod, setProd] = useState(prods[0]);
  useEffect(() => { setProd(D.crops[crop].filter((p) => (D.cur[crop] || {})[p])[0]); }, [crop]);
  const p = prods.includes(prod) ? prod : prods[0];
  const cur = (D.cur[crop] || {})[p] || [], m = med(cur.map((r) => r[1]));
  const rows = [...cur].sort((a, b) => b[1] - a[1]);
  const cropLabel = (c) => (lang === "rw" ? D.cropnames[c] || c : c);
  const S = D.strings[lang];
  const csv1 = [[tr("col_market"), tr("col_district"), tr("col_price"), tr("col_reports"), tr("col_last"), tr("col_vs")], ...rows.map((r) => [r[0], D.district[r[0]] || "", r[1], r[2], r[3], ((r[1] / m - 1) * 100).toFixed(1)])];
  const csv2 = [[tr("col_market"), tr("col_district"), tr("crops_n"), tr("records_n"), tr("col_last")], ...D.coverage.map((c) => [c.location, c.district, c.crops, c.records, c.last])];
  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 gap-4 max-w-xl">
        <Field id="mc" label={tr("pick_crop")}><select id="mc" className={inputCls} value={crop} onChange={(e) => setCrop(e.target.value)}>{crops.map((c) => <option key={c} value={c}>{cropLabel(c)}</option>)}</select></Field>
        <Field id="mp" label={tr("pick_product")}><select id="mp" className={inputCls} value={p} onChange={(e) => setProd(e.target.value)}>{prods.map((x) => <option key={x}>{x}</option>)}</select></Field>
      </div>
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3"><h3 className="font-display text-lg font-bold text-ink">{S.mk_title}</h3><CopyBtn rows={csv1} tr={tr} /></div>
        <p className="text-sm text-muted mb-3">{S.mk_caption}</p>
        <DataTable head={[tr("col_market"), tr("col_district"), tr("col_price"), tr("col_reports"), tr("col_last"), tr("col_vs")]}
          rows={rows.map((r) => { const v = (r[1] / m - 1) * 100; return [<b className="text-ink">{r[0]}</b>, D.district[r[0]] || "", num(r[1]), r[2], dateOf(r[3], lang), <Pill tone={v > 5 ? "sun" : v < -5 ? "sky" : "leaf"}>{(v > 0 ? "+" : "") + Math.round(v)}%</Pill>]; })} />
      </Card>
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3"><h3 className="font-display text-lg font-bold text-ink">{tr("mk_cov_title")}</h3><CopyBtn rows={csv2} tr={tr} /></div>
        <DataTable head={[tr("col_market"), tr("col_district"), tr("crops_n"), tr("records_n"), tr("col_last")]}
          rows={[...D.coverage].sort((a, b) => b.records - a.records).map((c) => [<b className="text-ink">{c.location}</b>, c.district, c.crops, num(c.records), dateOf(c.last, lang)])} />
      </Card>
    </div>
  );
}

function Trust({ D, lang, tr }) {
  const ml = D.ml;
  return (
    <div className="space-y-6">
      <Card className="p-5">
        <h3 className="font-display text-lg font-bold text-ink">{tr("ml_title")}</h3>
        {ml ? (
          <>
            <p className="text-sm text-muted mt-1 mb-3">{fill(tr("q_gate"), { n: ml.gate_needed_pct })}</p>
            <DataTable head={[tr("ml_method"), tr("ml_err"), tr("ml_type"), tr("ml_vs")]}
              rows={ml.table.map((r) => [r.model, r.mean_error_RWF.toFixed(1), <Pill tone={r.kind === "trained" ? "sky" : "leaf"}>{r.kind}</Pill>, (r["better_than_best_rule_%"] > 0 ? "+" : "") + r["better_than_best_rule_%"] + "%"])} />
            <div className={cx("mt-3 rounded-xl px-4 py-3 text-sm font-medium", ml.gate_pass ? "bg-leafsoft text-leaf" : "bg-sunsoft text-ink")}>{ml.reason}</div>
          </>
        ) : <p className="text-sm text-muted mt-2">Run tools/train_models.py to add the model check.</p>}
      </Card>
      {ml && ml.backtest && (
        <Card className="p-5">
          <h3 className="font-display text-lg font-bold text-ink mb-3">{tr("bt_title")}</h3>
          <HBars unit={tr("bt_won")} items={ml.backtest.map((r) => ({ label: r.model, value: r["share_won_%"], text: r["share_won_%"] + "%" }))} highlight={[...ml.backtest].sort((a, b) => b["share_won_%"] - a["share_won_%"])[0].model} />
        </Card>
      )}
      <Card className="p-5">
        <h3 className="font-display text-lg font-bold text-ink mb-2">{tr("limits_title")}</h3>
        <ul className="space-y-2 text-ink text-sm list-disc pl-5">{["lim1", "lim2", "lim3"].map((k) => <li key={k}>{tr(k)}</li>)}</ul>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ shell */
function Main({ D, init = {} }) {
  const [lang, setLang] = useState(init.lang || (() => { try { return localStorage.getItem("isoko-lang") || ((navigator.language || "").toLowerCase().startsWith("rw") ? "rw" : "en"); } catch (e) { return "en"; } })());
  useEffect(() => { try { localStorage.setItem("isoko-lang", lang); } catch (e) {} }, [lang]);
  const [view, setView] = useState(init.view || "home");
  const [sub, setSub] = useState(init.sub || {});
  const [preset, setPreset] = useState(null);
  const [theme, setTheme] = useState("system");
  const tr = (k, v) => fill((UI[lang] && UI[lang][k]) ?? UI.en[k] ?? D.strings[lang][k] ?? k, v);
  const farmerTabs = [["sell", tr("sub_sell")], ["trends", tr("sub_trends")], ["board", tr("sub_board")], ["sms", tr("sub_sms")]];
  const govTabs = [["overview", tr("sub_overview")], ["monthly", tr("sub_monthly")], ["markets", tr("sub_markets")], ["trust", tr("sub_trust")]];
  const hashOf = { home: "home", farmer: "farmer", gov: "government" };
  const go = (v, opts) => { setView(v); if (opts && opts.crop) setPreset(opts.crop); try { window.scrollTo({ top: 0 }); } catch (e) {} };
  useEffect(() => {
    const read = () => { const h = (location.hash || "").slice(1); const k = Object.keys(hashOf).find((x) => hashOf[x] === h); if (k) setView(k); };
    read(); window.addEventListener("hashchange", read); return () => window.removeEventListener("hashchange", read);
  }, []);
  useEffect(() => { try { if (location.hash.slice(1) !== hashOf[view]) history.replaceState(null, "", "#" + hashOf[view]); } catch (e) {} }, [view]);
  useEffect(() => { try { const r = document.documentElement; theme === "system" ? r.removeAttribute("data-theme") : r.setAttribute("data-theme", theme); } catch (e) {} }, [theme]);
  useEffect(() => { try { document.documentElement.lang = lang === "rw" ? "rw" : "en"; } catch (e) {} }, [lang]);
  const navItems = [["home", tr("nav_home")], ["farmer", tr("nav_farmer")], ["gov", tr("nav_gov")]];
  const subOf = (v, d) => sub[v] || d;
  const setSubOf = (v) => (x) => setSub({ ...sub, [v]: x });
  return (
    <div className="min-h-screen">
      <header className="sticky z-20 bg-surface border-b border-line" style={{ top: "env(safe-area-inset-top, 0px)" }}>
        <div className="gutter mx-auto max-w-6xl flex items-center gap-3 py-2.5">
          <button onClick={() => go("home")} className="flex items-center gap-2.5 min-w-0" aria-label="Isoko Smart AI">
            <Logo /><span className="font-display text-lg font-extrabold text-ink whitespace-nowrap">Isoko Smart AI</span>
          </button>
          <nav className="hidden md:flex items-center gap-1 ml-6" aria-label="Main">
            {navItems.map(([k, l]) => <button key={k} onClick={() => go(k)} aria-current={view === k ? "page" : undefined} className={cx("rounded-lg px-3.5 py-2 text-sm font-semibold transition", view === k ? "bg-leafsoft text-leaf" : "text-muted hover:text-ink")}>{l}</button>)}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <button onClick={() => setTheme(theme === "dark" ? "light" : theme === "light" ? "system" : "dark")} title={tr("theme") + ": " + theme} aria-label={tr("theme")} className="hidden sm:inline-flex h-9 w-9 items-center justify-center rounded-lg border border-line text-ink">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
            </button>
            <div role="group" aria-label="Language / Ururimi" className="flex rounded-lg border border-line p-0.5">
              {[["en", "EN"], ["rw", "RW"]].map(([k, l]) => <button key={k} onClick={() => setLang(k)} aria-pressed={lang === k} title={k === "en" ? "English" : "Kinyarwanda"} className={cx("rounded-md px-3 py-1.5 text-sm font-bold", lang === k ? "bg-leaf text-white" : "text-muted hover:text-ink")}>{l}</button>)}
            </div>
          </div>
        </div>
        <nav className="md:hidden border-t border-line" aria-label="Main">
          <div className="gutter mx-auto max-w-6xl flex gap-1 py-1.5 overflow-x-auto">
            {navItems.map(([k, l]) => <button key={k} onClick={() => go(k)} className={cx("whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-semibold", view === k ? "bg-leafsoft text-leaf" : "text-muted")}>{l}</button>)}
          </div>
        </nav>
      </header>

      <main>
        {view === "home" && <Home D={D} lang={lang} tr={tr} go={go} />}
        {view === "farmer" && (
          <div className="gutter mx-auto max-w-6xl py-8 space-y-6">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div><div className="text-xs font-bold uppercase tracking-wide text-leaf">{tr("nav_farmer")}</div><h1 className="font-display text-3xl font-extrabold text-ink">{D.strings[lang].sell_title}</h1></div>
              <Tabs items={farmerTabs} value={subOf("farmer", "sell")} onChange={setSubOf("farmer")} />
            </div>
            <StaleBanner D={D} tr={tr} lang={lang} />
            {subOf("farmer", "sell") === "sell" && <Sell D={D} lang={lang} tr={tr} preset={preset} key={preset || "x"} />}
            {subOf("farmer", "sell") === "trends" && <Trends D={D} lang={lang} tr={tr} />}
            {subOf("farmer", "sell") === "board" && <Board D={D} lang={lang} tr={tr} />}
            {subOf("farmer", "sell") === "sms" && <Sms D={D} lang={lang} tr={tr} />}
          </div>
        )}
        {view === "gov" && (
          <div className="gutter mx-auto max-w-6xl py-8 space-y-6">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div><div className="text-xs font-bold uppercase tracking-wide text-sky">MINAGRI</div><h1 className="font-display text-3xl font-extrabold text-ink">{D.strings[lang].view_gov.replace(/^[^\p{L}]+/u, "")}</h1></div>
              <Tabs items={govTabs} value={subOf("gov", "overview")} onChange={setSubOf("gov")} />
            </div>
            {subOf("gov", "overview") === "overview" && <Overview D={D} lang={lang} tr={tr} />}
            {subOf("gov", "overview") === "monthly" && <Monthly D={D} lang={lang} tr={tr} />}
            {subOf("gov", "overview") === "markets" && <Markets D={D} lang={lang} tr={tr} />}
            {subOf("gov", "overview") === "trust" && <Trust D={D} lang={lang} tr={tr} />}
          </div>
        )}
      </main>

      <footer className="border-t border-line mt-10">
        <div className="gutter mx-auto max-w-6xl py-6 text-sm text-muted space-y-1">
          <div>{fill(tr("footer_src"), { a: dateOf(D.meta.first, lang), b: dateOf(D.meta.asof, lang) })}</div>
        </div>
      </footer>
    </div>
  );
}

function Loader() {
  const [D, setD] = useState(null), [err, setErr] = useState(false);
  useEffect(() => { fetch("data.json").then((r) => r.json()).then(setD).catch(() => setErr(true)); }, []);
  if (err) return <div className="p-8 text-bad">The price file could not be loaded. / Ibiciro ntibyabashije gufungurwa.</div>;
  if (!D) return <div className="p-8 text-muted">Loading prices... / Biri gushakwa...</div>;
  return <Main D={D} />;
}

try { if ("serviceWorker" in navigator && location.protocol.startsWith("http")) navigator.serviceWorker.register("sw.js").catch(() => {}); } catch (e) {}
window.__Isoko = { Main, Loader };
if (typeof document !== "undefined" && document.getElementById("root") && !window.__ISOKO_TEST__) {
  ReactDOM.createRoot(document.getElementById("root")).render(<Loader />);
}
