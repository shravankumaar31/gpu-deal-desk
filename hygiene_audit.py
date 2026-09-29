"""
Hygiene Audit — portal-wide data quality, scored.

Audits every deal, contact and company against the rules in the Deal Desk
Playbook and sorts what it finds into three buckets:

  AUTO     mechanical and reversible — the audit fixes it and says so
  REVIEW   a human has to decide; the audit cannot know the right answer
  BLOCK    stops money moving (invoicing or revenue recognition)

It never reads data/issues_manifest.csv. Every finding is derived from the
playbook, which is the only way to know whether the rules actually work.

Also produces the finance handoff: for each Closed Won deal, the checklist from
playbook section 7, and an invoice-ready summary for the deals that pass.

Usage
  python3 hygiene_audit.py              full audit + score
  python3 hygiene_audit.py --fix        apply the AUTO fixes
  python3 hygiene_audit.py --handoff    the finance handoff only
  python3 hygiene_audit.py --verify     compare findings against the answer key
"""

import argparse
import csv
import os
import re
from collections import Counter, defaultdict
from datetime import date, datetime

import dealdesk as dd

AUTO, REVIEW, BLOCK = "AUTO", "REVIEW", "BLOCK"
PERSONAL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}

# Severity weights for the hygiene score. Anything that stops money moving
# costs more than anything that only makes a report wrong.
WEIGHT = {BLOCK: 5, REVIEW: 2, AUTO: 1}

HANDOFF_CHECKS = [
    ("Contract countersigned", lambda d, ctx: d.get("Contract Status") == "Countersigned"),
    ("Contract term recorded", lambda d, ctx: bool(d.get("Contract Term"))),
    ("GPU configuration recorded", lambda d, ctx: bool(d.get("GPU Type")) and bool(d.get("GPU Count"))),
    ("Billing frequency set", lambda d, ctx: bool(d.get("Billing Frequency"))),
    ("Billing contact on the account", lambda d, ctx: ctx["billing"].get(d["Company Domain Name"]) is not None),
    ("PO number captured (if required)", lambda d, ctx: not ctx["po_required"](d) or bool(d.get("PO Number"))),
    ("Fulfillment status set", lambda d, ctx: bool(d.get("Fulfillment Status"))),
]


def norm_company(name):
    """Normalize a company name for duplicate detection."""
    n = name.lower()
    n = re.sub(r"\b(inc|llc|ltd|corp|co|gmbh|sa|bv|plc|limited|incorporated)\b", "", n)
    return re.sub(r"[^a-z0-9]", "", n)


