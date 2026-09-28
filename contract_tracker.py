"""
Contract Tracker — the 3-Day Rule, running.

Reads every deal in Contract Out, works out how long the contract has sat
without movement, names the likely blocker, applies the escalation ladder from
config/price_book.json, and prints a digest. With SLACK_WEBHOOK_URL set it also
posts that digest to Slack.

The ladder (from the playbook):
    0-2 days   no action
    3 days     deal desk follows up, deal appears in the digest
    5 days     escalate to the Head of GTM with the blocker named
    10 days    escalate to the CEO — push, re-quote, or close it lost

Documented pauses are honored. A paused deal still appears in the digest, marked
as paused with its return date, so a pause hides nothing. When a pause expires
with no movement, the deal re-enters at the day-5 rung rather than day 3,
because it has already had its grace period.

Usage
  python3 contract_tracker.py                      print today's digest
  python3 contract_tracker.py --slack              also post it to Slack
  python3 contract_tracker.py --pauses             list active pauses
  python3 contract_tracker.py --pause "Solace" --reason "Customer legal review" --until 2026-10-08
  python3 contract_tracker.py --unpause "Solace"   contract moved; clear the pause
"""

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime

import dealdesk as dd

PAUSE_FILE = os.path.join(dd.BASE, "data", "pauses.json")
ESC = dd.POLICY["escalation"]
LADDER = ESC["ladder_days"]
PAUSE_RULES = ESC["pause"]

# What the Contract Status field implies about who we are waiting on.
BLOCKER = {
    "Not Started": ("contract not drafted", "deal desk"),
    "Drafting": ("order form being drafted", "deal desk"),
    "Redlines": ("customer legal has redlines", "customer legal"),
    "Legal Review": ("in legal review", "customer legal"),
    "Out for Signature": ("awaiting customer signature", "customer signatory"),
    "Countersigned": ("signed — should not be in Contract Out", "deal desk"),
}


# --------------------------------------------------------------------------
# Pause store
# --------------------------------------------------------------------------
def load_pauses():
    if not os.path.exists(PAUSE_FILE):
        return {}
    with open(PAUSE_FILE) as f:
        return json.load(f)


def save_pauses(p):
    with open(PAUSE_FILE, "w") as f:
        json.dump(p, f, indent=2, sort_keys=True)


def add_pause(deal_name, reason, until, last_contract_update):
    """Validate against the playbook's pause rules before recording one.

    The consecutive counter survives an unpause on purpose. Releasing a pause
    and immediately re-pausing would otherwise reset the count and defeat the
    one-pause rule. The counter only resets when the contract has actually
    moved — that is, when Last Contract Update is newer than the prior pause.
    """
    if reason not in PAUSE_RULES["allowed_reasons"]:
        sys.exit(f"'{reason}' is not an allowed pause reason. Allowed:\n  "
                 + "\n  ".join(PAUSE_RULES["allowed_reasons"]))
    ret = datetime.strptime(until, "%Y-%m-%d").date()
    days = (ret - date.today()).days
    if days < 1:
        sys.exit(f"Return date {until} must be in the future.")
    if days > PAUSE_RULES["max_days"]:
        sys.exit(f"{days} days exceeds the {PAUSE_RULES['max_days']}-day cap. "
                 "A longer hold escalates instead of pausing.")

    pauses = load_pauses()
    prior = pauses.get(deal_name)
    consecutive = prior["consecutive"] if prior else 0
    if prior and last_contract_update:
        moved = datetime.strptime(last_contract_update[:10], "%Y-%m-%d").date()
        if moved > datetime.strptime(prior["paused_on"], "%Y-%m-%d").date():
            consecutive = 0          # the contract moved; the streak is broken

    if consecutive >= PAUSE_RULES["max_consecutive"]:
        sys.exit(f"{deal_name} has already used its {PAUSE_RULES['max_consecutive']} "
                 "consecutive pause and the contract has not moved since. "
                 "Escalate it instead of pausing again.")

    pauses[deal_name] = {"reason": reason, "paused_on": date.today().isoformat(),
                         "return_on": until, "consecutive": consecutive + 1,
                         "active": True}
    save_pauses(pauses)
    print(f"Paused {deal_name}\n  reason: {reason}\n  returns: {until} ({days} days)")


