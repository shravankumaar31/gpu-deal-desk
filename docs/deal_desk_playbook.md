# Deal Desk Playbook

**Project:** The 3-Day Rule: A Quote-to-Cash Deal Desk for a GPU Cloud
**Version:** 1.3 (September 2026)
**Machine-readable version:** `config/price_book.json`. The quote engine (Day 3) and the hygiene audit (Day 5) read their rules from that file, so a policy change is made in one place.

> All discounts, thresholds, and approvers in this playbook are synthetic policy written for a portfolio project. The v2 list rates are calibrated to Hyperbolic's public on-demand rates (hyperbolic.ai/marketplace, checked September 2026).

---

## 1. What the deal desk owns

The deal desk makes sure every deal is priced correctly, approved by the right person, signed, and handed to finance cleanly, and that nothing sits for more than three days along the way.

It owns: quotes and order forms, the approval process, contract status tracking, CRM data quality on deals, and the handoff to finance for invoicing.

It does not own: negotiating price with the customer (that's the AE), legal redlines (outside counsel or the CEO), or invoicing itself (finance).

---

## 2. Price book

### Active: v2 (all new quotes from September 21, 2026)

| GPU | List rate per GPU-hour |
|---|---|
| H100 SXM | $3.19 |
| H200 | $3.99 |
| B200 | $5.99 |

| Term | Hours billed | Term discount |
|---|---|---|
| On-Demand | Usage (estimated at 730/month for quoting) | 0% |
| 1-Month Reserved | 730 | 5% |
| 3-Month Reserved | 2,190 | 10% |
| 6-Month Reserved | 4,380 | 15% |
| 12 months or longer | Private Cloud tier | Custom pricing |

**Quote formula:**
`Total Contract Value = GPU Count × Term Hours × List Rate × (1 − Term Discount) × (1 − Negotiated Discount)`

The **term discount** is automatic and doesn't need approval. The **negotiated discount** is anything the AE gives on top of it, and that's what the approval matrix controls.

### Legacy: v1 (grandfathered)

Every deal already in HubSpot was quoted on the v1 price book (H100 SXM $2.20, H200 $2.80, B200 $3.90, same term discounts, with a 20% discount for 12-month terms). Those prices are honored for the life of the quote or contract. The Day 5 amount check validates existing deals against v1, not v2.

**Why keep two price books:** GPU prices move fast. Hyperbolic refreshes its on-demand rates weekly from supplier prices, and its public H100 rate rose several times during 2026. A deal desk has to know which price book a quote was written on; otherwise every price change makes older deals look wrong.

---

## 3. Quote rules

| Rule | Standard |
|---|---|
| Quote validity | 7 days. Rates refresh weekly, so a longer validity period risks selling below cost. |
| Minimum reservation | 8 GPUs (one node) |
| Reservation increments | Multiples of 8 GPUs |
| Payment terms | Net 30 |
| Uptime SLA | 99.5% |
| Price book | Always the active version on the date the quote is created |

Anything outside these standards counts as a **non-standard term** and goes through the approval matrix.

---

## 4. Approval matrix

Each deal is checked against every rule below. If more than one rule applies, **every** listed approver signs off, and the deal's final approver is the most senior one on the list. Approver ranks, from least to most senior: Deal Desk (automatic) → Head of GTM → Finance → Infra / Supply Lead → CEO.

### Negotiated discount (on top of the term discount)

| Discount | Approver |
|---|---|
| 0–10% | Deal Desk (automatic) |
| Over 10%, up to 20% | Head of GTM |
| Over 20% | CEO |

### Total contract value (TCV)

| TCV | Approver |
|---|---|
| Up to $500K | Deal Desk (automatic) |
| Over $500K, up to $2M | Head of GTM |
| Over $2M | CEO |

### Non-standard terms

| Term | Approver(s) | Why |
|---|---|---|
| Net 60 payment terms | Finance | Cash flow and credit risk |
| Custom uptime SLA above 99.5% | Infra / Supply Lead + CEO | The capacity comes from supplier partners, so the SLA has to be backed by the supplier's own SLA |
| Capacity reservation guarantee | Infra / Supply Lead | Never sell reserved capacity that hasn't been secured on the supply side |
| Price lock beyond the contract term | Finance + CEO | Supplier costs change weekly; a lock can turn a profitable deal into a loss |
| Early termination clause | CEO | Breaks the revenue commitment the reserved price was based on |
| Any other non-standard term | CEO | Default when a term isn't covered above |

### Contract length

| Term | Approver | Why |
|---|---|---|
| 12 months or longer | Finance approves; CEO notified | The gate is credit risk, which Finance can test objectively. At a company this small the CEO still wants to know about every year-long commitment, so they're notified rather than asked to approve. |

### Calibrating the matrix

The first draft sent **36% of quoted deals to the CEO**. The two biggest causes were a $1M TCV threshold and routing every 12-month term to the CEO. At a startup, that makes the CEO the bottleneck on a third of all deals, which defeats the purpose of having a deal desk.

Version 1.1 raised the CEO's TCV threshold to $2M and moved 12-month terms to a Finance credit review. Results against the 44 quoted deals in HubSpot:

| Final approver | Draft 1 | v1.1 |
|---|---|---|
| Deal Desk (automatic) | 41% | 50% |
| Head of GTM | 18% | 16% |
| Finance | 2% | 16% |
| Infra / Supply Lead | 2% | 2% |
| CEO | 36% | 16% |

**Best practice:** an approval matrix should escalate the risky minority of deals, not the majority. Run it against real deals before rolling it out, and recalibrate if one approver gets flooded. The routing for each deal is in `data/approval_routing.csv`, and the first draft's routing is kept in `data/approval_routing_draft1.csv`.

### Approval rules of the road

- Approvals are logged in writing (in Slack or on the deal record). A verbal "looks fine" doesn't count.
- An approval expires with the quote, after 7 days. A re-quote needs a new approval.
- If the deal changes after approval (GPU count, term, discount, or terms), the approval is void.
- A notification is not an approval. Notified people can weigh in, but the deal isn't held waiting on them.
- The deal desk never guesses on contract language. If a term isn't covered by this playbook, it goes to the CEO.

---

## 5. Pipeline stages and exit criteria

| Stage | Exit criteria (all must be true to leave the stage) |
|---|---|
| Discovery | Workload identified; GPU type and rough count known |
| Technical Eval | Customer has validated performance; decision-maker identified |
| Quote Sent | Quote approved under section 4; Contract Term and Billing Frequency set |
| Contract Out | Order form sent; Contract Status is tracked; the account has a Finance Manager contact |
| Closed Won | Contract Status = Countersigned; PO Number captured if the company has 1,000+ employees |
| Closed Lost | Closed Lost Reason recorded |

---

## 6. The 3-Day Rule

Every deal in **Contract Out** has its **Last Contract Update** date refreshed whenever the contract moves: redlines received, legal feedback, a signature request sent, or a follow-up to the customer.

| Days since last update | Action |
|---|---|
| 0–2 | No action |
| 3 | Deal desk follows up with the customer and flags the deal in the daily Slack digest |
| 5 | Escalate to the Head of GTM with the blocker named (signature, redlines, PO, or legal) |
| 10 | Escalate to the CEO; decide whether to push, re-quote, or close the deal as lost |

### Documented pause

Some delays are legitimate. An enterprise legal team taking two weeks on redlines is normal, and a flat ladder would put that deal in front of the CEO while nothing is wrong. The deal desk can therefore **pause the clock**, but only on the record:

| Rule | |
|---|---|
| Allowed reasons | Customer legal review · Customer procurement cycle · Customer budget approval · Capacity confirmation with supplier |
| Required | A reason, an expected return date, and both logged on the deal record |
| Maximum | 14 days, and one consecutive pause — a second pause on the same deal escalates instead |
| On return | The clock restarts at day 0 |

A paused deal still appears in the daily digest, marked as paused with its return date, so a pause hides nothing. When the return date passes with no movement, the deal re-enters the ladder at day 5 rather than day 3, because it has already had its grace period.

**Why a pause rather than a longer ladder for legal deals.** A blocker-specific ladder sounds more accurate but asks everyone to remember four ladders instead of one, and reps learn to label anything slow "legal review." A pause keeps one rule, makes the exception visible and time-boxed, and puts the decision on a named person rather than on a category.

A follow-up counts as an update. The rule isn't "the contract must move every 3 days"; it's "someone must act on it every 3 days."

---

## 7. Handoff to finance (on Closed Won)

A deal isn't handed to finance until every item below is complete. Missing items block the invoice, and the deal desk chases them, not finance.

- Contract Status = Countersigned, with the signed PDF attached to the deal
- Price book version and final rate per GPU-hour recorded
- GPU type, GPU count, contract term, and start date confirmed
- Billing frequency and payment terms confirmed (Net 30 unless Finance approved otherwise)
- Billing contact (Finance Manager) on the company record
- PO number captured if the company has 1,000+ employees
- Approval record attached for any non-standard term
- Fulfillment Status set to Provisioning

---

## 8. Changing this playbook

A policy change goes into `config/price_book.json` first. Then re-run `python approval_check.py`, check the routing mix, update this document, and log the reason in `docs/decisions.md`.