# --------------------------------------------------------------------------
# The rules
# --------------------------------------------------------------------------
def audit(deals, contacts, companies, billing, employees):
    findings = []

    def add(bucket, obj, record, rule, detail, fix=None):
        findings.append({"bucket": bucket, "object": obj, "record": record,
                         "rule": rule, "detail": detail, "fix": fix})

    today = date.today()

    # ---- Companies -------------------------------------------------------
    by_norm = defaultdict(list)
    for c in companies:
        by_norm[norm_company(c["Company Name"])].append(c)

    deals_by_domain = Counter(d["Company Domain Name"] for d in deals)
    contacts_by_domain = Counter(c["Email"].split("@")[1] for c in contacts if "@" in c["Email"])

    for group in by_norm.values():
        if len(group) < 2:
            continue
        # An empty duplicate — no deals, no contacts — is mechanically safe to remove.
        for c in group:
            dom = c["Company Domain Name"]
            if deals_by_domain[dom] == 0 and contacts_by_domain[dom] == 0:
                keeper = next(g["Company Name"] for g in group if g is not c)
                add(AUTO, "Company", c["Company Name"], "duplicate_company",
                    f"Duplicate of '{keeper}' with no deals and no contacts",
                    f"delete {c['Company Domain Name']}")
                break
        else:
            names = " / ".join(g["Company Name"] for g in group)
            add(REVIEW, "Company", names, "duplicate_company",
                "Duplicate records, both carrying deals or contacts — needs a manual merge")

    # ---- Contacts --------------------------------------------------------
    known_domains = {c["Company Domain Name"] for c in companies}
    for c in contacts:
        email = c.get("Email", "")
        if "@" not in email:
            add(REVIEW, "Contact", email or c.get("Last Name", "?"), "invalid_email",
                "No usable email address")
            continue
        dom = email.split("@")[1]
        if dom in PERSONAL_DOMAINS:
            add(REVIEW, "Contact", email, "unassociated_contact",
                "Personal email domain — cannot be auto-associated; research and link by hand")
        elif dom not in known_domains:
            add(AUTO, "Contact", email, "unassociated_contact",
                f"Domain {dom} has no company record", f"create company for {dom}")

    # ---- Deals -----------------------------------------------------------
    for d in deals:
        name, stage = d["Deal Name"], d["Deal Stage"]
        closed = stage.startswith("Closed")
        dom = d["Company Domain Name"]

        close_raw = str(d.get("Close Date", "")).strip()
        if close_raw and not closed:
            if datetime.strptime(close_raw[:10], "%Y-%m-%d").date() < today:
                add(REVIEW, "Deal", name, "past_close_date_open_deal",
                    f"Close date {close_raw[:10]} has passed but the deal is {stage} — "
                    "the forecast is wrong until the rep re-dates it")

        # The playbook makes a billing contact an exit criterion for Contract Out,
        # not just a Closed Won requirement — catching it a stage earlier is the
        # whole point of having exit criteria.
        if stage in ("Contract Out", "Closed Won") and not billing.get(dom):
            add(BLOCK, "Deal", name, "missing_billing_contact",
                f"No {dd.BILLING_TITLE} contact on the account — nobody to send the invoice to "
                f"(required to leave {stage})")

        if stage == "Closed Won":
            if d.get("Contract Status") != "Countersigned":
                add(BLOCK, "Deal", name, "won_without_signature",
                    f"Closed Won but Contract Status is '{d.get('Contract Status') or 'empty'}' — "
                    "revenue recognized against an unsigned contract")
            if employees.get(dom, 0) >= dd.PO_MIN_EMPLOYEES and not d.get("PO Number"):
                add(BLOCK, "Deal", name, "missing_po_number",
                    f"Account has {employees.get(dom, 0):,} employees so a PO is required, "
                    "and none is recorded — finance cannot invoice")
            if not d.get("Fulfillment Status"):
                add(REVIEW, "Deal", name, "missing_fulfillment_status",
                    "Won but not marked Provisioning, Live or Invoiced — delivery is untracked")

        if stage == "Closed Lost" and not d.get("Closed Lost Reason"):
            add(REVIEW, "Deal", name, "missing_lost_reason",
                "Closed Lost with no reason — win/loss analysis is unusable without it")

        if stage in dd.QUOTED_STAGES:
            if not d.get("Contract Term"):
                add(BLOCK, "Deal", name, "missing_contract_term",
                    f"Quotable stage ({stage}) with no contract term — the deal cannot be priced")
            else:
                try:
                    q = dd.price(d["GPU Type"], int(float(d["GPU Count"])), d["Contract Term"],
                                 float(d.get("Negotiated Discount") or 0), "v1")
                    crm = float(d.get("Amount") or 0)
                    if abs(crm - q["tcv"]) > 1:
                        add(BLOCK, "Deal", name, "amount_mismatch",
                            f"Amount ${crm:,.2f} but the price book gives ${q['tcv']:,.2f} "
                            f"(off by ${crm - q['tcv']:,.2f}) — an unrecorded negotiation or a typo")
                except (ValueError, KeyError):
                    pass

    return findings


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------
def score(findings, totals):
    """Percentage of records that pass every check.

    An earlier version summed severity weights and divided by the record count,
    which drove Deals to 0.0/100 on 18 findings across 60 records — technically a
    number, useless as a signal. "72% of deals are clean" is a score anyone can
    act on, and severity is reported separately rather than mashed into it.
    """
    out = {}
    for obj, count in totals.items():
        dirty = {f["record"] for f in findings if f["object"] == obj}
        out[obj] = (100 * (1 - len(dirty) / max(count, 1)), len(dirty), count)
    all_dirty = sum(len({f["record"] for f in findings if f["object"] == o}) for o in totals)
    total = sum(totals.values())
    out["OVERALL"] = (100 * (1 - all_dirty / max(total, 1)), all_dirty, total)
    return out


