# -*- coding: utf-8 -*-
"""Dinner Persona Builder.

Airtable is the database (Dinners + Dinner Attendees tables in ITRM
Operations). Edit Bio / Reason for Inviting / Sector directly in Airtable
and it flows through automatically next time a PDF is generated here.
Photos can be dragged in either on this page or directly onto the Photo
attachment field in Airtable -- both write to the same place.
"""
import io
import os

from flask import Flask, abort, jsonify, render_template, request, send_file

import airtable_client as at
from pdf_builder import build_pdf

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
    return render_template("dinner.html", dinner=dinner, attendees=attendees)


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
