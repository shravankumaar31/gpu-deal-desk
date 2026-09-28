# Day 4: The Contract Tracker

**The 3-Day Rule, running.** The job description says *nothing sits for three days*. This turns that sentence into a system that reads the contract pipeline every morning, works out what has stalled, names who it's waiting on, and escalates on a fixed ladder.

---

## Running it

```bash
python3 contract_tracker.py            # today's digest
python3 contract_tracker.py --slack    # also post it to Slack
python3 contract_tracker.py --pauses   # list pauses, active and released

python3 contract_tracker.py --pause "Bramblecode" \
        --reason "Customer procurement cycle" --until 2026-10-06
python3 contract_tracker.py --unpause "Bramblecode"

python3 contract_tracker.py --followup "Starling" \
        --note "Emailed their Head of Legal; offered a call Thursday."
```

`--followup` is the action the digest is asking for. It records what you did in
`data/followups.csv` and sets Last Contract Update to today, so the deal drops
off tomorrow's list. **The clock resets on action, not on the contract moving** —
a customer's legal team can take two weeks, but nobody gets to ignore the deal
for two weeks. `--note` is required: an unlogged follow-up leaves no trail, and
the trail is the point.

Today's digest:

```
CONTRACT DESK — THE 3-DAY RULE   Sun 27 Sep 2026
====================================================================
4 need action · 1 paused · 5 healthy   ($378,507 at risk)

── ESCALATE TO CEO — 10+ days ── (push, re-quote, or close lost)
   13d  Starling Translate - 128x H100 SXM - 1-Month Reserved
        Legal Review · waiting on customer legal · in legal review · $175,761
   11d  Hollowpeak Materials - 32x H200 - 1-Month Reserved
        Legal Review · waiting on customer legal · in legal review · $60,273

── ESCALATE TO HEAD OF GTM — 5+ days ── (blocker named below)
    9d  Juniper Protein - 16x H100 SXM - On-Demand
        Out for Signature · waiting on customer signatory · awaiting customer signature · $24,411
    8d  Altitude Mapping - 64x H200 - 1-Month Reserved
        Legal Review · waiting on customer legal · in legal review · $118,061

── PAUSED — documented hold ── (visible, not hidden)
    5d  Bramblecode - 256x H100 SXM - 3-Month Reserved
        paused until 2026-10-06 · Customer procurement cycle · $999,060
```

Each run also writes `data/stale_report.csv`, one row per contract-stage deal.

---

## What makes it a tool rather than a filter

A saved HubSpot view can already list deals that haven't moved in three days. Three things this adds:

**It names who you're waiting on.** *Legal Review* becomes "waiting on customer legal"; *Out for Signature* becomes "waiting on customer signatory". A list of stale deals tells you something is wrong. A list that names the blocker tells you what to do next, which is the difference between a report and a follow-up.

**It sorts by the ladder, not by date.** Two deals at 11 and 13 days both belong on the CEO's desk; a deal at 5 belongs with the Head of GTM. Grouping by who needs to act means the digest can be read top-down and stopped at your own row.

**It closes its own loop.** The digest names a deal, `--followup` records the action, and the deal drops off the next run. Most "stale deal" reports stop at naming the problem, which is why people stop reading them.

**It shows the money at risk.** "$378,507 at risk" is the line that gets the digest read. Deal count alone doesn't distinguish a stalled $24K on-demand order from a stalled $999K reservation.

---

## Documented pauses

The pause rules from the playbook are enforced here rather than trusted:

| Rule | Behavior |
|---|---|
| Reason must be on the allowed list | A free-text reason is rejected, with the allowed list printed |
| Maximum 14 days | A longer hold is refused — "a longer hold escalates instead of pausing" |
| One consecutive pause | A second pause is refused unless the contract has actually moved |
| Reason and return date required | `--pause` without both is refused |
| A pause hides nothing | Paused deals still appear in the digest, in their own section, with the return date |
| Expired pause | The deal re-enters at the **day-5** rung, not day 3 — it has already had its grace period |

**The subtle one is the consecutive-pause counter.** The first version deleted the pause record on `--unpause`, which meant anyone could release a pause and immediately re-pause the same deal, resetting the count and defeating the rule. Now the record survives release, and the counter only resets when Last Contract Update proves the contract actually moved.

That is the general shape of the problem with exception processes: the rule is easy to write and easy to bypass, and the bypass is usually invisible. Worth checking for in any approval or exception workflow you inherit.

---

## Where pause state lives, and why that's a compromise

Pauses are stored in `data/pauses.json`, not on the HubSpot deal record. That is a limitation, not a design choice — all 10 free-tier custom properties are already used. On a paid tier the pause reason and return date would be deal properties, so the pause would be visible to anyone opening the deal instead of only to whoever runs the script.

A side file is the right call *given the constraint*, and the wrong one without it. State that belongs to a record should live on the record.

---

## Scheduling it

The digest is meant to arrive, not to be requested. On a Mac:

```bash
crontab -e
# 8:30am on weekdays
30 8 * * 1-5 cd ~/gpu-deal-desk && /usr/bin/python3 contract_tracker.py --slack
```

For Slack, create a free workspace, add an Incoming Webhook to a `#deal-desk` channel, and set `SLACK_WEBHOOK_URL` in your environment. Without it the digest just prints, which is enough to demo.

---

## Next: Day 5

The hygiene audit and the finance handoff. It should find the remaining planted problems — duplicate companies, unassociated contacts, Closed Won without a signature, missing PO numbers — and score the portal, without ever reading the answer key.
