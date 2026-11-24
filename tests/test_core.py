"""Unit tests for isoko_core. Run:  python -m unittest discover -s tests -v"""
import os
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import isoko_core as ic  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def raw_rows(**over):
    base = dict(observed_date="2026-06-02", product="Maize", unit="Kg", channel="farmgate",
                location="Musanze", price=500.0, currency="RWF", source="Esoko")
    base.update(over)
    return base


class CleaningTests(unittest.TestCase):
    def test_crop_is_inferred_when_column_missing(self):
        raw = pd.DataFrame([raw_rows(product=p, price=100 + i) for i, p in enumerate(
            ["Bean Shyushya", "Cassava", "Irish- Potato- Kirundo", "Maize", "Rice - TZ - No 2",
             "Sweet-Potatoes", "Tomatos", "Banana"])])
        out = ic.clean_prices(raw)
        got = dict(zip(out["product"], out["crop_category"]))
        self.assertEqual(got["Bean Shyushya"], "Beans")
        self.assertEqual(got["Irish- Potato- Kirundo"], "Irish Potatoes")
        self.assertEqual(got["Sweet-Potatoes"], "Sweet Potatoes")      # not "Irish Potatoes"
        self.assertEqual(got["Rice - TZ - No 2"], "Rice")
        self.assertEqual(got["Tomatos"], "Tomatoes")
        self.assertNotIn("Banana", got)                                  # not a project crop: dropped

    def test_real_esoko_names_that_look_like_crops_are_not_crops(self):
        for name in ("Maize Flour", "Maize-flour-imported", "Maize Bran", "Cassava leaves", "Cassava-flour",
                     "Soya-Bean", "Green bean", "Fresh bean", "Sweet pepper", "Sorghum flour", "Wheat-Flour",
                     "Palm-oil", "Banana", "Beef/Iroti"):
            self.assertIsNone(ic.infer_crop(name), name)
        for name, crop in (("Bean - Mushingiriro", "Beans"), ("Beans/Mutiki", "Beans"), ("Bean", "Beans"),
                           ("Irish potato - Kinigi Grade 2", "Irish Potatoes"), ("Irish-potato", "Irish Potatoes"),
                           ("Rice-Tz", "Rice"), ("RICE - luck Kema", "Rice"), ("Rice Pakistan", "Rice"),
                           ("Sweet-Potatoes", "Sweet Potatoes"), ("Tomatos", "Tomatoes"), ("Maize", "Maize"),
                           ("Cassava", "Cassava")):
            self.assertEqual(ic.infer_crop(name), crop, name)

    def test_existing_crop_column_is_kept(self):
        out = ic.clean_prices(pd.DataFrame([raw_rows(crop_category="Grains")]))
        self.assertEqual(out["crop_category"].iloc[0], "Grains")

    def test_window_unit_and_bad_values(self):
        raw = pd.DataFrame([raw_rows(observed_date="2026-04-30"),      # before window
                            raw_rows(unit="bunch"),                    # not kg
                            raw_rows(price=-5),                        # bad price
                            raw_rows(price=700.0)])                    # the only good row
        out = ic.clean_prices(raw)
        self.assertEqual(len(out), 1)
        self.assertEqual(out["price"].iloc[0], 700.0)

    def test_demo_data_is_labelled(self):
        out = ic.load_prices(os.path.join(DATA, "demo_crop_data.csv"))
        self.assertTrue((out["data_status"] == "demonstration").all())


