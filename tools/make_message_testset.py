"""Write docs/farmer_messages_testset.csv: realistic farmer messages with the answer a reader should extract.

    python tools/make_message_testset.py

Used to compare the SMS rule parser with a language model that reads free messages (see isoko_nlu.py).
The Kinyarwanda was written by an AI model and is NOT checked by a native speaker: every Kinyarwanda row carries
needs_native_review = yes. A reviewer should fix `text` (or mark it unusable) and fill native_speaker_ok.
"""
import csv
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROPS = {"Beans": ("beans", "ibishyimbo"), "Cassava": ("cassava", "imyumbati"), "Irish Potatoes": ("irish potatoes", "ibirayi"),
         "Maize": ("maize", "ibigori"), "Rice": ("rice", "umuceri"), "Sweet Potatoes": ("sweet potatoes", "ibijumba"),
         "Tomatoes": ("tomatoes", "inyanya")}
MARKETS = ["Nyabugogo", "Huye", "Musanze", "Kimironko", "Rwamagana", "Kamembe", "Nyagatare", "Muhanga", "Rubavu"]
QTY = [100, 200, 300, 500, 800, 1000, 1500, 2000]

# (template, language, intent). {crop} {rw} {q} {m}; upper-case variants for command messages.
TEMPLATES = [
    ("I want to sell {q} kg of {crop} at {m}. Where should I go?", "en", "sell"),
    ("where can i sell my {crop}, i have {q}kg and i'm at {m}", "en", "sell"),
    ("SELL {CROP} {q} {M}", "en", "sell"),
    ("best market for {crop} {q} kg from {m}", "en", "sell"),
    ("what is the price of {crop} today", "en", "price"),
    ("how much is {crop} now?", "en", "price"),
    ("PRICE {CROP}", "en", "price"),
    ("Ndashaka kugurisha {rw} ibiro {q} i {m}. Nabigurisha he?", "rw", "sell"),
    ("Mfite {rw} {q} kg i {m}, nabigurisha he?", "rw", "sell"),
    ("GURISHA {RW} IBIRO {q} {M}", "rw", "sell"),
    ("Mbwira igiciro {rw}", "rw", "price"),
    ("IGICIRO {RW}", "rw", "price"),
    ("nshaka sell {rw} {q}kg {m}", "mixed", "sell"),
    ("{rw} {q} {m}", "rw", "sell"),
]

# hand-written hard cases: (text, language, intent, crop, qty, market, note)
HARD = [
    ("Ndashaka kugurisha ibishyimbo magana atanu i Nyabugogo", "rw", "sell", "Beans", 500, "Nyabugogo", "number written in words"),
    ("Mfite ibigori igihumbi i Musanze, nabigurisha he?", "rw", "sell", "Maize", 1000, "Musanze", "number written in words"),
    ("sell beans 500 nyabugogoo", "en", "sell", "Beans", 500, "Nyabugogo", "typo in market"),
    ("sell rice 300 kimirinko", "en", "sell", "Rice", 300, "Kimironko", "typo in market"),
    ("GURISHA IBISHYIMBO 500 NYABUGOGO", "rw", "sell", "Beans", 500, "Nyabugogo", "no 'ibiro' word"),
    ("500kg beans nyabugogo sell", "en", "sell", "Beans", 500, "Nyabugogo", "words in another order"),
    ("ibishyimbo 500 Nyabugogo", "rw", "sell", "Beans", 500, "Nyabugogo", "no command word"),
    ("Where do I sell tomatoes? I have 300 kg", "en", "sell", "Tomatoes", 300, "", "market missing"),
    ("I want to sell maize at Huye", "en", "sell", "Maize", "", "Huye", "quantity missing"),
    ("sell 500 kg at Huye", "en", "sell", "", 500, "Huye", "crop missing"),
    ("I want to sell bananas 200 kg Huye", "en", "sell", "", 200, "Huye", "crop is not one of the 7"),
    ("Nagurishiriza he ibirayi 1000 kg? Ndi i Musanze", "rw", "sell", "Irish Potatoes", 1000, "Musanze", "question form"),
    ("Mfite imyumbati 800 kg kuri Rwamagana", "rw", "sell", "Cassava", 800, "Rwamagana", "'kuri' before the market"),
    ("price of irish potatoes", "en", "price", "Irish Potatoes", "", "", "two-word crop"),
    ("how much are sweet potatoes", "en", "price", "Sweet Potatoes", "", "", "two-word crop"),
    ("igiciro cy'ibijumba", "rw", "price", "Sweet Potatoes", "", "", "possessive form"),
    ("Muraho", "rw", "other", "", "", "", "greeting"),
    ("thank you", "en", "other", "", "", "", "thanks"),
    ("HELP", "en", "help", "", "", "", "help"),
    ("UBUFASHA", "rw", "help", "", "", "", "help"),
    ("what is the weather tomorrow", "en", "other", "", "", "", "off topic"),
    ("sell 5oo kg beans Huye", "en", "sell", "Beans", 500, "Huye", "letter O instead of zero"),
    ("I have 1,500 kg of maize in Muhanga to sell", "en", "sell", "Maize", 1500, "Muhanga", "thousands separator"),
]


