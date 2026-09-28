"""
Day 1 — Synthetic CRM data for "The 3-Day Rule: A Quote-to-Cash Deal Desk for a GPU Cloud".

Designed for HubSpot's free tier: uses exactly 10 custom deal properties.
Everything else uses HubSpot default properties or is derived in code.

Outputs (in data/):
  companies.csv        -> import first
  contacts.csv         -> import second (auto-associates to companies by email domain)
  deals.csv            -> import third (two-object import: Deals + Companies, keyed on domain)
  issues_manifest.csv  -> ANSWER KEY for the Day 5 hygiene audit. Do NOT import.

All prices are synthetic and for demo purposes only.
Run:  python generate_data.py
"""

import csv
import os
import random
from datetime import date, timedelta

random.seed(42)  # deterministic: same data every run

TODAY = date(2026, 9, 21)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# Pricing model (synthetic). Lives in code, not in HubSpot: list and effective
# rates are DERIVED from GPU Type + Contract Term + Negotiated Discount.
# ---------------------------------------------------------------------------
LIST_RATE = {"H100 SXM": 2.20, "H200": 2.80, "B200": 3.90}      # $/GPU-hour
TERM_HOURS = {"On-Demand": 730, "1-Month Reserved": 730, "3-Month Reserved": 2190,
              "6-Month Reserved": 4380, "12-Month Reserved": 8760}  # on-demand = est. 1 month
TERM_DISCOUNT = {"On-Demand": 0.00, "1-Month Reserved": 0.05, "3-Month Reserved": 0.10,
                 "6-Month Reserved": 0.15, "12-Month Reserved": 0.20}

# Business rules (also derived, not stored)
PO_REQUIRED_MIN_EMPLOYEES = 1000        # companies this size require a PO before invoicing
BILLING_CONTACT_TITLE = "Finance Manager"


def expected_amount(gpu_type, gpu_count, term, negotiated_discount):
    rate = LIST_RATE[gpu_type] * (1 - TERM_DISCOUNT[term]) * (1 - negotiated_discount)
    return round(gpu_count * TERM_HOURS[term] * rate, 2)


# ---------------------------------------------------------------------------
# Companies (default HubSpot properties only)
# ---------------------------------------------------------------------------
COMPANY_NAMES = [
    "Tensorfield Labs", "Quillmind AI", "Parallax Robotics", "Brightloom Bio", "Vectorwell",
    "Cobaltvoice", "Meridian Vision Systems", "Northgrain Genomics", "Driftwood Diffusion",
    "Halcyon Agents", "Lumenforge", "Kestrel Autonomy", "Sablecrest Analytics", "Orchard LLM",
    "Pinecurve Health AI", "Glasswing Models", "Ironbark Security AI", "Tidepool Research",
    "Copperline Finance AI", "Wrenfield Studios", "Marbleway Legal AI", "Foxglove Speech",
    "Stratacloud Media", "Emberlight Games", "Riverstone Retail AI", "Solace Biotech",
    "Altitude Mapping", "Quartzbridge Labs", "Nightjar Video", "Everfern Education AI",
    "Hollowpeak Materials", "Juniper Protein", "Clearwater Climate AI", "Bramblecode",
    "Starling Translate", "Ravenmoor Research", "Saltmarsh Agents", "Thistle Search",
    "Obsidian Vision", "Larkspur Robotics",
]
# Segment is used only to shape the data; in HubSpot it is derived from employee count.
SEGMENTS = ["AI Startup", "AI Startup", "AI Startup", "Growth-Stage AI", "Growth-Stage AI",
            "Enterprise", "Research Lab"]
EMPLOYEES = {"AI Startup": (8, 60), "Growth-Stage AI": (60, 400),
             "Enterprise": (1500, 20000), "Research Lab": (20, 300)}
