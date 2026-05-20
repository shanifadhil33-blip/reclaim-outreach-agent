"""
personalizer.py — Step 3: per-lead email content (icebreaker + subject line).

Everything here is deterministic. No AI, no API calls — so nothing can
hallucinate or invent facts. Each lead gets one hand-written variant of
each, chosen by hashing the lead's email. That makes the choice:
  - stable  — the same lead always gets the same line across reruns
  - spread  — adjacent leads get different lines, so a batch doesn't look
              obviously mass-mailed

To change the voice, edit the variant lists below — that is the only thing
controlling how the opener and subject read.
"""

import hashlib


# --- Icebreaker: the personalized opening sentence ---------------------------
# Placeholders: {company}, {position}. Each states something relatable and
# true for a solo biller — never a specific result or fact we didn't scrape.
ICEBREAKER_VARIANTS = [
    "Running {company} as a {position} means every claim ultimately lands on your desk.",
    "Handling {company} on your own as a {position}, your time is pretty much the whole business.",
    "Most independent billers I talk to are stretched thin, and I'd guess {company} keeps you just as busy.",
    "Keeping {company} going single-handed is a real grind for any {position}.",
    "As a {position}, you're the biller, the follow-up chaser, and the admin for {company} all at once.",
]

# --- Subject line ------------------------------------------------------------
# Placeholder: {first_name}. Short and curiosity-driven; deliberately no
# spam-trigger words ("free", "!", ALL CAPS). Rotating these lets you see
# which subject pulls the most opens in the MailerSend dashboard.
SUBJECT_VARIANTS = [
    "15 hours back, {first_name}?",
    "the EOB denial grind",
    "{first_name} - quick question on denials",
    "denials, minus the busywork",
    "{first_name}, about that EOB pile",
]

DEFAULT_COMPANY = "your billing practice"
DEFAULT_POSITION = "medical biller"


def _pick(variants: list[str], lead: dict, salt: str) -> str:
    """Deterministically choose one variant for this lead.

    `salt` decorrelates the choice, so a lead's subject and icebreaker are
    not locked to the same variant index.
    """
    key = ((lead.get("email") or "") + "|" + salt).encode("utf-8")
    index = int(hashlib.md5(key).hexdigest(), 16) % len(variants)
    return variants[index]


def generate_icebreaker(lead: dict) -> str:
    """Return one hand-written icebreaker sentence, built only from scraped data."""
    company = (lead.get("company_name") or "").strip() or DEFAULT_COMPANY
    # Lowercased so the title reads naturally mid-sentence ("as a medical biller").
    position = (lead.get("position") or "").strip().lower() or DEFAULT_POSITION
    return _pick(ICEBREAKER_VARIANTS, lead, "icebreaker").format(
        company=company, position=position
    )


def pick_subject(lead: dict) -> str:
    """Return one subject line for this lead, chosen deterministically."""
    first_name = (lead.get("first_name") or "").strip() or "there"
    return _pick(SUBJECT_VARIANTS, lead, "subject").format(first_name=first_name)
