"""Tests for the data tools and the backtest module."""
import json
import os
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import backtest as bt  # noqa: E402
import isoko_core as ic  # noqa: E402
from tools.add_prices import merge_prices  # noqa: E402
from tools.build_road_distances import parse_table  # noqa: E402
from tools.combine_crops import combine, crops_covered  # noqa: E402


class AddPricesTests(unittest.TestCase):
    def old(self):
        return pd.DataFrame({"observed_date": ["2026-11-01"], "product": ["Maize"], "unit": ["Kg"],
                             "channel": ["farmgate"], "location": ["Musanze"], "price": [500.0],
                             "currency": ["RWF"], "source": ["Esoko"]})

    def test_adds_new_and_skips_duplicates_and_bad_rows(self):
        new = pd.DataFrame({"observed_date": ["2026-11-01", "2026-11-08", "not a date", "2026-11-08", "2026-11-08"],
                            "product": ["Maize", "Maize", "Maize", "Banana", "Maize"],
                            "location": ["Musanze", "Musanze", "Musanze", "Musanze", "Huye"],
                            "price": [500, 520, 530, 800, 510],
                            "unit": ["Kg", "Kg", "Kg", "Kg", "bunch"]})
        merged, rep = merge_prices(self.old(), new)
        self.assertEqual(rep["skipped_bad"], 1)
        self.assertEqual(rep["skipped_not_kg"], 1)
        self.assertEqual(rep["added"], 2)                       # the 520 Maize row and the Banana row
        self.assertEqual(rep["unknown_products"], ["Banana"])
        self.assertEqual(list(merged.columns), list(self.old().columns))

    def test_missing_required_column_is_explained(self):
        with self.assertRaises(ValueError) as cm:
            merge_prices(self.old(), pd.DataFrame({"product": ["Maize"], "price": [1]}))
        self.assertIn("observed_date", str(cm.exception))


class RoadDistanceTests(unittest.TestCase):
    def test_parse_osrm_response(self):
        resp = {"code": "Ok", "distances": [[0, 91000.0, None], [92000.0, 0, 5000.0], [None, 5000.0, 0]]}
        out = parse_table(resp, ["A", "B", "C"])
        got = {(r.origin, r.destination): r.km for r in out.itertuples()}
        self.assertEqual(got[("A", "B")], 91.0)
        self.assertEqual(got[("B", "A")], 92.0)
        self.assertNotIn(("A", "C"), got)                       # no route: skipped, falls back to an estimate
        self.assertNotIn(("A", "A"), got)

    def test_error_response(self):
        with self.assertRaises(RuntimeError):
            parse_table({"code": "InvalidQuery", "message": "bad"}, ["A"])


class TransportFitTests(unittest.TestCase):
    def test_rate_from_quotes(self):
        q = pd.DataFrame({"vehicle": ["Pickup", "Pickup", "Pickup", "Motorbike"],
                          "capacity_kg": [1000, 1000, 1000, 100],
                          "distance_km": [100, 50, 80, 20],
                          "round_trip": ["yes", "yes", "no", "yes"],
                          "total_quote_rwf": [100000, 40000, 40000, 8000]})
        fit = ic.fit_vehicle_rates(q)
        # pickup rates: 100000/(100*2)=500, 40000/(50*2)=400, 40000/80=500 -> median 500
        self.assertEqual(fit["Pickup"]["rate_per_km"], 500)
        self.assertEqual(fit["Pickup"]["n_quotes"], 3)
        self.assertEqual(fit["Motorbike"]["rate_per_km"], 200)  # 8000/(20*2)

    def test_incomplete_quotes_are_ignored(self):
        q = pd.DataFrame({"vehicle": ["Truck", "Truck"], "capacity_kg": [5000, 5000],
                          "distance_km": [100, np.nan], "total_quote_rwf": [200000, 300000]})
        self.assertEqual(ic.fit_vehicle_rates(q)["Truck"]["n_quotes"], 1)

    def test_vehicles_file_overrides_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "vehicles.json")
            with open(p, "w") as f:
                json.dump({"Truck": {"capacity_kg": 4000, "rate_per_km": 999, "n_quotes": 6}}, f)
            v = ic.load_vehicles(p)
            self.assertEqual(v["Truck"]["rate_per_km"], 999)
            self.assertIn("Motorbike", v)                       # other defaults stay
        self.assertEqual(ic.load_vehicles(None)["Truck"]["rate_per_km"], ic.VEHICLES["Truck"]["rate_per_km"])


class BacktestTests(unittest.TestCase):
    def frame(self):
        rng = np.random.default_rng(0)
        rows = []
        for loc in ["A", "B"]:
            for d in pd.date_range("2026-05-04", "2026-11-09", freq="D"):
                if rng.random() < 0.6:
                    rows.append(("Maize", "Maize", loc, d, 500 + rng.normal(0, 15)))
        return pd.DataFrame(rows, columns=["crop_category", "product", "location", "observed_date", "price"])

    def test_runs_and_summarises(self):
        res = bt.run_backtest(self.frame(), min_weeks=14, test_points=6)
        self.assertEqual(len(res), 2)
        summ = bt.summarise(res)
        self.assertEqual(list(summ["model"]), bt.MODELS)
        self.assertAlmostEqual(summ["share_won_%"].sum(), 100.0, places=0)
        self.assertTrue((summ["mean_MAE"] >= 0).all())

    def test_short_series_are_skipped(self):
        res = bt.run_backtest(self.frame(), min_weeks=200)
        self.assertTrue(res.empty)
        self.assertEqual(len(bt.summarise(res)), 0)


