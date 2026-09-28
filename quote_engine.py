"""
Quote & Order Form Generator — the deal desk's guardrail.

Prices a deal from the price book, checks it against the approval matrix, and
then does exactly one of three things:

  BLOCKED           data is missing or wrong -> no document, list the problems
  PENDING APPROVAL  policy requires a named approver -> approval request, no order form
  APPROVED          within policy -> generate the order form PDF

It never fills a gap with a guess. That is the whole point: a quote with an
invented term or a silently corrected amount is worse than no quote.

Usage
  python quote_engine.py --list                      show quotable deals
  python quote_engine.py "Wrenfield Studios - 16x H100 SXM - 6-Month Reserved"
  python quote_engine.py --all                       run every quoted deal, write a summary
  python quote_engine.py <deal> --book v1            price on the legacy book

Order forms land in output/order_forms/. All data is synthetic.
"""

import argparse
import csv
import os
import sys
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

import dealdesk as dd

SELLER = "Demo GPU Cloud, Inc."
OUT_DIR = os.path.join(dd.BASE, "output", "order_forms")
NAVY = colors.HexColor("#1B2A4A")
GREY = colors.HexColor("#5A6472")
LINE = colors.HexColor("#D5D9E0")


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------
def evaluate(deal, billing, employees, book="v2"):
    """Return a result dict describing what the deal desk would do with this deal."""
    domain = deal.get("Company Domain Name", "")
    contact = billing.get(domain)
    res = {
        "deal": deal,
        "company": deal["Deal Name"].split(" - ")[0],
        "domain": domain,
        "billing_contact": contact,
        "po_required": employees.get(domain, 0) >= dd.PO_MIN_EMPLOYEES,
        "problems": dd.validate(deal, contact),
        "quote": None, "approvers": [], "notify": [], "reasons": [],
        "variance": None, "status": "BLOCKED",
    }
    if res["problems"]:
        return res

    try:
        res["quote"] = dd.price(deal["GPU Type"], int(float(deal["GPU Count"])),
                                deal["Contract Term"],
                                float(deal.get("Negotiated Discount") or 0), book)
    except ValueError as e:
        res["problems"].append(str(e))
        return res

    var = dd.amount_variance(deal, res["quote"])
    if var:
        crm, delta = var
        res["variance"] = {"crm": crm, "delta": delta}
        # A mismatch on the book the deal was quoted on is a real error.
        if book == "v1" and abs(delta) > 1:
            res["problems"].append(
                f"CRM amount ${crm:,.2f} does not match the price book "
                f"(${res['quote']['tcv']:,.2f}, off by ${delta:,.2f})")
            return res

    res["approvers"], res["notify"], res["reasons"] = dd.route(
        res["quote"]["negotiated_discount"], res["quote"]["tcv"],
        deal.get("Non-Standard Terms", ""), deal.get("Contract Term", ""))
    res["status"] = "PENDING APPROVAL" if res["approvers"] else "APPROVED"
    return res


# --------------------------------------------------------------------------
# Order form PDF
# --------------------------------------------------------------------------
def money(v):
    return f"${v:,.2f}"


