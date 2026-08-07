# -*- coding: utf-8 -*-
"""Drafts KPMG Post-Dinner Strategic Brief sections via the Claude API.

One-shot, on-demand drafting only -- there is no ongoing monitoring of
attendees' public statements. The "hook" (a recent public quote, if any)
is pasted in by a human for this one generation; the model is instructed
to never invent a quote or fact it wasn't given.
"""
import json

import anthropic

MODEL = "claude-opus-5"

SENDER_OPTIONS = ["Cindy Cohen", "Denis Serdiouk"]

BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "whyNow": {
            "type": "string",
            "description": "1-2 sentences on why a follow-up with this person is worth doing now.",
        },
        "kpmgAngle": {
            "type": "string",
            "description": (
                "How KPMG's capabilities connect to this person's role and authority. "
                "Cites matching Reference Library titles by exact name when genuinely "
                "relevant, and says plainly when nothing matches."
            ),
        },
        "emailSubject": {"type": "string"},
        "emailBody": {
            "type": "string",
            "description": "A short, low-pressure, relationship-first follow-up email draft.",
        },
        "sender": {"type": "string", "enum": SENDER_OPTIONS},
    },
    "required": ["whyNow", "kpmgAngle", "emailSubject", "emailBody", "sender"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are drafting one section of a confidential Post-Dinner Strategic Brief for KPMG's \
government advisory team, prepared by In The Room Media after a private dinner KPMG hosted with government \
and civic leaders.

For the single attendee described in the user message, produce strict JSON matching the given schema:

- whyNow: 1-2 sentences on why a follow-up with this person is worth doing now. Ground this ONLY in their \
stated role, bio, and (if provided) their recent public quote or hook. If no hook was provided, keep this \
honest and general -- do not invent one.
- kpmgAngle: How KPMG's relevant capabilities connect to this person's role and authority. You are given a \
list of KPMG Reference Library assets (title, type, topics, summary). Cite matching titles by their EXACT \
name only when they are genuinely relevant to this person's role and authority. If nothing in the library is \
a good match, say so plainly and honestly rather than forcing a connection.
- emailSubject / emailBody: A short, warm, low-pressure, relationship-first follow-up email. This is NOT a \
sales pitch -- no hard asks, no "let's schedule a call to discuss our services." It should read like a \
genuine personal follow-up from someone who enjoyed the conversation, referencing the dinner and (if given) \
their hook, and optionally offering something useful (an article, a relevant KPMG resource, an introduction) \
with zero pressure to reply or meet.
- sender: choose whichever of the two KPMG senders described in the user message best fits the angle and \
this person's sector/domain.

Critical constraints, in priority order:
1. NEVER invent a quote, statistic, or specific fact about this person. If no hook was provided, stay general \
and grounded only in their bio/role.
2. NEVER fabricate a KPMG Reference Library title or claim a match that isn't genuinely relevant.
3. Keep the email low-pressure and relationship-first above everything else -- this matters more than any \
other instruction here.

Respond with only the JSON object -- no other text."""

SENDER_BIOS = (
    "Cindy Cohen (KPMG's Housing Leader and State & Local Government Advisory Principal) or "
    "Denis Serdiouk (KPMG Advisory Director with hands-on multi-agency delivery experience)"
)


def _format_reference_library(reference_records):
    if not reference_records:
        return "(No KPMG Reference Library assets are available.)"
    lines = []
    for rec in reference_records:
        f = rec.get("fields", {})
        title = f.get("Title", "")
        kind = f.get("Type", "")
        topics = ", ".join(f.get("Topic Tags") or [])
        summary = f.get("Summary", "")
        lines.append(f'- "{title}" ({kind}; topics: {topics}): {summary}')
    return "\n".join(lines)


def _build_user_content(attendee, themes, reference_records):
    theme_text = "\n".join(f"- {t}" for t in themes if t and t.strip()) or "(No themes recorded.)"
    return f"""Attendee:
- Name: {attendee.get('name', '')}
- Role: {attendee.get('role', '')}
- Organization: {attendee.get('org', '')}
- Sector: {attendee.get('sector', '')}
- Bio: {attendee.get('bio') or '(none on file)'}
- Reason for inviting: {attendee.get('reason') or '(none on file)'}
- Recent public quote or hook (human-provided, optional): {attendee.get('hook') or '(none provided)'}

Themes discussed at the dinner:
{theme_text}

KPMG senders to choose from: {SENDER_BIOS}

KPMG Reference Library:
{_format_reference_library(reference_records)}"""


def generate_brief_section(attendee, themes, reference_records):
    """attendee: dict with name/role/org/sector/bio/reason/hook.
    themes: list of conversation-theme strings from the dinner.
    reference_records: raw KPMG Reference Library records from Airtable.
    Returns a dict matching BRIEF_SCHEMA.
    """
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": BRIEF_SCHEMA}},
        messages=[{"role": "user", "content": _build_user_content(attendee, themes, reference_records)}],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