if __name__ == "__main__":
    unittest.main()


class CombineCropsTests(unittest.TestCase):
    @staticmethod
    def _write(tmp, name, rows, columns=("observed_date", "product", "unit", "location", "price", "channel")):
        path = os.path.join(tmp, name)
        pd.DataFrame(rows, columns=list(columns)).to_csv(path, index=False)
        return path

    def test_one_file_per_crop_is_combined_and_duplicates_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self._write(tmp, "rice.csv", [("2026-06-01", "Rice - TZ - No 2", "Kg", "Huye", 1500, "farmgate"),
                                              ("2026-06-01", "Rice - TZ - No 2", "Kg", "Huye", 1500, "farmgate")])
            b = self._write(tmp, "beans.csv", [("2026-06-02", "Beans - Shyushya", "Kg", "Huye", 900, "farmgate")])
            combined, report, problems = combine([a, b])
        self.assertEqual(len(combined), 2)
        cov = crops_covered(ic.clean_prices(combined, start="2026-05-01"))
        self.assertEqual((cov["Rice"], cov["Beans"], cov["Maize"]), (1, 1, 0))
        self.assertTrue(any("duplicate" in p for p in problems))

    def test_crop_comes_from_the_product_not_the_file_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self._write(tmp, "beans.csv", [("2026-06-01", "Rice - TZ - No 2", "Kg", "Huye", 1500, "farmgate")])
            combined, report, _ = combine([f])
        self.assertEqual(report.crops_found.iloc[0], "Rice")

    def test_other_column_names_are_understood(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self._write(tmp, "maize.csv", [("2026-06-01", "Maize", "Kg", "Huye", 450)],
                            columns=("Date", "Commodity", "Unit", "Market", "Price"))
            combined, report, problems = combine([f])
        self.assertEqual(len(combined), 1)
        self.assertEqual(problems, [])

    def test_a_bad_file_is_reported_and_the_others_still_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = self._write(tmp, "rice.csv", [("2026-06-01", "Rice", "Kg", "Huye", 1500, "farmgate")])
            bad = self._write(tmp, "oops.csv", [("x", "y")], columns=("foo", "bar"))
            combined, report, problems = combine([good, bad])
        self.assertEqual(len(combined), 1)
        self.assertTrue(any("oops.csv" in p and "missing" in p for p in problems))


class MlTests(unittest.TestCase):
    @staticmethod
    def _frame(noise=0.0, weeks=40, markets=8):
        rng = np.random.default_rng(1)
        rows, mk = [], []
        for j in range(markets):
            mk.append(dict(location=f"M{j}", lat=-1.9 + 0.05 * j, lon=30.0 + 0.05 * j))
            for k in range(weeks):
                level = 800 * (1 + 0.004 * k)                       # prices drift up
                rows.append(dict(crop_category="Beans", observed_date=pd.Timestamp("2026-05-04") + pd.Timedelta(weeks=k),
                                 location=f"M{j}", price=level * (1 + 0.04 * j) * (1 + rng.normal(0, noise))))
        return pd.DataFrame(rows), pd.DataFrame(mk)

    def test_too_little_history_is_refused_not_guessed(self):
        import isoko_ml as ml
        df, mk = self._frame(weeks=5)
        r = ml.evaluate(df, mk)
        self.assertFalse(r["ok"])
        self.assertFalse(r["gate_pass"])

    def test_gate_opens_only_when_the_model_clearly_wins(self):
        import isoko_ml as ml
        df, mk = self._frame(noise=0.0)
        r = ml.evaluate(df, mk)
        self.assertTrue(r["ok"])
        self.assertEqual(set(r["table"]["kind"]), {"simple rule", "trained"})
        self.assertEqual(r["gate_pass"], r["gain_pct"] >= ml.GATE_GAIN_PCT)

    def test_model_is_tested_on_later_weeks_than_it_trained_on(self):
        import isoko_ml as ml
        df, mk = self._frame(noise=0.02)
        data = ml.build_dataset(df, mk)
        cut = data["wk"].quantile(0.7)
        r = ml.evaluate(df, mk)
        self.assertEqual(r["n_train"], int((data["wk"] <= cut).sum()))
        self.assertEqual(r["n_test"], int((data["wk"] > cut).sum()))


class ModelReportTests(unittest.TestCase):
    def test_saved_report_is_used_only_for_the_same_data(self):
        import tempfile
        import isoko_core as ic
        import isoko_ml
        df = ic.load_prices(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "demo_crop_data.csv"))
        rep = dict(key=isoko_ml.data_key(df), ok=False, reason="x", gate_pass=False, table=[], backtest=[])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "models", "r.json")
            isoko_ml.save_report(rep, path)
            self.assertEqual(isoko_ml.load_report(path, df)["key"], rep["key"])
            self.assertIsNone(isoko_ml.load_report(path, df.iloc[:-5]))       # data changed: report is out of date
            self.assertIsNone(isoko_ml.load_report(os.path.join(tmp, "missing.json"), df))