def build_order_form(res, path):
    deal, q = res["deal"], res["quote"]
    doc = SimpleDocTemplate(path, pagesize=LETTER,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            title=f"Order Form — {deal['Deal Name']}")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontName="Helvetica-Bold",
                        fontSize=17, textColor=NAVY, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontSize=9, textColor=GREY,
                         alignment=TA_CENTER, spaceAfter=14)
    h2 = ParagraphStyle("h2", parent=ss["Normal"], fontName="Helvetica-Bold",
                        fontSize=10, textColor=NAVY, spaceBefore=14, spaceAfter=5)
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=9, leading=13)
    fine = ParagraphStyle("fine", parent=ss["Normal"], fontSize=7.5,
                          textColor=GREY, leading=10)

    def grid(rows, widths, header=False):
        t = Table(rows, colWidths=widths, hAlign="LEFT")
        style = [("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                 ("FONTSIZE", (0, 0), (-1, -1), 9),
                 ("TEXTCOLOR", (0, 0), (0, -1), GREY),
                 ("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("TOPPADDING", (0, 0), (-1, -1), 4),
                 ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                 ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE)]
        if header:
            style += [("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                      ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
                      ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY)]
        t.setStyle(TableStyle(style))
        return t

    s = []
    s.append(Paragraph("GPU CAPACITY ORDER FORM", h1))
    s.append(Paragraph(f"{SELLER} &nbsp;·&nbsp; Quote {date.today():%Y-%m-%d} "
                       f"&nbsp;·&nbsp; Valid through {dd.quote_expiry():%B %d, %Y}", sub))

    contact = res["billing_contact"] or {}
    s.append(Paragraph("CUSTOMER", h2))
    s.append(grid([
        ["Company", res["company"]],
        ["Billing contact", f"{contact.get('First Name','')} {contact.get('Last Name','')}".strip() or "—"],
        ["Billing email", contact.get("Email", "—")],
        ["PO required", "Yes — PO number required before invoicing" if res["po_required"] else "No"],
    ], [1.5 * inch, 5.0 * inch]))

    s.append(Paragraph("CAPACITY ORDERED", h2))
    s.append(grid([
        ["GPU model", "Quantity", "Term", "Billed hours"],
        [deal["GPU Type"], str(q["gpu_count"]), deal["Contract Term"], f"{q['hours']:,}"],
    ], [1.9 * inch, 1.2 * inch, 2.0 * inch, 1.4 * inch], header=True))

    s.append(Paragraph("PRICING", h2))
    rows = [["Line", "Rate / GPU-hour", "Amount"],
            [f"List rate ({q['price_book']} price book)", money(q["list_rate"]), ""],
            [f"Term discount ({q['term_discount']:.0%})",
             f"-{money(q['list_rate'] * q['term_discount'])}", ""]]
    if q["negotiated_discount"]:
        after_term = q["list_rate"] * (1 - q["term_discount"])
        rows.append([f"Negotiated discount ({q['negotiated_discount']:.0%})",
                     f"-{money(after_term * q['negotiated_discount'])}", ""])
    rows += [["Effective rate", money(q["effective_rate"]), ""],
             [f"{q['gpu_count']} GPUs × {q['hours']:,} hours × {money(q['effective_rate'])}",
              "", money(q["tcv"])],
             ["TOTAL CONTRACT VALUE", "", money(q["tcv"])]]
    t = grid(rows, [3.6 * inch, 1.6 * inch, 1.3 * inch], header=True)
    t.setStyle(TableStyle([
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, -1), (-1, -1), NAVY),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, NAVY),
        ("LINEBELOW", (0, -1), (-1, -1), 0, colors.white),
        ("TEXTCOLOR", (0, 1), (0, -2), colors.black)]))
    s.append(t)

    s.append(Paragraph("COMMERCIAL TERMS", h2))
    terms = [["Billing frequency", deal["Billing Frequency"]],
             ["Payment terms", dd.RULES["standard_payment_terms"]],
             ["Uptime SLA", dd.RULES["standard_uptime_sla"]],
             ["Quote validity", f"{dd.RULES['quote_validity_days']} days from the quote date"]]
    if deal.get("Non-Standard Terms"):
        terms.append(["Non-standard term", f"{deal['Non-Standard Terms']} "
                                           f"(approved by {', '.join(res['approvers'])})"])
    s.append(grid(terms, [1.5 * inch, 5.0 * inch]))

    s.append(Paragraph("ACCEPTANCE", h2))
    s.append(Paragraph("Signing below accepts the capacity, pricing and terms set out above.", body))
    s.append(Spacer(1, 22))
    sig = Table([["_" * 34, "", "_" * 34],
                 [f"{res['company']}", "", SELLER],
                 ["Name / Title / Date", "", "Name / Title / Date"]],
                colWidths=[2.9 * inch, 0.7 * inch, 2.9 * inch], hAlign="LEFT")
    sig.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8),
                             ("TEXTCOLOR", (0, 2), (-1, 2), GREY),
                             ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                             ("TOPPADDING", (0, 1), (-1, 1), 3)]))
    s.append(sig)

    s.append(Spacer(1, 18))
    s.append(Paragraph(
        f"Generated by the deal desk quote engine on {date.today():%Y-%m-%d} from price book "
        f"{q['price_book']}. Approval route: {', '.join(res['approvers']) or 'auto-approved within policy'}."
        "<br/><br/><b>Portfolio demonstration — not a real commercial document.</b> "
        f"{SELLER} and every customer, price and figure in this document are fictional, "
        "created to demonstrate a quote-to-cash workflow.", fine))

    doc.build(s)


# --------------------------------------------------------------------------
# Console reporting
# --------------------------------------------------------------------------
BAR = "─" * 72


