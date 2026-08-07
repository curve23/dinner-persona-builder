# -*- coding: utf-8 -*-
"""Dinner Persona Builder.

Airtable is the database (Dinners + Dinner Attendees tables in ITRM
Operations). Edit Bio / Reason for Inviting / Sector directly in Airtable
and it flows through automatically next time a PDF is generated here.
Photos can be dragged in either on this page or directly onto the Photo
attachment field in Airtable -- both write to the same place.
"""
import datetime
import io
import os

from flask import Flask, abort, jsonify, render_template, request, send_file

import airtable_client as at
import claude_client
from pdf_builder import build_brief_pdf, build_pdf

app = Flask(__name__)


def _dinner_view(rec):
    f = rec.get("fields", {})
    return {
        "id": rec["id"],
        "name": f.get("Dinner Name", "Untitled Dinner"),
        "date": f.get("Date"),
        "theme": f.get("Theme", ""),
        "status": f.get("Status", ""),
        "venue": f.get("Venue", ""),
    }


def _attendee_view(rec):
    f = rec.get("fields", {})
    photos = f.get("Photo") or []
    photo_url = photos[0]["url"] if photos else None
    photo_thumb = (
        photos[0].get("thumbnails", {}).get("large", {}).get("url", photo_url)
        if photos else None
    )
    return {
        "id": rec["id"],
        "name": f.get("Name", ""),
        "role": f.get("Role", ""),
        "org": f.get("Organization", ""),
        "location": f.get("Location", ""),
        "sector": f.get("Sector", "Other"),
        "bio": f.get("Bio", ""),
        "reason": f.get("Reason for Inviting", ""),
        "rsvp": f.get("RSVP Status", ""),
        "photo_url": photo_url,
        "photo_thumb": photo_thumb,
    }


@app.route("/")
def index():
    dinners = [_dinner_view(r) for r in at.list_dinners()]
    dinners.sort(key=lambda d: d.get("date") or "", reverse=True)
    return render_template("index.html", dinners=dinners)


@app.route("/dinner/<dinner_id>")
def dinner_detail(dinner_id):
    dinner = _dinner_view(at.get_dinner(dinner_id))
    attendees = [_attendee_view(r) for r in at.list_attendees_for_dinner(dinner_id)]
    attendees.sort(key=lambda a: a["name"])
    return render_template(
        "dinner.html",
        dinner=dinner,
        attendees=attendees,
        sector_choices=at.SECTOR_CHOICES,
    )


@app.route("/dinner/<dinner_id>/attendee/<attendee_id>/field", methods=["POST"])
def update_attendee_field(dinner_id, attendee_id):
    data = request.get_json(force=True, silent=True) or {}
    field = data.get("field")
    value = data.get("value", "")
    try:
        at.update_attendee_field(attendee_id, field, value)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Airtable update failed"}), 502
    return jsonify({"ok": True})


@app.route("/dinner/<dinner_id>/field", methods=["POST"])
def update_dinner_field(dinner_id):
    data = request.get_json(force=True, silent=True) or {}
    field = data.get("field")
    value = data.get("value", "")
    try:
        at.update_dinner_field(dinner_id, field, value)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Airtable update failed"}), 502
    return jsonify({"ok": True})


@app.route("/dinner/<dinner_id>/attendee/<attendee_id>/photo", methods=["POST"])
def upload_photo(dinner_id, attendee_id):
    file = request.files.get("photo")
    if not file:
        return jsonify({"error": "No file provided"}), 400
    file_bytes = file.read()
    if len(file_bytes) > 8 * 1024 * 1024:
        return jsonify({"error": "File too large (8MB max)"}), 400
    result = at.upload_photo(
        attendee_id,
        filename=file.filename,
        content_type=file.mimetype,
        file_bytes=file_bytes,
    )
    photos = result.get("fields", {}).get("Photo") or []
    photo_url = photos[0]["url"] if photos else None
    return jsonify({"ok": True, "photo_url": photo_url})


