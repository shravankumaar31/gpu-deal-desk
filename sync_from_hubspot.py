"""
Rebuild the portal mirror (data/deals.csv) from a HubSpot deals export.

The local CSVs are a mirror of the portal, and a mirror that silently diverges
from its source is its own data quality problem. After fixing records in HubSpot,
run this so the audit and the tracker see the same world the CRM does.

Company Domain Name is not in HubSpot's deal export (it lives on the associated
company), so it is carried over from the existing mirror, matched on Deal Name.

Usage:  python3 sync_from_hubspot.py <hubspot_deals_export.csv>
"""
import csv
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DEALS = os.path.join(BASE, "data", "deals.csv")

SCHEMA = ["Deal Name", "Pipeline", "Deal Stage", "Amount", "Close Date", "Deal Type",
          "Closed Lost Reason", "GPU Type", "GPU Count", "Contract Term",
          "Negotiated Discount", "Billing Frequency", "Contract Status",
          "Last Contract Update", "Non-Standard Terms", "PO Number",
          "Fulfillment Status", "Company Domain Name"]

# HubSpot lowercases the tail of pipeline stage labels on export.
STAGE = {"quote sent": "Quote Sent", "contract out": "Contract Out",
         "closed won": "Closed Won", "closed lost": "Closed Lost",
         "discovery": "Discovery", "technical eval": "Technical Eval"}


def clean(v):
    return (v or "").strip()


def num(v):
    v = clean(v)
    if not v:
        return ""
    f = float(v)
    return str(int(f)) if f == int(f) else str(f)


src = sys.argv[1]
existing = list(csv.DictReader(open(DEALS)))
domain_by_name = {r["Deal Name"]: r["Company Domain Name"] for r in existing}

rows, missing = [], []
for r in csv.DictReader(open(src)):
    name = clean(r["Deal Name"])
    dom = domain_by_name.get(name, "")
    if not dom:
        missing.append(name)
    rows.append({
        "Deal Name": name,
        "Pipeline": clean(r.get("Pipeline")),
        "Deal Stage": STAGE.get(clean(r.get("Deal Stage")).lower(), clean(r.get("Deal Stage"))),
        "Amount": num(r.get("Amount")),
        "Close Date": clean(r.get("Close Date"))[:10],
        "Deal Type": clean(r.get("Deal Type")),
        "Closed Lost Reason": clean(r.get("Closed Lost Reason")),
        "GPU Type": clean(r.get("GPU Type")),
        "GPU Count": num(r.get("GPU Count")),
        "Contract Term": clean(r.get("Contract Term")),
        "Negotiated Discount": clean(r.get("Negotiated Discount")) or "0.0",
        "Billing Frequency": clean(r.get("Billing Frequency")),
        "Contract Status": clean(r.get("Contract Status")),
        "Last Contract Update": clean(r.get("Last Contract Update"))[:10],
        "Non-Standard Terms": clean(r.get("Non-Standard Terms")),
        "PO Number": clean(r.get("PO Number")),
        "Fulfillment Status": clean(r.get("Fulfillment Status")),
        "Company Domain Name": dom,
    })

with open(DEALS, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=SCHEMA)
    w.writeheader()
    w.writerows(rows)

print(f"Rebuilt {os.path.relpath(DEALS, BASE)} from {os.path.basename(src)} — {len(rows)} deals.")
if missing:
    print(f"WARNING: no company domain carried over for {len(missing)} deal(s):")
    for m in missing[:10]:
        print(f"  {m}")
