# -*- coding: utf-8 -*-
"""Drafts a KPMG Post-Dinner Strategic Brief via the Claude API.

One-shot, on-demand drafting only -- there is no ongoing monitoring of
attendees' public statements. The "hook" (a recent public quote, if any)
is pasted in by a human for this one generation; the model is instructed
to never invent a quote or fact it wasn't given.

Every flagged attendee, the recap summary, and the cited-material list are
drafted in a single call so the summary is genuinely derived from the same
pass that wrote the persona sections, rather than a second API call
re-summarizing them.

The KPMG sender for each section is chosen only from the dinner's actual
linked KPMG Team attendees (never invented), matched by Focus Area against
the attendee's role -- this scales to any number of KPMG Team members with
no code changes, since the roster and the schema's sender enum are built
dynamically from whatever is passed in.
"""
import json

import anthropic

MODEL = "claude-opus-5"
MAX_TOKENS = 16000


def _build_schema(attendee_ids, sender_names):
    return {
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "description": "One entry per flagged attendee, same order as given.",
                "items": {
                    "type": "object",
                    "properties": {
                        "attendeeId": {
                            "type": "string",
                            "enum": attendee_ids,
                            "description": "Echo back the exact attendeeId given for this person.",
                        },
                        "whyNow": {
                            "type": "string",
                            "description": "1-2 sentences on why a follow-up with this person is worth doing now.",
                        },
                        "kpmgAngle": {
                            "type": "string",
                            "description": (
                                "How KPMG's capabilities connect to this person's role and authority. "
                                "Cites matching Reference Library titles by exact name when genuinely "
                                "relevant, grounded in the assigned sender's real bio and focus areas, "
                                "and says plainly when nothing matches."
                            ),
                        },
                        "recommendedFollowUps": {
                            "type": "array",
                            "description": (
                                "2-4 distinct, dense, single-sentence recommendations -- each one combines a "
                                "channel, a specific cited KPMG asset, a specific timely hook, and a specific "
                                "offer into one sentence someone could act on immediately."
                            ),
                            "items": {
                                "type": "string",
                                "description": (
                                    "One dense sentence, e.g. \"Send email about dinner, attach 'From good to "
                                    "great,' mention that if Ballot Prop 4 passes there will be a real "
                                    "consolidation challenge across the 18 agencies, and offer to share how "
                                    "KPMG has approached that exact kind of consolidation with a different "
                                    "government agency.\""
                                ),
                            },
                        },
                        "sender": {
                            "type": "string",
                            "enum": sender_names,
                            "description": "The name of whichever actual KPMG attendee's focus areas best fit this person.",
                        },
                    },
                    "required": ["attendeeId", "whyNow", "kpmgAngle", "recommendedFollowUps", "sender"],
                    "additionalProperties": False,
                },
            },
            "followUpAreas": {
                "type": "array",
                "description": "One entry per flagged attendee -- a 10-second skim list, not a repeat of whyNow.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "reason": {
                            "type": "string",
                            "description": "A single clause, under ~12 words, on why they're worth following up on.",
                        },
                    },
                    "required": ["name", "reason"],
                    "additionalProperties": False,
                },
            },
            "relevantMaterial": {
                "type": "array",
                "description": (
                    "Every KPMG Reference Library item genuinely cited in any section above, "
                    "deduplicated by title. Empty if nothing was cited."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "url": {"type": "string"},
                    },
                    "required": ["title", "summary"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["sections", "followUpAreas", "relevantMaterial"],
        "additionalProperties": False,
    }


SYSTEM_PROMPT = """You are drafting a confidential Post-Dinner Strategic Brief for KPMG's government advisory \
team, prepared by In The Room Media after a private dinner KPMG hosted with government and civic leaders.

You will be given: the dinner's flagged attendees (present AND worth a priority follow-up), the dinner's actual \
KPMG attendees (their name, title, focus areas, and bio), themes discussed at the dinner, and the KPMG Reference \
Library.

For EACH flagged attendee, in the same order given, draft one entry in `sections`:
- attendeeId: echo back the exact attendeeId given for this person.
- whyNow: 1-2 sentences on why a follow-up with this person is worth doing now. Ground this ONLY in their stated \
role, bio, and (if provided) their recent public quote or hook. If no hook was provided, keep this honest and \
general -- do not invent one.
- kpmgAngle: How KPMG's relevant capabilities connect to this person's role and authority. Cite matching \
Reference Library titles by their EXACT name only when genuinely relevant -- if nothing in the library is a \
good match, say so plainly rather than forcing a connection. Also ground this in the assigned sender's real \
bio and focus areas, referencing their actual background honestly rather than generically.
- recommendedFollowUps: 2-4 distinct, dense, single-sentence recommendations, each one concrete enough to act \
on immediately. Every sentence should combine, where genuinely applicable: the CHANNEL (e.g. send an email, a \
short note, a text), the SPECIFIC KPMG Reference Library asset to attach or share (cite its exact title -- \
never invent one), the SPECIFIC timely hook to mention (drawn from their bio, their public quote/hook, or a \
concrete detail from the dinner's themes -- never invented), and the SPECIFIC value-add or offer being made. \
For example: "Send email about dinner, attach 'From good to great,' mention that if Ballot Prop 4 passes there \
will be a real consolidation challenge across the 18 agencies, and offer to share how KPMG has approached that \
exact kind of consolidation with a different government agency." NEVER write a generic recommendation like \
"share relevant KPMG content" -- every recommendation must name the actual asset, the actual hook, and the \
actual offer. If nothing in the Reference Library is a genuine match for a given recommendation, don't force \
one in -- build that recommendation around the hook/theme and a general offer to help instead. This is NOT a \
sales pitch -- keep every recommendation low-pressure and relationship-first (referencing something genuine, \
sharing a resource, extending an invitation), never a hard ask like "schedule a call to discuss our services."
- sender: the name of whichever KPMG attendee's focus areas best match this person's role and sector -- still \
useful context for whoever acts on these recommendations. Choose ONLY from the KPMG attendees you were given -- \
never invent a KPMG sender who isn't in that list. If only one KPMG attendee is listed, every section's sender \
must be that person.

After drafting all sections, also produce:
- followUpAreas: one entry per flagged attendee -- {name, reason}, where reason is a single clause (under ~12 \
words) capturing why they're worth following up on. This is a 10-second skim list, not a repeat of whyNow.
- relevantMaterial: every KPMG Reference Library item you genuinely cited in ANY section above, deduplicated by \
title -- {title, summary, url}. Copy the title, summary, and Source URL (if one was given) exactly from the \
library -- never invent or alter a URL, and leave url empty if none was given for that item. If nothing in the \
Reference Library was cited anywhere, return an empty array -- do not force a citation just to fill this list.

Critical constraints, in priority order:
1. NEVER invent a quote, statistic, or specific fact about any attendee. If no hook was provided for someone, \
stay general and grounded only in their bio/role.
2. NEVER fabricate a KPMG Reference Library title, URL, or claim a match that isn't genuinely relevant.
3. NEVER assign a sender who isn't one of the actual KPMG attendees you were given.
4. Keep every recommendation low-pressure and relationship-first above everything else -- this matters more \
than any other instruction here. Recommendations are options for the partner to execute in their own words, \
not a script -- never phrase one as prose addressed to the attendee or as if it were an email itself, and \
never leave one generic when a specific asset, hook, or offer is available.

Respond with only the JSON object -- no other text."""


def _format_kpmg_team(kpmg_team_records):
    lines = []
    for rec in kpmg_team_records:
        f = rec.get("fields", {})
        name = f.get("Name", "")
        title = f.get("Title", "")
        focus = ", ".join(f.get("Focus Areas") or [])
        bio = f.get("Bio") or "(none on file)"
        lines.append(f'- {name} ({title or "KPMG"}). Focus areas: {focus or "(none listed)"}. Bio: {bio}')
    return "\n".join(lines)


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
        url = f.get("Source URL", "")
        url_part = f" Source URL: {url}" if url else ""
        lines.append(f'- "{title}" ({kind}; topics: {topics}): {summary}{url_part}')
    return "\n".join(lines)


def _format_attendees(flagged_attendees):
    blocks = []
    for a in flagged_attendees:
        blocks.append(f"""attendeeId: {a['id']}
Name: {a.get('name', '')}
Role: {a.get('role', '')}
Organization: {a.get('org', '')}
Sector: {a.get('sector', '')}
Bio: {a.get('bio') or '(none on file)'}
Reason for inviting: {a.get('reason') or '(none on file)'}
Recent public quote or hook (human-provided, optional): {a.get('hook') or '(none provided)'}""")
    return "\n---\n".join(blocks)


def _build_user_content(flagged_attendees, themes, reference_records, kpmg_team_records):
    theme_text = "\n".join(f"- {t}" for t in themes if t and t.strip()) or "(No themes recorded.)"
    return f"""Flagged dinner attendees (draft one section per person, in this order):
{_format_attendees(flagged_attendees)}

Themes discussed at the dinner:
{theme_text}

KPMG attendees at this dinner (choose each section's sender only from this list):
{_format_kpmg_team(kpmg_team_records)}

KPMG Reference Library:
{_format_reference_library(reference_records)}"""


def generate_brief(flagged_attendees, themes, reference_records, kpmg_team_records):
    """flagged_attendees: list of attendee dicts (name/role/org/sector/bio/reason/hook), each with an 'id'.
    themes: list of conversation-theme strings from the dinner.
    reference_records: raw KPMG Reference Library records from Airtable.
    kpmg_team_records: raw KPMG Team records for this dinner's linked KPMG Attendees (non-empty).
    Returns {"sections": [...], "followUpAreas": [...], "relevantMaterial": [...]}.
    """
    attendee_ids = [a["id"] for a in flagged_attendees]
    sender_names = [rec.get("fields", {}).get("Name", "") for rec in kpmg_team_records]

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": _build_schema(attendee_ids, sender_names)}},
        messages=[{
            "role": "user",
            "content": _build_user_content(flagged_attendees, themes, reference_records, kpmg_team_records),
        }],
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
