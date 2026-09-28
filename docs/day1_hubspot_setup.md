# Day 1: HubSpot Foundation

**Project:** The 3-Day Rule: A Quote-to-Cash Deal Desk for a GPU Cloud
**Goal for today:** A HubSpot portal with a GPU-specific sales pipeline, 10 custom deal properties (the free-tier limit), and 60 realistic (and deliberately messy) deals loaded.

---

## 1. Create the HubSpot account

Sign up for the free HubSpot CRM using a personal email. When it asks about your company, call it something like **"Demo GPU Cloud"**. Skip the website-tracking and email-connection steps; this portal holds synthetic data only.

> **Important:** every contact in the dataset is fake. Never email them from HubSpot.

---

## 2. Build the pipeline

In HubSpot, go to **Settings → Objects → Deals → Pipelines**. Rename the default pipeline to **GPU Sales Pipeline** and replace its stages with the following:

| Stage | Win probability | Exit criteria (must be true to move *out* of this stage) |
|---|---|---|
| Discovery | 10% | Workload identified (training, inference, fine-tuning); GPU type and rough count known |
| Technical Eval | 25% | Customer validated performance (POC or benchmark); decision-maker identified |
| Quote Sent | 45% | Quote approved per the approval matrix; Contract Term and Billing Frequency set |
| Contract Out | 70% | Order form sent; Contract Status tracked; Billing Contact captured |
| Closed Won | 100% | Contract Countersigned; PO Number captured if PO Required = Yes |
| Closed Lost | 0% | Closed Lost Reason recorded |

**Best practice: stage exit criteria.** A stage should mean something verifiable, not a rep's feeling. HubSpot can require specific properties when a deal enters a stage; look for the setting that makes properties required in the pipeline's stage editing screen. Depending on your subscription tier, that setting may not be available. If it isn't, the Day 5 hygiene audit enforces the same rules in code, and that's a good story to tell in an interview: "the tool couldn't enforce it, so I built the check."

**Best practice: keep post-sale work out of the sales pipeline.** Provisioning and invoicing happen *after* the deal is won, so they're tracked in the **Fulfillment Status** property rather than as extra pipeline stages. That keeps win rate and sales-cycle math clean.

---

## 3. Create the 10 custom properties (before importing)

The free tier allows 10 custom properties, so all 10 go on the **Deal** object, where the deal desk work happens. Go to **Settings → Properties**, choose **Deal properties**, and click **Create property**. Put them in a new group called **Deal Desk**.

| # | Label | Field type | Options |
|---|---|---|---|
| 1 | GPU Type | Dropdown select | H100 SXM, H200, B200 |
| 2 | GPU Count | Number | |
| 3 | Contract Term | Dropdown select | On-Demand, 1-Month Reserved, 3-Month Reserved, 6-Month Reserved, 12-Month Reserved |
| 4 | Negotiated Discount | Number | Stored as a decimal: 0.15 = 15% |
| 5 | Billing Frequency | Dropdown select | Monthly, Quarterly, Prepaid Upfront |
| 6 | Contract Status | Dropdown select | Not Started, Drafting, Redlines, Legal Review, Out for Signature, Countersigned |
| 7 | Last Contract Update | Date picker | |
| 8 | Non-Standard Terms | Single-line text | Blank means standard terms |
| 9 | PO Number | Single-line text | |
| 10 | Fulfillment Status | Dropdown select | Provisioning, Live, Invoiced |

These HubSpot default properties are also used, and don't count against the limit: Deal Name, Pipeline, Deal Stage, Amount, Close Date, Deal Type, and Closed Lost Reason on deals; Company Name, Company Domain Name, Number of Employees, City, State/Region, and Country/Region on companies; First Name, Last Name, Email, and Job Title on contacts. For **Deal Type**, check that its options include *New Business* and *Expansion*.

### What got cut, and where it went instead

The first version of this design used 19 custom properties. The free-tier limit forced a rule that real RevOps teams follow anyway: **store what people enter; compute what you can derive.** Every derived field is one more value that can go stale.

| Cut property | Where it lives now |
|---|---|
| List Rate, Effective Rate | Computed by the quote engine from GPU Type, Contract Term, and Negotiated Discount (Day 3) |
| Non-Standard Terms (Yes/No) | Merged into the text field: blank = standard |
| PO Required | Business rule in code: companies with 1,000+ employees require a PO |
| Billing Contact Email | The account's contact with Job Title "Finance Manager" |
| Buying Role (contact) | Job Title (default property) |
| Customer Segment (company) | Derived from Number of Employees |
| Primary Workload (company) | Dropped; not needed for the deal desk |
| Account Executive | Dropped; use the default Deal Owner (you, in a one-user portal) |

