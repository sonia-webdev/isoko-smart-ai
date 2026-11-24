"""Isoko Smart AI - production server. Standard library only (plus pandas, which the project already needs).

    python server.py                 # http://localhost:8080
    PORT=9000 ISOKO_ADMIN_TOKEN=... python server.py

It serves the web interface (web/) and a small API:

    GET  /health                      status, newest price date, how fresh the data is
    GET  /api/advice                  ?crop=Beans&origin=Nyabugogo&qty=500&lang=rw   (same maths as the app)
    GET  /api/prices.csv              current prices, for analysts   (?crop=Beans optional)
    GET  /api/monthly.csv             month-by-month prices from May 2026
    POST /api/sms                     an SMS provider's callback (field text / Body / message); ?format=text|json|twiml
    POST /api/feedback                {"useful": true, "kind": "advice", "crop": "...", "lang": "rw", "comment": "..."}
    POST /admin/upload                new Esoko prices (CSV in the body). Needs header  X-Admin-Token

Environment variables
    PORT                     default 8080
    ISOKO_ADMIN_TOKEN        needed to use /admin/upload (admin is switched off without it)
    ISOKO_LOG_MESSAGES=1     keep SMS texts (phone numbers removed) in data/messages_log.csv, to build a real test set.
                             OFF by default. Tell farmers before you turn it on (see docs/PRIVACY.md).
    AT_USERNAME, AT_API_KEY  optional: reply through Africa's Talking's send API (otherwise the reply is in the HTTP answer)

Phone numbers are never stored and never logged.
"""
import csv
import hmac
import io
import json
import mimetypes
import os
import re
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import pandas as pd  # noqa: E402
import isoko_core as ic  # noqa: E402
import isoko_i18n as i18n  # noqa: E402
import isoko_sms  # noqa: E402

WEB = os.path.join(ROOT, "web")
DATA = os.path.join(ROOT, "data")
PRICES = os.path.join(DATA, "isoko_crop_data.csv")
DEMO = os.path.join(DATA, "demo_crop_data.csv")
WEB_DATA = os.path.join(DATA, "web_data.json")          # made by tools/refresh.py; overrides web/data.json
FEEDBACK = os.path.join(DATA, "feedback.jsonl")
MESSAGES = os.path.join(DATA, "messages_log.csv")
MAX_BODY, MAX_UPLOAD = 8 * 1024, 4 * 1024 * 1024
STALE_AFTER_DAYS = 7


# ---------------------------------------------------------------- data held in memory
class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.load()

    def load(self):
        using_demo = not os.path.exists(PRICES)
        df = ic.load_prices(DEMO if using_demo else PRICES)
        markets = ic.load_markets(os.path.join(DATA, "markets.csv"))
        roads = os.path.join(DATA, "road_distances.csv")
        road_km = ic.load_road_distances(roads) if os.path.exists(roads) else {}
        with self.lock:
            self.df, self.markets, self.road_km, self.using_demo = df, markets, road_km, using_demo
            self.asof = df["observed_date"].max()

    def snapshot(self):
        with self.lock:
            return self.df, self.markets, self.road_km


STATE = None


def freshness() -> dict:
    now = pd.Timestamp.now().normalize()
    age = int((now - STATE.asof).days)
    return dict(latest=f"{STATE.asof:%Y-%m-%d}", age_days=age, stale=age > STALE_AFTER_DAYS, demo=STATE.using_demo,
                records=int(len(STATE.df)))


# ---------------------------------------------------------------- the advice (same calls as the apps)
def advice(crop, product, origin, qty, rate, lang):
    df, markets, road_km = STATE.snapshot()
    crop_names = {c.lower(): c for c in df["crop_category"].unique()}
    crop = crop_names.get(str(crop).lower())
    if not crop:
        return 400, {"error": "unknown crop", "crops": sorted(crop_names.values())}
    known = {m.lower(): m for m in markets["location"]}
    origin = known.get(str(origin).strip().lower())
    if not origin:
        return 400, {"error": "unknown origin market", "markets": sorted(known.values())}
    if not 10 <= qty <= 100000:
        return 400, {"error": "qty must be between 10 and 100000 kg"}
    if not 0 <= rate <= 5:
        return 400, {"error": "rate must be between 0 and 5 RWF per kg per km"}
    product = product or isoko_sms._top_product(df, crop)
    cp = ic.current_prices(df, crop, product, asof=STATE.asof)
    if cp.empty:
        return 200, {"kind": "none", "message": i18n.t(lang, "no_recent"), "data": freshness()}
    cp = ic.trusted_only(cp, origin)
    ranked = ic.rank_markets(ic.add_distance(cp, markets, origin, road_km=road_km), qty, rate)
    rec = ic.recommend(ranked)
    if rec is None:
        return 200, {"kind": "none", "message": i18n.t(lang, "no_recent"), "data": freshness()}
    adv = i18n.advice(lang, rec, qty)
    rows = [dict(rank=i + 1, market=r.location, price=float(r.price), km=None if pd.isna(r.distance_km) else round(float(r.distance_km), 1),
                 net_return=None if pd.isna(r.net_return) else round(float(r.net_return)), reliability=r.reliability)
            for i, r in enumerate(ranked.itertuples())]
    return 200, dict(kind=adv["kind"], headline=adv["headline"], body=adv["body"], badge=adv["badge"], level=adv["level"],
                     crop=crop, product=product, origin=origin, qty=qty, markets=rows[:10], data=freshness())


