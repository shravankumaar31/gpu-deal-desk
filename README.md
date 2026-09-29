# GPU Cloud Deal Desk

**A working quote-to-cash deal desk for a GPU cloud company — built in HubSpot, enforced in Python.**

At a small GPU infrastructure company, one person holds together everything that makes a deal close: contract tracking, quote prep, CRM hygiene, customer follow-up, invoicing coordination. This is that job, built as a system — with the rule that **nothing sits for three days** enforced in code rather than remembered.

All data is synthetic. List rates are calibrated to public GPU cloud pricing; the company, customers and deals are fictional.

---

## Four decisions that shaped it

Any competent build produces working scripts. These are the calls that took judgment, including the ones I got wrong first.

**The quote engine refuses to fix a price it knows is wrong.**
Three deals have a CRM amount that disagrees with the price book. The engine computes the correct figure and then declines to write it, because a mismatch means either somebody negotiated a price that was never recorded or somebody mistyped a number — and those need opposite fixes. Auto-correcting picks one silently and produces a contract that looks finished and is wrong. This is the job description's *you do not guess on a customer contract*, as code.

**My first approval matrix sent 36% of deals to the CEO.**
At a twenty-person company that makes the CEO a bottleneck on a third of all business. I only found out by running the matrix against all 44 quoted deals and looking at the distribution. Raising the value threshold and moving twelve-month commitments to a Finance credit review brought it to 16%. An approval matrix should escalate the risky minority — and the only way to know which one you built is to test it.

**My pause rule was enforced in form and bypassable in one command.**
Deals can be paused once, for up to 14 days, with a reason and a return date. The first version deleted the pause record on release, so anyone could unpause and immediately re-pause, resetting the counter. I found it by trying to break my own rule. The counter now survives release and only resets when the contract has actually moved. Exception processes are easy to write, easy to bypass, and the bypass is usually invisible.

**An import reported success and created 41 empty records.**
Every company came through with a domain and nothing else — no name, no employee count. The row count was exactly right, so nothing looked wrong until I opened a record. The PO-required rule keys off employee count, so a core business rule had no data behind it. A row count is not a data quality check, and this is the argument for a scheduled audit existing at all.

All 25 are in [`docs/decisions.md`](docs/decisions.md).

---

## What it does

| The job | What's built | Result |
|---|---|---|
| Prep quotes and order forms | `quote_engine.py` — prices from a versioned price book, generates order form PDFs | 16 of 44 quoted deals cleared policy |
| Don't guess on a customer contract | Three outcomes: BLOCKED, PENDING APPROVAL, APPROVED | 10 deals blocked rather than quoted wrong |
| Track contracts and signatures | Contract Status, a 6-stage pipeline with exit criteria | 10 contracts tracked, blocker named on each |
| Nothing sits for three days | `contract_tracker.py` — escalation ladder, documented pauses, follow-up logging | 5 contracts needing action, money at risk quantified |
| Own CRM data quality | `hygiene_audit.py` — 9 rules across deals, contacts, companies | 23 findings on the first run; portal went 90.6% → 92.3% clean |
| Coordinate invoicing with finance | Handoff checklist enforced on every won deal | 11 of 17 invoice-ready ($4.5M); 6 blocked ($2.3M) |
| Automate the repetitive parts | All policy in one JSON file; every tool reads from it | Change a threshold once, every tool changes |

> **Figures are from a run on 29 September 2026.** They move as the demo data ages and as records get fixed — the 3-Day Rule digest changes daily by design. Run the commands below for current numbers.

---

## The shape of it

A quote engine that can only do three things:

| Outcome | When | Output |
|---|---|---|
| **BLOCKED** | Data is missing or contradictory | A list of problems. No document. |
| **PENDING APPROVAL** | Policy requires a named approver | The approvers and the reasons. No order form. |
| **APPROVED** | Within policy | An order form PDF |

The same principle runs through the hygiene audit. Of the 23 findings on its first run, exactly **one** was safe to fix automatically — a duplicate company record with no deals and no contacts, where nothing referenced it. The other 22 went to a human, because no rule can know whether a past close date means the deal slipped or the rep forgot. A tool that fixed all 23 would be faster and wrong.

And through the 3-Day Rule: the clock resets on **action**, not on the contract moving. A customer's legal team can take two weeks; nobody gets to ignore the deal for two weeks.