class DistanceTests(unittest.TestCase):
    def setUp(self):
        self.markets = ic.load_markets(os.path.join(DATA, "markets.csv"))
        self.prices = pd.DataFrame({"location": ["Nyabugogo", "Musanze", "Butare", "Nowhere"],
                                    "price": [800.0, 900.0, 850.0, 1000.0]})

    def test_same_market_is_zero(self):
        out = ic.add_distance(self.prices, self.markets, "Nyabugogo")
        self.assertEqual(out.loc[0, "distance_km"], 0.0)

    def test_estimate_and_unknown(self):
        out = ic.add_distance(self.prices, self.markets, "Nyabugogo").set_index("location")
        self.assertEqual(out.loc["Musanze", "distance_source"], "estimate")
        self.assertTrue(np.isnan(out.loc["Nowhere", "distance_km"]))
        self.assertEqual(out.loc["Nowhere", "distance_source"], "unknown")

    def test_alias_butare_is_huye(self):
        out = ic.add_distance(self.prices, self.markets, "Nyabugogo").set_index("location")
        self.assertFalse(np.isnan(out.loc["Butare", "distance_km"]))
        self.assertEqual(ic.missing_coordinates(
            pd.DataFrame({"location": ["Butare", "Nowhereville"]}), self.markets), ["Nowhereville"])

    def test_real_road_distance_beats_estimate(self):
        road = {("nyabugogo", "musanze"): 91.0}
        out = ic.add_distance(self.prices, self.markets, "Nyabugogo", road_km=road).set_index("location")
        self.assertEqual(out.loc["Musanze", "distance_km"], 91.0)
        self.assertEqual(out.loc["Musanze", "distance_source"], "road")
        back = ic.add_distance(self.prices, self.markets, "Musanze", road_km=road).set_index("location")
        self.assertEqual(back.loc["Nyabugogo", "distance_km"], 91.0)     # works in both directions

    def test_road_distance_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.csv")
            pd.DataFrame({"origin": ["Nyabugogo"], "destination": ["Huye"], "km": [130.5]}).to_csv(p, index=False)
            self.assertEqual(ic.load_road_distances(p), {("nyabugogo", "huye"): 130.5})


class MarketFileTests(unittest.TestCase):
    def test_coordinates_are_inside_rwanda_and_unique(self):
        m = ic.load_markets(os.path.join(DATA, "markets.csv"))
        self.assertTrue(m["lat"].between(-2.84, -1.05).all(), "a latitude is outside Rwanda")
        self.assertTrue(m["lon"].between(28.86, 30.90).all(), "a longitude is outside Rwanda")
        self.assertFalse(m["location"].str.lower().duplicated().any(), "duplicate market name")


class RankingTests(unittest.TestCase):
    def priced(self):
        return pd.DataFrame({"location": ["Home", "Far", "Mid"], "price": [800.0, 1000.0, 900.0],
                             "distance_km": [0.0, 100.0, 40.0], "reliability": ["High"] * 3,
                             "last_date": pd.to_datetime(["2026-11-01"] * 3)})

    def test_flat_rate_matches_formula(self):
        r = ic.rank_markets(self.priced(), 500, 0.2).set_index("location")
        self.assertAlmostEqual(r.loc["Far", "net_return"], 500 * (1000 - 0.2 * 100))
        self.assertAlmostEqual(r.loc["Home", "net_return"], 500 * 800)

    def test_vehicle_trips_and_round_trip(self):
        # 2,500 kg in a 1,000 kg pickup = 3 trips, 100 km each way, 500 RWF/km, 10,000 fixed per trip
        r = ic.rank_markets_vehicle(self.priced(), 2500, 1000, 500, round_trip=True, fixed_trip_cost=10000)
        far = r.set_index("location").loc["Far"]
        self.assertEqual(far["trips"], 3)
        self.assertAlmostEqual(far["transport_cost"], 3 * 2 * 100 * 500 + 3 * 10000)
        self.assertAlmostEqual(far["net_return"], 2500 * 1000 - far["transport_cost"])
        home = r.set_index("location").loc["Home"]
        self.assertEqual(home["transport_cost"], 0.0)                     # selling at home costs no transport

    def test_one_way_is_cheaper_than_round_trip(self):
        both = ic.rank_markets_vehicle(self.priced(), 500, 1000, 500, round_trip=True).set_index("location")
        one = ic.rank_markets_vehicle(self.priced(), 500, 1000, 500, round_trip=False).set_index("location")
        self.assertAlmostEqual(both.loc["Far", "transport_cost"], 2 * one.loc["Far", "transport_cost"])

    def test_loss_and_fees(self):
        # 2% lost per 100 km, 100 km away: 10 of 500 kg lost; fee 10 RWF per kg sold
        r = ic.rank_markets_vehicle(self.priced(), 500, 1000, 0, loss_pct_per_100km=2.0,
                                    market_fee_per_kg=10).set_index("location")
        far = r.loc["Far"]
        self.assertAlmostEqual(far["loss_kg"], 10.0)
        self.assertAlmostEqual(far["net_return"], 500 * 1000 - 10 * 1000 - 10 * 490)

    def test_unknown_distance_is_not_ranked_first(self):
        p = self.priced()
        p.loc[1, "distance_km"] = np.nan
        r = ic.rank_markets_vehicle(p, 500, 1000, 500)
        self.assertTrue(np.isnan(r.iloc[-1]["net_return"]))

    def test_recommend_worth_the_trip(self):
        r = ic.rank_markets(self.priced(), 500, 0.2)
        rec = ic.recommend(r)
        self.assertEqual(rec["best"]["location"], "Far")
        self.assertEqual(rec["baseline"]["location"], "Home")
        self.assertTrue(rec["worthwhile"])


