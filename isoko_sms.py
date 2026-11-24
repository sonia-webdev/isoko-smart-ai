"""Isoko Smart AI - SMS prototype (no Streamlit, no network here, so it can be tested alone).

A farmer with any phone texts a short command and gets a short reply, in the language of the command:

    SELL BEANS 500 NYABUGOGO       ->  where to sell 500 kg of beans from Nyabugogo
    GURISHA IBISHYIMBO 500 NYABUGOGO  (the same, in Kinyarwanda)
    PRICE MAIZE / IGICIRO IBIGORI  ->  highest, lowest and median price per kg
    HELP / UBUFASHA                ->  how to write a message

Replies use only characters of the basic SMS alphabet and are kept to 160 characters (one SMS).
The advice comes from the same logic as the dashboard (isoko_core), with the default transport rate.
"""
from __future__ import annotations

import math
import re

import pandas as pd

import isoko_core as ic
import isoko_i18n as i18n

SINGLE_SMS = 160
CROP_WORDS = {
    "beans": "Beans", "bean": "Beans", "ibishyimbo": "Beans", "bishyimbo": "Beans",
    "cassava": "Cassava", "imyumbati": "Cassava", "umyumbati": "Cassava", "umumbati": "Cassava",
    "potato": "Irish Potatoes", "potatoes": "Irish Potatoes", "irish": "Irish Potatoes",
    "ibirayi": "Irish Potatoes", "ikirayi": "Irish Potatoes",
    "maize": "Maize", "ibigori": "Maize", "ikigori": "Maize",
    "rice": "Rice", "umuceri": "Rice",
    "sweet": "Sweet Potatoes", "ibijumba": "Sweet Potatoes", "ikijumba": "Sweet Potatoes",
    "tomato": "Tomatoes", "tomatoes": "Tomatoes", "inyanya": "Tomatoes",
}
COMMANDS = {"sell": ("en", "sell"), "gurisha": ("rw", "sell"),
            "price": ("en", "price"), "igiciro": ("rw", "price"),
            "help": ("en", "help"), "ubufasha": ("rw", "help"), "amabwiriza": ("rw", "help")}
NOISE = {"kg", "kgs", "ibiro", "at", "from", "i", "in", "of"}

_GSM7 = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
_GSM7_EXT = set("^{}\\[~]|€")          # allowed, but each counts as two characters


def is_gsm7(text: str) -> bool:
    return all(c in _GSM7 or c in _GSM7_EXT for c in text)


def sms_length(text: str) -> int:
    return sum(2 if c in _GSM7_EXT else 1 for c in text) if is_gsm7(text) else len(text)


def sms_segments(text: str) -> int:
    """How many SMS the text costs (160 characters for one; 153 each when joined; 70/67 with special letters)."""
    n = sms_length(text)
    if is_gsm7(text):
        return 1 if n <= 160 else math.ceil(n / 153)
    return 1 if n <= 70 else math.ceil(n / 67)


# ---------------------------------------------------------------- reading the message
def _tokens(text: str) -> list:
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", str(text).lower())          # 1,500 -> 1500
    out = []
    for tok in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text):
        m = re.fullmatch(r"(\d[\do]*?)(kgs?)?", tok)
        out.append(m.group(1).replace("o", "0") + (m.group(2) or "") if m and "o" in m.group(1) else tok)   # 5oo -> 500
    return out


def _parse_crop(tokens: list):
    """(crop or None, tokens left over). Understands 'sweet potatoes' and 'irish potatoes' as two words."""
    for i, tok in enumerate(tokens):
        crop = CROP_WORDS.get(tok)
        if crop:
            rest = tokens[:i] + tokens[i + 1:]
            if tok in ("sweet", "irish") and i < len(rest) and rest[i] in ("potato", "potatoes"):
                rest = rest[:i] + rest[i + 1:]
            return crop, rest
    return None, tokens


_RW_HUNDREDS = {"ijana": 100, "abiri": 200, "atatu": 300, "ane": 400, "atanu": 500, "atandatu": 600,
                "arindwi": 700, "inani": 800, "cyenda": 900}
_RW_THOUSANDS = {"bibiri": 2000, "bitatu": 3000, "bine": 4000, "bitanu": 5000, "bitandatu": 6000, "birindwi": 7000,
                 "umunani": 8000, "icyenda": 9000}