LOCATIONS = [("San Francisco", "California", "United States"), ("Palo Alto", "California", "United States"),
             ("San Jose", "California", "United States"), ("Seattle", "Washington", "United States"),
             ("New York", "New York", "United States"), ("Austin", "Texas", "United States"),
             ("Boston", "Massachusetts", "United States"), ("Toronto", "Ontario", "Canada"),
             ("London", "England", "United Kingdom")]


def domain_for(name):
    return name.lower().replace(" ai", "").replace(" ", "") + ".ai"


companies = []
for name in COMPANY_NAMES:
    seg = random.choice(SEGMENTS)
    city, state, country = random.choice(LOCATIONS)
    companies.append({
        "Company Name": name,
        "Company Domain Name": domain_for(name),
        "Number of Employees": random.randint(*EMPLOYEES[seg]),
        "City": city,
        "State/Region": state,
        "Country/Region": country,
    })

customers = list(companies)          # the real 40 accounts
issues = []                          # answer key rows: object, record, issue_type, detail

# Messy: duplicate company under a different domain (survives HubSpot's domain dedupe)
companies.append({**companies[0], "Company Name": "Tensorfield Labs, Inc.",
                  "Company Domain Name": "tensorfield-labs.ai"})
issues.append(["Company", "Tensorfield Labs, Inc.", "duplicate_company",
               "Same company as 'Tensorfield Labs' under a second domain"])

# ---------------------------------------------------------------------------
# Contacts (default properties only; the role lives in Job Title)
# ---------------------------------------------------------------------------
FIRST = ["Priya", "Marcus", "Elena", "Jordan", "Wei", "Aisha", "Tomas", "Hannah", "Kenji", "Sofia",
         "Daniel", "Fatima", "Lucas", "Mei", "Omar", "Grace", "Ravi", "Chloe", "Andre", "Nadia",
         "Ethan", "Leila", "Mateo", "Yuki", "Samuel", "Irene", "Kofi", "Anya", "Diego", "Rachel"]
LAST = ["Shah", "Bennett", "Rossi", "Kim", "Zhang", "Okafor", "Novak", "Fischer", "Tanaka",
        "Alvarez", "Cohen", "Haddad", "Moreau", "Lin", "Nasser", "Walsh", "Iyer", "Dubois",
        "Carter", "Petrova", "Brooks", "Karimi", "Silva", "Mori", "Adeyemi", "Larsen"]
BASE_TITLES = ["ML Infrastructure Lead", "CTO", BILLING_CONTACT_TITLE]  # every account
LEGAL_TITLE = "Head of Legal"                                           # large accounts only

contacts = []
for c in customers:
    titles = list(BASE_TITLES)
    if c["Number of Employees"] >= PO_REQUIRED_MIN_EMPLOYEES:
        titles.append(LEGAL_TITLE)
    for title in titles:
        fn, ln = random.choice(FIRST), random.choice(LAST)
        contacts.append({"First Name": fn, "Last Name": ln,
                         "Email": f"{fn.lower()}.{ln.lower()}@{c['Company Domain Name']}",
                         "Job Title": title})

# Messy: contacts on personal email -> won't auto-associate to a company
for fn, ln, title in [("Jamie", "Ortiz", "Founder"), ("Alex", "Reyes", "ML Engineer"),
                      ("Sam", "Patel", "Head of Platform")]:
    email = f"{fn.lower()}.{ln.lower()}{random.randint(10, 99)}@gmail.com"
    contacts.append({"First Name": fn, "Last Name": ln, "Email": email, "Job Title": title})
    issues.append(["Contact", email, "unassociated_contact",
                   "Personal email domain; will not associate with any company"])

# ---------------------------------------------------------------------------
# Deals — 10 custom properties + HubSpot defaults
# ---------------------------------------------------------------------------
STAGE_PLAN = (["Discovery"] * 8 + ["Technical Eval"] * 8 + ["Quote Sent"] * 9 +
              ["Contract Out"] * 10 + ["Closed Won"] * 17 + ["Closed Lost"] * 8)