class StabilityTests(unittest.TestCase):
    def priced(self, far_price):
        return pd.DataFrame({"location": ["Home", "Far"], "price": [800.0, far_price],
                             "distance_km": [0.0, 100.0], "reliability": ["High"] * 2,
                             "last_date": pd.to_datetime(["2026-11-01"] * 2)})

    def test_stable_when_gap_is_large(self):
        p = self.priced(1500.0)
        s = ic.best_market_stability(lambda k: ic.rank_markets(p, 500, 0.2 * k))
        self.assertTrue(s["stable"])
        self.assertEqual(s["base_best"], "Far")

    def test_unstable_when_gap_is_small(self):
        # at 0.2 RWF/kg/km Far nets 1000-20=980 (> 800 by 22%); at 2x cost 1000-40=960; at big scales it flips
        p = self.priced(860.0)                       # 860 - 20 = 840 (5% better): fragile
        s = ic.best_market_stability(lambda k: ic.rank_markets(p, 500, 0.2 * k), scales=(0.5, 1.0, 1.5, 2.0))
        self.assertFalse(s["stable"])
        self.assertLess(s["same_share"], 1.0)

    def test_scale_one_is_always_included(self):
        p = self.priced(1500.0)
        s = ic.best_market_stability(lambda k: ic.rank_markets(p, 500, 0.2 * k), scales=(2.0,))
        self.assertIn(1.0, s["by_scale"])


class ForecastTests(unittest.TestCase):
    def test_gate_needs_enough_weeks(self):
        s = pd.Series(np.arange(5.0), index=pd.date_range("2026-06-01", periods=5, freq="7D"))
        self.assertFalse(ic.forecast_gate(s)["show"])

    def test_gate_shows_on_a_clean_trend(self):
        s = pd.Series(500 + 10 * np.arange(20.0) + np.tile([0, 3], 10),
                      index=pd.date_range("2026-06-01", periods=20, freq="7D"))
        g = ic.forecast_gate(s)
        self.assertTrue(g["show"])
        self.assertGreater(g["forecast"], 600)

    def test_trend_signal(self):
        s = pd.Series([500.0] * 4 + [600.0] * 2)
        self.assertEqual(ic.trend_signal(s)["direction"], "rising")

    def test_data_age(self):
        df = pd.DataFrame({"observed_date": pd.to_datetime(["2026-11-01", "2026-11-05"])})
        self.assertEqual(ic.data_age_days(df, today="2026-11-16"), 11)


class ReliabilityTests(unittest.TestCase):
    def test_labels(self):
        self.assertEqual(ic.reliability(5, 2, False), "High")
        self.assertEqual(ic.reliability(3, 9, False), "Medium")
        self.assertEqual(ic.reliability(5, 20, False), "Low")
        self.assertEqual(ic.reliability(1, 1, False), "Low")


if __name__ == "__main__":
    unittest.main()


class TestTrustedOnly(unittest.TestCase):
    def test_single_report_markets_dropped_but_origin_kept(self):
        import pandas as pd
        cp = pd.DataFrame({"location": ["A", "B", "C", "D"], "days_with_price": [1, 3, 2, 1]})
        out = ic.trusted_only(cp, "A")
        self.assertEqual(sorted(out.location), ["A", "B", "C"])

    def test_nothing_dropped_when_too_few_remain(self):
        import pandas as pd
        cp = pd.DataFrame({"location": ["A", "B", "C"], "days_with_price": [1, 1, 3]})
        self.assertEqual(len(ic.trusted_only(cp, "A")), 3)


