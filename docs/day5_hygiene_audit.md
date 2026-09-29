# Day 5: Hygiene Audit and Finance Handoff

Audits every deal, contact and company against the Deal Desk Playbook, scores the portal, and produces the invoice-ready handoff to finance.

**It never reads the answer key.** Every finding is derived from the playbook rules — which is the only way to know whether the rules actually work.

---

## Running it

```bash
python3 hygiene_audit.py            # full audit + score
python3 hygiene_audit.py --fix      # apply the AUTO bucket
python3 hygiene_audit.py --handoff  # finance handoff only
python3 hygiene_audit.py --verify   # compare findings against the answer key
```

```
HYGIENE AUDIT   Mon 28 Sep 2026
========================================================================
Hygiene score: 90.6%   (212 of 234 records clean)
  23 findings — 13 blocking · 9 to review · 1 auto-fixable
  Deals       70.0%   42 of 60 clean
  Contacts    97.7%   130 of 133 clean
  Companies   97.6%   40 of 41 clean
```

---

## Three buckets, not one list

| Bucket | Meaning | Count |
|---|---|---|
| **BLOCK** | Stops money moving — invoicing or revenue recognition | 13 |
| **REVIEW** | A human has to decide; the audit cannot know the right answer | 9 |
| **AUTO** | Mechanical and reversible — the audit fixes it | 1 |

A flat list of 23 problems tells you nothing about what to do first. The split does, and the ratio is the point: **only one of 23 findings is safe to fix automatically.**

That is not a weak automation story, it is the correct one. Consider what the others would require:

- An **amount mismatch** could be an unrecorded negotiation or a typo — opposite fixes.
- A **past close date** needs the rep's new forecast, which no rule can supply.
- A **duplicate company** carrying deals on both records needs someone to decide which survives.
- A **missing lost reason** exists only in the rep's head.

The single AUTO fix is a duplicate company record with no deals and no contacts attached. Nothing references it, and removing it destroys no information. That is the whole test for "safe to automate": *is it reversible, and does it require zero judgment?*

---

## What it finds

Run `--verify` and it reconciles against `data/issues_manifest.csv`:

| Issue type | Planted | Found | Owner |
|---|---|---|---|
| past_close_date_open_deal | 4 | 4 | audit |
| missing_billing_contact | 4 | 4 | audit |
| amount_mismatch | 3 | 3 | audit |
| unassociated_contact | 3 | 3 | audit |
| missing_contract_term | 2 | 2 | audit |
| missing_lost_reason | 2 | 2 | audit |
| missing_po_number | 2 | 2 | audit |
| won_without_signature | 2 | 2 | audit |
| duplicate_company | 1 | 1 | audit |
| stale_contract | 5 | 0 | Day 4 tracker |
| needs_discount_approval | 6 | 0 | quote engine |
| needs_terms_review | 6 | 0 | quote engine |

All 23 audit-owned issues found; the other 17 belong to tools that already own them. Nothing is double-reported and nothing is missed.

**One rule changed during the build.** The first version only checked for a billing contact on Closed Won deals and found 3 of 4. The playbook makes a billing contact an **exit criterion for Contract Out**, so checking a stage earlier caught the fourth. Exit criteria are worth writing precisely — if they only get enforced at the last stage, they aren't exit criteria, they're a final inspection.

---

## The hygiene score

**Share of records that pass every check.** 90.6% overall; 70% of deals.

The first version summed severity weights and divided by record count, which drove Deals to **0.0/100** on 18 findings across 60 records. Technically a number, useless as a signal, and the kind of metric people quietly stop looking at. "70% of deals are clean" is something anyone can act on and watch move. Severity is reported alongside it rather than mashed into it.

---

## The finance handoff

```
FINANCE HANDOFF
  11 of 17 won deals are invoice-ready ($4,547,325)
  6 blocked ($2,280,539):
     · Thistle Search — missing: Billing contact on the account
     · Larkspur Robotics — missing: PO number captured (if required)
     · Nightjar Video — missing: Billing contact; PO number
     · Pinecurve Health AI — missing: Contract countersigned
     · Orchard LLM — missing: Billing contact on the account
     · Ravenmoor Research — missing: Contract countersigned
```

Each won deal is checked against the seven items in playbook section 7. Deals that pass get an invoice-ready row — GPU config, term, amount, billing frequency, payment terms, billing contact, PO number, start date. Deals that fail get the list of what's missing.

**The deal desk chases the missing items, not finance.** $2.3M of won business cannot be invoiced right now, and two of those deals are marked Closed Won against contracts nobody has countersigned. Handing finance a list of six problems to chase is how the handoff becomes a monthly argument; handing them eleven clean rows and keeping the six is how it doesn't.

Both outputs land in `data/finance_handoff.csv` and `data/hygiene_findings.csv`.

---

## Next: Day 6

Package it. README with the JD-to-feature table, screenshots, a 3-minute Loom, and send it to the hiring team directly rather than only through the application form.