def _rw_number(tokens: list):
    """(value, start, end) of a Kinyarwanda number such as 'magana atanu' (500) or 'igihumbi na magana atanu' (1500)."""
    n = len(tokens)
    for i in range(n):
        value, j = 0, i
        if tokens[j] == "igihumbi":
            value, j = 1000, j + 1
        elif tokens[j] == "ibihumbi" and j + 1 < n and tokens[j + 1] in _RW_THOUSANDS:
            value, j = _RW_THOUSANDS[tokens[j + 1]], j + 2
        if value and j < n and tokens[j] in ("na", "n"):
            j += 1
        if j < n and tokens[j].startswith("n'"):
            tokens = tokens[:j] + [tokens[j][2:]] + tokens[j + 1:]
        if j < n and tokens[j] == "ijana":
            return value + 100, i, j + 1
        if j + 1 < n and tokens[j] == "magana" and tokens[j + 1] in _RW_HUNDREDS and tokens[j + 1] != "ijana":
            return value + _RW_HUNDREDS[tokens[j + 1]], i, j + 2
        if value:
            return value, i, i + (1 if tokens[i] == "igihumbi" else 2)
    return None, 0, 0


def _parse_qty(tokens: list):
    """(kg or None, tokens left over). Accepts 500, 500kg, '500 kg' and Kinyarwanda words such as 'magana atanu'."""
    for i, tok in enumerate(tokens):
        m = re.fullmatch(r"(\d+)(?:kg|kgs)?", tok)
        if m:
            return int(m.group(1)), tokens[:i] + tokens[i + 1:]
    value, a, b = _rw_number(tokens)
    if value:
        return value, tokens[:a] + tokens[b:]
    return None, tokens


def _match_market(tokens: list, markets: pd.DataFrame):
    words = [t for t in tokens if t not in NOISE]
    if not words:
        return None
    name = " ".join(words)
    names = {ic._market_key(m): m for m in markets["location"]}
    key = ic._market_key(name)
    if key in names:
        return names[key]
    starts = [n for k, n in names.items() if k.startswith(key)]
    if len(starts) == 1:
        return starts[0]
    inside = [n for k, n in names.items() if key in k]
    return inside[0] if len(inside) == 1 else None


_STOP = NOISE | {"the", "a", "to", "my", "where", "should", "go", "sell", "best", "market", "price", "how", "much", "is",
                 "now", "today", "what", "want", "have", "can", "do", "kuri", "ku", "ndi", "he", "na", "uyu", "munsi",
                 "nabigurisha", "nagurishiriza", "ndashaka", "nshaka", "mfite", "mbwira", "igiciro", "angahe", "gurisha",
                 "kugurisha", "ibiro", "tomorrow", "weather", "thank", "you", "hello", "muraho", "murakoze", "with"}
_PRICE_CUES = {"price", "prices", "igiciro", "angahe", "cost", "costs", "much", "bigura", "igura"}
_SELL_CUES = {"sell", "gurisha", "kugurisha", "nabigurisha", "nagurishiriza", "nagurisha", "ndashaka", "nshaka", "mfite",
              "best", "where", "have"}
_RW_CUES = {"ibiro", "ndashaka", "mfite", "nabigurisha", "nagurishiriza", "nagurisha", "igiciro", "angahe", "mbwira",
            "kuri", "uyu", "munsi", "muraho", "nshaka", "he", "ndi", "kugurisha", "murakoze", "ijana", "magana",
            "igihumbi", "ibihumbi"}


def _find_market(tokens: list, markets: pd.DataFrame):
    """The market named anywhere in a message (one to three words). Exact name first, then a unique start of a name,
    then a close spelling (a typo). None when nothing fits or the start is ambiguous."""
    import difflib
    names = {ic._market_key(m): m for m in markets["location"]}
    for n in (3, 2, 1):                                                           # exact, longest name first
        for i in range(len(tokens) - n + 1):
            key = ic._market_key(" ".join(tokens[i:i + n]))
            if key in names:
                return names[key]
    crop_words = set(CROP_WORDS)
    for tok in tokens:
        if tok in _STOP or tok in crop_words or tok.isdigit() or len(tok) < 4:
            continue
        key = ic._market_key(tok)
        starts = [v for k, v in names.items() if k.startswith(key)]
        if len(starts) == 1:
            return starts[0]
        close = difflib.get_close_matches(key, list(names), n=1, cutoff=0.82) if len(key) >= 5 else []
        if close:
            return names[close[0]]
    return None


