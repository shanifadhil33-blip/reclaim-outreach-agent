"""
database.py — SQLite system-of-record for the Reclaim cold outreach agent.

This database is the single source of truth for who has been contacted.
It does two jobs:

  1. Idempotency  — the UNIQUE constraint on `sent_emails.email` plus
                    `was_emailed()` guarantees we never email an address twice.
  2. Suppression  — `suppressed` holds unsubscribes, bounces, and complaints.
                    The loop must check `is_suppressed()` before every send
                    (required by CAN-SPAM, and critical for deliverability).

Run `python database.py` once to create outreach.db.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).with_name("outreach.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sent_emails (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT NOT NULL UNIQUE COLLATE NOCASE,   -- NOCASE: Jane@x = jane@x
    first_name      TEXT,
    last_name       TEXT,
    company_name    TEXT,
    linkedin_url    TEXT,
    icebreaker      TEXT,                                  -- the AI-generated line used
    subject         TEXT,
    provider_msg_id TEXT,                                  -- id returned by MailerSend/SES
    status          TEXT NOT NULL DEFAULT 'sent',          -- sent | failed
    error           TEXT,                                  -- exception text if failed
    sent_at         TEXT NOT NULL DEFAULT (datetime('now'))-- UTC
);

CREATE TABLE IF NOT EXISTS suppressed (
    email      TEXT PRIMARY KEY COLLATE NOCASE,
    reason     TEXT,                                       -- unsubscribe | bounce | complaint | manual
    added_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sent_status ON sent_emails(status);
CREATE INDEX IF NOT EXISTS idx_sent_date   ON sent_emails(sent_at);
"""


@contextmanager
def get_connection():
    """Yield a connection that commits on success and always closes."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create the database and tables if they do not already exist."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
    print(f"Database ready: {DB_PATH}")


# --- Filtering (idempotency check) ------------------------------------------

def was_emailed(email: str) -> bool:
    """True if this address already has a successful send logged."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM sent_emails WHERE email = ? AND status = 'sent' LIMIT 1",
            (email,),
        ).fetchone()
        return row is not None


def is_suppressed(email: str) -> bool:
    """True if this address has unsubscribed, bounced, or was suppressed manually."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM suppressed WHERE email = ? LIMIT 1", (email,)
        ).fetchone()
        return row is not None


def count_sent_today() -> int:
    """Number of successful sends logged today (UTC) — used for the daily cap."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM sent_emails "
            "WHERE status = 'sent' AND date(sent_at) = date('now')"
        ).fetchone()
        return row["n"]


# --- Logging -----------------------------------------------------------------

def log_send(lead: dict, *, icebreaker=None, subject=None,
             provider_msg_id=None, status="sent", error=None):
    """Record the outcome of a send attempt.

    Uses UPSERT so a lead that previously `failed` can be retried and updated
    rather than raising a UNIQUE violation.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sent_emails
                (email, first_name, last_name, company_name, linkedin_url,
                 icebreaker, subject, provider_msg_id, status, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                status          = excluded.status,
                error           = excluded.error,
                icebreaker      = excluded.icebreaker,
                subject         = excluded.subject,
                provider_msg_id = excluded.provider_msg_id,
                sent_at         = datetime('now')
            """,
            (lead["email"], lead.get("first_name"), lead.get("last_name"),
             lead.get("company_name"), lead.get("linkedin_url"),
             icebreaker, subject, provider_msg_id, status, error),
        )


def suppress(email: str, reason: str = "manual"):
    """Add an address to the suppression list (idempotent)."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO suppressed (email, reason) VALUES (?, ?)",
            (email, reason),
        )


if __name__ == "__main__":
    init_db()
