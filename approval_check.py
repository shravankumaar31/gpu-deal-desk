"""
Calibration check for the approval matrix.

Routes every quoted deal through the matrix and reports how the workload lands
across approvers. Use it after any change to config/price_book.json: if one
approver is taking more than roughly a fifth of all deals, the thresholds are
wrong and that person becomes the bottleneck.

The routing logic itself lives in dealdesk.py, so this script and the quote
engine can never drift apart.

Run:  python approval_check.py
"""

import csv
import os
from collections import Counter

import dealdesk as dd

deals, _, _ = dd.load_portal()
rows, counts = [], Counter()

for d in deals:
    if d["Deal Stage"] not in dd.QUOTED_STAGES:
        continue
    try:
        q = dd.price(d["GPU Type"], int(float(d["GPU Count"])), d["Contract Term"],
                     float(d.get("Negotiated Discount") or 0), "v1")
        tcv, disc = q["tcv"], q["negotiated_discount"]
    except (ValueError, KeyError):
        tcv = float(d.get("Amount") or 0)          # unpriceable: route on the CRM amount
        disc = float(d.get("Negotiated Discount") or 0)

    approvers, notify, reasons = dd.route(disc, tcv, d.get("Non-Standard Terms", ""),
                                          d.get("Contract Term", ""))
    final = dd.final_approver(approvers)
    counts[final] += 1
    rows.append({"Deal Name": d["Deal Name"], "Stage": d["Deal Stage"],
                 "Final Approver": final,
                 "All Approvers": "; ".join(approvers) or dd.AUTO,
                 "Notify": "; ".join(notify),
                 "Reasons": "; ".join(reasons) or "within policy"})

out = os.path.join(dd.BASE, "data", "approval_routing.csv")
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

total = len(rows)
print(f"Quoted deals routed: {total}\n")
for approver in dd.RANK:
    n = counts[approver]
    print(f"  {approver:<22} {n:>3}  ({n / total:.0%})")
print(f"\nwrote {os.path.relpath(out, dd.BASE)}")
