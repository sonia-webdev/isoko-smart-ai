"""Isoko Smart AI - understanding free messages from farmers.

A language model READS the message and returns four fields: intent, crop, quantity (kg) and market.
It never chooses the market and never writes a price: the fields are checked against Isoko's own lists,
and the answer is then calculated by the same code as the dashboard (isoko_core / isoko_sms).

    extractor = rule_extractor(markets)                      # today's SMS parser, as a baseline
    extractor = llm_extractor(load_hf_generate(), markets)    # a language model (needs transformers; run in Colab)
    reply = answer("Ndashaka kugurisha ibishyimbo ibiro 500 i Nyabugogo", extractor, df, markets, road_km)

If the model's output cannot be read or fails the checks, the rule parser is used instead, so a farmer always gets an answer.
"""
from __future__ import annotations

import json
import re

import pandas as pd

import isoko_core as ic
import isoko_i18n as i18n
import isoko_sms as sms

CROPS = list(i18n.CROPS)
INTENTS = ("sell", "price", "help", "other")


# ---------------------------------------------------------------- the rule-based reader
NUMBER_WORDS = [("ibihumbi bibiri", 2000), ("igihumbi", 1000), ("magana cyenda", 900), ("magana inani", 800),
                ("magana arindwi", 700), ("magana atandatu", 600), ("magana atanu", 500), ("magana ane", 400),
                ("magana atatu", 300), ("magana abiri", 200), ("ijana", 100)]
PRICE_WORDS = {"price", "prices", "igiciro", "ibiciro", "angahe", "cost", "much"}
SELL_WORDS = {"market", "markets", "where", "sell", "selling", "gurisha", "kugurisha", "nabigurisha", "nagurishiriza", "ndashaka", "nshaka", "want", "mfite"}
HELP_WORDS = {"help", "ubufasha", "amabwiriza"}
RW_WORDS = {"ibishyimbo", "imyumbati", "ibirayi", "ibigori", "umuceri", "ibijumba", "inyanya", "ibiro", "ndashaka", "mfite",
            "nabigurisha", "gurisha", "kugurisha", "igiciro", "ibiciro", "ubufasha", "muraho", "nshaka", "nagurishiriza",
            "mbwira", "kuri", "angahe", "uyu", "munsi", "ndi", "bigura", "magana", "igihumbi", "ijana", "nabigurisha"}


def _clean(text: str) -> list:
    """Lower-case words. Numbers in words become digits, '1,500' becomes 1500, '5oo' becomes 500."""
    t = str(text).lower().replace("'", " ").replace("\u2019", " ")
    for words, value in NUMBER_WORDS:
        t = t.replace(words, f" {value} ")
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", t)
    t = re.sub(r"\b(\d+)(o+)\b", lambda m: m.group(1) + "0" * len(m.group(2)), t)
    return re.findall(r"[a-z0-9]+", t)


def _find_market(tokens: list, markets: pd.DataFrame):
    """A market named anywhere in the message, also with a small spelling mistake."""
    import difflib
    keys = {ic._market_key(m): m for m in markets["location"]}
    for n in (2, 1):                                           # two-word names first
        for i in range(len(tokens) - n + 1):
            k = ic._market_key(" ".join(tokens[i:i + n]))
            if k in keys:
                return keys[k]
    for tok in tokens:
        if len(tok) >= 5 and not tok.isdigit() and tok not in sms.CROP_WORDS and tok not in RW_WORDS:
            close = difflib.get_close_matches(ic._market_key(tok), list(keys), n=1, cutoff=0.84)
            if close:
                return keys[close[0]]
    return None


