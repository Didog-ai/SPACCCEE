"""Lightweight CRM stored in a local SQLite file (data/crm.db).

No server, no subscription. Back the file up (or commit an export) regularly.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("INNOVATIX_DB", ROOT / "data" / "crm.db"))

# Pipeline stages, in order. Probabilities are used for the weighted forecast.
STAGES: dict[str, float] = {
    "new": 0.02,             # on the list, not yet researched
    "researched": 0.04,      # fit confirmed, decision-maker identified
    "contacted": 0.06,       # first outreach sent
    "engaged": 0.12,         # replied / had a conversation
    "meeting": 0.25,         # face-to-face or video meeting held
    "trial_offered": 0.40,   # trial container / sample unit proposed with pricing
    "trial_order": 0.65,     # first (trial) container ordered
    "active": 1.0,           # repeat-ordering customer
    "nurture": 0.03,         # not now — revisit later
    "lost": 0.0,
    "not_a_fit": 0.0,
}
OPEN_STAGES = [s for s in STAGES if s not in ("active", "nurture", "lost", "not_a_fit")]

SEGMENTS = [
    "trailer_dealer",          # trailer retailers / wholesalers
    "trailer_manufacturer",    # AU builders who could buy kits / chassis / private label
    "hire_company",            # equipment & trailer hire fleets
    "rural_ag",                # rural merchandise, farm machinery dealers
    "caravan_camper_boat",     # caravan, camper, off-road, boat dealers
    "fleet_buyer",             # councils, mining, construction, utilities, landscaping
    "government",              # tenders / panels
    "auto_accessory",          # 4x4, towbar, ute accessory chains
    "online_reseller",         # marketplace / e-commerce trailer sellers
    "other",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    segment TEXT NOT NULL DEFAULT 'other',
    state TEXT,
    city TEXT,
    website TEXT,
    phone TEXT,
    email TEXT,
    contact_name TEXT,
    contact_role TEXT,
    source TEXT,
    stage TEXT NOT NULL DEFAULT 'new',
    est_containers_per_month REAL DEFAULT 0,
    fit_score INTEGER,
    pain_points TEXT,
    notes TEXT,
    next_action TEXT,
    next_action_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL REFERENCES prospects(id),
    kind TEXT NOT NULL,
    summary TEXT NOT NULL,
    outcome TEXT,
    occurred_on TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER NOT NULL REFERENCES prospects(id),
    containers REAL NOT NULL,
    order_date TEXT NOT NULL,
    eta TEXT,
    value_aud REAL,
    terms TEXT,
    is_trial INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id INTEGER REFERENCES prospects(id),
    channel TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prospects_stage ON prospects(stage);
CREATE INDEX IF NOT EXISTS idx_activities_prospect ON activities(prospect_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
"""

PROSPECT_FIELDS = {
    "company", "segment", "state", "city", "website", "phone", "email",
    "contact_name", "contact_role", "source", "stage", "est_containers_per_month",
    "fit_score", "pain_points", "notes", "next_action", "next_action_date",
}


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today() -> str:
    return date.today().isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def validate(fields: dict) -> None:
    if "stage" in fields and fields["stage"] not in STAGES:
        raise ValueError(f"Unknown stage '{fields['stage']}'. Use one of: {', '.join(STAGES)}")
    if "segment" in fields and fields["segment"] not in SEGMENTS:
        raise ValueError(f"Unknown segment '{fields['segment']}'. Use one of: {', '.join(SEGMENTS)}")
    for key in ("next_action_date",):
        if fields.get(key):
            date.fromisoformat(fields[key])  # raises on bad format


# ---- prospects -------------------------------------------------------------

def add_prospect(conn, **fields) -> int:
    fields = {k: v for k, v in fields.items() if k in PROSPECT_FIELDS and v not in (None, "")}
    validate(fields)
    dup = conn.execute(
        "SELECT id FROM prospects WHERE lower(company) = lower(?)", (fields["company"],)
    ).fetchone()
    if dup:
        raise ValueError(f"'{fields['company']}' already exists as prospect #{dup['id']}")
    fields["created_at"] = fields["updated_at"] = now()
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    cur = conn.execute(f"INSERT INTO prospects ({cols}) VALUES ({marks})", tuple(fields.values()))
    conn.commit()
    return cur.lastrowid


