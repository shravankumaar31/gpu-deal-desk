"""
Re-anchor the demo dataset's dates to today.

Why this exists: the synthetic data was generated with dates relative to a fixed
"today". Every day that passes, another Contract Out deal drifts past the 3-day
threshold until all of them look stale and the demo stops being legible. This
shifts every date forward by the days elapsed since the last anchor, so
"5 stale contracts" stays true whenever the project is demoed.

It is idempotent. The current anchor is recorded in data/anchor.json and the
shift is measured from there, so running it twice in one day does nothing the
second time. (The first version measured from a hardcoded date and re-shifted
the data on every run — silently doubling every gap.)

Writes:
  data/deals.csv              updated in place
  data/anchor.json            the new anchor date
  data/deal_date_refresh.csv  a HubSpot update file, keyed on Deal Name

Note: HubSpot can only update deals by Record ID, so to push these dates to the
portal use build_date_update.py against a fresh deals export.

Run:  python3 refresh_dates.py
"""

import csv
import json
import os
from datetime import date, datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
DEALS = os.path.join(BASE, "data", "deals.csv")
ANCHOR_FILE = os.path.join(BASE, "data", "anchor.json")
GENESIS = date(2026, 9, 21)          # the date the dataset was originally generated for
DATE_COLS = ["Close Date", "Last Contract Update"]


def read_anchor():
    if os.path.exists(ANCHOR_FILE):
        with open(ANCHOR_FILE) as f:
            return datetime.strptime(json.load(f)["anchor"], "%Y-%m-%d").date()
    return GENESIS


def write_anchor(d):
    with open(ANCHOR_FILE, "w") as f:
        json.dump({"anchor": d.isoformat(),
                   "note": "Dates in deals.csv are anchored to this date. "
                           "refresh_dates.py shifts from here, so it is safe to re-run."},
                  f, indent=2)


def shift_dates(shift):
    rows = list(csv.DictReader(open(DEALS)))
    for r in rows:
        for col in DATE_COLS:
            if r[col]:
                d = datetime.strptime(r[col][:10], "%Y-%m-%d").date() + timedelta(days=shift)
                r[col] = d.isoformat()
    with open(DEALS, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return rows


def main():
    anchor = read_anchor()
    today = date.today()
    shift = (today - anchor).days

    if shift == 0:
        print(f"Already anchored to {today}. Nothing to do.")
        rows = list(csv.DictReader(open(DEALS)))
    else:
        rows = shift_dates(shift)
        write_anchor(today)
        print(f"Shifted all dates {shift:+d} days. Anchor is now {today}.")

    out = os.path.join(BASE, "data", "deal_date_refresh.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Deal Name"] + DATE_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in ["Deal Name"] + DATE_COLS})

    stale = sum(1 for r in rows if r["Deal Stage"] == "Contract Out" and r["Last Contract Update"]
                and (today - datetime.strptime(r["Last Contract Update"][:10], "%Y-%m-%d").date()).days > 3)
    print(f"Contract Out deals stale past 3 days: {stale}")
    print(f"wrote {os.path.relpath(out, BASE)}")


if __name__ == "__main__":
    main()
