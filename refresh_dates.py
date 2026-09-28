"""
Re-anchor the demo dataset's dates to today.

Why this exists: the synthetic data was generated with dates relative to a fixed
"today" (2026-09-21). Every day that passes, more Contract Out deals drift past
the 3-day threshold until all of them look stale and the demo stops being
legible. This shifts every date forward by the elapsed days, so "5 stale
contracts" stays true whenever the project is demoed.

It writes two things:
  data/deals.csv                  -> updated in place (source of truth for scripts)
  data/deal_date_refresh.csv      -> HubSpot update import (Deal Name + 2 dates)

Run:  python refresh_dates.py
Then import deal_date_refresh.csv into HubSpot as a Deals update, keyed on Deal Name.
"""

import csv
import os
from datetime import date, datetime, timedelta

ANCHOR = date(2026, 9, 21)          # the date the dataset was generated for
BASE = os.path.dirname(os.path.abspath(__file__))
DEALS = os.path.join(BASE, "data", "deals.csv")
DATE_COLS = ["Close Date", "Last Contract Update"]

shift = (date.today() - ANCHOR).days
if shift <= 0:
    print(f"No shift needed (anchor {ANCHOR} is not in the past).")
    raise SystemExit

rows = list(csv.DictReader(open(DEALS)))
for r in rows:
    for col in DATE_COLS:
        if r[col]:
            d = datetime.strptime(r[col], "%Y-%m-%d").date() + timedelta(days=shift)
            r[col] = d.isoformat()

with open(DEALS, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

out = os.path.join(BASE, "data", "deal_date_refresh.csv")
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["Deal Name"] + DATE_COLS)
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in ["Deal Name"] + DATE_COLS})

stale = sum(1 for r in rows if r["Deal Stage"] == "Contract Out"
            and (date.today() - datetime.strptime(r["Last Contract Update"], "%Y-%m-%d").date()).days > 3)
print(f"Shifted all dates +{shift} days. Anchor is now {date.today()}.")
print(f"Contract Out deals stale past 3 days: {stale}")
print(f"wrote {out}  -> import into HubSpot as a Deals update, keyed on Deal Name")