@app.route("/dinner/<dinner_id>/pdf")
def dinner_pdf(dinner_id):
    dinner = _dinner_view(at.get_dinner(dinner_id))
    attendees = [_attendee_view(r) for r in at.list_attendees_for_dinner(dinner_id)]
    if not attendees:
        abort(400, "This dinner has no attendees linked yet.")
    attendees.sort(key=lambda a: a["name"])
    pdf_bytes = build_pdf(dinner, attendees)
    filename = f"{dinner['name'].replace(' ', '_')}_Guest_Personas.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=filename,
    )


@app.route("/dinner/<dinner_id>/brief")
def dinner_brief(dinner_id):
    dinner = _dinner_view(at.get_dinner(dinner_id))
    attendees = [_attendee_view(r) for r in at.list_attendees_for_dinner(dinner_id)]
    attendees.sort(key=lambda a: a["name"])
    return render_template("brief.html", dinner=dinner, attendees=attendees)


@app.route("/dinner/<dinner_id>/brief/generate", methods=["POST"])
def generate_brief(dinner_id):
    data = request.get_json(force=True, silent=True) or {}
    themes = data.get("themes") or []
    selections = data.get("selections") or {}

    attendees = [_attendee_view(r) for r in at.list_attendees_for_dinner(dinner_id)]

    flagged = []
    for a in attendees:
        sel = selections.get(a["id"]) or {}
        if sel.get("attended") and sel.get("priority"):
            a = dict(a)
            a["hook"] = (sel.get("hook") or "").strip()
            flagged.append(a)

    if not flagged:
        return jsonify({"error": "No attendees are flagged as both Attended and Priority follow-up."}), 400

    try:
        reference_records = at.list_reference_library()
    except Exception:
        return jsonify({"error": "Could not load the KPMG Reference Library from Airtable"}), 502

    sections = []
    for a in flagged:
        try:
            content = claude_client.generate_brief_section(a, themes, reference_records)
        except Exception as e:
            return jsonify({"error": f"Claude generation failed for {a['name']}: {e}"}), 502
        sections.append({
            "attendeeId": a["id"],
            "name": a["name"],
            "role": a["role"],
            "org": a["org"],
            "sector": a["sector"],
            "photoThumb": a["photo_thumb"],
            "hook": a["hook"],
            **content,
        })

    return jsonify({"sections": sections})


@app.route("/dinner/<dinner_id>/brief/pdf", methods=["POST"])
def dinner_brief_pdf(dinner_id):
    data = request.get_json(force=True, silent=True) or {}
    dinner = data.get("dinner") or {}
    sections = data.get("sections") or []
    if not sections:
        abort(400, "No brief sections to export.")
    pdf_bytes = build_brief_pdf(dinner, sections)
    filename = f"{(dinner.get('name') or 'Dinner').replace(' ', '_')}_KPMG_Post-Dinner_Brief.pdf"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=filename,
    )


@app.route("/dinner/<dinner_id>/brief/touchpoint", methods=["POST"])
def log_brief_touchpoint(dinner_id):
    data = request.get_json(force=True, silent=True) or {}
    dinner_name = data.get("dinnerName") or ""
    names = [n for n in (data.get("names") or []) if n]
    if not names:
        return jsonify({"error": "No flagged attendees to log."}), 400

    fields = {
        "Name": f"KPMG Post-Dinner Brief — {dinner_name}".strip(),
        "Client": "KPMG",
        "Type": "Event",
        "Date": datetime.date.today().isoformat(),
        "Description": (
            f"Post-dinner strategic brief generated for {dinner_name}, "
            f"covering {len(names)} priority follow-up(s)."
        ),
        "People": ", ".join(names),
        "Source": "Dinner Persona Builder",
    }
    try:
        at.create_touchpoint(fields)
    except Exception:
        return jsonify({"error": "Airtable write failed"}), 502
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