GPU_COUNTS = [8, 8, 16, 16, 32, 32, 64, 128, 256]
TERMS = list(TERM_HOURS)
NONSTD = ["Net 60 payment terms", "Custom 99.95% uptime SLA", "Early termination clause",
          "24-month price lock", "Capacity reservation guarantee"]
LOST_REASONS = ["Chose competitor on price", "Capacity not available in time",
                "Moved to on-prem", "Budget frozen", "No decision"]
LATE_STAGES = ("Contract Out", "Closed Won")
emp_by_domain = {c["Company Domain Name"]: c["Number of Employees"] for c in customers}


def negotiated_discount():
    r = random.random()
    if r < 0.55:
        return 0.0
    if r < 0.85:
        return random.choice([0.03, 0.05, 0.08, 0.10])
    return random.choice([0.12, 0.15, 0.18, 0.22, 0.25])  # needs approval on Day 2


deals = []
for i, stage in enumerate(STAGE_PLAN):
    co = customers[i] if i < len(customers) else random.choice(customers)
    gpu_type = random.choices(list(LIST_RATE), weights=[5, 3, 2])[0]
    gpu_count = random.choice(GPU_COUNTS)
    term = random.choice(TERMS)
    disc = negotiated_discount()

    if stage.startswith("Closed"):
        close = TODAY - timedelta(days=random.randint(5, 270))
    else:
        close = TODAY + timedelta(days=random.randint(10, 120))

    contract_status = {
        "Discovery": "Not Started", "Technical Eval": "Not Started",
        "Quote Sent": random.choice(["Not Started", "Drafting"]),
        "Contract Out": random.choice(["Redlines", "Legal Review", "Out for Signature"]),
        "Closed Won": "Countersigned", "Closed Lost": "",
    }[stage]

    if stage == "Contract Out":
        last_update = TODAY - timedelta(days=random.randint(0, 2))   # healthy by default
    elif stage.startswith("Closed"):
        last_update = close
    else:
        last_update = TODAY - timedelta(days=random.randint(1, 20))

    po_required = emp_by_domain[co["Company Domain Name"]] >= PO_REQUIRED_MIN_EMPLOYEES
    nonstd = random.random() < 0.2

    deals.append({
        # HubSpot default properties
        "Deal Name": f"{co['Company Name']} - {gpu_count}x {gpu_type} - {term}",
        "Pipeline": "GPU Sales Pipeline",
        "Deal Stage": stage,
        "Amount": expected_amount(gpu_type, gpu_count, term, disc),
        "Close Date": close.isoformat(),
        "Deal Type": random.choice(["New Business"] * 3 + ["Expansion"]),
        "Closed Lost Reason": random.choice(LOST_REASONS) if stage == "Closed Lost" else "",
        # The 10 custom properties
        "GPU Type": gpu_type,
        "GPU Count": gpu_count,
        "Contract Term": term,
        "Negotiated Discount": disc,
        "Billing Frequency": random.choice(["Monthly", "Monthly", "Quarterly", "Prepaid Upfront"])
                             if stage not in ("Discovery", "Technical Eval") else "",
        "Contract Status": contract_status,
        "Last Contract Update": last_update.isoformat(),
        "Non-Standard Terms": random.choice(NONSTD) if nonstd else "",
        "PO Number": f"PO-{random.randint(100000, 999999)}" if (po_required and stage == "Closed Won") else "",
        "Fulfillment Status": random.choice(["Provisioning", "Live", "Live", "Invoiced"]) if stage == "Closed Won" else "",
        # Association key (not a property)
        "Company Domain Name": co["Company Domain Name"],
    })

# ---------------------------------------------------------------------------
# Inject realistic data-quality problems (and log them in the answer key)
# ---------------------------------------------------------------------------
touched = set()


def pick(stages, n, extra=lambda d: True):
    pool = [d for d in deals if d["Deal Stage"] in stages and d["Deal Name"] not in touched and extra(d)]
    chosen = random.sample(pool, min(n, len(pool)))
    touched.update(d["Deal Name"] for d in chosen)
    return chosen


