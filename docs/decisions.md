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
**Day 3.** Three outcomes, not two: BLOCKED, PENDING APPROVAL, APPROVED. The tempting design is for the engine to auto-correct a CRM amount that doesn't match the price book. It refuses, because a mismatch means either somebody negotiated a price that was never recorded or somebody mistyped a number, and those need opposite fixes. Guessing which one produces a confident, wrong contract. On the v1 book the engine blocked 11 of 44 quoted deals — exactly the 11 problems planted in the dataset, found without being told where to look.

### 13. Pricing and routing live in one module, not in each script
**Day 3.** `dealdesk.py` holds pricing, validation and approval routing; `quote_engine.py` and `approval_check.py` both import it, and all policy values come from `config/price_book.json`. Before this, the approval logic existed twice and could silently drift. Policy as code only works if there is exactly one copy of the policy.

### 14. The order form shows the discount math, not just the total
**Day 3.** The pricing table walks from list rate through the term discount and the negotiated discount to the effective rate. A customer who can check the arithmetic doesn't open a pricing dispute; a customer handed only a total has to take it on trust.

<!-- Add your own entries below, same format: title, day, reasoning. -->
