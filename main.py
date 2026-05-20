"""
main.py — one outreach "tick" for the Reclaim cold email agent.

Built to run on a schedule (GitHub Actions cron). Each invocation:

  1. Ingest      — read leads.csv
  2. Filter      — skip leads already emailed or on the suppression list
  3. Personalize — build a fact-based icebreaker (personalizer.py)
  4. Assemble    — merge it into the email template
  5. Send        — transmit via MailerSend (email_sender.py)
  6. Log         — record the outcome in outreach.db

It sends at most BATCH_SIZE emails, never exceeds DAILY_CAP for the calendar
day, then exits. The schedule itself (a tick every ~15 min) provides the
human-like spacing — there is no long in-process sleep.

Config comes from environment variables: a local .env file when testing,
GitHub Actions secrets/variables in production.
"""

import csv
import os
import random
import textwrap
import time
from pathlib import Path

from dotenv import load_dotenv

from database import (
    init_db, was_emailed, is_suppressed, count_sent_today, log_send,
)
from personalizer import generate_icebreaker, pick_subject
from email_sender import send_email

load_dotenv()

# --- Configuration -----------------------------------------------------------

# `getenv("X") or default` (not the 2-arg form) so a blank env var falls back
# to the default — empty GitHub Variables would otherwise produce empty strings.
LEADS_CSV  = os.getenv("LEADS_CSV")  or "leads.csv"
DAILY_CAP  = int(os.getenv("DAILY_CAP")  or "30")   # max emails per calendar day
BATCH_SIZE = int(os.getenv("BATCH_SIZE") or "2")    # max emails per scheduled tick
DRY_RUN    = (os.getenv("DRY_RUN") or "true").lower() == "true"

# Sender identity — appears in the email and the CAN-SPAM footer.
SENDER_NAME     = os.getenv("SENDER_NAME")     or "Your Name"
SENDER_COMPANY  = os.getenv("SENDER_COMPANY")  or "Reclaim"
SENDER_ADDRESS  = os.getenv("SENDER_ADDRESS")  or "123 Example St, City, ST 00000"
UNSUBSCRIBE_URL = os.getenv("UNSUBSCRIBE_URL") or "https://yourdomain.com/unsubscribe"
APP_URL         = os.getenv("APP_URL")         or "https://yourdomain.com/try"  # the CTA link

# --- Email template ----------------------------------------------------------
# Plain text converts better than HTML for cold B2B. The footer (postal
# address + opt-out) is legally required under CAN-SPAM — do not remove it.

EMAIL_TEMPLATE = """\
Hi {first_name},

{icebreaker}

Most solo billers lose 10-15 hours a month manually hunting denied
claims through 50-page faxed EOBs - the worst part of the job.

Reclaim does only that: drop in the EOB PDF, and it pulls every
denial into a clean table and writes the appeal letters for you as
ready-to-send Word docs.

Free for 14 days - try it on your next EOB here:
{app_url}

Best,
{sender_name}
{sender_company}

--
Sent by {sender_company} as business outreach.
{sender_address}
Not a fit? Unsubscribe here: {unsubscribe_url}
"""


# --- Step 1: Ingest ----------------------------------------------------------

def load_leads(path: str) -> list[dict]:
    """Read leads.csv into a list of normalized lead dicts.

    Expected headers: FirstName, LastName, CompanyName, Title, Email, LinkedInURL.
    `utf-8-sig` strips the BOM that Apollo.io exports include.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Lead file not found: {p.resolve()}")

    leads = []
    with p.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            email = (row.get("Email") or "").strip().lower()
            if not email:
                continue  # a lead with no email is unusable
            leads.append({
                "first_name":   (row.get("FirstName") or "").strip(),
                "last_name":    (row.get("LastName") or "").strip(),
                "company_name": (row.get("CompanyName") or "").strip(),
                "position":     (row.get("Title") or "").strip(),
                "email":        email,
                "linkedin_url": (row.get("LinkedInURL") or "").strip(),
            })
    return leads


# --- Step 4: Assemble --------------------------------------------------------

def assemble_email(lead: dict, icebreaker: str) -> tuple[str, str]:
    """Return (subject, body) with the icebreaker and sender details merged in."""
    subject = pick_subject(lead)
    body = EMAIL_TEMPLATE.format(
        first_name=lead["first_name"] or "there",
        icebreaker=icebreaker,
        app_url=APP_URL,
        sender_name=SENDER_NAME,
        sender_company=SENDER_COMPANY,
        sender_address=SENDER_ADDRESS,
        unsubscribe_url=UNSUBSCRIBE_URL,
    )
    return subject, body


# --- One scheduled tick ------------------------------------------------------

def run():
    init_db()
    leads = load_leads(LEADS_CSV)
    sent_today = count_sent_today()
    print(f"Leads: {len(leads)} | sent today: {sent_today}/{DAILY_CAP} | "
          f"batch size: {BATCH_SIZE}" + ("  [DRY_RUN]" if DRY_RUN else ""))

    # How many we may send this tick: the batch size, capped by what's left today.
    budget = min(BATCH_SIZE, DAILY_CAP - sent_today)
    if budget <= 0:
        print("Daily cap already reached - nothing to send this tick.")
        return

    sent_this_tick = 0
    for lead in leads:
        if sent_this_tick >= budget:
            break
        email = lead["email"]

        # Step 2: Filter (idempotency + suppression)
        if was_emailed(email) or is_suppressed(email):
            continue

        # Steps 3-6: Personalize, Assemble, Send, Log
        try:
            icebreaker = generate_icebreaker(lead)
            subject, body = assemble_email(lead, icebreaker)

            if DRY_RUN:
                print(f"  [dry-run] -> {email} | subject: {subject}")
                print(textwrap.indent(body, "  | "))
                msg_id = "dry-run-no-id"
            else:
                msg_id = send_email(email, subject, body)  # Step 5

            log_send(lead, icebreaker=icebreaker, subject=subject,
                     provider_msg_id=msg_id, status="sent")
            sent_this_tick += 1
            print(f"[sent] {email}  ({sent_today + sent_this_tick}/{DAILY_CAP})")
        except Exception as exc:
            log_send(lead, status="failed", error=str(exc))
            print(f"[fail] {email} - {exc}")

        # Small jitter between the few sends in one tick — NOT the long throttle.
        # The 15-minute schedule is what spaces emails out across the day.
        if sent_this_tick < budget:
            time.sleep(1 if DRY_RUN else random.randint(5, 25))

    if sent_this_tick == 0:
        print("No new leads to email (list exhausted, or all filtered).")
    else:
        print(f"Tick complete: {sent_this_tick} email(s) sent.")


if __name__ == "__main__":
    run()
