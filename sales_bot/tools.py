"""Tools the sales-manager agent can call. Each one reads or writes the local CRM.

Nothing here sends email or contacts anyone: outreach is saved as drafts for a human to review.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from anthropic import beta_tool

from . import db
from .config import TARGET_CONTAINERS, PLAYBOOK_DIR

_conn = None


def conn():
    global _conn
    if _conn is None:
        _conn = db.connect()
    return _conn


def _ok(data) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)


@beta_tool
def add_prospect(
    company: str,
    segment: str,
    state: str | None = None,
    city: str | None = None,
    website: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    contact_name: str | None = None,
    contact_role: str | None = None,
    source: str | None = None,
    est_containers_per_month: float | None = None,
    fit_score: int | None = None,
    pain_points: str | None = None,
    notes: str | None = None,
    next_action: str | None = None,
    next_action_date: str | None = None,
) -> str:
    """Add a new prospect (a business that could buy Innovatix trailers) to the CRM.

    Only record contact details you actually found in a source or that the user gave you; never invent
    phone numbers, emails or names.

    Args:
        company: Business name.
        segment: One of trailer_dealer, trailer_manufacturer, hire_company, rural_ag, caravan_camper_boat, fleet_buyer, government, auto_accessory, online_reseller, other.
        state: Australian state/territory code, e.g. QLD, NSW, VIC, WA, SA, TAS, NT, ACT.
        city: Town or city.
        website: Website URL.
        phone: Business phone, if found in a source.
        email: Contact email, if found in a source.
        contact_name: Decision-maker name, if known.
        contact_role: Their role, e.g. Owner, Purchasing Manager.
        source: Where this lead came from (URL, show name, referral).
        est_containers_per_month: Realistic estimate of containers/month if they became a regular customer (often 0.5-2).
        fit_score: 1-10 fit with Innovatix's ideal customer profile.
        pain_points: Known problems, e.g. quality issues with current imports, supply delays.
        notes: Anything else useful.
        next_action: The next concrete step.
        next_action_date: Date for the next step, YYYY-MM-DD.
    """
    pid = db.add_prospect(conn(), **{k: v for k, v in locals().items()})
    return _ok({"created_prospect_id": pid})


@beta_tool
def find_prospects(
    text: str | None = None,
    stage: str | None = None,
    segment: str | None = None,
    state: str | None = None,
    limit: int = 50,
) -> str:
    """Search the CRM. All filters are optional; with none, lists the best-fit prospects.

    Args:
        text: Free text matched against company, contact, city and notes.
        stage: new, researched, contacted, engaged, meeting, trial_offered, trial_order, active, nurture, lost, not_a_fit.
        segment: Segment filter (see add_prospect).
        state: State code filter.
        limit: Maximum rows.
    """
    return _ok(db.find_prospects(conn(), text, stage, segment, state, limit))


@beta_tool
def get_prospect(prospect_id: int) -> str:
    """Get one prospect with its recent activity history and orders.

    Args:
        prospect_id: CRM id.
    """
    p = db.get_prospect(conn(), prospect_id)
    p["recent_activities"] = db.activities_for(conn(), prospect_id)
    p["orders"] = db.rows(conn().execute(
        "SELECT containers, order_date, eta, value_aud, terms, is_trial FROM orders WHERE prospect_id = ? "
        "ORDER BY order_date DESC", (prospect_id,)))
    return _ok(p)


@beta_tool
def update_prospect(
    prospect_id: int,
    stage: str | None = None,
    segment: str | None = None,
    contact_name: str | None = None,
    contact_role: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    website: str | None = None,
    est_containers_per_month: float | None = None,
    fit_score: int | None = None,
    pain_points: str | None = None,
    notes: str | None = None,
    next_action: str | None = None,
    next_action_date: str | None = None,
) -> str:
    """Update fields on a prospect, e.g. move it to a new stage or set the next action. Only passed fields change.

    Args:
        prospect_id: CRM id.
        stage: New pipeline stage.
        segment: New segment.
        contact_name: Decision-maker name.
        contact_role: Their role.
        phone: Phone.
        email: Email.
        website: Website.
        est_containers_per_month: Updated estimate.
        fit_score: 1-10.
        pain_points: Replaces the pain points text.
        notes: Replaces the notes text (include old notes you want to keep).
        next_action: Next concrete step.
        next_action_date: YYYY-MM-DD.
    """
    args = {k: v for k, v in locals().items() if k != "prospect_id"}
    return _ok(db.update_prospect(conn(), prospect_id, **args))


@beta_tool
def log_activity(
    prospect_id: int,
    kind: str,
    summary: str,
    outcome: str | None = None,
    occurred_on: str | None = None,
    next_action: str | None = None,
    next_action_date: str | None = None,
    new_stage: str | None = None,
) -> str:
    """Record something that happened with a prospect (call, email, visit, meeting, show, sample sent) and optionally set the next step and stage.

    Args:
        prospect_id: CRM id.
        kind: call, email, visit, meeting, trade_show, sample_sent, quote_sent, linkedin, sms, other.
        summary: What happened, in a sentence or two.
        outcome: Result, e.g. 'interested - wants pricing on 7x4 cage'.
        occurred_on: YYYY-MM-DD, defaults to today.
        next_action: Next concrete step.
        next_action_date: YYYY-MM-DD.
        new_stage: Move the prospect to this stage.
    """
    aid = db.log_activity(conn(), prospect_id, kind, summary, outcome, occurred_on)
    upd = {"next_action": next_action, "next_action_date": next_action_date, "stage": new_stage}
    if any(v is not None for v in upd.values()):
        db.update_prospect(conn(), prospect_id, **upd)
    return _ok({"activity_id": aid})


@beta_tool
def record_order(
    prospect_id: int,
    containers: float,
    is_trial: bool = False,
    order_date: str | None = None,
    eta: str | None = None,
    value_aud: float | None = None,
    terms: str | None = None,
    notes: str | None = None,
) -> str:
    """Record a confirmed container order. Moves the customer to trial_order or active.

    Only call this when the user confirms an order actually happened.

    Args:
        prospect_id: CRM id.
        containers: Number of containers ordered.
        is_trial: True if this is a first/trial container.
        order_date: YYYY-MM-DD, defaults to today.
        eta: Expected arrival in Australia, YYYY-MM-DD.
        value_aud: Order value in AUD.
        terms: Payment terms, e.g. 'consignment - pay on sale, 90 day cap'.
        notes: Model mix etc.
    """
    oid = db.record_order(conn(), prospect_id, containers, order_date, eta, value_aud, terms, is_trial, notes)
    return _ok({"order_id": oid})


@beta_tool
def pipeline_summary() -> str:
    """Current pipeline by stage, containers ordered this month, active run rate, weighted forecast and gap to the monthly container target."""
    return _ok(db.pipeline_summary(conn(), TARGET_CONTAINERS))


@beta_tool
def follow_ups(days_ahead: int = 0) -> str:
    """Prospects whose next action is due (overdue or due within days_ahead), plus open deals with no activity in 14+ days.

    Args:
        days_ahead: Include actions due up to this many days from today.
    """
    return _ok({
        "due": db.due_follow_ups(conn(), days_ahead),
        "stale_open_deals": db.stale_deals(conn()),
    })


@beta_tool
def weekly_activity() -> str:
    """Counts of sales activities logged in the last 7 days, by kind, to check effort against weekly targets."""
    since = (date.today() - timedelta(days=7)).isoformat()
    return _ok({"since": since, "counts": db.activity_counts(conn(), since)})


@beta_tool
def save_draft(channel: str, body: str, subject: str | None = None, prospect_id: int | None = None) -> str:
    """Save an outreach message (email, LinkedIn, SMS, call script, letter) as a draft for the user to review and send. Never claims the message was sent.

    Args:
        channel: email, linkedin, sms, call_script, letter.
        body: Full message text.
        subject: Email subject line.
        prospect_id: CRM id the message is for, if any.
    """
    did = db.save_draft(conn(), channel, body, subject, prospect_id)
    return _ok({"draft_id": did, "note": "Saved for review. Run `python -m sales_bot drafts` to see it."})


@beta_tool
def read_playbook(section: str) -> str:
    """Read a section of the Innovatix sales playbook in full.

    Args:
        section: File name without extension, e.g. 01-strategy, 02-target-segments, 03-messaging-and-scripts, 04-objection-handling, 05-trade-shows-and-events, 06-government-and-fleet, 07-credit-and-risk, 08-weekly-operating-rhythm, 09-new-zealand, 00-company-facts.
    """
    path = PLAYBOOK_DIR / f"{section}.md"
    if not path.exists():
        available = sorted(p.stem for p in PLAYBOOK_DIR.glob("*.md"))
        return _ok({"error": f"No section '{section}'", "available": available})
    return path.read_text(encoding="utf-8")


ALL_TOOLS = [
    add_prospect, find_prospects, get_prospect, update_prospect, log_activity, record_order,
    pipeline_summary, follow_ups, weekly_activity, save_draft, read_playbook,
]