def update_prospect(conn, prospect_id: int, **fields) -> dict:
    fields = {k: v for k, v in fields.items() if k in PROSPECT_FIELDS and v is not None}
    if not fields:
        raise ValueError("Nothing to update")
    validate(fields)
    get_prospect(conn, prospect_id)  # raises if missing
    fields["updated_at"] = now()
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE prospects SET {sets} WHERE id = ?", (*fields.values(), prospect_id))
    conn.commit()
    return get_prospect(conn, prospect_id)


def get_prospect(conn, prospect_id: int) -> dict:
    row = conn.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
    if not row:
        raise ValueError(f"No prospect with id {prospect_id}")
    return dict(row)


def find_prospects(conn, text=None, stage=None, segment=None, state=None, limit=50) -> list[dict]:
    q = ("SELECT id, company, segment, state, city, stage, contact_name, est_containers_per_month, "
         "fit_score, next_action, next_action_date FROM prospects WHERE 1=1")
    args: list = []
    if text:
        q += " AND (company LIKE ? OR notes LIKE ? OR contact_name LIKE ? OR city LIKE ?)"
        args += [f"%{text}%"] * 4
    if stage:
        q += " AND stage = ?"
        args.append(stage)
    if segment:
        q += " AND segment = ?"
        args.append(segment)
    if state:
        q += " AND upper(state) = upper(?)"
        args.append(state)
    q += " ORDER BY COALESCE(fit_score, 0) DESC, updated_at DESC LIMIT ?"
    args.append(limit)
    return rows(conn.execute(q, args))


# ---- activities ------------------------------------------------------------

def log_activity(conn, prospect_id: int, kind: str, summary: str, outcome=None, occurred_on=None) -> int:
    get_prospect(conn, prospect_id)
    occurred_on = occurred_on or today()
    date.fromisoformat(occurred_on)
    cur = conn.execute(
        "INSERT INTO activities (prospect_id, kind, summary, outcome, occurred_on, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (prospect_id, kind, summary, outcome, occurred_on, now()),
    )
    conn.execute("UPDATE prospects SET updated_at = ? WHERE id = ?", (now(), prospect_id))
    conn.commit()
    return cur.lastrowid


def activities_for(conn, prospect_id: int, limit=20) -> list[dict]:
    return rows(conn.execute(
        "SELECT kind, summary, outcome, occurred_on FROM activities WHERE prospect_id = ? "
        "ORDER BY occurred_on DESC, id DESC LIMIT ?", (prospect_id, limit)))


# ---- orders ----------------------------------------------------------------

def record_order(conn, prospect_id: int, containers: float, order_date=None, eta=None,
                 value_aud=None, terms=None, is_trial=False, notes=None) -> int:
    p = get_prospect(conn, prospect_id)
    order_date = order_date or today()
    date.fromisoformat(order_date)
    cur = conn.execute(
        "INSERT INTO orders (prospect_id, containers, order_date, eta, value_aud, terms, is_trial, notes, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (prospect_id, containers, order_date, eta, value_aud, terms, int(is_trial), notes, now()),
    )
    new_stage = "trial_order" if is_trial and p["stage"] != "active" else "active"
    conn.execute("UPDATE prospects SET stage = ?, updated_at = ? WHERE id = ?", (new_stage, now(), prospect_id))
    conn.commit()
    return cur.lastrowid


def containers_in_month(conn, year: int, month: int) -> float:
    prefix = f"{year:04d}-{month:02d}"
    r = conn.execute("SELECT COALESCE(SUM(containers), 0) AS c FROM orders WHERE substr(order_date, 1, 7) = ?",
                     (prefix,)).fetchone()
    return float(r["c"])


