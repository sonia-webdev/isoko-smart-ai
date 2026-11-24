"""Isoko SMS webhook (prototype) - no extra packages needed.

    python tools/sms_webhook.py --simulate        type messages, see replies (no network)
    python tools/sms_webhook.py --port 8080       web server for an SMS provider's callback

The server accepts a form POST to /sms with a field called `text` (the farmer's message) and answers with
the reply as plain text. GET /health answers "ok".

Connecting a real SMS number is NOT done here. A provider (for example Africa's Talking, which serves Rwanda)
needs an account, a registered number or short code, and costs money. Read the provider's documentation:
some providers send the plain-text answer back to the farmer, others require your server to call their send API.
Do not run this server on the open internet without HTTPS and some access control.
The phone number is never stored or printed.
"""
import argparse
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_core as ic  # noqa: E402
import isoko_i18n as i18n  # noqa: E402
import isoko_sms  # noqa: E402


def load_context():
    real = os.path.join(ROOT, "data", "isoko_crop_data.csv")
    demo = os.path.join(ROOT, "data", "demo_crop_data.csv")
    using_demo = not os.path.exists(real)
    df = ic.load_prices(demo if using_demo else real)
    markets = ic.load_markets(os.path.join(ROOT, "data", "markets.csv"))
    roads = os.path.join(ROOT, "data", "road_distances.csv")
    road_km = ic.load_road_distances(roads) if os.path.exists(roads) else {}
    return df, markets, road_km, using_demo


def make_handler(df, markets, road_km):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._send(200, "ok") if self.path == "/health" else self._send(404, "not found")

        def do_POST(self):
            if self.path not in ("/", "/sms"):
                return self._send(404, "not found")
            size = min(int(self.headers.get("Content-Length") or 0), 4096)
            fields = parse_qs(self.rfile.read(size).decode("utf-8", "replace"))
            text = (fields.get("text") or [""])[0]
            try:
                result = isoko_sms.handle_sms(text, df, markets, road_km)
                print(f"sms handled: command={result['command']} lang={result['lang']} sms={result['segments']}")
                self._send(200, result["reply"])
            except Exception as exc:                                  # a farmer must always get an answer
                print("sms error:", type(exc).__name__, exc)
                self._send(200, i18n.t("en", "sms_help"))

        def log_message(self, *args):                                  # no access log: it would hold phone details
            pass
    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--simulate", action="store_true")
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()
    df, markets, road_km, using_demo = load_context()
    if using_demo:
        print("NOTE: using DEMONSTRATION data (data/isoko_crop_data.csv not found).")
    if args.simulate:
        print("Type a message (e.g. SELL BEANS 500 NYABUGOGO). Empty line to quit.")
        while True:
            try:
                text = input("> ").strip()
            except EOFError:
                break
            if not text:
                break
            r = isoko_sms.handle_sms(text, df, markets, road_km)
            print(f"{r['reply']}\n[{r['length']} characters, {r['segments']} SMS]")
        return
    print(f"Listening on port {args.port}  (POST /sms with field 'text')")
    HTTPServer(("0.0.0.0", args.port), make_handler(df, markets, road_km)).serve_forever()


if __name__ == "__main__":
    main()
