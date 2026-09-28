# Decisions Log

Every judgment call made while building this deal desk, and why. Written as I went, not reconstructed afterward.

---

### 1. Post-sale status is a property, not a pipeline stage
**Day 1.** Provisioning and invoicing happen after a deal is won. Adding them as pipeline stages would stretch every sales cycle measurement and distort win rate. They live in the Fulfillment Status property instead.

### 2. "Last Contract Update" is a custom date field
**Day 1.** HubSpot calculates its own last-activity date from logged emails, calls, and meetings, and that value can't be set by an import. A deal desk also needs a narrower signal: when did the *contract* last move? That's the date the 3-Day Rule watches.

### 3. Designed within the free tier's 10-property limit
**Day 1.** The first design used 19 custom properties. Cutting to 10 forced a rule worth keeping: store what people enter, compute what you can derive. Rates, PO requirements, customer segment, and the billing contact are all derived in code instead of stored. Fewer stored fields means fewer values that can go stale.

### 4. Billing contact is identified by job title, not a dedicated field
**Day 1.** The account's contact with the title "Finance Manager" is the billing contact. This keeps the information on the contact record where finance would look for it, and it saves a custom property.

### 5. The duplicate company was given a second domain
**Day 1.** HubSpot deduplicates companies by domain on import. A duplicate with the same domain would have been silently merged, which would have hidden the problem the hygiene audit is supposed to catch.

### 6. Two price books, with old deals grandfathered
**Day 2.** GPU prices move constantly; Hyperbolic refreshes its rates weekly from supplier prices, and its public H100 rate rose more than once during 2026. So the price book is versioned. Deals already in HubSpot are validated against the v1 rates they were quoted on; new quotes use v2. Without versioning, every price change would make older deals look mispriced.

### 7. The approval matrix was recalibrated after testing it
**Day 2.** The first draft routed 36% of quoted deals to the CEO, mostly because of a $1M TCV threshold and sending every 12-month term to the CEO. At a startup that turns the CEO into a bottleneck on a third of all deals. Raising the CEO threshold to $2M and moving 12-month commitments to a Finance credit review brought CEO approvals down to 16%. An approval matrix should escalate the risky minority, not the majority, and the only way to know which you've built is to run it against real deals.

---

### 8. Approve versus notify are separate rules
**Day 2.** The 12-month approval rule was split: Finance approves, and the CEO is notified. The actual gate on a long commitment is credit risk, which Finance can test objectively, so making the CEO an approver adds delay without adding information. But at a 20-person company the CEO genuinely wants to know about every year-long commitment, and a rule people quietly bypass is worse than no rule. Separating "who blocks the deal" from "who needs to know" satisfies both without slowing the deal down. Seven of the 44 quoted deals now trigger a CEO notification while keeping CEO approvals at 16%.

### 9. The demo dataset re-anchors its own dates
**Day 2.** The data was generated with dates relative to a fixed "today," so every day that passed pushed another Contract Out deal past the 3-day threshold. Six days in, all 10 looked stale and the 3-Day Rule demo stopped being legible. `refresh_dates.py` shifts every date forward by the elapsed days and emits a HubSpot update file, so "5 stale contracts" stays true whenever the project is demoed. Any dataset built for a live demo needs this; otherwise it quietly rots.

### 10. Deals have no natural key, so updates require a Record ID round-trip
**Day 2.** HubSpot dedupes contacts on email and companies on domain, but deals have no natural unique identifier — the import tool accepts only Record ID. The date refresh therefore needs an export-join-import round-trip rather than a straight update. The export also proved the point: two deals share the name "Meridian Vision Systems - 32x B200 - 6-Month Reserved," so even matching on deal name would have been ambiguous. `build_date_update.py` reads the export and emits a Record ID-keyed file. Worth knowing before promising anyone a bulk deal update.

### 11. Slow deals get a documented pause, not a longer ladder
**Day 2.** A flat 3/5/10 ladder puts a deal on the CEO's desk when an enterprise legal team takes its normal two weeks on redlines. The alternatives were a ladder that varies by blocker or a pause. The pause won: a blocker-specific ladder asks everyone to remember four ladders instead of one, and reps quickly learn to label anything slow "legal review." A pause keeps one rule, and makes the exception visible — capped at 14 days, one consecutive use, reason and return date on the record, still shown in the daily digest marked as paused. A deal whose pause expires re-enters at day 5, not day 3, since it has already had its grace period. The test of an exception process is whether it leaves a trail; this one does.

### 12. The quote engine blocks rather than guesses
**Day 3.** Three outcomes, not two: BLOCKED, PENDING APPROVAL, APPROVED. The tempting design is for the engine to auto-correct a CRM amount that doesn't match the price book. It refuses, because a mismatch means either somebody negotiated a price that was never recorded or somebody mistyped a number, and those need opposite fixes. Guessing which one produces a confident, wrong contract. On the v1 book the engine blocked 11 of 44 quoted deals and routed another 12 to approval — every one derived from the playbook rules, never from the answer key. The dataset holds 40 planted issues in total; the engine is scoped to the 23 that belong to quoting. The other 17 are stale contracts (Day 4) and post-sale or record-level problems (Day 5). A quote engine that also flagged a duplicate company would be doing another tool's job.

### 13. Pricing and routing live in one module, not in each script
**Day 3.** `dealdesk.py` holds pricing, validation and approval routing; `quote_engine.py` and `approval_check.py` both import it, and all policy values come from `config/price_book.json`. Before this, the approval logic existed twice and could silently drift. Policy as code only works if there is exactly one copy of the policy.

### 14. The order form shows the discount math, not just the total
**Day 3.** The pricing table walks from list rate through the term discount and the negotiated discount to the effective rate. A customer who can check the arithmetic doesn't open a pricing dispute; a customer handed only a total has to take it on trust.

### 15. refresh_dates.py measured from a hardcoded date, and double-shifted the data
**Day 4.** The first version computed its shift from a constant genesis date and rewrote `deals.csv` in place, so every run moved the data again — running it twice in one day silently doubled every gap and turned 5 stale contracts into 3. It now records the current anchor in `data/anchor.json` and shifts from there, so re-running is a no-op. A script that mutates its own input has to be idempotent, or it is a loaded gun.

### 16. The consecutive-pause counter has to survive an unpause
**Day 4.** The pause rule allows one consecutive pause per deal. The first implementation deleted the pause record on `--unpause`, which meant anyone could release a pause and immediately re-pause the same deal, resetting the count to zero. The rule was enforced in form and bypassable in one command. Now the record survives release and the counter only resets when Last Contract Update proves the contract actually moved. Exception processes are easy to write and easy to bypass, and the bypass is usually invisible — worth testing for deliberately rather than trusting the happy path.

### 17. The digest names the blocker, not just the delay
**Day 4.** A saved HubSpot view can already list deals untouched for three days. The tracker adds three things a filter cannot: it translates Contract Status into who you are waiting on ("Legal Review" becomes "waiting on customer legal"), it groups by escalation rung rather than by date so each person can read to their own row and stop, and it totals the money at risk. A list of stale deals says something is wrong; a list that names the blocker says what to do next.

### 18. Pause state lives in a side file, and that is a compromise
**Day 4.** Pauses are stored in `data/pauses.json` rather than on the deal record, because all 10 free-tier custom properties are spent. On a paid tier the reason and return date would be deal properties, visible to anyone opening the deal instead of only to whoever runs the script. Right call given the constraint, wrong call without it — state that belongs to a record should live on the record.

<!-- Add your own entries below, same format: title, day, reasoning. -->
