"""Build data/road_distances.csv: real road distances between all markets in data/markets.csv.

    python tools/build_road_distances.py

Needs internet and uses the public OSRM demo server (OpenStreetMap roads). Run it ONCE on your own
computer, not inside the app, and commit the resulting CSV. Please do not call the demo server repeatedly.
"""
import json
import os
import sys
import urllib.request

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://router.project-osrm.org/table/v1/driving/{coords}?annotations=distance"


def parse_table(response: dict, names: list) -> pd.DataFrame:
    """OSRM 'table' response (distances in metres) -> origin, destination, km rows."""
    if response.get("code") != "Ok":
        raise RuntimeError(f"OSRM answered: {response.get('code')} {response.get('message', '')}")
    rows = []
    for i, origin in enumerate(names):
        for j, dest in enumerate(names):
            metres = response["distances"][i][j]
            if i != j and metres is not None:
                rows.append({"origin": origin, "destination": dest, "km": round(metres / 1000.0, 1)})
    return pd.DataFrame(rows)


def main():
    markets = pd.read_csv(os.path.join(ROOT, "data", "markets.csv"))
    coords = ";".join(f"{lon},{lat}" for lat, lon in zip(markets["lat"], markets["lon"]))   # OSRM wants lon,lat
    req = urllib.request.Request(URL.format(coords=coords), headers={"User-Agent": "isoko-smart-ai-student-project"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    out = parse_table(data, list(markets["location"]))
    path = os.path.join(ROOT, "data", "road_distances.csv")
    out.to_csv(path, index=False)
    print(f"Wrote {len(out)} distances for {len(markets)} markets to {path}")


if __name__ == "__main__":
    sys.exit(main())
