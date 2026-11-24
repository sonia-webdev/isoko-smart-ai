"""Runs the real app.py page by page with a stand-in for Streamlit and Plotly.

It does not draw anything; it checks that every page, in both languages and both transport modes, runs without an
error and writes the sentences we expect. (Streamlit does not have to be installed for this test.)
"""
import os
import runpy
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
# Import everything the app needs BEFORE the stand-in modules are patched in; otherwise patching sys.modules would
# throw away pandas and numpy again afterwards.
import numpy  # noqa: E402,F401
import pandas  # noqa: E402,F401
import sklearn.ensemble  # noqa: E402,F401  (import before sys.modules is patched, like numpy and pandas)
import isoko_core  # noqa: E402,F401
import isoko_i18n  # noqa: E402,F401
import isoko_sms  # noqa: E402,F401


class _Stop(Exception):
    pass


class FakeStreamlit:
    """Returns the first option / default value of every widget and records what the page writes."""

    def __init__(self, radio_plan):
        self.radio_plan = list(radio_plan)
        self.calls = []
        self.sidebar = self
        self.session_state = {}
        self.column_config = types.SimpleNamespace(NumberColumn=lambda *a, **k: "num", TextColumn=lambda *a, **k: "text")

    def text(self, kind=None):
        return "\n".join(str(c[1]) for c in self.calls if kind is None or c[0] == kind)

    def cache_data(self, func=None, **kw):
        return func if func else (lambda g: g)

    def radio(self, label, options, index=0, **kw):
        options = list(options)
        return options[self.radio_plan.pop(0) if self.radio_plan else index]

    def selectbox(self, label, options, index=0, **kw):
        options = list(options)
        return options[min(index, len(options) - 1)]

    def number_input(self, label, min_value=None, max_value=None, value=None, step=None, **kw):
        return value

    def slider(self, label, min_value=None, max_value=None, value=None, step=None, **kw):
        return value

    def checkbox(self, label, value=False, **kw):
        return value

    typed = None          # set to a string to simulate the user typing in the text box

    def text_input(self, label, value="", **kw):
        return self.typed if self.typed is not None else value

    def columns(self, spec, **kw):
        return [self] * (spec if isinstance(spec, int) else len(spec))

    def expander(self, *a, **kw):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def stop(self):
        raise _Stop()

    def set_page_config(self, *a, **kw):
        pass

    def __getattr__(self, name):                 # markdown, caption, warning, info, success, dataframe, code, metric ...
        def record(*a, **kw):
            self.calls.append((name, a[0] if a else None))
        return record


class FakeFigure:
    def __init__(self, *a, **kw):
        pass

    def update_layout(self, *a, **kw):
        pass

    def add_trace(self, *a, **kw):
        pass


def make_project_copy(tmp, real_data=False):
    """A copy of the app and data in `tmp`. Without real_data the Esoko file is left out, so the app shows demo data;
    with real_data the demo file stands in for it (the app cannot tell the difference)."""
    shutil.copy(os.path.join(ROOT, "app.py"), tmp)
    shutil.copytree(os.path.join(ROOT, "data"), os.path.join(tmp, "data"),
                    ignore=shutil.ignore_patterns("isoko_crop_data.csv", "quality_report.csv"))
    if real_data:
        shutil.copy(os.path.join(tmp, "data", "demo_crop_data.csv"), os.path.join(tmp, "data", "isoko_crop_data.csv"))
    return tmp


def run_app(radio_plan, app_dir=None, typed=None):
    if app_dir is None:                                  # default: demo data, whatever is in the real data folder
        with tempfile.TemporaryDirectory() as tmp:
            return run_app(radio_plan, app_dir=make_project_copy(tmp), typed=typed)
    fake = FakeStreamlit(radio_plan)
    fake.typed = typed
    go = types.ModuleType("plotly.graph_objects")
    go.Figure, go.Bar, go.Scatter, go.Heatmap = FakeFigure, dict, dict, dict
    plotly = types.ModuleType("plotly")
    plotly.graph_objects = go
    modules = {"streamlit": fake, "plotly": plotly, "plotly.graph_objects": go}
    with mock.patch.dict(sys.modules, modules):
        try:
            runpy.run_path(os.path.join(app_dir, "app.py"), run_name="__main__")
        except _Stop:
            pass
    return fake