class TestSeasonal(unittest.TestCase):
    @staticmethod
    def _history(years=5, trend=0.0):
        """Maize-like series: cheap in March, dear in November, plus an optional steady price rise."""
        import numpy as np
        import pandas as pd
        rows = []
        for market in ("A", "B", "C"):
            for y in range(2015, 2015 + years):
                for m in range(1, 13):
                    season = 1 + 0.2 * np.cos((m - 11) / 12 * 2 * np.pi)          # peak in November, low in May
                    t = (y - 2015) * 12 + m
                    rows.append(dict(crop="Maize", commodity="Maize", market=market,
                                     date=f"{y}-{m:02d}-01", price=300 * season * (1 + trend) ** t))
        return pd.DataFrame(rows)

    def test_finds_the_peak_and_low_month(self):
        si = ic.seasonal_index(self._history())
        s = ic.seasonal_summary(si, self._history()).iloc[0]
        self.assertEqual((s.dearest_month, s.cheapest_month), ("Nov", "May"))
        self.assertAlmostEqual(si["index"].mean(), 100, places=6)

    def test_steady_inflation_is_not_mistaken_for_a_season(self):
        flat = self._history(trend=0.0)
        flat["price"] = 300.0
        rising = flat.copy()
        rising["price"] = [300 * 1.01 ** i for i in range(len(rising))]            # grows, no season at all
        rising["price"] = rising.groupby("market").cumcount().map(lambda i: 300 * 1.01 ** i)
        si = ic.seasonal_index(rising)
        self.assertLess(si["index"].max() - si["index"].min(), 5)

    def test_crop_with_too_few_years_is_left_out(self):
        self.assertTrue(ic.seasonal_index(self._history(years=2)).empty)

    def test_monthly_farmgate_spread_needs_five_markets(self):
        import pandas as pd
        d = pd.DataFrame({"crop_category": "Beans", "observed_date": pd.Timestamp("2026-06-10"),
                          "location": list("ABCDE") + list("ABC"), "price": [100, 120, 140, 160, 180, 90, 100, 110]})
        d["month"] = 0
        a = ic.monthly_farmgate(d.iloc[:5].copy())
        b = ic.monthly_farmgate(d.iloc[:4].copy())
        self.assertIsNotNone(a.spread_pct.iloc[0])
        self.assertTrue(b.spread_pct.isna().iloc[0])


class TestPattern2026(unittest.TestCase):
    @staticmethod
    def _df():
        import pandas as pd
        rows = []
        for month, price in ((5, 500), (6, 600), (7, 450)):
            for mk in "ABCDE":
                rows.append(dict(crop_category="Beans", observed_date=pd.Timestamp(2026, month, 10), location=mk, price=price))
        return pd.DataFrame(rows)

    def test_index_is_relative_to_first_month(self):
        pm = ic.pattern_2026(self._df())
        self.assertEqual(pm["index_may"].tolist(), [100.0, 120.0, 90.0])

    def test_summary_finds_cheapest_and_dearest(self):
        s = ic.pattern_summary(ic.pattern_2026(self._df())).iloc[0]
        self.assertEqual((s.cheapest_month, s.dearest_month, s.change_pct), ("Jul", "Jun", -10.0))

    def test_last_month_with_few_days_is_marked_partial(self):
        import pandas as pd
        d = self._df()
        d.loc[d.observed_date.dt.month == 7, "observed_date"] = pd.Timestamp(2026, 7, 8)
        self.assertEqual(ic.pattern_2026(d)["partial"].tolist(), [False, False, True])

    def test_month_with_too_few_markets_is_left_out(self):
        import pandas as pd
        d = self._df()
        extra = pd.DataFrame([dict(crop_category="Beans", observed_date=pd.Timestamp(2026, 8, 3), location="A", price=9999)])
        pm = ic.pattern_2026(pd.concat([d, extra]))
        self.assertEqual(len(pm), 3)
        self.assertNotIn(9999, pm["median_price"].tolist())


