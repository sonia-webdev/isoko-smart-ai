"""Tests for the retail benchmark, the Kinyarwanda text and the SMS prototype."""
import copy
import csv
import os
import sys
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from http.server import HTTPServer

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_core as ic  # noqa: E402
import isoko_i18n as i18n  # noqa: E402
import isoko_sms as sms  # noqa: E402
from tools.sms_webhook import make_handler  # noqa: E402

DATA = os.path.join(ROOT, "data")


# ------------------------------------------------------------------ retail benchmark
class BenchmarkTests(unittest.TestCase):
    def test_wfp_names_map_to_crops(self):
        m = ic.wfp_to_crop
        self.assertEqual(m("Beans (dry)"), "Beans")
        self.assertEqual(m("Potatoes (Irish)"), "Irish Potatoes")
        self.assertEqual(m("Sweet potatoes"), "Sweet Potatoes")
        self.assertEqual(m("Rice (imported, Tanzanian)"), "Rice")
        for not_a_crop in ("Maize flour", "Cassava leaves", "Beans (fresh)", "Beans (green, fresh)", "Salt", "Sorghum",
                           "Oil (palm)"):
            self.assertIsNone(m(not_a_crop), not_a_crop)

    def test_load_wfp_filters(self):
        raw = pd.DataFrame({
            "date": ["#date", "2026-05-15", "2026-06-15", "2026-06-15", "2026-06-15", "2026-04-15", "2026-06-15"],
            "market": ["#market", "Huye", "Huye", "Huye", "Huye", "Huye", "Huye"],
            "commodity": ["#item", "Beans (dry)", "Beans (dry)", "Maize flour", "Maize", "Beans (dry)", "Maize"],
            "unit": ["#u", "KG", "Sack", "KG", "KG", "KG", "KG"],
            "currency": ["#c", "RWF", "RWF", "RWF", "RWF", "RWF", "USD"],
            "price": ["#p", "900", "50000", "300", "500", "800", "1"]})
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "w.csv")
            raw.to_csv(p, index=False)
            w = ic.load_wfp(p)
        self.assertEqual(sorted(zip(w["crop"], w["price"])), [("Beans", 900.0), ("Maize", 500.0)])

    def frames(self):
        esoko = pd.DataFrame({
            "crop_category": ["Beans"] * 5 + ["Maize"],
            "observed_date": pd.to_datetime(["2026-05-10", "2026-06-10", "2026-07-10", "2026-09-10", "2026-10-10",
                                             "2026-05-10"]),
            "price": [700.0, 700.0, 700.0, 100.0, 100.0, 400.0],        # Sept/Oct must be ignored (no WFP months)
            "location": ["A", "B", "A", "A", "B", "A"]})
        wfp = pd.DataFrame({"crop": ["Beans"] * 3, "market": ["X", "Y", "X"],
                            "date": pd.to_datetime(["2026-05-15", "2026-06-15", "2026-07-15"]),
                            "price": [900.0, 900.0, 900.0]})
        return esoko, wfp

    def test_same_months_only_and_premium(self):
        b = ic.retail_benchmark(*self.frames()).set_index("crop")
        self.assertEqual(b.loc["Beans", "esoko_farmgate_median"], 700.0)
        self.assertEqual(b.loc["Beans", "wfp_retail_median"], 900.0)
        self.assertAlmostEqual(b.loc["Beans", "retail_premium_pct"], 200 / 700 * 100)
        self.assertEqual(b.loc["Beans", "months_compared"], 3)

    def test_crop_without_wfp_is_explained_not_invented(self):
        b = ic.retail_benchmark(*self.frames()).set_index("crop")
        self.assertTrue(np.isnan(b.loc["Maize", "wfp_retail_median"]))
        self.assertIn("no WFP", b.loc["Maize", "note"])

    def test_retail_below_farmgate_is_flagged(self):
        esoko, wfp = self.frames()
        wfp["price"] = 500.0
        b = ic.retail_benchmark(esoko, wfp).set_index("crop")
        self.assertIn("check", b.loc["Beans", "note"])

    def test_shipped_wfp_file_loads(self):
        w = ic.load_wfp(os.path.join(DATA, "wfp_retail_rwa_2026.csv"))
        self.assertGreater(len(w), 100)
        self.assertTrue((w["price"] > 0).all())
        self.assertTrue(set(w["crop"]) <= {c for _, c in ic.CROP_RULES})