# ---------------------------------------------------------------- SMS
PHONE_LIKE = re.compile(r"\+?\d[\d\s\-]{7,}\d")


def redact(text: str) -> str:
    return PHONE_LIKE.sub("[number]", text)[:300]


def log_message(text, result):
    if os.environ.get("ISOKO_LOG_MESSAGES") != "1":
        return
    new = not os.path.exists(MESSAGES)
    with open(MESSAGES, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time_utc", "text", "command", "lang"])
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), redact(text), result["command"], result["lang"]])


def send_via_africastalking(to: str, message: str, opener=None) -> bool:
    """Optional outbound SMS through Africa's Talking. Needs AT_USERNAME and AT_API_KEY. Returns True if accepted."""
    user, key = os.environ.get("AT_USERNAME"), os.environ.get("AT_API_KEY")
    if not (user and key and to):
        return False
    import urllib.request
    from urllib.parse import urlencode
    host = "https://api.sandbox.africastalking.com" if user == "sandbox" else "https://api.africastalking.com"
    req = urllib.request.Request(host + "/version1/messaging", data=urlencode({"username": user, "to": to, "message": message}).encode(),
                                 headers={"apiKey": key, "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=10) as r:
            return 200 <= r.status < 300
    except Exception as exc:
        print("outbound sms failed:", type(exc).__name__)
        return False


def sms_reply(fields: dict):
    text = next((fields[k][0] for k in ("text", "Body", "message") if fields.get(k)), "")
    df, markets, road_km = STATE.snapshot()
    try:
        result = isoko_sms.handle_sms(text, df, markets, road_km)
    except Exception as exc:                                         # a farmer must always get an answer
        print("sms error:", type(exc).__name__)
        result = dict(reply=i18n.t("en", "sms_help"), lang="en", command="error", segments=1, length=0)
    log_message(text, result)
    return result


def twiml(reply: str) -> str:
    esc = reply.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{esc}</Message></Response>'


# ---------------------------------------------------------------- feedback and admin
def save_feedback(payload: dict) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("useful"), bool):
        return False
    row = dict(time_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), useful=payload["useful"],
               kind=str(payload.get("kind", "advice"))[:20], crop=str(payload.get("crop", ""))[:30],
               market=str(payload.get("market", ""))[:40], lang=str(payload.get("lang", ""))[:5],
               comment=redact(str(payload.get("comment", ""))))
    with open(FEEDBACK, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return True


def admin_upload(body: bytes):
    """New prices in -> merged into data/isoko_crop_data.csv -> web data rebuilt -> memory reloaded."""
    import refresh
    with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as tmp:
        tmp.write(body)
        path = tmp.name
    try:
        report = refresh.refresh(path, train=False)
    finally:
        os.unlink(path)
    STATE.load()
    return report


# ---------------------------------------------------------------- a small guard against floods
class RateLimit:
    def __init__(self, per_minute=60):
        self.per, self.hits, self.lock = per_minute, {}, threading.Lock()

    def ok(self, who: str) -> bool:
        now = time.time()
        with self.lock:
            q = [t for t in self.hits.get(who, []) if now - t < 60]
            if len(q) >= self.per:
                self.hits[who] = q
                return False
            q.append(now)
            self.hits[who] = q
            if len(self.hits) > 5000:
                self.hits = {k: v for k, v in self.hits.items() if v and now - v[-1] < 60}
            return True


LIMIT = RateLimit(60)


# ---------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "IsokoSmartAI"

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else (json.dumps(body, ensure_ascii=False) if not isinstance(body, str) else body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _body(self, limit):
        size = int(self.headers.get("Content-Length") or 0)
        if size > limit:
            return None
        return self.rfile.read(size)

    def _who(self):
        return self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/health":
                return self._send(200, dict(status="ok", **freshness()))
            if u.path == "/api/advice":
                if not LIMIT.ok(self._who()):
                    return self._send(429, {"error": "too many requests"})
                try:
                    qty, rate = float(q.get("qty", 500)), float(q.get("rate", ic.DEFAULT_RATE))
                except ValueError:
                    return self._send(400, {"error": "qty and rate must be numbers"})
                lang = q.get("lang", "en") if q.get("lang") in ("en", "rw") else "en"
                code, out = advice(q.get("crop", ""), q.get("product"), q.get("origin", ""), qty, rate, lang)
                return self._send(code, out)
            if u.path == "/api/prices.csv":
                df, _, _ = STATE.snapshot()
                rows = []
                for crop, g in df.groupby("crop_category"):
                    if q.get("crop") and q["crop"].lower() != crop.lower():
                        continue
                    for product in g["product"].unique():
                        cp = ic.current_prices(df, crop, product, asof=STATE.asof)
                        if len(cp):
                            cp.insert(0, "product", product)
                            cp.insert(0, "crop", crop)
                            rows.append(cp)
                out = pd.concat(rows) if rows else pd.DataFrame()
                return self._send(200, out.to_csv(index=False), "text/csv; charset=utf-8")
            if u.path == "/api/monthly.csv":
                df, _, _ = STATE.snapshot()
                return self._send(200, ic.pattern_2026(df).to_csv(index=False), "text/csv; charset=utf-8")
            return self._static(u.path)
        except Exception as exc:
            print("error:", type(exc).__name__, exc)
            return self._send(500, {"error": "server error"})

    do_HEAD = do_GET

    def _static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        if path == "/data.json" and os.path.exists(WEB_DATA):
            full = WEB_DATA
        else:
            full = os.path.realpath(os.path.join(WEB, path.lstrip("/")))
            if not full.startswith(os.path.realpath(WEB) + os.sep) or not os.path.isfile(full):
                return self._send(404, {"error": "not found"})
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if full.endswith(".webmanifest"):
            ctype = "application/manifest+json"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json", "application/manifest+json"):
            ctype += "; charset=utf-8"
        cache = "no-cache" if full.endswith(("data.json", "web_data.json", "sw.js", "index.html")) else "public, max-age=86400"
        with open(full, "rb") as f:
            self._send(200, f.read(), ctype, {"Cache-Control": cache})

    def do_POST(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/api/sms":
                if not LIMIT.ok(self._who()):
                    return self._send(429, "too many requests", "text/plain; charset=utf-8")
                raw = self._body(MAX_BODY)
                if raw is None:
                    return self._send(413, "too large", "text/plain; charset=utf-8")
                ctype = self.headers.get("Content-Type", "")
                if "json" in ctype:
                    try:
                        j = json.loads(raw.decode("utf-8", "replace"))
                        fields = {k: [str(v)] for k, v in j.items()} if isinstance(j, dict) else {}
                    except ValueError:
                        fields = {}
                else:
                    fields = parse_qs(raw.decode("utf-8", "replace"))
                result = sms_reply(fields)
                fmt = q.get("format", "text")
                sender = (fields.get("from") or fields.get("From") or [""])[0]
                if os.environ.get("AT_API_KEY") and fmt == "text" and sender:
                    send_via_africastalking(sender, result["reply"])        # the phone number is used once, never kept
                if fmt == "json":
                    return self._send(200, dict(reply=result["reply"], lang=result["lang"], command=result["command"],
                                                segments=result["segments"], length=result["length"]))
                if fmt == "twiml":
                    return self._send(200, twiml(result["reply"]), "text/xml; charset=utf-8")
                return self._send(200, result["reply"], "text/plain; charset=utf-8")
            if u.path == "/api/feedback":
                if not LIMIT.ok(self._who()):
                    return self._send(429, {"error": "too many requests"})
                raw = self._body(MAX_BODY)
                try:
                    ok = raw is not None and save_feedback(json.loads(raw.decode("utf-8", "replace")))
                except ValueError:
                    ok = False
                return self._send(200 if ok else 400, {"saved": bool(ok)})
            if u.path == "/admin/upload":
                token = os.environ.get("ISOKO_ADMIN_TOKEN", "")
                if not token or not hmac.compare_digest(self.headers.get("X-Admin-Token", ""), token):
                    return self._send(403, {"error": "forbidden"})
                raw = self._body(MAX_UPLOAD)
                if raw is None:
                    return self._send(413, {"error": "file too large"})
                try:
                    return self._send(200, admin_upload(raw))
                except ValueError as exc:
                    return self._send(400, {"error": str(exc)})
            return self._send(404, {"error": "not found"})
        except Exception as exc:
            print("error:", type(exc).__name__, exc)
            return self._send(500, {"error": "server error"})

    def log_message(self, *args):                                        # no access log: it would hold phone details
        pass


def make_server(port):
    global STATE
    STATE = State()
    return ThreadingHTTPServer(("0.0.0.0", port), Handler)


def main():
    port = int(os.environ.get("PORT", "8080"))
    srv = make_server(port)
    f = freshness()
    print(f"Isoko Smart AI on http://0.0.0.0:{port}   data to {f['latest']} ({f['age_days']} days old)"
          + ("   DEMONSTRATION DATA" if f["demo"] else ""))
    if f["stale"]:
        print("WARNING: prices are more than 7 days old. Load fresh Esoko prices (see docs/OPERATIONS.md).")
    if not os.environ.get("ISOKO_ADMIN_TOKEN"):
        print("Admin upload is OFF (set ISOKO_ADMIN_TOKEN to turn it on).")
    srv.serve_forever()


if __name__ == "__main__":
    main()