def read_message(text: str, markets: pd.DataFrame) -> dict:
    """Understand a message without a language model: intent, language, crop, quantity and market.
    One reader for the whole project: it lives in isoko_nlu so the app, the SMS server and the tests agree.
    Works for commands ('SELL BEANS 500 NYABUGOGO') and for ordinary sentences in English or Kinyarwanda."""
    import isoko_nlu
    f = isoko_nlu.rule_extractor(markets)(text)
    if f["intent"] == "other":
        f["intent"] = "help"                  # anything we cannot read gets the help text
    return f


# ---------------------------------------------------------------- building the reply
def _fit(main: str, *tails: str) -> str:
    """The main sentence, plus each optional tail that still fits in one SMS."""
    text = main
    for tail in tails:
        if tail and sms_length(text + tail) <= SINGLE_SMS:
            text += tail
    if sms_length(text) > SINGLE_SMS:          # never send more than one SMS by accident
        text = text[:SINGLE_SMS - 3] + "..."
    return text


def _short_date(ts) -> str:
    return f"{ts.day}/{ts.month}"


def _top_product(df, crop):
    d = df[df["crop_category"] == crop]
    return None if d.empty else d["product"].value_counts().index[0]


def _reply_sell(lang, df, markets, road_km, crop, qty, origin):
    product = _top_product(df, crop)
    cp = pd.DataFrame() if product is None else ic.current_prices(df, crop, product, asof=df["observed_date"].max())
    crop_txt = i18n.crop_name(lang, crop)
    if cp.empty:
        return i18n.t(lang, "sms_no_price", crop=crop_txt)
    cp = ic.trusted_only(cp, origin)
    ranked = ic.rank_markets(ic.add_distance(cp, markets, origin, road_km=road_km), qty, ic.DEFAULT_RATE)
    rec = ic.recommend(ranked)
    if rec is None:
        return i18n.t(lang, "sms_no_price", crop=crop_txt)
    best, base = rec["best"], rec["baseline"]
    old = i18n.t(lang, "sms_old") if best["reliability"] == "Low" else ""
    if rec["worthwhile"]:
        main = i18n.t(lang, "sms_sell", crop=crop_txt, qty=qty, best=best["location"], net=f"{best['net_return']:,.0f}",
                      pct=f"{rec['uplift_pct']:.0f}", base=base["location"], price=f"{best['price']:,.0f}",
                      date=_short_date(best["last_date"]))
        return _fit(main, old, i18n.t(lang, "sms_sell_tail"))
    main = i18n.t(lang, "sms_stay", crop=crop_txt, qty=qty, base=base["location"], net=f"{base['net_return']:,.0f}",
                  price=f"{base['price']:,.0f}", date=_short_date(base["last_date"]))
    return _fit(main, old, i18n.t(lang, "sms_stay_tail"))


def _reply_price(lang, df, crop):
    product = _top_product(df, crop)
    cp = pd.DataFrame() if product is None else ic.current_prices(df, crop, product, asof=df["observed_date"].max())
    crop_txt = i18n.crop_name(lang, crop)
    if cp.empty:
        return i18n.t(lang, "sms_no_price", crop=crop_txt)
    good = cp[cp["reliability"] != "Low"]
    cp = good if len(good) >= 2 else cp
    hi, lo = cp.loc[cp["price"].idxmax()], cp.loc[cp["price"].idxmin()]
    return _fit(i18n.t(lang, "sms_price", crop=crop_txt, hi_market=hi["location"], hi=f"{hi['price']:,.0f}",
                       lo_market=lo["location"], lo=f"{lo['price']:,.0f}", med=f"{cp['price'].median():,.0f}",
                       date=_short_date(cp["last_date"].max())))


def handle_sms(text: str, df: pd.DataFrame, markets: pd.DataFrame, road_km: dict | None = None) -> dict:
    """One incoming text -> {reply, lang, command, segments}. Never raises for a badly written message."""
    f = read_message(text, markets)
    lang, command = f["lang"], f["intent"]
    if command == "help":
        reply = i18n.t(lang, "sms_help")
    elif not f["crop"]:
        reply, command = i18n.t(lang, "sms_bad_crop"), "error"
    elif command == "price":
        reply = _reply_price(lang, df, f["crop"])
    elif f["qty"] == "" or not 10 <= f["qty"] <= 100000:
        reply, command = i18n.t(lang, "sms_bad_qty"), "error"
    elif not f["market"]:
        reply, command = i18n.t(lang, "sms_bad_market"), "error"
    else:
        reply = _reply_sell(lang, df, markets, road_km, f["crop"], int(f["qty"]), f["market"])
    return dict(reply=reply, lang=lang, command=command, segments=sms_segments(reply), length=sms_length(reply))