def rule_extractor(markets: pd.DataFrame):
    """Reads commands AND free sentences by rules (no model needed). Kinyarwanda in -> lang 'rw' out."""
    def extract(text: str) -> dict:
        raw = sms._tokens(text)
        if raw and raw[0] in sms.COMMANDS:                    # a command: SELL ..., GURISHA ..., PRICE ..., HELP
            lang, intent = sms.COMMANDS[raw[0]]
            tokens = _clean(" ".join(raw[1:]))
        else:
            lang, intent, tokens = None, None, _clean(text)
        crop, rest = sms._parse_crop(tokens)
        qty, rest = sms._parse_qty(rest)
        if qty is not None and not 10 <= qty <= 100000:
            qty = None
        words = set(tokens)
        if lang is None:
            lang = "rw" if words & RW_WORDS else "en"
            if words & HELP_WORDS:
                intent = "help"
            elif crop and words & PRICE_WORDS and qty is None:      # a weight means a farmer with a harvest to sell
                intent = "price"
            elif crop and (qty is not None or words & SELL_WORDS or _find_market(rest, markets)):
                intent = "sell"
            elif crop:
                intent = "price"                                  # just a crop name: show its price
            else:
                intent = "other"
        market = _find_market(rest, markets) if intent == "sell" else None
        if intent == "sell" and not market:
            market = sms._match_market(rest, markets)
        return dict(intent=intent, lang=lang, crop=crop or "", qty=qty if qty is not None else "", market=market or "")
    return extract


# ---------------------------------------------------------------- the language-model reader
SYSTEM = ("You read short messages from Rwandan farmers, written in Kinyarwanda, English or a mix. "
          "You only extract information. You never give advice and never mention prices.")


def build_prompt(text: str, markets: pd.DataFrame) -> str:
    names = ", ".join(sorted(markets["location"]))
    kin = ", ".join(f"{rw} = {en}" for en, rw in i18n.CROPS.items())
    return (
        "Extract these fields from the farmer's message and answer with ONE JSON object and nothing else.\n"
        'Fields: "intent" is "sell" (wants to know where to sell), "price" (asks the price of a crop), "help" '
        '(asks how to use the service) or "other" (anything else).\n'
        f'"crop" is one of: {", ".join(CROPS)} or "" if none is named. Kinyarwanda names: {kin}.\n'
        '"qty" is the weight in kilograms as a number, or "" if not given (convert number words, e.g. magana atanu = 500, '
        "igihumbi = 1000).\n"
        f'"market" is the market where the farmer is, copied from this list, or "" if not given: {names}.\n'
        '"lang" is "rw" if the message is mainly Kinyarwanda, otherwise "en".\n\n'
        'Example: Message: "Mfite ibishyimbo 500 kg i Nyabugogo, nabigurisha he?" -> '
        '{"intent": "sell", "crop": "Beans", "qty": 500, "market": "Nyabugogo", "lang": "rw"}\n'
        'Example: Message: "price of rice" -> {"intent": "price", "crop": "Rice", "qty": "", "market": "", "lang": "en"}\n\n'
        f'Message: "{text}"\nJSON:')