# --------------------------------------------------------------------------
# Assessment
# --------------------------------------------------------------------------
def assess(deal, pauses):
    """Return one row describing where this contract stands today."""
    raw = str(deal.get("Last Contract Update", "")).strip()
    last = datetime.strptime(raw[:10], "%Y-%m-%d").date() if raw else None
    days = (date.today() - last).days if last else None

    status = deal.get("Contract Status", "")
    blocker, waiting_on = BLOCKER.get(status, ("status not set", "deal desk"))

    row = {
        "deal": deal["Deal Name"],
        "amount": float(deal.get("Amount") or 0),
        "status": status,
        "days": days,
        "last_update": raw[:10] if raw else "never",
        "blocker": blocker,
        "waiting_on": waiting_on,
        "paused": None,
        "tier": "healthy",
    }

    p = pauses.get(deal["Deal Name"])
    if p and p.get("active"):
        ret = datetime.strptime(p["return_on"], "%Y-%m-%d").date()
        row["paused"] = p
        if ret >= date.today():
            row["tier"] = "paused"
            return row
        # Pause expired with no movement: re-enter at the day-5 rung.
        row["tier"] = "head_of_gtm"
        row["blocker"] = f"pause expired {p['return_on']} — {p['reason']}"
        return row

    if days is None or days < LADDER["follow_up"]:
        row["tier"] = "healthy"
    elif days >= LADDER["ceo"]:
        row["tier"] = "ceo"
    elif days >= LADDER["head_of_gtm"]:
        row["tier"] = "head_of_gtm"
    else:
        row["tier"] = "follow_up"
    return row


TIERS = [
    ("ceo", f"ESCALATE TO CEO — {LADDER['ceo']}+ days", "push, re-quote, or close lost"),
    ("head_of_gtm", f"ESCALATE TO HEAD OF GTM — {LADDER['head_of_gtm']}+ days", "blocker named below"),
    ("follow_up", f"DEAL DESK FOLLOW-UP — {LADDER['follow_up']}+ days", "contact the customer today"),
    ("paused", "PAUSED — documented hold", "visible, not hidden"),
]


def money(v):
    return f"${v:,.0f}"


def build_digest(rows):
    lines = []
    today = date.today()
    needs = [r for r in rows if r["tier"] in ("ceo", "head_of_gtm", "follow_up")]
    paused = [r for r in rows if r["tier"] == "paused"]
    healthy = [r for r in rows if r["tier"] == "healthy"]

    lines.append(f"CONTRACT DESK — THE 3-DAY RULE   {today:%a %d %b %Y}")
    lines.append("=" * 68)
    lines.append(f"{len(needs)} need action · {len(paused)} paused · {len(healthy)} healthy"
                 f"   ({money(sum(r['amount'] for r in needs))} at risk)")

    for key, heading, hint in TIERS:
        group = sorted([r for r in rows if r["tier"] == key],
                       key=lambda r: -(r["days"] or 0))
        if not group:
            continue
        lines.append("")
        lines.append(f"── {heading} ── ({hint})")
        for r in group:
            age = f"{r['days']}d" if r["days"] is not None else " — "
            lines.append(f"  {age:>4}  {r['deal']}")
            if r["tier"] == "paused":
                lines.append(f"        paused until {r['paused']['return_on']} · "
                             f"{r['paused']['reason']} · {money(r['amount'])}")
            else:
                lines.append(f"        {r['status']} · waiting on {r['waiting_on']} · "
                             f"{r['blocker']} · {money(r['amount'])}")

    if not needs:
        lines.append("")
        lines.append("Nothing has sat for three days. Nice.")
    lines.append("")
    lines.append("Every deal above needs an action logged today. A logged follow-up")
    lines.append("resets the clock; a pause needs a reason and a return date.")
    return "\n".join(lines)


