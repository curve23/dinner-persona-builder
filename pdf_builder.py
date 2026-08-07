# -*- coding: utf-8 -*-
"""Renders the landscape guest-persona PDF from live Airtable data.

Same visual design validated with Carolyn: navy/coral/indigo/sky palette
(sourced from the SATA logo), Lato + Caladea type, sector-color-coded
sidebars, two guests per landscape page with a two-column bio/reason split.
Photos come straight from Airtable attachment URLs -- weasyprint fetches
them itself at render time, so editing a photo in Airtable is reflected on
the next PDF generation with no extra plumbing.
"""
import html

from weasyprint import HTML

NAVY = "#0B1059"
CORAL = "#FE4A4A"
INDIGO = "#3F32B0"
SKY = "#9DC5FD"
LILAC = "#988DF6"
OFFWHITE = "#FEFEFE"
INK = "#14163A"

SECTOR_COLORS = {
    "Government": NAVY,
    "Private Sector": INDIGO,
    "Nonprofit & Advocacy": CORAL,
    "Faith & Community": "#2E6F9E",
    "Media": INDIGO,
    "Other": "#5B5F8A",
}
SECTOR_TINTS = {
    "Government": "#E7E8F5",
    "Private Sector": "#EBE8FA",
    "Nonprofit & Advocacy": "#FEEAEA",
    "Faith & Community": "#EAF3FC",
    "Media": "#EBE8FA",
    "Other": "#ECECF3",
}

ROW_H = 4.25  # in, half of 8.5in landscape page height