---

## Running it

```bash
pip install -r requirements.txt

# Quote engine
python3 quote_engine.py --all --book v1          # evaluate all 44 quoted deals
python3 quote_engine.py "Marbleway" --book v1    # blocked — no contract term
python3 quote_engine.py "Riverstone" --book v1   # pending — 3 rules fire at once
python3 quote_engine.py "Copperline" --book v1   # approved — writes a PDF

# Contract tracker — the 3-Day Rule
python3 contract_tracker.py                      # today's digest
python3 contract_tracker.py --followup "Starling" --note "Emailed their legal team"
python3 contract_tracker.py --pause "Bramblecode" \
        --reason "Customer procurement cycle" --until 2026-10-06

# Hygiene audit
python3 hygiene_audit.py                         # full audit + score
python3 hygiene_audit.py --handoff               # finance handoff
python3 hygiene_audit.py --verify                # findings vs. the answer key
python3 hygiene_audit.py --fix                   # apply the AUTO bucket

# Keep the mirror honest
python3 sync_from_hubspot.py <deals_export.csv>  # after fixing records in HubSpot
```

No HubSpot credentials needed — the scripts read a CSV mirror of the portal in `data/`.

---

## How it's put together

```
config/price_book.json      All policy: rates, discounts, approval thresholds, escalation rules
dealdesk.py                 Pricing, validation, approval routing — one copy of the logic
quote_engine.py             Three-way decision + order form PDFs
contract_tracker.py         The 3-Day Rule: digest, escalation, pauses, follow-ups
hygiene_audit.py            Portal-wide data quality + finance handoff
approval_check.py           How approval workload distributes across approvers
sync_from_hubspot.py        Rebuild the mirror from a HubSpot export
generate_data.py            Builds the synthetic dataset, problems included
refresh_dates.py            Re-anchors demo dates so the 3-Day Rule stays legible
data/                       Import files, the issue answer key, run outputs
docs/                       Setup guide, playbook, decisions log
output/order_forms/         Generated PDFs
```

Every threshold, rate and rule lives in `config/price_book.json`, and every tool reads from it. Change the discount ceiling once and the quote engine, the calibration report and the playbook all agree. Policy as code only works when there is exactly one copy of the policy.

**The dataset is seeded with 40 known problems** (`data/issues_manifest.csv`), and no tool ever reads that file during a normal run. `hygiene_audit.py --verify` reconciles findings against it afterwards — which is the only honest way to know the rules work rather than assuming they do.

---

## Built within the free tier

HubSpot's free tier allows 10 custom properties. The first design used 19. Cutting to 10 forced a rule worth keeping: **store what people enter, compute what you can derive.** Rates, PO requirements, customer segment and billing contact are all derived in code rather than stored, so there are fewer values that can go stale.

Two places where the constraint shows, and what I'd do with a budget:
- **Pause state** lives in `data/pauses.json` rather than on the deal record, so it's visible only to whoever runs the script. On a paid tier it would be deal properties.
- **The engine's verdict** can't be written back, so the HubSpot views filter on inputs (discount, empty term) rather than showing the actual decision. On a paid tier an "Approval Status" property would close that loop.

Knowing where a tool stops and code takes over is most of the work.

---

## Documentation

| Document | What's in it |
|---|---|
| [`docs/deal_desk_playbook.md`](docs/deal_desk_playbook.md) | The policy: price book, quote rules, approval matrix, stage exit criteria, the 3-Day Rule, the finance handoff checklist |
| [`docs/decisions.md`](docs/decisions.md) | All 25 judgment calls, with reasoning |
| [`docs/project_plan.md`](docs/project_plan.md) | What was built, day by day |
| [`docs/day1_hubspot_setup.md`](docs/day1_hubspot_setup.md) | Pipeline design, custom properties, import order |
| [`docs/day3_quote_engine.md`](docs/day3_quote_engine.md) | How the engine works and what it caught |
| [`docs/day4_contract_tracker.md`](docs/day4_contract_tracker.md) | The 3-Day Rule and the pause rules |
| [`docs/day5_hygiene_audit.md`](docs/day5_hygiene_audit.md) | The audit, the scoring, the finance handoff |

---

*Portfolio project. Demo GPU Cloud, Inc. and all customers, prices and figures are fictional.*