# radio order in the app: language, dashboard (view), page inside it, (transport method on the "sell" page)
EN, RW = 0, 1
HOME_V, FARMER, GOV = 0, 1, 2
HOME = [HOME_V]
SELL, TRENDS, SMS = [FARMER, 0], [FARMER, 1], [FARMER, 2]
OVERVIEW, SEASON, MARKETS, DATA = [GOV, 0], [GOV, 1], [GOV, 2], [GOV, 3]


class AppSmokeTests(unittest.TestCase):
    def test_sell_page_english(self):
        s = run_app([EN, *SELL])
        text = s.text()
        self.assertTrue("Sell at" in text or "Selling at" in text)
        self.assertIn("Data reliability:", text)
        self.assertIn("transport costs", text)

    def test_sell_page_kinyarwanda(self):
        s = run_app([RW, *SELL])
        text = s.text()
        self.assertTrue("Gurishiriza i" in text or "Kugurishiriza i" in text)
        self.assertIn("Kwizerwa kw'amakuru", text)
        self.assertNotIn("Data reliability", text)

    def test_sell_page_kinyarwanda_has_no_english_recommendation_text(self):
        text = run_app([RW, *SELL]).text()
        for english in ("RECOMMENDED", "Pays less per kg", "Pays more per kg", "Closer (", "Why this market",
                        "Transport costs (you", "Income after transport"):
            self.assertNotIn(english, text)
        self.assertIn("Impamvu iri soko", text)

    def test_sell_page_by_vehicle(self):
        s = run_app([EN, *SELL, 1])
        self.assertTrue("Sell at" in s.text() or "Selling at" in s.text())

    def test_trends_page(self):
        self.assertIn("Recent movement", run_app([EN, *TRENDS]).text())

    def test_data_page_shows_demo_warning_and_no_benchmark_on_demo_data(self):
        text = run_app([EN, *DATA]).text()
        self.assertIn("DEMONSTRATION DATA", text)
        self.assertNotIn("Retail benchmark", text)

    def test_sms_page_both_languages(self):
        empty = run_app([EN, *SMS])                       # nothing typed yet: no reply, a waiting note
        self.assertIn("Waiting for your message", empty.text())
        self.assertFalse(empty.text("code"))
        for plan, msg in (([EN, *SMS], "SELL BEANS 500 NYABUGOGO"), ([RW, *SMS], "GURISHA IBISHYIMBO IBIRO 500 NYABUGOGO")):
            s = run_app(plan, typed=msg)
            self.assertIn("characters", s.text("caption"))
            self.assertTrue(s.text("code"))

    def test_monthly_2026_page_both_languages(self):
        for plan in ([EN, *SEASON], [RW, *SEASON]):
            text = run_app(plan).text()
            self.assertIn("was cheapest in", text)
            self.assertIn("All crops at a glance", text)

    def test_home_page_both_languages(self):
        en = run_app([EN, *HOME]).text()
        self.assertIn("Know the market. Choose wisely. Earn more.", en)
        self.assertIn("Honest about AI", en)
        rw = run_app([RW, *HOME]).text()
        self.assertIn("Menya isoko", rw)
        self.assertNotIn("Honest about AI", rw)

    def test_home_page_shows_a_live_example_on_real_looking_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = run_app([EN, *HOME], app_dir=make_project_copy(tmp, real_data=True)).text()
        self.assertIn("A live example from today's data", text)

    def test_government_overview_and_market_pages_both_languages(self):
        en = run_app([EN, *OVERVIEW]).text()
        self.assertIn("National overview", en)
        self.assertIn("Data coverage", en)
        self.assertIn("Kugereranya amasoko", run_app([RW, *MARKETS]).text())
        self.assertIn("Market comparison", run_app([EN, *MARKETS]).text())
        self.assertIn("Incamake y'igihugu", run_app([RW, *OVERVIEW]).text())

    def test_data_page_with_real_looking_data_shows_the_benchmark(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = run_app([EN, *DATA], app_dir=make_project_copy(tmp, real_data=True)).text()
        self.assertIn("Retail benchmark", text)
        self.assertNotIn("DEMONSTRATION DATA:", text)

    @unittest.skipUnless(os.path.exists(os.path.join(ROOT, "data", "isoko_crop_data.csv")),
                         "no real data file in data/")
    def test_every_page_runs_on_the_real_project_file(self):
        for plan in ([EN, *SELL], [RW, *SELL], [EN, *SELL, 1], [RW, *TRENDS], [EN, *DATA], [RW, *SMS]):
            text = run_app(plan, app_dir=ROOT).text()
            self.assertNotIn("DEMONSTRATION DATA:", text, plan)
            self.assertTrue(len(text) > 500, plan)


if __name__ == "__main__":
    unittest.main()