The field-by-field reasoning is interview material: you designed within a constraint rather than around it.

---

## 4. Import the data (in this order)

Go to **CRM → Contacts** and click **Import**, or use the Imports page from the menu.

1. **companies.csv.** Import a file with one object: Companies. The columns should auto-match default properties. HubSpot deduplicates companies by domain, which is why the duplicate "Tensorfield Labs, Inc." was given a *different* domain.
2. **contacts.csv.** Import a file with one object: Contacts. HubSpot's default setting associates contacts with companies that share their email domain. The three Gmail contacts won't match any company, and that's intentional.
3. **deals.csv.** Import a file with **two objects: Deals and Companies**. Map "Company Domain Name" as the Companies identifier so each deal attaches to its company. Set the date format to **Year-Month-Day**. Map "Deal Stage" and "Pipeline" to the stage and pipeline you built in section 2; the stage names must match exactly.

HubSpot's import screens change occasionally, so the exact button labels may differ slightly from what's described here.

**Do not import `issues_manifest.csv`.** It's the answer key listing every problem planted in the data. On Day 5, the hygiene audit has to find all of them.

### Check the import worked

- 41 companies, 133 contacts, and 60 deals are in the portal.
- The deal board view shows deals spread across all 6 stages.
- Opening any deal shows an associated company and filled-in Deal Desk properties.
- Any rows that failed are listed on the import's error page; screenshot them for your decisions log.

---

## 5. What's in the data

**The business:** 40 fictional AI companies of all sizes (startups, growth-stage companies, research labs, and 1,000+ employee enterprises). Each account has an ML Infrastructure Lead, a CTO, and a Finance Manager (the billing contact); large accounts also have a Head of Legal. They rent H100, H200, and B200 GPUs either on-demand or on reserved terms of 1 to 12 months.

**The pricing math (synthetic, computed in code):**
`Amount = GPU Count × Term Hours × List Rate × (1 − Term Discount) × (1 − Negotiated Discount)`

| GPU | List $/GPU-hr | | Term | Hours | Term discount |
|---|---|---|---|---|---|
| H100 SXM | 2.20 | | On-Demand (est. 1 month) | 730 | 0% |
| H200 | 2.80 | | 1-Month Reserved | 730 | 5% |
| B200 | 3.90 | | 3-Month Reserved | 2,190 | 10% |
| | | | 6-Month Reserved | 4,380 | 15% |
| | | | 12-Month Reserved | 8,760 | 20% |

**Planted problems** (all logged in the answer key):

| Issue | Count | What a deal desk does about it |
|---|---|---|
| Stale contract (no update in more than 3 days) | 5 | Escalate to the rep and the customer |
| Open deal with a past close date | 4 | Rep updates it with a reason |
| Late-stage deal at an account with no Finance Manager contact | 4 | Blocks the handoff to finance |
| Amount doesn't match the GPU math | 3 | Recalculate from the pricing sheet |
| Unassociated personal-email contacts | 3 | Research the contact and link them |
| Missing contract term | 2 | Blocks the quote |
| Closed Won without a countersigned contract | 2 | Revert the stage or collect the signature |
| Missing PO number at a 1,000+ employee account | 2 | Blocks the invoice |
| Closed Lost with no reason | 2 | Needed for win/loss analysis |
| Duplicate company | 1 | Merge the records |
| Discount above 10% | 6 | Day 2 approval matrix |
| Non-standard terms | 6 | Day 2 terms review |

---

## 6. Start your decisions log

Create `docs/decisions.md` and write one entry per judgment call, the same way you did in the GTM analytics project. Here are today's first entries:

1. **Post-sale tracked in a property, not the pipeline.** Keeps sales metrics (win rate, sales cycle) clean.
2. **Custom "Last Contract Update" field.** HubSpot's built-in activity date can't be imported, and contract movement is the signal a deal desk actually needs.
3. **Designed to the 10-property free-tier limit.** Stored only what humans enter; moved everything derivable (rates, PO requirement, segment, billing contact) into code. Fewer fields means fewer stale values.
4. **Billing contact identified by Job Title instead of a dedicated field.** Keeps the contact on the company record where finance can find it, without spending a custom property.
5. **Duplicate company given a second domain.** Otherwise HubSpot's domain dedupe would have merged it on import and hidden the problem.

---

## Up next: Day 2

Day 2 turns this pricing model into a formal pricing sheet and writes the **approval matrix**: who can approve which discounts and non-standard terms. The 11 high-discount deals and 9 non-standard-terms deals become the test cases.
