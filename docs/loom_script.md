# Loom Script — 3 minutes

Record with Loom's free tier. Screen only, or screen with a small camera bubble — the camera helps, since they're hiring a person, not a repo.

**Have open before you start:** HubSpot on the Stale Contracts view · a terminal in `~/gpu-deal-desk` · the Copperline order form PDF · the GitHub repo.

Don't rehearse it to sound polished. Slightly rough and specific beats smooth and generic.

---

## 0:00 — What this is (20 seconds)

> "Hi — I'm Shravan. Your posting describes one person holding together contracts, quotes, CRM hygiene, follow-up and invoicing, with the rule that nothing sits for three days. I built that system for a fictional GPU cloud so you can see how I'd run it. Three minutes."

---

## 0:20 — The 3-Day Rule (50 seconds)

Terminal:

```
python3 contract_tracker.py
```

> "Every morning this reads the contract pipeline. Four contracts need action, one is paused, and it names who we're waiting on — not just that the deal is stale. Legal review means the customer's lawyers; out for signature means a specific person hasn't signed. And it totals the money at risk, which is what gets a digest actually read."

Then:

```
python3 contract_tracker.py --followup "Starling" --note "Emailed their Head of Legal, offered a call Thursday"
python3 contract_tracker.py
```

> "I log the follow-up, the deal drops off. The clock resets on *action*, not on the contract moving — a customer's legal team can take two weeks, but nobody gets to ignore the deal for two weeks."

---

## 1:10 — Quotes that refuse to guess (50 seconds)

```
python3 quote_engine.py "Marbleway" --book v1
```

> "Blocked. No contract term, so it can't be priced — and it won't invent one."

```
python3 quote_engine.py "Riverstone" --book v1
```

> "This one prices fine, but three rules fire: 12% discount over the ceiling, $1.5M value, twelve-month term. Head of GTM and Finance both have to sign, Finance is final, CEO is notified but doesn't block. No order form until those approvals are logged."

```
python3 quote_engine.py "Copperline" --book v1
```

Open the PDF.

> "Within policy, so it generates the order form. The pricing table shows list rate, term discount, negotiated discount, effective rate — a customer who can check the arithmetic doesn't open a pricing dispute."

**Say this part deliberately:**

> "The one I'd point at: three deals have a CRM amount that disagrees with the price book. The engine knows the right number and refuses to fix it — because a mismatch is either an unrecorded negotiation or a typo, and those need opposite fixes. Guessing gives you a contract that looks finished and is wrong."

---

## 2:00 — The audit and the handoff (50 seconds)

```
python3 hygiene_audit.py
```

> "Nine rules across deals, contacts and companies. It found 23 problems — and one was safe to fix automatically. One. Everything else needs a decision the data can't supply."

Switch to HubSpot, show a fixed record, then:

```
python3 hygiene_audit.py
```

> "I fixed four in HubSpot, re-ran, and the score moved from 90.6 to 92.3. The thirteen blockers that remain should stay blocked — two deals are marked Closed Won against contracts nobody has countersigned."

```
python3 hygiene_audit.py --handoff
```

> "Eleven of seventeen won deals are invoice-ready. Six are blocked, worth $2.3 million. Finance gets the clean eleven — the deal desk chases the six. Handing finance six problems is how that handoff turns into a monthly argument."

---

## 2:50 — Close (20 seconds)

Show the repo.

> "The repo has the playbook, the code, and a decisions log — 24 entries on every judgment call, including the ones I got wrong first. One I like: an import reported success and created 41 company records that were completely empty except the domain. The count was right, so nothing looked wrong until I opened one. A row count is not a data quality check.
>
> Happy to walk through any of it. Thanks."

---

## Rules for the recording

- **Don't narrate what's on screen.** Say why it's built that way.
- **Keep the mistakes in.** The double-shifted dates, the bypassable pause rule, the empty import. That's the part that reads as real.
- **One take is fine.** Two at most.
- **Before recording**, run `python3 refresh_dates.py` so the stale contracts look right, and check the digest shows a sensible spread.