def rows():
    rnd = random.Random(7)
    out = []
    for tpl, lang, intent in TEMPLATES:
        for _ in range(5):
            crop = rnd.choice(list(CROPS))
            en, rw = CROPS[crop]
            q, m = rnd.choice(QTY), rnd.choice(MARKETS)
            text = tpl.format(crop=en, rw=rw, q=q, m=m, CROP=en.upper(), RW=rw.upper(), M=m.upper())
            has_qty, has_market = "{q}" in tpl, "{m}" in tpl or "{M}" in tpl
            out.append((text, lang, intent, crop, q if has_qty else "", m if has_market else "", "template"))
    out += HARD
    return out


# A second set written AFTER the rule reader was tuned on the first one. It is never used to tune anything:
# it shows how the readers do on messages they were not built for.
HELD_OUT = [
    ("Hello, I have 400 kg of cassava in Rubavu. Where is the best place to sell?", "en", "sell", "Cassava", 400, "Rubavu", "held out"),
    ("tomatoes price please", "en", "price", "Tomatoes", "", "", "held out"),
    ("Can you tell me today's rice price?", "en", "price", "Rice", "", "", "held out"),
    ("sell my sweet potatoes 250kg Muhanga", "en", "sell", "Sweet Potatoes", 250, "Muhanga", "held out"),
    ("I'm in Nyagatare with 1200 kg maize", "en", "sell", "Maize", 1200, "Nyagatare", "held out, intent implied"),
    ("Need to sell beans, 600 kg, Musanze", "en", "sell", "Beans", 600, "Musanze", "held out"),
    ("How much is irish potato at the moment", "en", "price", "Irish Potatoes", "", "", "held out"),
    ("which market pays most for maize", "en", "sell", "Maize", "", "", "held out, fields missing"),
    ("Please how do I use this service", "en", "help", "", "", "", "held out"),
    ("I have 2,000 kg of rice at Kamembe and want the best price", "en", "sell", "Rice", 2000, "Kamembe", "held out"),
    ("SELL TOMATOES 150 RWAMAGANA", "en", "sell", "Tomatoes", 150, "Rwamagana", "held out"),
    ("beans 300kg kimironko where to sell", "en", "sell", "Beans", 300, "Kimironko", "held out"),
    ("Muraho, ndashaka kumenya igiciro cy'ibigori", "rw", "price", "Maize", "", "", "held out"),
    ("Mfite ibirayi magana abiri i Rubavu, nabigurisha he?", "rw", "sell", "Irish Potatoes", 200, "Rubavu", "held out, number in words"),
    ("Nshaka kugurisha umuceri ibiro 1000 Huye", "rw", "sell", "Rice", 1000, "Huye", "held out"),
    ("Ibijumba bigura angahe?", "rw", "price", "Sweet Potatoes", "", "", "held out"),
    ("Ndi i Nyabugogo mfite inyanya 100 kg", "rw", "sell", "Tomatoes", 100, "Nyabugogo", "held out, intent implied"),
    ("Ndashaka kugurisha imyumbati yanjye", "rw", "sell", "Cassava", "", "", "held out, fields missing"),
    ("Mwaramutse", "rw", "other", "", "", "", "held out"),
    ("Murakoze cyane", "rw", "other", "", "", "", "held out"),
    ("Nabona he isoko ryiza ry'ibishyimbo? Mfite ibiro 500 i Musanze", "rw", "sell", "Beans", 500, "Musanze", "held out"),
    ("igiciro cy'umuceri uyu munsi", "rw", "price", "Rice", "", "", "held out"),
    ("Gurisha ibigori 300 Rwamagana", "rw", "sell", "Maize", 300, "Rwamagana", "held out"),
    ("nagurisha he ibishyimbo ibiro 700 ndi i Kamembe", "rw", "sell", "Beans", 700, "Kamembe", "held out"),
    ("ibiro 500 by'ibigori i Muhanga", "rw", "sell", "Maize", 500, "Muhanga", "held out"),
]


def write(path, items, prefix):
    seen, n = set(), 0
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "language", "text", "expected_intent", "expected_crop", "expected_qty", "expected_market", "note",
                    "needs_native_review", "native_speaker_ok", "corrected_text"])
        for text, lang, intent, crop, q, m, note in items:
            if text in seen:
                continue
            seen.add(text)
            n += 1
            w.writerow([f"{prefix}{n:03d}", lang, text, intent, crop, q, m, note, "yes" if lang in ("rw", "mixed") else "no", "", ""])
    print(f"Wrote {n} messages to {path}")


def main():
    write(os.path.join(ROOT, "docs", "farmer_messages_testset.csv"), rows(), "m")
    write(os.path.join(ROOT, "docs", "farmer_messages_heldout.csv"), HELD_OUT, "h")


def _old_main():
    path = os.path.join(ROOT, "docs", "farmer_messages_testset.csv")
    seen, n = set(), 0
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "language", "text", "expected_intent", "expected_crop", "expected_qty", "expected_market", "note",
                    "needs_native_review", "native_speaker_ok", "corrected_text"])
        for text, lang, intent, crop, q, m, note in rows():
            if text in seen:
                continue
            seen.add(text)
            n += 1
            w.writerow([f"m{n:03d}", lang, text, intent, crop, q, m, note, "yes" if lang in ("rw", "mixed") else "no", "", ""])
    print(f"Wrote {n} messages to {path}")


if __name__ == "__main__":
    main()