class TestPriceStory(unittest.TestCase):
    @staticmethod
    def _df():
        import pandas as pd
        rows = []
        for mk in "ABCDEFGHIJ":
            rows += [dict(crop_category="Rice", observed_date=pd.Timestamp(2026, 5, 10), location=mk, price=1500),
                     dict(crop_category="Rice", observed_date=pd.Timestamp(2026, 6, 10), location=mk, price=1480),
                     dict(crop_category="Beans", observed_date=pd.Timestamp(2026, 5, 10), location=mk, price=900),
                     dict(crop_category="Beans", observed_date=pd.Timestamp(2026, 6, 10), location=mk, price=1170)]
        return pd.DataFrame(rows)

    def test_direction_and_same_market_check(self):
        d = self._df()
        st = ic.price_story(ic.pattern_2026(d), d).set_index("crop")
        self.assertEqual(st.loc["Beans", "direction"], "Rising")
        self.assertEqual(st.loc["Rice", "direction"], "About the same")
        self.assertEqual(st.loc["Beans", "same_market_change_pct"], 30.0)
        self.assertEqual(st.loc["Beans", "evidence"], "Good")

    def test_plain_words_separates_high_price_from_big_rise(self):
        d = self._df()
        text = " ".join(ic.plain_words(ic.price_story(ic.pattern_2026(d), d)))
        self.assertIn("Highest price per kg now:** Rice", text)
        self.assertIn("Rose the most since May:** Beans", text)
        self.assertIn("A high price is not the same as a rise", text)
        self.assertIn("did not rise", text)

    def test_different_markets_in_the_two_months_are_not_trusted(self):
        import pandas as pd
        d = self._df()
        d = d[~((d.crop_category == "Beans") & (d.observed_date.dt.month == 6) & d.location.isin(list("ABCDE")))]
        d = d[~((d.crop_category == "Beans") & (d.observed_date.dt.month == 5) & d.location.isin(list("FGHIJ")))]
        st = ic.price_story(ic.pattern_2026(d, min_markets=5), d).set_index("crop")
        self.assertEqual(st.loc["Beans", "same_markets"], 0)
        self.assertEqual(st.loc["Beans", "evidence"], "Weak")


class TestExplainRanking(unittest.TestCase):
    @staticmethod
    def _ranked():
        import pandas as pd
        prices = pd.DataFrame({"location": ["Home", "Near", "Far", "Cheap"], "price": [1000.0, 1400.0, 1700.0, 900.0],
                               "distance_km": [0.0, 20.0, 150.0, 10.0], "reliability": ["High", "High", "Low", "High"],
                               "days_with_price": [3, 3, 1, 3]})
        return ic.rank_markets(prices, 500, 5.0)

    def test_every_market_gets_a_reason_and_the_best_is_marked(self):
        r = self._ranked()
        rec = ic.recommend(r)
        why = ic.explain_ranking(r, rec)
        self.assertTrue(all(why.str.len() > 20))
        self.assertTrue(why[r.location == "Near"].iloc[0].startswith("RECOMMENDED"))

    def test_far_market_with_higher_price_is_explained_by_transport(self):
        r = self._ranked()
        why = ic.explain_ranking(r, ic.recommend(r))
        far = why[r.location == "Far"].iloc[0]
        self.assertIn("Pays more per kg", far)
        self.assertIn("less than at Near", far)
        self.assertIn("old or rests on few reports", far)

    def test_home_market_is_explained_when_nothing_beats_it(self):
        import pandas as pd
        prices = pd.DataFrame({"location": ["Home", "Other"], "price": [1000.0, 1020.0], "distance_km": [0.0, 30.0],
                               "reliability": ["High", "High"], "days_with_price": [3, 3]})
        r = ic.rank_markets(prices, 500, 1.0)
        why = ic.explain_ranking(r, ic.recommend(r))
        self.assertIn("Your own market", why[r.location == "Home"].iloc[0])
        self.assertIn("No other market beats it", why[r.location == "Home"].iloc[0])
        self.assertIn("Pays more per kg", why[r.location == "Other"].iloc[0])

    def test_reasons_can_be_given_in_kinyarwanda(self):
        r = self._ranked()
        rec = ic.recommend(r)
        rw = ic.explain_ranking(r, rec, lang="rw")
        self.assertTrue(rw[r.location == "Near"].iloc[0].startswith("BYASHISHIJWE"))
        self.assertIn("bishyura menshi ku kilo", rw[r.location == "Far"].iloc[0].lower())
        self.assertFalse(any("RECOMMENDED" in x or "Pays" in x for x in rw))
