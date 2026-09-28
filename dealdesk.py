"""
dealdesk — shared pricing, validation and approval logic.

Single source of truth for the rules in docs/deal_desk_playbook.md.
Both approval_check.py and quote_engine.py import from here, so a policy
change in config/price_book.json changes every tool at once.
"""

import csv
import json
import os
from datetime import date, datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
POLICY = json.load(open(os.path.join(BASE, "config", "price_book.json")))
MATRIX = POLICY["approval_matrix"]
TERM_HOURS = POLICY["term_hours"]
RULES = POLICY["quote_rules"]
RANK = MATRIX["approver_rank"]
AUTO = "Deal Desk (auto)"

QUOTED_STAGES = ("Quote Sent", "Contract Out", "Closed Won", "Closed Lost")
BILLING_TITLE = "Finance Manager"
PO_MIN_EMPLOYEES = 1000


# --------------------------------------------------------------------------
# Pricing
# --------------------------------------------------------------------------
def book(version):
    return POLICY["price_books"][version]


def price(gpu_type, gpu_count, term, discount, version="v2"):
    """Return a priced quote dict, or raise ValueError if the inputs can't be priced."""
    b = book(version)
    if gpu_type not in b["list_rate_per_gpu_hour"]:
        raise ValueError(f"{gpu_type!r} is not on price book {version}")
    if term not in b["term_discount"]:
        raise ValueError(f"{term!r} is not on price book {version}"
                         f" ({b.get('twelve_month_and_longer', '')})".rstrip(" ()"))
    list_rate = b["list_rate_per_gpu_hour"][gpu_type]
    term_disc = b["term_discount"][term]
    eff_rate = list_rate * (1 - term_disc) * (1 - discount)
    hours = TERM_HOURS[term]
    return {
        "price_book": version,
        "list_rate": round(list_rate, 4),
        "term_discount": term_disc,
        "negotiated_discount": discount,
        "effective_rate": round(eff_rate, 4),
        "hours": hours,
        "gpu_count": gpu_count,
        "tcv": round(gpu_count * hours * eff_rate, 2),
    }


# --------------------------------------------------------------------------
# Approval routing
# --------------------------------------------------------------------------
def _tier(value, bands):
    for band in bands:
        if value <= band["max"]:
            return band["approver"]
    return RANK[-1]


def route(discount, tcv, non_standard_terms, term):
    """Return (approvers, notify, reasons)."""
    approvers, reasons = set(), []

    a = _tier(discount, MATRIX["discount"])
    if a != AUTO:
        approvers.add(a)
        reasons.append(f"negotiated discount {discount:.0%}")

    a = _tier(tcv, MATRIX["total_contract_value"])
    if a != AUTO:
        approvers.add(a)
        reasons.append(f"total contract value ${tcv:,.0f}")

    if non_standard_terms:
        approvers.update(MATRIX["non_standard_terms"].get(non_standard_terms, ["CEO"]))
        reasons.append(f"non-standard term: {non_standard_terms}")

    if term in MATRIX.get("term", {}):
        approvers.update(MATRIX["term"][term])
        reasons.append(f"contract term: {term}")

    notify = MATRIX.get("notify_only", {}).get("term", {}).get(term, [])
    return sorted(approvers, key=RANK.index), notify, reasons


def final_approver(approvers):
    return max(approvers, key=RANK.index) if approvers else AUTO


# --------------------------------------------------------------------------
# Validation — the "do not guess on a customer contract" guardrails
# --------------------------------------------------------------------------
def validate(deal, billing_contact=None):
    """Return a list of blocking problems. Empty list means the deal can be quoted."""
    problems = []

    for field in ("GPU Type", "GPU Count", "Contract Term"):
        if not str(deal.get(field, "")).strip():
            problems.append(f"{field} is empty — cannot price the deal")

    if not str(deal.get("Billing Frequency", "")).strip():
        problems.append("Billing Frequency is empty — finance cannot invoice")

    if deal.get("Deal Stage") in ("Contract Out", "Closed Won") and not billing_contact:
        problems.append(f"Account has no {BILLING_TITLE} contact — no one to bill")

    close = str(deal.get("Close Date", "")).strip()
    if close and deal.get("Deal Stage") not in ("Closed Won", "Closed Lost"):
        if datetime.strptime(close[:10], "%Y-%m-%d").date() < date.today():
            problems.append(f"Close date {close[:10]} is in the past on an open deal")

    return problems


def amount_variance(deal, quote):
    """CRM amount vs the price book. Returns (crm_amount, delta) or None if unset."""
    raw = str(deal.get("Amount", "")).strip()
    if not raw:
        return None
    crm = float(raw)
    return crm, round(crm - quote["tcv"], 2)


# --------------------------------------------------------------------------
# Offline data source (CSV mirror of the HubSpot portal)
# --------------------------------------------------------------------------
def load_csv(name):
    path = os.path.join(BASE, "data", name)
    with open(path) as f:
        return list(csv.DictReader(f))


def load_portal():
    """Return (deals, billing_contact_by_domain, employees_by_domain)."""
    deals = load_csv("deals.csv")
    contacts = load_csv("contacts.csv")
    companies = load_csv("companies.csv")

    billing = {}
    for c in contacts:
        if c.get("Job Title") == BILLING_TITLE and "@" in c.get("Email", ""):
            billing[c["Email"].split("@")[1]] = c

    employees = {}
    for c in companies:
        if c.get("Number of Employees"):
            employees[c["Company Domain Name"]] = int(float(c["Number of Employees"]))

    return deals, billing, employees


def quote_expiry(days=None):
    return date.today() + timedelta(days=days or RULES["quote_validity_days"])
