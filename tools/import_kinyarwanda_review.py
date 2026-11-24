"""Turn a reviewed kinyarwanda_review.csv into data/kinyarwanda_corrections.csv.

    python tools/import_kinyarwanda_review.py reviewed.csv

A row is taken when the reviewer filled `kinyarwanda_corrected`, or when they edited the `kinyarwanda` column itself.
Rows whose placeholders like {market} were lost are refused and listed. Nothing else in the project needs editing.
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import isoko_i18n as i18n  # noqa: E402


def read_changes(path: str):
    """(changes {key: text}, refused [messages])."""
    changes, refused = {}, []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = (row.get("key") or "").strip()
            new = (row.get("kinyarwanda_corrected") or "").strip() or (row.get("kinyarwanda") or "")
            if not key or not new.strip():
                continue
            cur = i18n.CROPS.get(key[5:]) if key.startswith("crop:") else i18n.STR["rw"].get(key)
            if cur is None:
                refused.append(f"{key}: unknown key")
            elif new == cur:
                continue
            elif not key.startswith("crop:") and i18n._fields(new) != i18n._fields(i18n.STR["en"][key]):
                refused.append(f"{key}: keep the placeholders {sorted(i18n._fields(i18n.STR['en'][key]))}")
            else:
                changes[key] = new
    return changes, refused


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    changes, refused = read_changes(sys.argv[1])
    out = os.path.join(ROOT, "data", "kinyarwanda_corrections.csv")
    existing = {}
    if os.path.exists(out):
        with open(out, encoding="utf-8", newline="") as f:
            existing = {r["key"]: r["kinyarwanda"] for r in csv.DictReader(f)}
    existing.update(changes)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "kinyarwanda"])
        w.writerows(existing.items())
    print(f"{len(changes)} change(s) written to {out}")
    for k, v in changes.items():
        print(f"  {k}: {v[:90]}")
    for r in refused:
        print("REFUSED:", r)


if __name__ == "__main__":
    main()