# ------------------------------------------------------------------ Kinyarwanda text
class I18nTests(unittest.TestCase):
    def setUp(self):
        self._saved = copy.deepcopy(i18n.STR)

    def tearDown(self):
        i18n.STR.clear()
        i18n.STR.update(self._saved)

    def rec(self, worthwhile=True, level="Medium"):
        return dict(best=dict(location="Rwamagana", net_return=669360.0, price=1350.0,
                              last_date=pd.Timestamp("2026-11-12"), reliability=level),
                    baseline=dict(location="Nyabugogo", net_return=656250.0, price=1312.0),
                    uplift=13110.0, uplift_pct=2.0, worthwhile=worthwhile)

    def test_no_missing_keys_or_placeholder_mismatch(self):
        self.assertEqual(i18n.check_translations(), [])

    def test_all_seven_crops_have_a_kinyarwanda_name(self):
        self.assertEqual(set(i18n.CROPS), {c for _, c in ic.CROP_RULES})

    def test_english_advice_is_unchanged_from_the_original_dashboard(self):
        a = i18n.advice("en", self.rec(True), 500)
        self.assertEqual(a["headline"], "Sell at Rwamagana")
        self.assertEqual(a["body"], "After transport you could earn about 669,360 RWF for 500 kg, which is 13,110 RWF "
                                    "(2%) more than selling at Nyabugogo. Price used: 1,350 RWF/kg, last seen 12 Nov.")
        s = i18n.advice("en", self.rec(False), 500)
        self.assertEqual(s["headline"], "Selling at Nyabugogo is fine")
        self.assertEqual(s["body"], "No other market beats it by enough to cover the trip. Expected about 656,250 RWF "
                                    "for 500 kg at 1,312 RWF/kg.")
        self.assertEqual(a["badge"], "Data reliability: Medium")

    def test_kinyarwanda_advice_uses_local_words_and_numbers(self):
        a = i18n.advice("rw", self.rec(True), 500)
        self.assertEqual(a["headline"], "Gurishiriza i Rwamagana")
        for piece in ("669,360 FRW", "13,110 FRW", "500", "Nyabugogo", "12 Ugushyingo"):
            self.assertIn(piece, a["body"])
        self.assertIn("Hagati", a["badge"])
        self.assertEqual(i18n.advice("rw", self.rec(False), 500)["headline"], "Kugurishiriza i Nyabugogo ni byiza")

    def test_missing_translation_falls_back_to_english(self):
        del i18n.STR["rw"]["crop"]
        self.assertEqual(i18n.t("rw", "crop"), "Crop")

    def test_corrections_applied_and_bad_ones_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "c.csv")
            with open(p, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["key", "kinyarwanda"])
                w.writerow(["crop", "Igihingwa cyawe"])
                w.writerow(["head_sell", "Gurisha i (nta izina)"])          # lost the {market} placeholder
                w.writerow(["no_such_key", "x"])
            refused = i18n.apply_corrections(p)
        self.assertEqual(i18n.STR["rw"]["crop"], "Igihingwa cyawe")
        self.assertEqual(i18n.STR["rw"]["head_sell"], self._saved["rw"]["head_sell"])
        self.assertEqual(len(refused), 2)
        self.assertEqual(i18n.apply_corrections(os.path.join(d, "missing.csv")), [])

    def test_review_sheet_lists_every_string(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.csv")
            i18n.export_review_sheet(p)
            with open(p, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        keys = {r["key"] for r in rows}
        self.assertTrue(set(i18n.STR["en"]) <= keys)
        self.assertIn("crop:Beans", keys)


# ------------------------------------------------------------------ SMS prototype
class SmsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = ic.load_prices(os.path.join(DATA, "demo_crop_data.csv"))
        cls.markets = ic.load_markets(os.path.join(DATA, "markets.csv"))

    def reply(self, text):
        return sms.handle_sms(text, self.df, self.markets)

    def test_every_reply_is_one_gsm7_sms(self):
        crops = list(i18n.CROPS) + ["Bananas"]
        n = 0
        for market in self.markets["location"]:
            for cmd, crop in [("SELL", "beans"), ("SELL", "maize"), ("SELL", "irish potatoes"), ("SELL", "rice"),
                              ("GURISHA", "ibishyimbo"), ("GURISHA", "ibigori"), ("GURISHA", "umuceri"),
                              ("SELL", "sweet potatoes"), ("SELL", "cassava"), ("GURISHA", "inyanya"),
                              ("PRICE", "rice"), ("IGICIRO", "ibirayi")]:
                for qty in (10, 500, 20000):
                    r = self.reply(f"{cmd} {crop} {qty} {market}")
                    n += 1
                    self.assertLessEqual(r["length"], 160, r["reply"])
                    self.assertEqual(r["segments"], 1, r["reply"])
                    self.assertTrue(sms.is_gsm7(r["reply"]), r["reply"])
        self.assertGreater(n, 400)
        for crop in crops:
            for text in ("HELP", "UBUFASHA", f"SELL {crop} abc huye", f"GURISHA {crop} 500 nowhere"):
                r = self.reply(text)
                self.assertLessEqual(r["length"], 160)
                self.assertTrue(sms.is_gsm7(r["reply"]))

    def test_sell_advice_english_and_kinyarwanda(self):
        en = self.reply("sell maize 500 nyabugogo")
        self.assertEqual((en["command"], en["lang"]), ("sell", "en"))
        self.assertIn("SELL at", en["reply"])
        rw = self.reply("gurisha ibigori 500 nyabugogo")
        self.assertEqual((rw["command"], rw["lang"]), ("sell", "rw"))
        self.assertIn("Gurishiriza i", rw["reply"])
        self.assertTrue(rw["reply"].startswith("Ibigori 500kg"))

    def test_same_advice_as_the_dashboard_logic(self):
        r = self.reply("SELL MAIZE 500 NYABUGOGO")["reply"]
        product = self.df[self.df.crop_category == "Maize"]["product"].value_counts().index[0]
        cp = ic.current_prices(self.df, "Maize", product, asof=self.df["observed_date"].max())
        ranked = ic.rank_markets(ic.add_distance(cp, self.markets, "Nyabugogo"), 500, ic.DEFAULT_RATE)
        rec = ic.recommend(ranked)
        self.assertIn(rec["best"]["location"], r)
        self.assertIn(f"{rec['best']['net_return']:,.0f}", r)

    def test_message_styles_give_the_same_answer(self):
        base = self.reply("SELL BEANS 500 NYABUGOGO")["reply"]
        for variant in ("sell beans 500kg nyabugogo", "Sell  Beans 500 kg at Nyabugogo", "sell 500 beans nyabugogo",
                        "SELL, BEANS, 500, NYABUGOGO"):
            self.assertEqual(self.reply(variant)["reply"], base, variant)

    def test_two_word_crops(self):
        self.assertEqual(sms._parse_crop(["sweet", "potatoes", "100"]), ("Sweet Potatoes", ["100"]))
        self.assertEqual(sms._parse_crop(["irish", "potatoes", "100"]), ("Irish Potatoes", ["100"]))
        self.assertEqual(sms._parse_crop(["potato", "100"]), ("Irish Potatoes", ["100"]))

    def test_market_matching(self):
        self.assertEqual(sms._match_market(["nyabu"], self.markets), "Nyabugogo")      # unique prefix
        self.assertEqual(sms._match_market(["butare"], self.markets), "Huye")          # alias
        self.assertIsNone(sms._match_market(["atlantis"], self.markets))
        self.assertIsNone(sms._match_market(["ny"], self.markets))                      # ambiguous: Nyabugogo/Nyanza/...

    def test_errors_are_helpful_not_crashes(self):
        self.assertEqual(self.reply("sell banana 100 huye")["command"], "error")
        self.assertIn("weight", self.reply("sell beans abc huye")["reply"])
        self.assertIn("weight", self.reply("sell beans 5 huye")["reply"])                # below 10 kg
        self.assertIn("Market not found", self.reply("sell beans 500 atlantis")["reply"])
        self.assertEqual(self.reply("")["command"], "help")
        self.assertEqual(self.reply("hello there")["command"], "help")
        self.assertEqual(self.reply("ibishyimbo 500 huye")["lang"], "rw")                 # no command word

    def test_price_command(self):
        r = self.reply("PRICE RICE")["reply"]
        self.assertTrue(r.startswith("Rice RWF/kg: highest"))
        self.assertTrue(self.reply("IGICIRO IBIRAYI")["reply"].startswith("Ibirayi FRW/kg: hejuru"))

    def test_crop_without_prices_says_so(self):
        self.assertIn("No recent price for Cassava", self.reply("sell cassava 100 huye")["reply"])

    def test_segment_counting(self):
        self.assertEqual(sms.sms_segments("a" * 160), 1)
        self.assertEqual(sms.sms_segments("a" * 161), 2)
        self.assertEqual(sms.sms_segments("a" * 306), 2)
        self.assertEqual(sms.sms_segments("a" * 307), 3)
        self.assertEqual(sms.sms_segments("ŵ" * 70), 1)      # w with circumflex: not in the SMS alphabet
        self.assertEqual(sms.sms_segments("ŵ" * 71), 2)
        self.assertEqual(sms.sms_length("[a]"), 5)                # [ and ] count as two each

    def test_overlong_reply_is_cut_to_one_sms(self):
        self.assertLessEqual(len(sms._fit("x" * 500)), 160)
        self.assertEqual(sms._fit("short", " tail"), "short tail")


class WebhookTests(unittest.TestCase):
    def test_http_roundtrip(self):
        df = ic.load_prices(os.path.join(DATA, "demo_crop_data.csv"))
        markets = ic.load_markets(os.path.join(DATA, "markets.csv"))
        server = HTTPServer(("127.0.0.1", 0), make_handler(df, markets, {}))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            self.assertEqual(urllib.request.urlopen(base + "/health", timeout=5).read(), b"ok")
            body = urllib.parse.urlencode({"from": "+250700000000", "text": "GURISHA IBIGORI 500 NYABUGOGO"}).encode()
            out = urllib.request.urlopen(urllib.request.Request(base + "/sms", data=body), timeout=5).read().decode()
            self.assertIn("Gurishiriza i", out)
            junk = urllib.request.urlopen(urllib.request.Request(base + "/sms", data=b"text=%FF%FE"), timeout=5).read()
            self.assertTrue(junk)                                      # still answers
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