def report(res, pdf_path=None):
    deal, q = res["deal"], res["quote"]
    print(f"\n{BAR}\n{deal['Deal Name']}\n{BAR}")
    print(f"  stage            {deal['Deal Stage']}")
    if q:
        print(f"  priced           {q['gpu_count']} × {deal['GPU Type']}, {deal['Contract Term']}"
              f"  ({q['price_book']} book)")
        print(f"  effective rate   {money(q['effective_rate'])}/GPU-hour"
              f"   (list {money(q['list_rate'])}, term -{q['term_discount']:.0%},"
              f" negotiated -{q['negotiated_discount']:.0%})")
        print(f"  contract value   {money(q['tcv'])}")
        if res["variance"] and abs(res["variance"]["delta"]) > 1:
            v = res["variance"]
            if q["price_book"] == "v1":
                print(f"  CRM amount       {money(v['crm'])}"
                      f"   ⚠ off by {money(v['delta'])}")
            else:
                print(f"  booked at        {money(v['crm'])} on the v1 book"
                      f"   (re-quote is {money(v['delta']):>12} higher)")

    print(f"\n  STATUS: {res['status']}")
    if res["problems"]:
        print("  Blocked — nothing is generated until these are resolved:")
        for p in res["problems"]:
            print(f"    ✗ {p}")
        print("  The deal desk does not guess on a customer contract.")
    elif res["approvers"]:
        print(f"  Approval required from: {', '.join(res['approvers'])}"
              f"   (final: {dd.final_approver(res['approvers'])})")
        for r in res["reasons"]:
            print(f"    • {r}")
        if res["notify"]:
            print(f"  Notify (not a gate): {', '.join(res['notify'])}")
        print("  No order form generated until the approval is logged in writing.")
    else:
        print("  Within policy — no approval needed.")
        if res["notify"]:
            print(f"  Notify (not a gate): {', '.join(res['notify'])}")
        if pdf_path:
            print(f"  Order form: {os.path.relpath(pdf_path, dd.BASE)}")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deal", nargs="?", help="deal name (or a unique part of one)")
    ap.add_argument("--all", action="store_true", help="evaluate every quoted deal")
    ap.add_argument("--list", action="store_true", help="list quotable deals")
    ap.add_argument("--book", default="v2", choices=["v1", "v2"], help="price book version")
    args = ap.parse_args()

    deals, billing, employees = dd.load_portal()
    quotable = [d for d in deals if d["Deal Stage"] in dd.QUOTED_STAGES]

    if args.list:
        for d in sorted(quotable, key=lambda x: x["Deal Name"]):
            print(f"  [{d['Deal Stage']:<13}] {d['Deal Name']}")
        print(f"\n{len(quotable)} quotable deals.")
        return

    os.makedirs(OUT_DIR, exist_ok=True)

    if args.all:
        rows, counts = [], {"APPROVED": 0, "PENDING APPROVAL": 0, "BLOCKED": 0}
        for d in quotable:
            res = evaluate(d, billing, employees, args.book)
            counts[res["status"]] += 1
            rows.append({
                "Deal Name": d["Deal Name"], "Stage": d["Deal Stage"],
                "Status": res["status"],
                "Contract Value": res["quote"]["tcv"] if res["quote"] else "",
                "Approvers": "; ".join(res["approvers"]),
                "Notify": "; ".join(res["notify"]),
                "Blockers": "; ".join(res["problems"]),
                "Reasons": "; ".join(res["reasons"]),
            })
        out = os.path.join(dd.BASE, "data", "quote_run.csv")
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        total = len(rows)
        print(f"Evaluated {total} quotable deals on price book {args.book}:\n")
        for k in ("APPROVED", "PENDING APPROVAL", "BLOCKED"):
            print(f"  {k:<18} {counts[k]:>3}  ({counts[k]/total:.0%})")
        print(f"\nwrote {os.path.relpath(out, dd.BASE)}")
        return

    if not args.deal:
        ap.print_help()
        return

    matches = [d for d in quotable if args.deal.lower() in d["Deal Name"].lower()]
    if not matches:
        print(f"No quotable deal matching {args.deal!r}. Try --list.")
        sys.exit(1)
    if len(matches) > 1:
        print(f"{len(matches)} deals match {args.deal!r}:")
        for d in matches:
            print(f"  {d['Deal Name']}")
        sys.exit(1)

    res = evaluate(matches[0], billing, employees, args.book)
    pdf_path = None
    if res["status"] == "APPROVED":
        safe = "".join(c if c.isalnum() or c in " -_" else "" for c in matches[0]["Deal Name"])
        pdf_path = os.path.join(OUT_DIR, f"{safe[:80]}.pdf")
        build_order_form(res, pdf_path)
    report(res, pdf_path)


if __name__ == "__main__":
    main()
