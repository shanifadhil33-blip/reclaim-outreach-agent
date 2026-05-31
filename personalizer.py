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


# --- Opening line: a personalized statement of the core problem --------------
# The email leads with the prospect's pain. Placeholders: {company}, {position}.
# Each variant states the EOB-denial problem and is true for any solo biller —
# never a specific result or fact we didn't scrape.
ICEBREAKER_VARIANTS = [
    "Running {company} as a {position}, you've probably lost whole afternoons hunting denied claims through 50-page faxed EOBs.",
    "At {company}, the manual EOB denial hunt likely eats 10-15 hours of your month - time you can't bill for.",
    "As a {position}, a real chunk of your week probably disappears into reading faxed EOBs just to find the denied claims.",
    "Digging denied claims out of 50-page faxed EOBs by hand is probably one of the worst parts of running {company}.",
    "Reading faxed EOBs line by line to catch every denial is slow, draining work - and at {company} it's likely on you alone.",
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
