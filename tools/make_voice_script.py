"""Write docs/voice_recording_script.csv: the list of words and phrases a Kinyarwanda speaker records.

    python tools/make_voice_script.py

The fixed phrases are taken from the app's own Kinyarwanda text (isoko_i18n.py), so the recording matches the
sentences on screen. Markets come from data/markets.csv, most-reported first. Tier 1 is the minimum for a spoken
"where to sell" answer; tier 2 (optional) adds spoken prices per kg in steps of 50 FRW.
"""
import csv
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_i18n as i18n  # noqa: E402

RW, EN = i18n.STR["rw"], i18n.STR["en"]

# (clip id, template key it comes from, text spoken, meaning, note)
PHRASES = [
    ("phrase_sell", "head_sell", "Gurishiriza i", "Sell at (the market name follows)", "Stop after 'i'; the market name is played next."),
    ("phrase_stay", "head_stay", "Kugurishiriza i", "Selling at ... (the market name follows)", "Stop after 'i'."),
    ("phrase_is_fine", "head_stay", "ni byiza", "... is fine", "Said after the market name."),
    ("phrase_reliab", "badge", "Kwizerwa kw'amakuru", "Data reliability", "Said before High / Medium / Low."),
    ("level_high", "level_High", "Hejuru", "High", ""),
    ("level_medium", "level_Medium", "Hagati", "Medium", ""),
    ("level_low", "level_Low", "Hasi", "Low", ""),
    ("phrase_warn_a", "warn_low", "Igiciro cy'i", "The price at (the market name follows)", "Stop after 'i'."),
    ("phrase_warn_b", "warn_low", "ni icy'igihe gishize cyangwa gishingiye ku makuru make. Hamagara umucuruzi waho mbere yo gukora urugendo.",
     "... is old or rests on few reports. Call a trader there before you travel.", "Said after the market name."),
    ("phrase_price", None, "Igiciro", "The price is", "Said before the price number (tier 2)."),
    ("phrase_per_kg", None, "amafaranga ku kilo", "francs per kilo", "Said after the price number (tier 2)."),
    ("phrase_estimate", None, "Ibi ni ibigereranyo, si ikiguzi cyizewe.", "These are estimates, not a guaranteed price.", "Said at the end."),
]


def slug(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def build_rows(markets):
    rows = []
    for crop, rw in i18n.CROPS.items():
        rows.append((f"crop_{slug(crop)}", 1, "crop", rw, crop, "Say only the word, like the name of a crop in a list.", f"crop_{slug(crop)}.wav"))
    for clip_id, key, text, meaning, note in PHRASES:
        if key is not None:
            assert text in RW[key], f"{clip_id}: '{text}' is not in the app text for {key}: {RW[key]}"
        rows.append((clip_id, 2 if clip_id in ("phrase_price", "phrase_per_kg", "phrase_estimate") else 1,
                     "phrase", text, meaning, note, f"{clip_id}.wav"))
    for m in markets:
        rows.append((f"market_{slug(m)}", 1, "market", m, "market name", "Say the name the way people there say it. Skip it if you do not know the place.", f"market_{slug(m)}.wav"))
    for n in range(50, 3001, 50):
        rows.append((f"price_{n:04d}", 2, "price", str(n), f"{n} francs (price per kilo)",
                     "Say the number in Kinyarwanda, the way you would say a price per kilo. Not the numerals.", f"price_{n:04d}.wav"))
    return rows


def main():
    import pandas as pd
    mk = pd.read_csv(os.path.join(ROOT, "data", "markets.csv"))
    counts_path = os.path.join(ROOT, "data", "market_report_counts.csv")
    order = list(mk["location"])
    if os.path.exists(counts_path):
        c = pd.read_csv(counts_path).sort_values("rows", ascending=False)
        order = [m for m in c["location"] if m in set(mk["location"])] + [m for m in mk["location"] if m not in set(c["location"])]
    rows = build_rows(order)
    ids = [r[0] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate clip ids"
    out = os.path.join(ROOT, "docs", "voice_recording_script.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:      # utf-8-sig so Excel shows the letters correctly
        w = csv.writer(f)
        w.writerow(["no", "clip_id", "tier", "category", "say_this", "english_meaning", "note", "save_file_as",
                    "what_you_actually_said (only if different)", "problem (noisy / mistake / skip)"])
        for i, (cid, tier, cat, say, meaning, note, fname) in enumerate(rows, 1):
            w.writerow([i, cid, tier, cat, say, meaning, note, fname, "", ""])
    t1 = sum(1 for r in rows if r[1] == 1)
    print(f"Wrote {len(rows)} clips ({t1} in tier 1, {len(rows) - t1} in tier 2) to {out}")


if __name__ == "__main__":
    main()
