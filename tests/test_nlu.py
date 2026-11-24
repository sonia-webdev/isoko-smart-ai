"""Tests for isoko_nlu with a stand-in model (the real language model needs Colab)."""
import json
import os
import re
import sys
import unittest

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_core as ic  # noqa: E402
import isoko_nlu as nlu  # noqa: E402

MARKETS = ic.load_markets(os.path.join(ROOT, "data", "markets.csv"))
TESTSET = pd.read_csv(os.path.join(ROOT, "docs", "farmer_messages_testset.csv"), encoding="utf-8-sig")


def message_of(prompt):
    return prompt.rsplit('Message: "', 1)[1].rsplit('"\nJSON:', 1)[0]


def oracle(prompt):
    """Stand-in 'model' that knows the right answers, to test everything around the model."""
    r = TESTSET[TESTSET.text == message_of(prompt)].iloc[0]
    return "Sure! ```json\n" + json.dumps(dict(intent=r.expected_intent, crop=r.expected_crop if isinstance(r.expected_crop, str) else "",
                                            qty=r.expected_qty if str(r.expected_qty) != "nan" else "",
                                            market=r.expected_market if isinstance(r.expected_market, str) else "",
                                            lang="rw" if r.language == "rw" else "en")) + "\n```"


def demo_prices():
    rows = []
    for mk in ("Nyabugogo", "Huye", "Musanze", "Kimironko"):
        for d in range(3):
            rows.append(dict(observed_date=pd.Timestamp("2026-11-10") + pd.Timedelta(days=d), crop_category="Beans",
                             product="Bean Shyushya", unit="Kg", channel="farmgate", location=mk, price=1500 + 100 * len(mk) % 7 * 10,
                             data_status="verified", crop_cat="Beans"))
    return pd.DataFrame(rows)


class ParsingTests(unittest.TestCase):
    def test_json_is_found_inside_extra_words_and_fences(self):
        self.assertEqual(nlu.parse_llm_json('Here: ```json\n{"intent": "sell"}\n``` ok'), {"intent": "sell"})
        self.assertIsNone(nlu.parse_llm_json("I cannot help"))
        self.assertIsNone(nlu.parse_llm_json("{broken json"))

    def test_checks_drop_invented_or_impossible_fields(self):
        clean, problems = nlu.normalise(dict(intent="sell", crop="Bananas", qty="9999999", market="Atlantis", lang="rw"), MARKETS)
        self.assertEqual((clean["crop"], clean["qty"], clean["market"]), ("", "", ""))
        self.assertEqual(len(problems), 3)

    def test_good_fields_are_kept_and_market_spelling_is_matched(self):
        clean, problems = nlu.normalise(dict(intent="sell", crop="beans", qty="1,500", market="nyabugogo", lang="rw"), MARKETS)
        self.assertEqual((clean["crop"], clean["qty"], clean["market"], clean["lang"]), ("Beans", 1500, "Nyabugogo", "rw"))
        self.assertEqual(problems, [])

    def test_kinyarwanda_crop_name_is_accepted(self):
        clean, _ = nlu.normalise(dict(intent="price", crop="ibigori"), MARKETS)
        self.assertEqual(clean["crop"], "Maize")


class PipelineTests(unittest.TestCase):
    def test_a_perfect_model_scores_100_percent(self):
        res = nlu.evaluate(nlu.llm_extractor(oracle, MARKETS), TESTSET, MARKETS)
        self.assertGreaterEqual(res.all_ok.mean(), 0.97)

    def test_unreadable_model_output_falls_back_to_the_rule_reader(self):
        ex = nlu.llm_extractor(lambda p: "I do not know", MARKETS)("SELL BEANS 500 NYABUGOGO")
        self.assertEqual((ex["crop"], ex["qty"], ex["market"]), ("Beans", 500, "Nyabugogo"))
        self.assertIn("rules", ex["source"])

    def test_model_cannot_make_up_a_market(self):
        bad = lambda p: json.dumps(dict(intent="sell", crop="Beans", qty=500, market="Moonbase", lang="en"))
        r = nlu.answer("sell beans 500", nlu.llm_extractor(bad, MARKETS), demo_prices(), MARKETS)
        self.assertEqual(r["fields"]["market"], "")
        self.assertIn("Market not found", r["reply"])

    def test_answer_for_a_complete_message_is_one_sms_and_has_no_model_text(self):
        ex = nlu.llm_extractor(lambda p: json.dumps(dict(intent="sell", crop="Beans", qty=500, market="Nyabugogo", lang="en")), MARKETS)
        r = nlu.answer("whatever the farmer typed", ex, demo_prices(), MARKETS)
        self.assertLessEqual(r["segments"], 1)
        self.assertTrue(r["reply"].startswith("Beans 500kg"))

    def test_help_and_missing_fields_get_helpful_replies(self):
        ex = lambda t: dict(intent="sell", lang="en", crop="Beans", qty="", market="Huye")
        self.assertIn("weight", nlu.answer("x", ex, demo_prices(), MARKETS)["reply"])
        ex2 = lambda t: dict(intent="other", lang="rw", crop="", qty="", market="")
        self.assertIn("GURISHA", nlu.answer("Muraho", ex2, demo_prices(), MARKETS)["reply"])


class TestsetTests(unittest.TestCase):
    def test_every_kinyarwanda_row_is_marked_for_native_review(self):
        rw = TESTSET[TESTSET.language.isin(["rw", "mixed"])]
        self.assertTrue((rw.needs_native_review == "yes").all())

    def test_expected_markets_and_crops_are_real(self):
        self.assertTrue(set(TESTSET.expected_market.dropna()) <= set(MARKETS.location))
        self.assertTrue(set(TESTSET.expected_crop.dropna()) <= set(nlu.CROPS))


class RuleReaderTests(unittest.TestCase):
    HELD = pd.read_csv(os.path.join(ROOT, "docs", "farmer_messages_heldout.csv"), encoding="utf-8-sig")

    def test_rule_reader_handles_free_sentences_in_both_languages(self):
        for name, ts in (("tuning set", TESTSET), ("held-out set", self.HELD)):
            res = nlu.evaluate(nlu.rule_extractor(MARKETS), ts, MARKETS)
            self.assertGreaterEqual(res.all_ok.mean(), 0.95, name)

    def test_kinyarwanda_possessive_forms_are_understood(self):
        ex = nlu.rule_extractor(MARKETS)
        self.assertEqual(ex("igiciro cy'ibijumba")["crop"], "Sweet Potatoes")
        self.assertEqual(ex("ibiro 500 by'ibigori i Muhanga")["market"], "Muhanga")

    def test_a_farmer_who_writes_kinyarwanda_gets_kinyarwanda_back(self):
        import isoko_sms
        r = isoko_sms.handle_sms("Ndashaka kugurisha ibishyimbo ibiro 500 i Nyabugogo. Nabigurisha he?", demo_prices(), MARKETS)
        self.assertEqual(r["lang"], "rw")
        self.assertTrue(r["reply"].startswith("Ibishyimbo 500kg"))
        self.assertLessEqual(r["segments"], 1)

    def test_numbers_written_in_kinyarwanda_words(self):
        ex = nlu.rule_extractor(MARKETS)("Mfite ibirayi magana abiri i Rubavu, nabigurisha he?")
        self.assertEqual((ex["crop"], ex["qty"], ex["market"]), ("Irish Potatoes", 200, "Rubavu"))
