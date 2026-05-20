"""
suppress_email.py — opt-out helper for the manual unsubscribe workflow.

When a prospect replies asking to be removed, run this. CAN-SPAM requires
honoring opt-out requests within 10 business days; doing it immediately also
protects your sending domain's reputation. Once suppressed, main.py will
never email that address again.

Usage:
    python suppress_email.py someone@example.com
    python suppress_email.py someone@example.com complaint
    python suppress_email.py someone@example.com bounce
"""

import sys

from database import init_db, suppress, is_suppressed

VALID_REASONS = {"unsubscribe", "bounce", "complaint", "manual"}


def main():
    if len(sys.argv) < 2:
        print("Usage: python suppress_email.py <email> [unsubscribe|bounce|complaint|manual]")
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    reason = sys.argv[2].strip().lower() if len(sys.argv) > 2 else "unsubscribe"
    if reason not in VALID_REASONS:
        print(f"Unknown reason '{reason}'. Use one of: {', '.join(sorted(VALID_REASONS))}")
        sys.exit(1)

    init_db()
    if is_suppressed(email):
        print(f"{email} is already on the suppression list.")
        return

    suppress(email, reason)
    print(f"Suppressed {email} (reason: {reason}). It will not be emailed again.")


if __name__ == "__main__":
    main()