CSS = f"""
  @page {{ size: 11in 8.5in; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: 'Lato', sans-serif; color: {INK}; }}
  .page {{
    width: 11in; height: 8.5in; page-break-after: always;
    position: relative; background: {OFFWHITE};
  }}
  .page:last-child {{ page-break-after: auto; }}

  .cover {{ background: {NAVY}; color: {OFFWHITE}; }}
  .cover-inner {{ position: absolute; left: 1.1in; top: 1.7in; width: 8.2in; text-align: left; }}
  .cover-kicker {{
    font-size: 13pt; letter-spacing: 2pt; text-transform: uppercase;
    color: {SKY}; margin-bottom: 18pt; font-weight: 700;
  }}
  .cover-title {{
    font-family: 'Caladea', Georgia, serif; font-size: 46pt; line-height: 1.1;
    margin: 0 0 10pt 0; font-weight: 700;
  }}
  .cover-sub {{ font-size: 16pt; color: {LILAC}; margin-bottom: 20pt; font-weight: 700; }}
  .cover-desc {{ font-size: 12.5pt; line-height: 1.6; max-width: 7.2in; color: #DCE0F5; margin-bottom: 24pt; }}
  .cover-legend {{ display: flex; gap: 24pt; flex-wrap: wrap; }}
  .legend-item {{ font-size: 10.5pt; color: {OFFWHITE}; display: flex; align-items: center; font-weight: 700; }}
  .dot {{ width: 10pt; height: 10pt; border-radius: 50%; display: inline-block; margin-right: 6pt; border: 1.2pt solid rgba(255,255,255,0.85); }}

  .sidebar {{
    position: absolute; left: 0; width: 2.15in; height: {ROW_H}in;
    padding: 0.3in 0.28in; color: {OFFWHITE};
  }}
  .avatar {{
    width: 1.55in; height: 1.55in; border-radius: 50%; border: 2.5pt solid {OFFWHITE};
    background: rgba(255,255,255,0.14); display: table-cell; text-align: center;
    vertical-align: middle; font-family: 'Caladea', Georgia, serif; font-size: 32pt;
    font-weight: 700; margin-bottom: 0.24in; overflow: hidden;
  }}
  .avatar img {{ width: 1.55in; height: 1.55in; object-fit: cover; border-radius: 50%; display: block; }}
  .sector-tag {{
    display: inline-block; font-size: 9pt; text-transform: uppercase; letter-spacing: 1pt;
    font-weight: 700; background: rgba(255,255,255,0.18); padding: 6pt 9pt; border-radius: 3pt;
    margin-bottom: 12pt; line-height: 1.35;
  }}
  .location {{ font-size: 10.5pt; font-weight: 400; opacity: 0.92; }}
  .location-label {{
    font-size: 7.5pt; text-transform: uppercase; letter-spacing: 1pt; opacity: 0.65;
    margin-bottom: 3pt; font-weight: 700;
  }}

  .content {{ position: absolute; left: 2.15in; width: 8.35in; height: {ROW_H}in; padding: 0.4in 0.5in 0.3in 0.35in; }}
  .kicker {{ font-size: 8.5pt; text-transform: uppercase; letter-spacing: 1.6pt; font-weight: 700; margin-bottom: 6pt; }}
  .content h1 {{ font-family: 'Caladea', Georgia, serif; font-size: 25pt; margin: 0 0 6pt 0; color: {NAVY}; line-height: 1.08; }}
  .role-line {{ font-size: 11.3pt; margin-bottom: 12pt; color: #3A3D5C; line-height: 1.4; }}
  .role-line .role {{ font-weight: 700; }}
  .role-line .org {{ font-weight: 400; }}
  .rule {{ width: 0.55in; height: 2.5pt; margin-bottom: 15pt; }}
  .two-col {{ width: 100%; }}
  .two-col::after {{ content: ""; display: block; clear: both; }}
  .bio {{ float: left; width: 47%; font-size: 10.8pt; line-height: 1.58; color: {INK}; }}
  .reason-block {{ float: right; width: 47%; padding: 14pt 17pt; border-radius: 2pt; }}
  .reason-label {{ font-size: 8pt; text-transform: uppercase; letter-spacing: 1pt; font-weight: 700; margin-bottom: 6pt; }}
  .reason-text {{ font-size: 10.8pt; line-height: 1.55; color: {INK}; }}

  .brief-sidebar {{
    position: absolute; left: 0; top: 0; width: 2.15in; height: 8.5in;
    padding: 0.5in 0.28in; color: {OFFWHITE}; text-align: center;
  }}
  .brief-content {{
    position: absolute; left: 2.15in; top: 0; width: 8.35in; height: 8.5in;
    padding: 0.55in 0.6in 0.5in 0.45in;
  }}
  .brief-section {{ margin-bottom: 16pt; }}
  .brief-label {{
    font-size: 9pt; text-transform: uppercase; letter-spacing: 1pt; font-weight: 700;
    margin-bottom: 5pt;
  }}
  .brief-text {{ font-size: 11pt; line-height: 1.55; color: {INK}; }}
  .followups-box {{ padding: 16pt 18pt; border-radius: 2pt; margin-top: 6pt; }}
  .followup-item {{ margin-bottom: 10pt; }}
  .followup-item:last-child {{ margin-bottom: 0; }}
  .followup-action {{ font-size: 10.8pt; font-weight: 700; color: {NAVY}; line-height: 1.4; }}
  .followup-rationale {{ font-size: 10pt; line-height: 1.5; color: {INK}; margin-top: 2pt; }}

  .recap-page {{ padding: 0.9in 1.1in; }}
  .recap-heading {{
    font-family: 'Caladea', Georgia, serif; font-size: 20pt; color: {NAVY};
    margin: 0 0 14pt 0; font-weight: 700;
  }}
  .recap-heading.second {{ margin-top: 0.5in; }}
  .recap-list {{ margin-bottom: 10pt; }}
  .recap-row {{ font-size: 11.5pt; line-height: 1.7; color: {INK}; margin-bottom: 4pt; }}
  .recap-name {{ font-weight: 700; color: {NAVY}; }}
  .recap-dash {{ color: #9396B8; margin: 0 5pt; }}
  .recap-material-row {{ margin-bottom: 10pt; }}
  .recap-material-title {{ font-weight: 700; font-size: 11.5pt; color: {NAVY}; }}
  .recap-material-summary {{ font-size: 10.5pt; line-height: 1.5; color: {INK}; }}
  .recap-material-url {{ font-size: 9pt; color: {INDIGO}; }}
  .recap-empty {{ font-size: 11pt; color: #8B8EB0; font-style: italic; }}
"""


def _initials(name):
    parts = [
        p for p in name.replace(",", "").replace(".", "").split()
        if p[:1].isupper() and p.lower() not in ("phd", "rev", "dr", "jr", "sr")
    ]
    letters = [p[0] for p in parts if p[0].isalpha()]
    return "".join(letters[:2]).upper() or "?"


