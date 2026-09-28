# Day 3: The Quote Engine

**What it does:** takes a deal, prices it from the price book, checks it against the approval matrix, and produces one of three outcomes. It never fills a gap with a guess.

| Outcome | Meaning | What comes out |
|---|---|---|
| **BLOCKED** | Data is missing or wrong | A list of problems. No document. |
| **PENDING APPROVAL** | Policy requires a named approver | The approvers and why. No order form. |
| **APPROVED** | Within policy | An order form PDF |

That three-way split is the whole point of the tool, and it's the direct answer to the line in the job description: *you do not guess on a customer contract.* A quote with an invented term, or an amount silently "corrected" to match the math, is worse than no quote, because it looks finished.

---

## Running it

```bash
python quote_engine.py --list                  # what's quotable
python quote_engine.py --all --book v1         # evaluate all 44, write data/quote_run.csv
python quote_engine.py "Copperline" --book v1  # one deal; generates a PDF if it passes
```

Partial names work as long as they match one deal. Order forms land in `output/order_forms/`.

**Which price book to use.** Every deal in the portal was quoted on **v1**, so `--book v1` is the right check for existing deals. Running the same deal on `--book v2` re-quotes it at today's rates and shows the uplift, which is what you'd do at renewal.

---

## The guardrails

### Blockers — the engine refuses to produce anything

| Check | Why it blocks |
|---|---|
| GPU Type, GPU Count or Contract Term empty | The deal cannot be priced at all |
| Billing Frequency empty | Finance cannot invoice it |
| No Finance Manager contact at the account (late-stage deals) | There is nobody to send the invoice to |
| Close date in the past on an open deal | The forecast is wrong and nobody has owned it |
| CRM amount doesn't match the price book (on the book it was quoted on) | Either the amount or the configuration is wrong, and the deal desk doesn't get to decide which |

That last one matters most. The tempting move is to overwrite the CRM amount with the computed figure. The engine refuses, because a mismatch means a human negotiated something that wasn't recorded, or someone typed a number wrong, and those need opposite fixes.

### Approval gates — the engine prices the deal but withholds the document

Discount tier, contract value tier, non-standard terms, and contract length, all read from `config/price_book.json`. The engine names every required approver and the most senior one, lists the reason for each, and separately lists anyone who is only **notified** — a notification is not a gate.

---

## Results against the portal (price book v1)

| Outcome | Count | Share |
|---|---|---|
| Pending approval | 18 | 41% |
| Approved, order form generated | 15 | 34% |
| Blocked | 11 | 25% |

The 11 blocked deals are exactly the 11 data problems planted in the dataset, found without being told where to look:

| Blocker | Count |
|---|---|
| Account has no Finance Manager contact | 4 |
| CRM amount doesn't match the price book | 3 |
| Close date in the past on an open deal | 2 |
| Contract Term empty | 2 |

The full run is in `data/quote_run.csv`, one row per deal with its status, approvers, and blockers.

---

## How the code is arranged

| File | Role |
|---|---|
| `config/price_book.json` | All policy: rates, discounts, thresholds, approvers |
| `dealdesk.py` | Pricing, validation and approval routing — the only place the rules live |
| `quote_engine.py` | CLI, three-way decision, order form PDF |
| `approval_check.py` | Calibration report on how approvals distribute |

Pricing and routing sit in `dealdesk.py` rather than in each script, so the quote engine and the calibration report can't drift apart. Change a threshold in the JSON and every tool changes with it. This is what "policy as code" means in practice, and it's why the playbook and the engine always agree.

---

## What's on the order form

Customer and billing contact, PO requirement, the capacity ordered, a pricing table that shows list rate then each discount then the effective rate, commercial terms, and a signature block. Any approved non-standard term is printed with the name of who approved it.

The footer records which price book and approval route produced the document, and states plainly that it's a portfolio demonstration with fictional customers and prices.

**Showing the discount math rather than just the total is deliberate.** A customer who sees "$3.19 list, 10% term discount, 5% negotiated, $2.73 effective" can check the arithmetic. A customer who sees only a total has to take it on trust, and that's where pricing disputes start.

---

## Next: Day 4

The contract tracker and the 3-day stale alert. It reads the deals in Contract Out, finds any that haven't moved in three days, and posts a digest naming the deal, the owner, the blocker, and the days stuck.
