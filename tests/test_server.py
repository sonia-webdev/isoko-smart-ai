"""Tests for server.py: the API, the SMS webhook, feedback, admin upload and safety limits."""
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def call(base, path, data=None, headers=None, method=None):
    req = urllib.request.Request(base + path, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8"), dict(e.headers)


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # work on a copy so tests never touch real files
        cls.tmp = tempfile.mkdtemp()
        cls.proj = os.path.join(cls.tmp, "isoko")
        shutil.copytree(ROOT, cls.proj, ignore=shutil.ignore_patterns("__pycache__", "*.bak", "web_data.json", "feedback.jsonl", "messages_log.csv"))
        import sys
        sys.path.insert(0, cls.proj)
        sys.path.insert(0, os.path.join(cls.proj, "tools"))
        for m in [m for m in sys.modules if m in ("server", "refresh", "export_web_data", "add_prices")]:
            del sys.modules[m]
        import importlib
        cls.server = importlib.import_module("server")
        # point the module at the copy
        s = cls.server
        s.ROOT, s.WEB, s.DATA = cls.proj, os.path.join(cls.proj, "web"), os.path.join(cls.proj, "data")
        s.PRICES, s.DEMO = os.path.join(s.DATA, "isoko_crop_data.csv"), os.path.join(s.DATA, "demo_crop_data.csv")
        s.WEB_DATA, s.FEEDBACK, s.MESSAGES = (os.path.join(s.DATA, "web_data.json"), os.path.join(s.DATA, "feedback.jsonl"),
                                              os.path.join(s.DATA, "messages_log.csv"))
        cls.had_real = os.path.exists(s.PRICES)
        cls.httpd = s.make_server(0)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_health_and_static(self):
        code, body, _ = call(self.base, "/health")
        self.assertEqual(code, 200)
        self.assertIn("latest", json.loads(body))
        code, body, h = call(self.base, "/")
        self.assertEqual(code, 200)
        self.assertIn("Isoko Smart AI", body)
        self.assertEqual(h.get("X-Content-Type-Options"), "nosniff")

    def test_no_path_traversal(self):
        for p in ("/../server.py", "/..%2fserver.py", "/%2e%2e/server.py", "/img/../../server.py"):
            code, body, _ = call(self.base, p)
            self.assertNotIn("def make_server", body, p)

    def test_advice_matches_the_core_maths_in_both_languages(self):
        code, body, _ = call(self.base, "/api/advice?crop=Beans&origin=Nyabugogo&qty=500&lang=en")
        self.assertEqual(code, 200)
        en = json.loads(body)
        self.assertIn(en["kind"], ("sell", "stay"))
        self.assertTrue(en["headline"])
        _, body, _ = call(self.base, "/api/advice?crop=Beans&origin=Nyabugogo&qty=500&lang=rw")
        rw = json.loads(body)
        self.assertEqual(en["kind"], rw["kind"])
        self.assertNotEqual(en["headline"], rw["headline"])

    def test_advice_rejects_bad_input(self):
        for q in ("crop=Gold&origin=Nyabugogo", "crop=Beans&origin=Nowhere", "crop=Beans&origin=Nyabugogo&qty=3",
                  "crop=Beans&origin=Nyabugogo&rate=99", "crop=Beans&origin=Nyabugogo&qty=abc"):
            code, _, _ = call(self.base, "/api/advice?" + q)
            self.assertEqual(code, 400, q)

    def test_csv_exports(self):
        code, body, h = call(self.base, "/api/prices.csv?crop=Beans")
        self.assertEqual(code, 200)
        self.assertIn("text/csv", h["Content-Type"])
        self.assertIn("location", body.splitlines()[0])
        code, body, _ = call(self.base, "/api/monthly.csv")
        self.assertEqual(code, 200)

    def test_sms_webhook_formats(self):
        form = {"Content-Type": "application/x-www-form-urlencoded"}
        data = b"text=GURISHA+IBISHYIMBO+IBIRO+500+NYABUGOGO&from=%2B250788000000"
        code, body, _ = call(self.base, "/api/sms", data, form)
        self.assertEqual(code, 200)
        self.assertLessEqual(len(body), 320)
        code, body, _ = call(self.base, "/api/sms?format=json", data, form)
        self.assertEqual(json.loads(body)["lang"], "rw")
        code, body, h = call(self.base, "/api/sms?format=twiml", b"Body=SELL+BEANS+500+NYABUGOGO", form)
        self.assertIn("<Response><Message>", body)
        code, body, _ = call(self.base, "/api/sms", b"", form)           # empty text still gets an answer
        self.assertEqual(code, 200)
        self.assertTrue(body)

    def test_phone_numbers_are_never_kept(self):
        s = self.server
        self.assertNotIn("0788", s.redact("call me on +250 788 123 456 please"))
        os.environ["ISOKO_LOG_MESSAGES"] = "1"
        try:
            call(self.base, "/api/sms", b"text=PRICE+BEANS+0788123456&from=%2B250788123456", {"Content-Type": "application/x-www-form-urlencoded"})
            log = open(s.MESSAGES, encoding="utf-8").read()
            self.assertNotIn("0788123456", log)
            self.assertNotIn("250788", log)
        finally:
            del os.environ["ISOKO_LOG_MESSAGES"]

    def test_messages_not_logged_by_default(self):
        s = self.server
        if os.path.exists(s.MESSAGES):
            os.unlink(s.MESSAGES)
        call(self.base, "/api/sms", b"text=PRICE+BEANS", {"Content-Type": "application/x-www-form-urlencoded"})
        self.assertFalse(os.path.exists(s.MESSAGES))

    def test_feedback(self):
        j = {"Content-Type": "application/json"}
        code, body, _ = call(self.base, "/api/feedback", json.dumps({"useful": True, "crop": "Beans", "lang": "rw", "comment": "ok 0788123456"}).encode(), j)
        self.assertEqual(code, 200)
        saved = open(self.server.FEEDBACK, encoding="utf-8").read()
        self.assertIn("Beans", saved)
        self.assertNotIn("0788123456", saved)
        code, _, _ = call(self.base, "/api/feedback", b'{"useful":"yes"}', j)
        self.assertEqual(code, 400)
        code, _, _ = call(self.base, "/api/feedback", b"not json", j)
        self.assertEqual(code, 400)

    def test_admin_is_off_or_protected(self):
        os.environ.pop("ISOKO_ADMIN_TOKEN", None)
        code, _, _ = call(self.base, "/admin/upload", b"x", {"X-Admin-Token": "anything"})
        self.assertEqual(code, 403)
        os.environ["ISOKO_ADMIN_TOKEN"] = "secret-token"
        try:
            code, _, _ = call(self.base, "/admin/upload", b"x", {"X-Admin-Token": "wrong"})
            self.assertEqual(code, 403)
            code, body, _ = call(self.base, "/admin/upload", b"a,b\n1,2\n", {"X-Admin-Token": "secret-token"})
            self.assertEqual(code, 400)                                  # right token, but not a price file
        finally:
            del os.environ["ISOKO_ADMIN_TOKEN"]

    def test_admin_upload_adds_prices(self):
        if not self.had_real:
            self.skipTest("needs the real price file")
        import pandas as pd
        s = self.server
        before = len(pd.read_csv(s.PRICES))
        day = (pd.read_csv(s.PRICES)["observed_date"].max())
        newday = (pd.Timestamp(day) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        csv = f"observed_date,product,location,price,unit\n{newday},Bean,Nyabugogo,1500,kg\n{newday},Bean,Nyabugogo,1500,kg\n{newday},Bean,Nyabugogo,abc,kg\n"
        os.environ["ISOKO_ADMIN_TOKEN"] = "t"
        try:
            code, body, _ = call(self.base, "/admin/upload", csv.encode(), {"X-Admin-Token": "t"})
        finally:
            del os.environ["ISOKO_ADMIN_TOKEN"]
        self.assertEqual(code, 200, body)
        rep = json.loads(body)
        self.assertEqual(rep["added"]["added"], 1)                       # duplicate and bad row not added
        self.assertEqual(len(pd.read_csv(s.PRICES)), before + 1)
        self.assertTrue(os.path.exists(s.WEB_DATA))
        _, body, _ = call(self.base, "/data.json")
        self.assertEqual(json.loads(body)["meta"]["asof"], newday)
        self.assertEqual(json.loads(call(self.base, "/health")[1])["latest"], newday)

    def test_first_upload_becomes_the_main_file(self):
        import refresh
        d = tempfile.mkdtemp()
        new = os.path.join(d, "new.csv")
        open(new, "w").write("observed_date,product,location,price,unit\n2026-11-01,Bean,Nyabugogo,1500,kg\n2026-11-02,Bean,Nyabugogo,1550,kg\n")
        target, out = os.path.join(d, "main.csv"), os.path.join(d, "web.json")
        rep = refresh.refresh(new, target=target, out_web=out)
        self.assertEqual(rep["added"]["added"], 2)
        self.assertTrue(os.path.exists(target) and os.path.exists(out))
        with self.assertRaises(ValueError):
            open(new, "w").write("a,b\n1,2\n")
            refresh.refresh(new, target=os.path.join(d, "other.csv"), out_web=out)

    def test_outbound_sms_needs_keys_and_uses_them(self):
        s = self.server
        os.environ.pop("AT_API_KEY", None)
        self.assertFalse(s.send_via_africastalking("+250788000000", "hi"))
        os.environ["AT_USERNAME"], os.environ["AT_API_KEY"] = "sandbox", "k"
        seen = {}

        class Resp:
            status = 201
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake(req, timeout=0):
            seen["url"], seen["key"] = req.full_url, req.headers.get("Apikey")
            return Resp()
        try:
            self.assertTrue(s.send_via_africastalking("+250788000000", "hi", opener=fake))
        finally:
            del os.environ["AT_USERNAME"], os.environ["AT_API_KEY"]
        self.assertIn("sandbox", seen["url"])
        self.assertEqual(seen["key"], "k")

    def test_rate_limit(self):
        rl = self.server.RateLimit(3)
        self.assertEqual([rl.ok("a") for _ in range(5)], [True, True, True, False, False])
        self.assertTrue(rl.ok("b"))


if __name__ == "__main__":
    unittest.main()
