"""
email_sender.py — Step 5: send one plain-text email via the MailerSend API.

Free tier: 3,000 emails/month. Requires a verified sending domain.

IMPORTANT: while your MailerSend account is on the trial plan (domain not yet
approved) you can ONLY send to your own account email. Verify your domain and
request trial approval before running against a real lead list.

Raises on any non-success response so main.py logs the lead as `failed`.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

MAILERSEND_API_KEY = os.getenv("MAILERSEND_API_KEY", "")
MAILERSEND_URL     = "https://api.mailersend.com/v1/email"

SENDER_EMAIL   = os.getenv("SENDER_EMAIL", "")
SENDER_NAME    = os.getenv("SENDER_NAME", "Reclaim")
REPLY_TO_EMAIL = os.getenv("REPLY_TO_EMAIL", "") or SENDER_EMAIL  # replies hit your inbox


def send_email(to_email: str, subject: str, body: str, timeout: int = 30) -> str:
    """Send the email and return MailerSend's message id on success."""
    if not MAILERSEND_API_KEY:
        raise RuntimeError("MAILERSEND_API_KEY is not set in .env")
    if not SENDER_EMAIL:
        raise RuntimeError("SENDER_EMAIL is not set in .env")

    payload = {
        "from":    {"email": SENDER_EMAIL, "name": SENDER_NAME},
        "to":      [{"email": to_email}],
        "subject": subject,
        "text":    body,
        # MailerSend logs clicks/opens server-side; view them in the dashboard
        # under Analytics. track_clicks rewrites links; track_opens adds a
        # 1px pixel (invisible — not a content image).
        "settings": {
            "track_clicks": True,
            "track_opens":  True,
        },
    }
    if REPLY_TO_EMAIL:
        payload["reply_to"] = {"email": REPLY_TO_EMAIL}

    resp = requests.post(
        MAILERSEND_URL,
        headers={
            "Authorization": f"Bearer {MAILERSEND_API_KEY}",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        json=payload,
        timeout=timeout,
    )

    # MailerSend returns 202 Accepted on a successful queue.
    if resp.status_code != 202:
        raise RuntimeError(
            f"MailerSend send failed (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    return resp.headers.get("x-message-id", "accepted-no-id")
