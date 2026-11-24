"""Command line for the Innovatix sales bot.

  python -m sales_bot chat                    talk to your sales manager
  python -m sales_bot brief                   today's priorities (AI)
  python -m sales_bot weekly                  weekly review vs the 10-container target (AI)
  python -m sales_bot hunt trailer_dealer NSW research and add new prospects (AI)
  python -m sales_bot pipeline                pipeline numbers (no AI, free)
  python -m sales_bot followups               who to contact (no AI, free)
  python -m sales_bot drafts [--sent ID]      review saved outreach drafts
  python -m sales_bot import FILE.csv         bulk import prospects
  python -m sales_bot export FILE.csv         export all prospects
"""
from __future__ import annotations

import argparse
import csv
import sys

from . import db
from .config import TARGET_CONTAINERS

BRIEF_PROMPT = """Give me today's sales brief. Check follow_ups (next 2 days) and pipeline_summary. Then tell me:
1. The 5-10 most important contacts to make today, in order, each with the reason and the one-line opener.
2. Any deal that's stalling and what to do about it.
3. If the pipeline has fewer than 30 prospects in new/researched, say how many to research today and in which segment/state.
Keep it short enough to read on a phone."""

WEEKLY_PROMPT = """Run the weekly sales review. Use pipeline_summary, weekly_activity and follow_ups.
Report: containers ordered this month and the run rate vs the target; pipeline by stage and weighted forecast;
activity last week vs the weekly targets in the playbook (read 08-weekly-operating-rhythm); what's working and
what isn't; and the plan for next week with specific numbers (how many new prospects, calls, visits, trial
offers) needed to stay on track for the target. Be blunt if we're behind."""

HUNT_PROMPT = """Find new prospects in segment '{segment}'{where}. First check find_prospects so you don't add
duplicates. Then use web search to find {n} real businesses that fit the ideal customer profile. For each one,
check its website, then add it with add_prospect: segment, location, website, source URL, a fit score with a
one-line reason in notes, a realistic containers/month estimate, any public contact details you actually found,
and a next action dated within the next 7 days. Finish with a table of what you added and the top 3 to contact first."""


def _print_table(rows: list[dict], cols: list[str]) -> None:
    if not rows:
        print("  (none)")
        return
    widths = {c: min(32, max(len(c), *(len(str(r.get(c) or "")) for r in rows))) for c in cols}
    print("  " + "  ".join(c.ljust(widths[c]) for c in cols))
    for r in rows:
        print("  " + "  ".join(str(r.get(c) or "")[:32].ljust(widths[c]) for c in cols))


def cmd_pipeline(_args) -> None:
    s = db.pipeline_summary(db.connect(), TARGET_CONTAINERS)
    print(f"\nTarget: {s['target_containers_per_month']:g} containers/month")
    print(f"Ordered this month: {s['ordered_this_month']:g}")
    print(f"Active customer run rate: {s['active_customer_run_rate_pm']:g}/month")
    print(f"Weighted pipeline (new): +{s['weighted_pipeline_new_containers_pm']:g}/month")
    print(f"Gap to target: {s['gap_to_target_pm']:g}/month\n")
    _print_table([x for x in s["stages"] if x["count"]], ["stage", "count", "est_containers_pm", "weighted_new_containers_pm"])
    print("\nRecent months:")
    _print_table(s["recent_months"], ["month", "containers", "trial_containers", "customers"])


def cmd_followups(args) -> None:
    c = db.connect()
    print("\nDue:")
    _print_table(db.due_follow_ups(c, args.days), ["id", "company", "stage", "contact_name", "phone", "next_action", "next_action_date"])
    print("\nStale open deals (no update in 14+ days):")
    _print_table(db.stale_deals(c), ["id", "company", "stage", "updated_at", "next_action"])


def cmd_drafts(args) -> None:
    c = db.connect()
    if args.sent:
        db.mark_draft(c, args.sent, "sent")
        print(f"Draft {args.sent} marked as sent.")
        return
    if args.discard:
        db.mark_draft(c, args.discard, "discarded")
        print(f"Draft {args.discard} discarded.")
        return
    for d in db.list_drafts(c):
        print("=" * 72)
        print(f"#{d['id']}  {d['channel']}  to: {d['company'] or '-'} {('<' + d['email'] + '>') if d['email'] else ''}")
        if d["subject"]:
            print(f"Subject: {d['subject']}")
        print("-" * 72)
        print(d["body"])
    print("=" * 72 + "\nMark one sent with: python -m sales_bot drafts --sent ID")


def cmd_import(args) -> None:
    c = db.connect()
    added = skipped = 0
    with open(args.file, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
            if not row.get("company"):
                continue
            row.setdefault("segment", "other")
            if not row["segment"]:
                row["segment"] = "other"
            try:
                db.add_prospect(c, **row)
                added += 1
            except ValueError as e:
                skipped += 1
                print(f"  skipped: {e}")
    print(f"Imported {added}, skipped {skipped}.")


def cmd_export(args) -> None:
    rows = db.rows(db.connect().execute("SELECT * FROM prospects ORDER BY id"))
    with open(args.file, "w", newline="", encoding="utf-8") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(f"Exported {len(rows)} prospects to {args.file}")


def _agent():
    from .agent import SalesAgent
    return SalesAgent()


def _one_shot(prompt: str) -> None:
    print(_agent().ask(prompt))


def cmd_chat(_args) -> None:
    agent = _agent()
    print("Innovatix Sales Manager. Type your message (or 'quit'). Tip: tell me about calls/visits and I'll log them.\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not text:
            continue
        if text.lower() in {"quit", "exit", "q"}:
            return
        print("\nsales manager>\n" + agent.ask(text) + "\n")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="sales_bot", description="Innovatix sales manager bot")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("chat")
    sub.add_parser("brief")
    sub.add_parser("weekly")
    h = sub.add_parser("hunt")
    h.add_argument("segment")
    h.add_argument("state", nargs="?")
    h.add_argument("-n", type=int, default=10)
    sub.add_parser("pipeline")
    f = sub.add_parser("followups")
    f.add_argument("--days", type=int, default=2)
    d = sub.add_parser("drafts")
    d.add_argument("--sent", type=int)
    d.add_argument("--discard", type=int)
    i = sub.add_parser("import")
    i.add_argument("file")
    e = sub.add_parser("export")
    e.add_argument("file")
    args = p.parse_args(argv)

    match args.cmd:
        case None | "chat":
            cmd_chat(args)
        case "brief":
            _one_shot(BRIEF_PROMPT)
        case "weekly":
            _one_shot(WEEKLY_PROMPT)
        case "hunt":
            where = f" in {args.state}" if args.state else " anywhere in Australia"
            _one_shot(HUNT_PROMPT.format(segment=args.segment, where=where, n=args.n))
        case "pipeline":
            cmd_pipeline(args)
        case "followups":
            cmd_followups(args)
        case "drafts":
            cmd_drafts(args)
        case "import":
            cmd_import(args)
        case "export":
            cmd_export(args)


if __name__ == "__main__":
    sys.exit(main())