def parse_llm_json(raw: str):
    """The first JSON object in the model's output (it may add words or code fences). None if there is none."""
    m = re.search(r"\{.*?\}", str(raw), flags=re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def normalise(ex: dict | None, markets: pd.DataFrame):
    """Check the fields against Isoko's lists. Returns (clean fields or None, problems)."""
    if not ex:
        return None, ["no readable answer"]
    problems = []
    intent = str(ex.get("intent", "")).strip().lower()
    if intent not in INTENTS:
        problems.append(f"unknown intent {intent!r}")
        intent = "other"
    crop = str(ex.get("crop", "") or "").strip()
    crop = next((c for c in CROPS if c.lower() == crop.lower()), "") or sms.CROP_WORDS.get(crop.lower(), "")
    if str(ex.get("crop", "")).strip() and not crop:
        problems.append(f"crop {ex.get('crop')!r} is not one of the 7")
    qty = ex.get("qty", "")
    try:
        qty = int(float(str(qty).replace(",", ""))) if str(qty).strip() != "" else ""
    except ValueError:
        problems.append(f"quantity {qty!r} is not a number")
        qty = ""
    if qty != "" and not 10 <= qty <= 100000:
        problems.append(f"quantity {qty} is outside 10 to 100,000 kg")
        qty = ""
    market = str(ex.get("market", "") or "").strip()
    if market:
        found = sms._match_market(sms._tokens(market), markets)
        if not found:
            problems.append(f"market {market!r} is not in the markets list")
        market = found or ""
    lang = "rw" if str(ex.get("lang", "")).strip().lower() == "rw" else "en"
    return dict(intent=intent, lang=lang, crop=crop, qty=qty, market=market), problems


def llm_extractor(generate, markets: pd.DataFrame, fallback=None):
    """generate(prompt) -> text from any language model. Falls back to the rule reader when the output fails the checks."""
    fallback = fallback or rule_extractor(markets)

    def extract(text: str) -> dict:
        clean, problems = normalise(parse_llm_json(generate(build_prompt(text, markets))), markets)
        if clean is None:
            out = fallback(text)
            out["source"] = "rules (model output unreadable)"
            return out
        clean["source"] = "model" if not problems else "model (some fields dropped by the checks)"
        return clean
    return extract


def load_hf_generate(model_name: str = "Qwen/Qwen2.5-1.5B-Instruct", max_new_tokens: int = 80):
    """Load an open chat model with Hugging Face transformers (run in Colab, ideally with a GPU)."""
    import torch  # noqa: F401
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto", device_map="auto")

    def generate(prompt: str) -> str:
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tok(text, return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return generate


# ---------------------------------------------------------------- scoring
def evaluate(extractor, testset: pd.DataFrame, markets: pd.DataFrame) -> pd.DataFrame:
    """One row per message with the extracted fields and whether each matches what a reader should find."""
    rows = []
    for r in testset.itertuples():
        got = extractor(str(r.text))
        exp = dict(intent=r.expected_intent, crop=r.expected_crop if isinstance(r.expected_crop, str) else "",
                   qty=int(r.expected_qty) if str(r.expected_qty).strip() not in ("", "nan") else "",
                   market=r.expected_market if isinstance(r.expected_market, str) else "")
        ok = {f: (got.get(f, "") == exp[f]) for f in exp}
        # 'help' and 'other' both end in the help text for a farmer, so they count as the same intent
        ok["intent"] = ok["intent"] or {got.get("intent"), exp["intent"]} <= {"help", "other"}
        rows.append(dict(id=r.id, language=r.language, text=r.text, note=r.note, **{f"got_{k}": got.get(k, "") for k in exp},
                         **{f"ok_{k}": v for k, v in ok.items()}, all_ok=all(ok.values())))
    return pd.DataFrame(rows)


def summarise(res: pd.DataFrame) -> pd.DataFrame:
    out = []
    for name, g in [("all messages", res)] + [(f"language: {k}", v) for k, v in res.groupby("language")]:
        out.append({"group": name, "messages": len(g), "intent_%": round(g.ok_intent.mean() * 100, 1),
                    "crop_%": round(g.ok_crop.mean() * 100, 1), "quantity_%": round(g.ok_qty.mean() * 100, 1),
                    "market_%": round(g.ok_market.mean() * 100, 1), "all_fields_right_%": round(g.all_ok.mean() * 100, 1)})
    return pd.DataFrame(out)


# ---------------------------------------------------------------- the answer
def answer(text: str, extractor, df: pd.DataFrame, markets: pd.DataFrame, road_km: dict | None = None) -> dict:
    """Free message -> reply. The reply is built by isoko_sms from the checked fields, never by the model."""
    ex = extractor(text)
    lang, intent, crop, qty, market = ex["lang"], ex["intent"], ex["crop"], ex["qty"], ex["market"]
    if intent in ("help", "other"):
        reply = i18n.t(lang, "sms_help")
    elif not crop:
        reply = i18n.t(lang, "sms_bad_crop")
    elif intent == "price":
        reply = sms._reply_price(lang, df, crop)
    elif qty == "":
        reply = i18n.t(lang, "sms_bad_qty")
    elif not market:
        reply = i18n.t(lang, "sms_bad_market")
    else:
        reply = sms._reply_sell(lang, df, markets, road_km, crop, int(qty), market)
    return dict(reply=reply, fields=ex, length=sms.sms_length(reply), segments=sms.sms_segments(reply))
