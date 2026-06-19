from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import anthropic

from .models import ClientProfile, Firm

log = logging.getLogger(__name__)


SYSTEM = """\
You write concise, professional outreach emails from a prospective client \
to a personal-injury/mass-tort law firm.

Hard rules:
- The client is a real person seeking representation; the tone is sincere, \
  not a marketing pitch.
- Never invent facts. Use exactly what the client profile and firm hints \
  provide. If a date is missing, write the placeholder verbatim \
  (e.g. "[INJURY_DATE]"). Do NOT replace placeholders with guesses.
- Keep the body under 200 words. Plain text. No marketing fluff, no \
  emojis, no markdown.
- Vary phrasing per firm — never reuse the same opening sentence.
- Mention the firm by name once. If personalization_hints are provided, \
  reference one concrete signal (e.g. their role in the TDF JCCP, a \
  specific case they led). Otherwise stay generic.
- Subject line: short, specific, no "URGENT" or all-caps. Include \
  "Truvada" or "TDF" so intake routes it correctly.
- Sign with the client's full name, city/state, and phone — no titles, \
  no "Esq.", no postscript.

Output strict JSON with keys: subject, body. No prose around the JSON.
"""


@dataclass
class Composed:
    subject: str
    body: str


def compose_email(
    client: anthropic.Anthropic,
    model: str,
    firm: Firm,
    profile: ClientProfile,
) -> Composed:
    user_payload = {
        "firm": {
            "name": firm.name,
            "personalization_hints": firm.personalization_hints,
            "intake_email": firm.intake_email,
            "location": firm.location,
        },
        "client": {
            "full_name": profile.full_name,
            "city": profile.city,
            "state": profile.state,
            "age": profile.age,
            "sex": profile.sex,
            "phone": profile.phone,
            "email": profile.email,
            "indication": profile.indication,
            "truvada_start_year": profile.truvada_start_year,
            "truvada_still_taking": profile.truvada_still_taking,
            "injury_summary": profile.injury_summary,
            "injury_date": profile.injury_date,
            "diagnosing_provider": profile.diagnosing_provider,
            "dexa_findings": profile.dexa_findings,
            "treating_specialty": profile.treating_specialty,
            "other_relevant": profile.other_relevant,
        },
    }

    resp = client.messages.create(
        model=model,
        max_tokens=800,
        system=SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    "Draft an intake email. Context:\n"
                    + json.dumps(user_payload, indent=2)
                ),
            }
        ],
    )

    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return _parse(text)


def _parse(text: str) -> Composed:
    # Tolerate stray ```json fences if the model adds them.
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"composer did not return valid JSON: {e}\n{text[:400]}")
    subject = obj.get("subject", "").strip()
    body = obj.get("body", "").strip()
    if not subject or not body:
        raise RuntimeError(f"composer returned empty subject/body: {obj!r}")
    return Composed(subject=subject, body=body)
