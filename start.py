"""Start Isoko Smart AI (the new React interface) on your own computer.

    python start.py

Windows: double-click start_isoko.bat.   Mac/Linux: ./start_isoko.sh
It looks for your price file (isoko_crop_data.csv) in this folder or in data/, rebuilds the data the page reads,
starts the server and opens http://localhost:8080 in your browser. Press Ctrl+C to stop.
"""
import os
import shutil
import sys
import threading
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

try:
    import pandas  # noqa: F401
except ImportError:
    sys.exit("pandas is missing. Install it with:   pip install pandas numpy")

DATA = os.path.join(ROOT, "data", "isoko_crop_data.csv")
for candidate in ("isoko_crop_data.csv", os.path.join("data", "isoko_crop_data.csv")):
    here = os.path.join(ROOT, candidate)
    if os.path.exists(here) and os.path.abspath(here) != os.path.abspath(DATA):
        shutil.copy(here, DATA)
        print("Using your price file:", candidate)
        break

if os.path.exists(DATA):
    import refresh
    r = refresh.refresh()                                   # rebuilds data/web_data.json from your real prices
    h = r["health"]
    print(f"Prices to {h['latest']} ({h['records']:,} records). Reliability: {h['reliability']}")
else:
    print("NOTE: no isoko_crop_data.csv found. Put your price file in this folder and run again.")
    print("      Until then the page shows the prices that came with the project.")

import server  # noqa: E402

port = int(os.environ.get("PORT", "8080"))
httpd = server.make_server(port)
url = f"http://localhost:{port}"
print(f"\nIsoko Smart AI is running. Open {url}   (Ctrl+C to stop)\n")
if not os.environ.get("ISOKO_NO_BROWSER"):
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("Stopped.")