def monthly_containers(conn, months=6) -> list[dict]:
    return rows(conn.execute(
        "SELECT substr(order_date, 1, 7) AS month, SUM(containers) AS containers, "
        "SUM(CASE WHEN is_trial = 1 THEN containers ELSE 0 END) AS trial_containers, "
        "COUNT(DISTINCT prospect_id) AS customers "
        "FROM orders GROUP BY month ORDER BY month DESC LIMIT ?", (months,)))


# ---- drafts ----------------------------------------------------------------

def save_draft(conn, channel: str, body: str, subject=None, prospect_id=None) -> int:
    if prospect_id is not None:
        get_prospect(conn, prospect_id)
    cur = conn.execute(
        "INSERT INTO drafts (prospect_id, channel, subject, body, created_at) VALUES (?, ?, ?, ?, ?)",
        (prospect_id, channel, subject, body, now()))
    conn.commit()
    return cur.lastrowid


def list_drafts(conn, status="draft") -> list[dict]:
    return rows(conn.execute(
        "SELECT d.id, d.channel, d.subject, d.body, d.created_at, p.company, p.email, p.contact_name "
        "FROM drafts d LEFT JOIN prospects p ON p.id = d.prospect_id WHERE d.status = ? ORDER BY d.id",
        (status,)))


def mark_draft(conn, draft_id: int, status: str) -> None:
    conn.execute("UPDATE drafts SET status = ? WHERE id = ?", (status, draft_id))
    conn.commit()


# ---- reporting -------------------------------------------------------------

def pipeline_summary(conn, target_containers: float) -> dict:
    by_stage = {r["stage"]: r for r in rows(conn.execute(
        "SELECT stage, COUNT(*) AS n, COALESCE(SUM(est_containers_per_month), 0) AS est "
        "FROM prospects GROUP BY stage"))}
    stages = []
    weighted = 0.0
    for s, p in STAGES.items():
        r = by_stage.get(s, {"n": 0, "est": 0})
        w = r["est"] * p if s != "active" else 0
        weighted += w
        stages.append({"stage": s, "count": r["n"], "est_containers_pm": round(r["est"], 1),
                       "probability": p, "weighted_new_containers_pm": round(w, 2)})
    active_run_rate = by_stage.get("active", {"est": 0})["est"]
    d = date.today()
    this_month = containers_in_month(conn, d.year, d.month)
    return {
        "target_containers_per_month": target_containers,
        "ordered_this_month": this_month,
        "active_customer_run_rate_pm": round(active_run_rate, 1),
        "weighted_pipeline_new_containers_pm": round(weighted, 2),
        "projected_run_rate_pm": round(active_run_rate + weighted, 1),
        "gap_to_target_pm": round(max(0.0, target_containers - active_run_rate - weighted), 1),
        "stages": stages,
        "recent_months": monthly_containers(conn),
    }


def due_follow_ups(conn, days_ahead=0) -> list[dict]:
    cutoff = date.fromordinal(date.today().toordinal() + days_ahead).isoformat()
    return rows(conn.execute(
        "SELECT id, company, stage, contact_name, phone, email, next_action, next_action_date "
        "FROM prospects WHERE next_action_date IS NOT NULL AND next_action_date <= ? "
        "AND stage NOT IN ('lost', 'not_a_fit') ORDER BY next_action_date", (cutoff,)))


def stale_deals(conn, days=14) -> list[dict]:
    cutoff = date.fromordinal(date.today().toordinal() - days).isoformat()
    marks = ",".join("?" for _ in OPEN_STAGES)
    return rows(conn.execute(
        f"SELECT id, company, stage, updated_at, next_action FROM prospects "
        f"WHERE stage IN ({marks}) AND stage NOT IN ('new') AND substr(updated_at, 1, 10) < ? "
        f"ORDER BY updated_at", (*OPEN_STAGES, cutoff)))


def activity_counts(conn, since: str) -> dict:
    r = rows(conn.execute(
        "SELECT kind, COUNT(*) AS n FROM activities WHERE occurred_on >= ? GROUP BY kind", (since,)))
    return {x["kind"]: x["n"] for x in r}