def _guest_block(g, row):
    sector = g.get("sector") or "Other"
    color = SECTOR_COLORS.get(sector, SECTOR_COLORS["Other"])
    tint = SECTOR_TINTS.get(sector, SECTOR_TINTS["Other"])
    top = "0in" if row == "top" else f"{ROW_H}in"
    divider = (
        f'<div style="position:absolute; left:0.5in; top:{ROW_H}in; right:0.5in; '
        'height:1pt; background:#E4E5F0;"></div>'
        if row == "top" else ""
    )
    if g.get("photo_url"):
        avatar_inner = f'<img src="{html.escape(g["photo_url"])}" />'
    else:
        avatar_inner = f"<span>{html.escape(_initials(g['name']))}</span>"

    role_bits = " &middot; ".join(
        f'<span class="{cls}">{html.escape(val)}</span>'
        for cls, val in (("role", g.get("role") or ""), ("org", g.get("org") or ""))
        if val
    )

    return f"""
      <div class="sidebar" style="top:{top}; background:{color};">
        <div class="avatar">{avatar_inner}</div>
        <div class="sector-tag">{html.escape(sector)}</div>
        <div class="location-label">Location</div>
        <div class="location">{html.escape(g.get('location') or '')}</div>
      </div>
      <div class="content" style="top:{top};">
        <div class="header-block">
          <div class="kicker" style="color:{color};">Guest Persona</div>
          <h1>{html.escape(g['name'])}</h1>
          <div class="role-line">{role_bits}</div>
          <div class="rule" style="background:{color};"></div>
        </div>
        <div class="two-col">
          <div class="bio">{html.escape(g.get('bio') or '')}</div>
          <div class="reason-block" style="background:{tint}; border-left:4px solid {color};">
            <div class="reason-label" style="color:{color};">Why They&rsquo;re At The Table</div>
            <div class="reason-text">{html.escape(g.get('reason') or '')}</div>
          </div>
        </div>
      </div>
      {divider}
    """


def build_pdf(dinner, guests):
    """dinner: {"name": str, "theme": str}
    guests: list of {"name","role","org","location","sector","bio","reason","photo_url"}
    Returns PDF bytes.
    """
    sectors_present = sorted({g.get("sector") or "Other" for g in guests}, key=lambda s: list(SECTOR_COLORS).index(s) if s in SECTOR_COLORS else 99)
    legend = "".join(
        f'<div class="legend-item"><span class="dot" style="background:{SECTOR_COLORS.get(s, SECTOR_COLORS["Other"])};"></span>{html.escape(s)}</div>'
        for s in sectors_present
    )

    cover = f"""
    <section class="page cover">
      <div class="cover-inner">
        <div class="cover-kicker">In The Room Media &middot; Guest Persona Brief</div>
        <h1 class="cover-title">{html.escape(dinner.get('name') or 'Private Dinner')}</h1>
        <div class="cover-sub">A Single-Table Conversation</div>
        <p class="cover-desc">{html.escape(dinner.get('theme') or '')}</p>
        <div class="cover-legend">{legend}</div>
      </div>
    </section>
    """

    pages = [cover]
    for i in range(0, len(guests), 2):
        pair = guests[i:i + 2]
        blocks = _guest_block(pair[0], "top")
        if len(pair) > 1:
            blocks += _guest_block(pair[1], "bottom")
        pages.append(f'<section class="page guest-page">{blocks}</section>')

    doc = f"""<!DOCTYPE html>
    <html><head><meta charset="utf-8"><style>{CSS}</style></head>
    <body>{''.join(pages)}</body></html>
    """
    return HTML(string=doc).write_pdf()


