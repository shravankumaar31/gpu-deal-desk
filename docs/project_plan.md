# Project Plan

**The 3-Day Rule: A Quote-to-Cash Deal Desk for a GPU Cloud**
Built for the Hyperbolic Labs GTM operations role.

Two tracks run in parallel every day: **HubSpot** (the system of record, where the work shows) and **code** (the automation on top). The code is already written for Days 1–3; your work is the HubSpot side plus the judgment calls.

---

## Status at a glance

| Day | What it delivers | Code | HubSpot |
|---|---|---|---|
| 1 | Pipeline, properties, data loaded | Done | **Done** |
| 2 | Price book, approval matrix, playbook | Done | n/a |
| 3 | Quote engine + order forms | Done | Done |
| 4 | Contract tracker + 3-day stale alert | Done | **← you are here** |
| 5 | Hygiene audit + finance handoff | Not started | Not started |
| 6 | README, screenshots, Loom, outreach | Not started | Not started |

Repo: `github.com/shravankumaar31/gpu-deal-desk` · Local: `~/gpu-deal-desk`

---

## Day 1 — Foundation ✅ complete

- [x] Free HubSpot account
- [x] "GPU Sales Pipeline" with 6 stages and exit criteria
- [x] 10 custom deal properties (the free-tier limit)
- [x] Imported 41 companies, 133 contacts, 60 deals
- [x] Saved views: *Contracts in Flight*, *Stale Contracts (3-Day Rule)*
- [x] Refreshed the demo dates so 5 deals read as stale, not 10

---

## Day 2 — Policy ✅ complete

- [x] Versioned price book (v1 legacy, v2 at today's public GPU rates)
- [x] Approval matrix, recalibrated from 36% CEO-approved down to 16%
- [x] Approve vs notify split as separate rules
- [x] Documented-pause rule for legitimately slow deals
- [x] `docs/deal_desk_playbook.md` v1.3
- [x] `docs/decisions.md`, 14 entries
- [x] Pushed to GitHub

---

## Day 3 — Quote engine ← **current**

The engine is built and tested. Three outcomes: **BLOCKED**, **PENDING APPROVAL**, **APPROVED**. On the v1 price book it blocked 11 of 44 quoted deals — exactly the 11 problems planted in the dataset.

### What's left, all in HubSpot (~30 min)

- [ ] **Saved view: Blocked — Cannot Quote** — Deal Stage is Quote Sent / Contract Out / Closed Won, and Contract Term is empty
- [ ] **Saved view: Needs Approval — Discount** — Negotiated Discount greater than 0.10
- [ ] **Saved view: Needs Approval — Non-Standard Terms** — Non-Standard Terms is known
- [ ] **Attach an order form to its deal.** Open *Copperline Finance AI - 16x B200 - 3-Month Reserved*, upload the PDF from `output/order_forms/`, set Contract Status to Drafting and Last Contract Update to today
- [ ] **Log an approval decision.** On *Riverstone Retail AI - 64x B200 - 12-Month Reserved*, add a Note recording why it's held: 12% discount over the 10% ceiling, $1.54M TCV, 12-month term, Head of GTM and Finance required, CEO notified
- [ ] Screenshot all of it into `docs/screenshots/`

If the free tier caps your saved views, build the first two and skip the third.

### Optional, if you want to see the engine run

```bash
cd ~/gpu-deal-desk
python3 quote_engine.py --all --book v1      # 15 approved / 18 pending / 11 blocked
python3 quote_engine.py "Marbleway" --book v1  # blocked
python3 quote_engine.py "Riverstone" --book v1 # pending approval
python3 quote_engine.py "Copperline" --book v1 # approved, writes a PDF
```

---

## Day 4 — Contract tracker and the 3-Day Rule

The centerpiece. The job description says *nothing sits for three days*; this turns that into a running system.

**Code:** a tracker that reads deals in Contract Out, calculates days since the last contract movement, applies the escalation ladder (day 3 follow-up, day 5 Head of GTM, day 10 CEO), honors documented pauses, and posts a digest naming each deal, its blocker, its owner, and the days stuck. Delivered to a free Slack workspace via webhook, with a plain-text fallback.

**HubSpot:** a Note logged on one stale deal showing the follow-up actually happening, and a pause recorded on another to demonstrate the exception path.

**You decide:** whether the digest goes out daily or twice daily, and whether paused deals appear in the main list or a separate section.

---

## Day 5 — Hygiene audit and the finance handoff

**Code:** a rules engine that audits every deal, contact and company against the playbook — past close dates, missing associations, amounts that don't match the GPU math, duplicate companies, Closed Won without a countersigned contract, missing PO numbers — then scores the portal, auto-fixes only what is unambiguously safe, and queues the rest for a human. Plus an invoice-ready handoff summary for finance on won deals.

**HubSpot:** merge the duplicate company, fix two or three flagged records by hand, then re-run the audit to show the score move.

**The point:** it should find the same problems as `data/issues_manifest.csv` without ever reading it.

---

## Day 6 — Package and ship

- [ ] Finish the README: the JD-to-feature table, screenshots, the headline numbers
- [ ] Record a 3-minute Loom: the stale-contract view, one blocked quote, one approval, the audit
- [ ] Clean the repo and write the final decisions entries
- [ ] Send it — the Loom link plus two or three sentences, direct to the hiring team, not only through the application form

---

## What to say about it

Three things carry the most weight in an interview:

**The engine blocks rather than guesses.** It could auto-correct a CRM amount that disagrees with the price book. It refuses, because a mismatch means either an unrecorded negotiation or a typo, and those need opposite fixes. That is the JD's *you do not guess on a customer contract*, written as code.

**The approval matrix was calibrated against real deals.** The first draft sent 36% of quoted deals to the CEO. Testing it and adjusting brought that to 16%. An approval process should escalate the risky minority, not the majority.

**The free tier's 10-property limit shaped the design.** Store what people enter, compute what you can derive. Designing inside a constraint instead of complaining about it is the whole job.

---

## Where things live

| | |
|---|---|
| `config/price_book.json` | All policy. Change it here and every tool changes. |
| `dealdesk.py` | Pricing, validation, approval routing — one copy of the logic |
| `quote_engine.py` | The three-way decision and order form PDFs |
| `docs/deal_desk_playbook.md` | The policy in prose |
| `docs/decisions.md` | Every judgment call and why — your interview script |
| `data/issues_manifest.csv` | The answer key. Never imported. |