for d in pick(["Discovery", "Technical Eval", "Quote Sent", "Contract Out"], 4):
    d["Close Date"] = (TODAY - timedelta(days=random.randint(3, 45))).isoformat()
    issues.append(["Deal", d["Deal Name"], "past_close_date_open_deal",
                   f"Close date {d['Close Date']} but stage is {d['Deal Stage']}"])

for d in pick(["Contract Out"], 5):
    d["Last Contract Update"] = (TODAY - timedelta(days=random.randint(4, 16))).isoformat()
    issues.append(["Deal", d["Deal Name"], "stale_contract",
                   f"No contract update since {d['Last Contract Update']} (status: {d['Contract Status']})"])

for d in pick(["Quote Sent", "Contract Out", "Closed Won"], 3):
    correct = d["Amount"]
    d["Amount"] = round(correct * random.choice([0.5, 1.25, 2.0]), 2)
    issues.append(["Deal", d["Deal Name"], "amount_mismatch",
                   f"Amount {d['Amount']} vs expected {correct} from GPU math"])

for d in pick(["Quote Sent", "Contract Out"], 2):
    d["Contract Term"] = ""
    issues.append(["Deal", d["Deal Name"], "missing_contract_term",
                   f"Stage {d['Deal Stage']} requires a contract term"])

for d in pick(["Closed Won"], 2):
    d["Contract Status"] = "Out for Signature"
    issues.append(["Deal", d["Deal Name"], "won_without_signature",
                   "Closed Won but contract not countersigned"])

for d in pick(["Closed Lost"], 2):
    d["Closed Lost Reason"] = ""
    issues.append(["Deal", d["Deal Name"], "missing_lost_reason", "Closed Lost with no reason recorded"])

for d in pick(["Closed Won"], 2, lambda d: emp_by_domain[d["Company Domain Name"]] >= PO_REQUIRED_MIN_EMPLOYEES):
    d["PO Number"] = ""
    issues.append(["Deal", d["Deal Name"], "missing_po_number",
                   f"Company has {PO_REQUIRED_MIN_EMPLOYEES}+ employees (PO required) but no PO number"])

# Missing billing contact: remove the Finance Manager at 3 accounts with late-stage deals
late_domains = sorted({d["Company Domain Name"] for d in deals if d["Deal Stage"] in LATE_STAGES})
for dom in random.sample(late_domains, 3):
    contacts = [c for c in contacts
                if not (c["Email"].endswith("@" + dom) and c["Job Title"] == BILLING_CONTACT_TITLE)]
    for d in deals:
        if d["Company Domain Name"] == dom and d["Deal Stage"] in LATE_STAGES:
            issues.append(["Deal", d["Deal Name"], "missing_billing_contact",
                           f"Stage {d['Deal Stage']} but account has no {BILLING_CONTACT_TITLE} contact"])

# Review flags (not errors): Day 2 approval-matrix test cases
for d in deals:
    if d["Deal Stage"] in ("Discovery", "Technical Eval"):
        continue
    if d["Negotiated Discount"] > 0.10:
        issues.append(["Deal", d["Deal Name"], "needs_discount_approval",
                       f"Negotiated discount {d['Negotiated Discount']:.0%} exceeds 10% auto-approve"])
    if d["Non-Standard Terms"]:
        issues.append(["Deal", d["Deal Name"], "needs_terms_review", d["Non-Standard Terms"]])


# ---------------------------------------------------------------------------
# Write files
# ---------------------------------------------------------------------------
def write(name, rows, fields=None):
    path = os.path.join(OUT, name)
    with open(path, "w", newline="") as f:
        if isinstance(rows[0], list):
            w = csv.writer(f)
            w.writerow(fields)
            w.writerows(rows)
        else:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


write("companies.csv", companies)
write("contacts.csv", contacts)
write("deals.csv", deals)
write("issues_manifest.csv", issues, ["Object", "Record", "Issue Type", "Detail"])