def _brief_block(section):
    sector = section.get("sector") or "Other"
    color = SECTOR_COLORS.get(sector, SECTOR_COLORS["Other"])
    tint = SECTOR_TINTS.get(sector, SECTOR_TINTS["Other"])

    if section.get("photoThumb"):
        avatar_inner = f'<img src="{html.escape(section["photoThumb"])}" />'
    else:
        avatar_inner = f"<span>{html.escape(_initials(section.get('name') or ''))}</span>"

    role_bits = " &middot; ".join(
        f'<span class="{cls}">{html.escape(val)}</span>'
        for cls, val in (("role", section.get("role") or ""), ("org", section.get("org") or ""))
        if val
    )

    followups = section.get("recommendedFollowUps") or []
    if followups:
        followups_html = "".join(
            f'<div class="followup-item">'
            f'<div class="followup-action">{i + 1}. {html.escape(fu.get("action") or "")}</div>'
            f'<div class="followup-rationale">{html.escape(fu.get("rationale") or "")}</div>'
            f'</div>'
            for i, fu in enumerate(followups)
        )
    else:
        followups_html = '<div class="followup-item"><div class="followup-rationale">No follow-up actions were drafted.</div></div>'

    return f"""
      <div class="brief-sidebar" style="background:{color};">
        <div class="avatar">{avatar_inner}</div>
        <div class="sector-tag">{html.escape(sector)}</div>
      </div>
      <div class="brief-content">
        <div class="kicker" style="color:{color};">Post-Dinner Strategic Brief</div>
        <h1>{html.escape(section.get('name') or '')}</h1>
        <div class="role-line">{role_bits}</div>
        <div class="rule" style="background:{color};"></div>

        <div class="brief-section">
          <div class="brief-label" style="color:{color};">Why Now</div>
          <div class="brief-text">{html.escape(section.get('whyNow') or '')}</div>
        </div>

        <div class="brief-section">
          <div class="brief-label" style="color:{color};">KPMG Angle</div>
          <div class="brief-text">{html.escape(section.get('kpmgAngle') or '')}</div>
        </div>

        <div class="followups-box" style="background:{tint}; border-left:4px solid {color};">
          <div class="brief-label" style="color:{color};">Recommended Follow-Ups &mdash; {html.escape(section.get('sender') or '')}</div>
          {followups_html}
        </div>
      </div>
    """


def _recap_block(follow_up_areas, relevant_material):
    if follow_up_areas:
        followup_html = "".join(
            f'<div class="recap-row"><span class="recap-name">{html.escape(fa.get("name") or "")}</span>'
            f'<span class="recap-dash">&mdash;</span>'
            f'<span class="recap-reason">{html.escape(fa.get("reason") or "")}</span></div>'
            for fa in follow_up_areas
        )
    else:
        followup_html = '<div class="recap-empty">No attendees were flagged for follow-up.</div>'

    if relevant_material:
        material_html = "".join(
            f'<div class="recap-material-row">'
            f'<div class="recap-material-title">{html.escape(m.get("title") or "")}</div>'
            f'<div class="recap-material-summary">{html.escape(m.get("summary") or "")}</div>'
            + (
                f'<div class="recap-material-url">{html.escape(m.get("url") or "")}</div>'
                if m.get("url") else ""
            )
            + "</div>"
            for m in relevant_material
        )
    else:
        material_html = (
            '<div class="recap-empty">No KPMG Reference Library material was cited '
            "for this dinner&rsquo;s attendees.</div>"
        )

    return f"""
      <div class="recap-heading">Worth Following Up On</div>
      <div class="recap-list">{followup_html}</div>
      <div class="recap-heading second">Relevant KPMG Material</div>
      <div class="recap-list">{material_html}</div>
    """


def build_brief_pdf(dinner, sections, follow_up_areas=None, relevant_material=None):
    """dinner: {"name": str, "theme": str}
    sections: list of {"name","role","org","sector","photoThumb","whyNow",
                        "kpmgAngle","recommendedFollowUps","sender"}
    follow_up_areas: list of {"name","reason"}
    relevant_material: list of {"title","summary","url"}
    Returns PDF bytes.
    """
    cover = f"""
    <section class="page cover">
      <div class="cover-inner">
        <div class="cover-kicker">In The Room Media &middot; KPMG Post-Dinner Strategic Brief</div>
        <h1 class="cover-title">{html.escape(dinner.get('name') or 'Private Dinner')}</h1>
        <div class="cover-sub">Priority Follow-Up Brief</div>
        <p class="cover-desc">{html.escape(dinner.get('theme') or '')}</p>
      </div>
    </section>
    """

    recap = f'<section class="page recap-page">{_recap_block(follow_up_areas or [], relevant_material or [])}</section>'

    pages = [cover, recap]
    for section in sections:
        pages.append(f'<section class="page brief-page">{_brief_block(section)}</section>')

    doc = f"""<!DOCTYPE html>
    <html><head><meta charset="utf-8"><style>{CSS}</style></head>
    <body>{''.join(pages)}</body></html>
    """
    return HTML(string=doc).write_pdf()