# --------------------------------------------------------------------------
# Finance handoff
# --------------------------------------------------------------------------
def handoff(deals, ctx):
    ready, blocked = [], []
    for d in deals:
        if d["Deal Stage"] != "Closed Won":
            continue
        failed = [label for label, check in HANDOFF_CHECKS if not check(d, ctx)]
        row = {
            "Deal Name": d["Deal Name"],
            "Company": d["Deal Name"].split(" - ")[0],
            "Amount": float(d.get("Amount") or 0),
            "GPU": f"{d.get('GPU Count', '?')}x {d.get('GPU Type', '?')}",
            "Term": d.get("Contract Term", ""),
            "Billing Frequency": d.get("Billing Frequency", ""),
            "Payment Terms": dd.RULES["standard_payment_terms"],
            "Billing Contact": (ctx["billing"].get(d["Company Domain Name"]) or {}).get("Email", ""),
            "PO Number": d.get("PO Number", ""),
            "Start Date": str(d.get("Close Date", ""))[:10],
            "Fulfillment": d.get("Fulfillment Status", ""),
            "Missing": "; ".join(failed),
        }
        (blocked if failed else ready).append(row)
    return ready, blocked


# --------------------------------------------------------------------------
def report(findings, scores, ready, blocked):
    bars = "=" * 72
    print(f"HYGIENE AUDIT   {date.today():%a %d %b %Y}\n{bars}")

    s, dirty, rec = scores["OVERALL"]
    sev = Counter(f["bucket"] for f in findings)
    print(f"Hygiene score: {s:.1f}%   ({rec - dirty} of {rec} records clean)")
    print(f"  {len(findings)} findings — "
          f"{sev[BLOCK]} blocking · {sev[REVIEW]} to review · {sev[AUTO]} auto-fixable")
    for obj in ("Deal", "Contact", "Company"):
        if obj in scores:
            os_, od, oc = scores[obj]
            print(f"  {obj + 's':<10} {os_:>5.1f}%   {oc - od} of {oc} clean")

    for bucket, blurb in ((BLOCK, "stops money moving — fix before invoicing"),
                          (REVIEW, "needs a human decision"),
                          (AUTO, "mechanical and reversible — run --fix")):
        group = [f for f in findings if f["bucket"] == bucket]
        print(f"\n── {bucket} ({len(group)}) ── {blurb}")
        if not group:
            print("   none")
            continue
        by_rule = defaultdict(list)
        for f in group:
            by_rule[f["rule"]].append(f)
        for rule, items in sorted(by_rule.items(), key=lambda kv: -len(kv[1])):
            print(f"\n   {rule}  ({len(items)})")
            for f in items[:4]:
                print(f"     · {f['record']}")
                print(f"       {f['detail']}")
            if len(items) > 4:
                print(f"     · … and {len(items) - 4} more")

    print(f"\n{bars}\nFINANCE HANDOFF")
    print(f"  {len(ready)} of {len(ready) + len(blocked)} won deals are invoice-ready "
          f"(${sum(r['Amount'] for r in ready):,.0f})")
    if blocked:
        print(f"  {len(blocked)} blocked (${sum(r['Amount'] for r in blocked):,.0f}):")
        for r in blocked:
            print(f"     · {r['Deal Name']}\n       missing: {r['Missing']}")