def post_to_slack(text):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        print("\n[SLACK_WEBHOOK_URL not set — digest printed above, not posted]")
        return False
    try:
        import requests
    except ImportError:
        print("\n[requests not installed: pip3 install requests]")
        return False
    r = requests.post(url, json={"text": f"```\n{text}\n```"}, timeout=10)
    if r.status_code == 200:
        print("\n[posted to Slack]")
        return True
    print(f"\n[Slack returned {r.status_code}: {r.text[:200]}]")
    return False


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slack", action="store_true", help="post the digest to Slack")
    ap.add_argument("--pauses", action="store_true", help="list active pauses")
    ap.add_argument("--pause", metavar="DEAL", help="pause a deal (partial name)")
    ap.add_argument("--reason", help="pause reason (must be an allowed reason)")
    ap.add_argument("--until", metavar="YYYY-MM-DD", help="expected return date")
    ap.add_argument("--unpause", metavar="DEAL", help="clear a pause (partial name)")
    args = ap.parse_args()

    deals, _, _ = dd.load_portal()
    tracked = [d for d in deals if d["Deal Stage"] == "Contract Out"]
    pauses = load_pauses()

    def find(fragment):
        m = [d for d in tracked if fragment.lower() in d["Deal Name"].lower()]
        if len(m) != 1:
            sys.exit(f"{len(m)} contract-stage deals match {fragment!r}"
                     + ("" if not m else ":\n  " + "\n  ".join(d["Deal Name"] for d in m)))
        return m[0]

    if args.pauses:
        if not pauses:
            print("No pauses recorded.")
            return
        for name, p in sorted(pauses.items()):
            left = (datetime.strptime(p["return_on"], "%Y-%m-%d").date() - date.today()).days
            if not p.get("active"):
                state = f"released {p.get('released_on', '?')}"
            else:
                state = f"{left}d left" if left >= 0 else f"EXPIRED {-left}d ago"
            print(f"  {name}\n    {p['reason']} · returns {p['return_on']} · {state}"
                  f" · pause {p['consecutive']} of {PAUSE_RULES['max_consecutive']}")
        return

    if args.pause:
        if not (args.reason and args.until):
            sys.exit("--pause needs both --reason and --until. A pause without a "
                     "reason and a return date is just a deal nobody is watching.")
        d = find(args.pause)
        add_pause(d["Deal Name"], args.reason, args.until, d.get("Last Contract Update"))
        return

    if args.unpause:
        name = find(args.unpause)["Deal Name"]
        p = pauses.get(name)
        if p and p.get("active"):
            p["active"] = False
            p["released_on"] = date.today().isoformat()
            save_pauses(pauses)
            print(f"Released the pause on {name}.\n"
                  "  The record is kept so the one-pause rule still applies until\n"
                  "  the contract actually moves.")
        else:
            print(f"{name} is not currently paused.")
        return

    rows = [assess(d, pauses) for d in tracked]
    digest = build_digest(rows)
    print(digest)

    out = os.path.join(dd.BASE, "data", "stale_report.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Deal Name", "Days Since Update", "Tier",
                                          "Contract Status", "Waiting On", "Blocker",
                                          "Amount", "Last Contract Update"])
        w.writeheader()
        for r in sorted(rows, key=lambda r: -(r["days"] or 0)):
            w.writerow({"Deal Name": r["deal"], "Days Since Update": r["days"],
                        "Tier": r["tier"], "Contract Status": r["status"],
                        "Waiting On": r["waiting_on"], "Blocker": r["blocker"],
                        "Amount": r["amount"], "Last Contract Update": r["last_update"]})
    print(f"\nwrote {os.path.relpath(out, dd.BASE)}")

    if args.slack:
        post_to_slack(digest)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:          # e.g. piped into `head`
        os._exit(0)
