# -*- coding: utf-8 -*-
"""Thin wrapper around the Airtable REST API for the Dinner Persona Builder.

No SDK dependency -- just `requests`, mirroring the pattern of the existing
SATA Carousel Builder (reads live from Airtable, no local cache of content).
"""
import base64
import os

import requests

AIRTABLE_API_KEY = os.environ["AIRTABLE_API_KEY"]
BASE_ID = os.environ.get("AIRTABLE_BASE_ID", "appRgPaSgXtzA3xpP")
DINNERS_TABLE = os.environ.get("AIRTABLE_DINNERS_TABLE", "Dinners")
ATTENDEES_TABLE = os.environ.get("AIRTABLE_ATTENDEES_TABLE", "Dinner Attendees")

API_ROOT = "https://api.airtable.com/v0"
CONTENT_ROOT = "https://content.airtable.com/v0"

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json",
}


def _get(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _patch(url, payload):
    resp = requests.patch(url, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def list_dinners():
    """Return all Dinners records, most recently created last-in-first-out isn't
    guaranteed by Airtable, so we just return them as-is."""
    records = []
    offset = None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        data = _get(f"{API_ROOT}/{BASE_ID}/{DINNERS_TABLE}", params=params)
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def get_dinner(dinner_record_id):
    return _get(f"{API_ROOT}/{BASE_ID}/{DINNERS_TABLE}/{dinner_record_id}")


def list_attendees_for_dinner(dinner_record_id):
    """Fetch every attendee record and filter client-side on the linked Dinner
    field. Simpler and more robust than building a filterByFormula string,
    and attendee counts per dinner are small (~20)."""
    records = []
    offset = None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        data = _get(f"{API_ROOT}/{BASE_ID}/{ATTENDEES_TABLE}", params=params)
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break

    def linked(rec):
        return dinner_record_id in (rec.get("fields", {}).get("Dinner") or [])

    return [r for r in records if linked(rec=r)]


def clear_photo(attendee_record_id):
    """Clear the Photo attachment field before uploading a replacement, so a
    drag-and-drop always results in exactly one photo per attendee."""
    url = f"{API_ROOT}/{BASE_ID}/{ATTENDEES_TABLE}/{attendee_record_id}"
    return _patch(url, {"fields": {"Photo": []}})


def upload_photo(attendee_record_id, filename, content_type, file_bytes):
    """Upload a headshot via Airtable's attachment upload endpoint.
    Clears any existing photo first so there's always exactly one."""
    clear_photo(attendee_record_id)
    url = f"{CONTENT_ROOT}/{BASE_ID}/{attendee_record_id}/Photo/uploadAttachment"
    payload = {
        "contentType": content_type or "image/jpeg",
        "file": base64.b64encode(file_bytes).decode("ascii"),
        "filename": filename or "photo.jpg",
    }
    resp = requests.post(url, headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()
