"""
Build a Record ID-keyed date update from a HubSpot deals export.

HubSpot can only update deals by Record ID (deal names are not unique), so the
refreshed dates have to be joined back to the portal's own IDs. This reads the
export, shifts both date columns by the elapsed days, and writes a minimal
3-column update file.

Usage:  python build_date_update.py <hubspot_export.csv> [anchor_date]
"""
import csv, sys, os
from datetime import date, datetime, timedelta

src = sys.argv[1]
anchor = datetime.strptime(sys.argv[2], "%Y-%m-%d").date() if len(sys.argv) > 2 else date(2026, 9, 21)
shift = (date.today() - anchor).days
BASE = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(BASE, "data", "deal_date_update_by_id.csv")

def bump(v):
    if not v.strip():
        return ""
    d = datetime.strptime(v.strip()[:10], "%Y-%m-%d").date() + timedelta(days=shift)
    return d.isoformat()

rows, stale, names = [], 0, {}
for r in csv.DictReader(open(src)):
    new_lcu = bump(r["Last Contract Update"])
    rows.append({"Record ID": r["Record ID"], "Close Date": bump(r["Close Date"]),
                 "Last Contract Update": new_lcu})
    names[r["Deal Name"]] = names.get(r["Deal Name"], 0) + 1
    if r["Deal Stage"].lower() == "contract out" and new_lcu:
        if (date.today() - datetime.strptime(new_lcu, "%Y-%m-%d").date()).days > 3:
            stale += 1

with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["Record ID", "Close Date", "Last Contract Update"])
    w.writeheader(); w.writerows(rows)

dupes = {k: v for k, v in names.items() if v > 1}
print(f"shift +{shift} days -> anchor {date.today()}")
print(f"{len(rows)} deals written to {out}")
print(f"Contract Out stale past 3 days after update: {stale}")
print(f"duplicate deal names in portal: {len(dupes)} {list(dupes)[:3]}")
