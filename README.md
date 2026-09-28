# GPU Cloud Deal Desk

**A working quote-to-cash deal desk for a GPU cloud company, built in HubSpot with Python automation.**

One person at a small GPU infrastructure company holds together everything that makes a deal close: contract tracking, quote prep, CRM hygiene, customer follow-up, invoicing coordination. This is that job, built as a system — with the rule that **nothing sits for three days** enforced in code rather than remembered.

All data is synthetic. Prices are calibrated to public GPU cloud rates but the company, customers and deals are fictional.

---

## What it covers

| The job | What's built |
|---|---|
| Track contracts — status, signatures, what is stuck | Contract Status property, a 6-stage pipeline, and the 3-Day Rule escalation ladder |
| Prep quotes and order forms | `quote_engine.py` — prices from a versioned price book, generates order form PDFs |
| Own CRM data quality | Stage exit criteria, plus validation that blocked 11 of 44 quoted deals on real data problems |
| Follow up until things close | Documented-pause rules so legitimate delays don't escalate and stalled deals can't hide |
| Coordinate invoicing with finance | A handoff checklist the engine enforces: billing contact, PO, countersigned contract |
| Don't guess on a customer contract | The engine refuses to generate a document when data is missing or contradictory |
| Automate the repetitive parts | All policy lives in one JSON file; every tool reads from it |

---

## The core idea

A quote engine that can only do three things:

| Outcome | When | Output |
|---|---|---|
| **BLOCKED** | Data is missing or contradictory | A list of problems. No document. |
| **PENDING APPROVAL** | Policy requires a named approver | The approvers and the reasons. No order form. |
| **APPROVED** | Within policy | An order form PDF |

Most tools would auto-correct a CRM amount that doesn't match the price book. This one refuses. A mismatch means either somebody negotiated a price that was never recorded, or somebody mistyped a number — and those need opposite fixes. Guessing produces a confident, wrong contract.

Run against the 44 quoted deals in the portal:

| Outcome | Count | Share |
|---|---|---|
| Pending approval | 18 | 41% |
| Approved | 15 | 34% |
| Blocked | 11 | 25% |

Those 11 are exactly the 11 data problems planted in the dataset, found without being told where to look.

---

## Repository

```
config/price_book.json      All policy: rates, discounts, approval thresholds, escalation rules
dealdesk.py                 Pricing, validation, approval routing — the only copy of the logic
quote_engine.py             CLI; the three-way decision; order form PDFs
approval_check.py           Calibration: how approval workload lands across approvers
generate_data.py            Builds the synthetic dataset, problems included
refresh_dates.py            Re-anchors demo dates so the 3-Day Rule stays legible
build_date_update.py        Converts a HubSpot export into a Record ID-keyed update file
data/                       Import files, the issue answer key, run outputs
docs/                       Setup guide, the Deal Desk Playbook, the decisions log
output/order_forms/         Generated PDFs
```

### Running it

```bash
pip install -r requirements.txt

python quote_engine.py --list                  # quotable deals
python quote_engine.py --all --book v1         # evaluate all 44
python quote_engine.py "Copperline" --book v1  # one deal, generates a PDF if it passes
python quote_engine.py "Marbleway" --book v1   # a blocked deal
python quote_engine.py "Riverstone" --book v1  # one pending approval
python approval_check.py                       # approval workload distribution
```

No HubSpot credentials needed — the scripts read the CSV mirror of the portal in `data/`.

---

## Design decisions worth reading

`docs/decisions.md` records every judgment call and why. A few:

- **The approval matrix was recalibrated after testing it.** The first draft sent 36% of quoted deals to the CEO. At a startup that makes the CEO a bottleneck on a third of all deals. Adjusted thresholds brought it to 16%. An approval matrix should escalate the risky minority, not the majority — and the only way to know which you built is to run it against real deals.
- **Approve and notify are separate rules.** A 12-month commitment is gated by Finance on credit risk; the CEO is notified but doesn't block. Collapsing the two is why approval processes get slow and then get bypassed.
- **Slow deals get a documented pause, not a longer ladder.** Capped at 14 days, one consecutive use, reason and return date on the record, still visible in the daily digest. The test of an exception process is whether it leaves a trail.
- **Designed within the free tier's 10-property limit.** Which forced a rule worth keeping: store what people enter, compute what you can derive.
- **The price book is versioned.** GPU rates move weekly, so deals are validated against the book they were quoted on rather than today's.

---

## Documentation

| Document | What's in it |
|---|---|
| `docs/deal_desk_playbook.md` | The policy: price book, quote rules, approval matrix, stage exit criteria, the 3-Day Rule, the finance handoff checklist |
| `docs/day1_hubspot_setup.md` | Pipeline design, custom properties, import order |
| `docs/day3_quote_engine.md` | How the engine works and what it caught |
| `docs/decisions.md` | Every judgment call, with reasoning |

---

*Built as a portfolio project. Demo GPU Cloud, Inc. and all customers, prices and figures are fictional.*