def apply_fixes(findings, companies, contacts):
    """Apply only the AUTO bucket, and only to the portal mirror."""
    autos = [f for f in findings if f["bucket"] == AUTO]
    if not autos:
        print("Nothing in the AUTO bucket. Nothing to fix.")
        return
    drop_domains = {f["fix"].split()[-1] for f in autos
                    if f["rule"] == "duplicate_company" and f["fix"]}
    if drop_domains:
        kept = [c for c in companies if c["Company Domain Name"] not in drop_domains]
        path = os.path.join(dd.BASE, "data", "companies.csv")
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(companies[0].keys()))
            w.writeheader()
            w.writerows(kept)
        for dom in sorted(drop_domains):
            print(f"  removed duplicate company record: {dom}")
    print(f"\nApplied {len(drop_domains)} fix(es). "
          "Everything else needs a human — see the REVIEW and BLOCK buckets.")


def verify(findings):
    """Compare findings against the answer key. Only ever run by hand."""
    path = os.path.join(dd.BASE, "data", "issues_manifest.csv")
    planted = Counter(r["Issue Type"] for r in csv.DictReader(open(path)))
    found = Counter(f["rule"] for f in findings)
    owned_elsewhere = {"stale_contract": "Day 4 tracker",
                       "needs_discount_approval": "quote engine",
                       "needs_terms_review": "quote engine"}
    print(f"{'issue type':<32} {'planted':>8} {'found':>7}   note")
    print("-" * 72)
    for rule in sorted(set(planted) | set(found)):
        note = owned_elsewhere.get(rule, "")
        if rule not in planted:
            note = "not planted — audit's own finding"
        print(f"{rule:<32} {planted.get(rule, 0):>8} {found.get(rule, 0):>7}   {note}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fix", action="store_true", help="apply the AUTO bucket")
    ap.add_argument("--handoff", action="store_true", help="finance handoff only")
    ap.add_argument("--verify", action="store_true", help="compare against the answer key")
    args = ap.parse_args()

    deals, billing, employees = dd.load_portal()
    contacts = dd.load_csv("contacts.csv")
    companies = dd.load_csv("companies.csv")
    ctx = {"billing": billing,
           "po_required": lambda d: employees.get(d["Company Domain Name"], 0) >= dd.PO_MIN_EMPLOYEES}

    findings = audit(deals, contacts, companies, billing, employees)
    ready, blocked = handoff(deals, ctx)

    if args.verify:
        verify(findings)
        return
    if args.fix:
        apply_fixes(findings, companies, contacts)
        return
    if args.handoff:
        print(f"FINANCE HANDOFF   {date.today():%a %d %b %Y}\n" + "=" * 72)
        for r in ready:
            print(f"  ✓ {r['Deal Name']}\n    {r['GPU']} · {r['Term']} · ${r['Amount']:,.0f} · "
                  f"{r['Billing Frequency']} · {r['Payment Terms']} · {r['Billing Contact']}"
                  + (f" · {r['PO Number']}" if r["PO Number"] else ""))
        for r in blocked:
            print(f"  ✗ {r['Deal Name']}\n    BLOCKED: {r['Missing']}")
        return

    totals = {"Deal": len(deals), "Contact": len(contacts), "Company": len(companies)}
    report(findings, score(findings, totals), ready, blocked)

    out = os.path.join(dd.BASE, "data", "hygiene_findings.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["bucket", "object", "record", "rule", "detail", "fix"])
        w.writeheader()
        w.writerows(findings)
    out2 = os.path.join(dd.BASE, "data", "finance_handoff.csv")
    with open(out2, "w", newline="") as f:
        rows = ready + blocked
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {os.path.relpath(out, dd.BASE)} and {os.path.relpath(out2, dd.BASE)}")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:          # e.g. piped into `head`
        os._exit(0)
