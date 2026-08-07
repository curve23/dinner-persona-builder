// Post-Dinner Strategic Brief: attendee flagging, brief generation, in-place
// editing of the drafted sections, PDF export, and Touchpoints logging.

const SECTOR_COLORS = {
  "Government": "#0B1059",
  "Private Sector": "#3F32B0",
  "Nonprofit & Advocacy": "#FE4A4A",
  "Faith & Community": "#2E6F9E",
  "Media": "#3F32B0",
  "Other": "#5B5F8A",
};

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

function escapeAttr(str) {
  return escapeHtml(str).replace(/"/g, "&quot;");
}

document.addEventListener("DOMContentLoaded", () => {
  const dinnerId = document.body.dataset.dinnerId;
  const dinnerName = document.body.dataset.dinnerName;
  const hasKpmgAttendees = document.body.dataset.hasKpmgAttendees === "true";

  let kpmgAttendees = [];
  const kpmgDataEl = document.getElementById("kpmg-attendees-data");
  if (kpmgDataEl) {
    try { kpmgAttendees = JSON.parse(kpmgDataEl.textContent) || []; } catch (e) { kpmgAttendees = []; }
  }

  // ---- Attendee flagging ----
  document.querySelectorAll(".brief-attendee-card").forEach((card) => {
    const attendedCheck = card.querySelector(".attended-check");
    const priorityCheck = card.querySelector(".priority-check");
    const updateFlag = () => {
      card.classList.toggle("flagged", attendedCheck.checked && priorityCheck.checked);
    };
    attendedCheck.addEventListener("change", updateFlag);
    priorityCheck.addEventListener("change", updateFlag);
  });

  const generateBtn = document.getElementById("generate-btn");
  const statusEl = document.getElementById("generate-status");
  const summaryEl = document.getElementById("brief-summary");
  const followupList = document.getElementById("followup-list");
  const materialList = document.getElementById("material-list");
  const resultsEl = document.getElementById("brief-results");
  const exportActions = document.getElementById("export-actions");
  if (!generateBtn) return; // no attendees on this dinner

  if (!hasKpmgAttendees) {
    generateBtn.disabled = true;
    generateBtn.title = "Link at least one KPMG attendee in Airtable (Dinners → KPMG Attendees) first.";
  }

  // ---- Generate ----
  generateBtn.addEventListener("click", () => {
    const selections = {};
    document.querySelectorAll(".brief-attendee-card").forEach((card) => {
      selections[card.dataset.attendeeId] = {
        attended: card.querySelector(".attended-check").checked,
        priority: card.querySelector(".priority-check").checked,
        hook: card.querySelector(".hook-input").value,
      };
    });
    const themes = ["theme-1", "theme-2", "theme-3"]
      .map((id) => document.getElementById(id).value)
      .filter((v) => v && v.trim());

    statusEl.textContent = "Generating brief… this can take a minute for several people.";
    statusEl.className = "save-status";
    generateBtn.disabled = true;
    summaryEl.style.display = "none";
    resultsEl.innerHTML = "";
    exportActions.style.display = "none";

    fetch(`/dinner/${dinnerId}/brief/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selections, themes }),
    })
      .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "Generation failed");
        renderSummary(data.followUpAreas, data.relevantMaterial);
        renderResults(data.sections);
        statusEl.textContent = `Generated ${data.sections.length} section(s). Edit anything below before exporting.`;
        statusEl.className = "save-status ok";
        exportActions.style.display = "flex";
      })
      .catch((err) => {
        statusEl.textContent = err.message;
        statusEl.className = "save-status err";
      })
      .finally(() => {
        generateBtn.disabled = !hasKpmgAttendees;
      });
  });

  // ---- Worth Following Up On / Relevant KPMG Material ----
  function renderSummary(followUpAreas, relevantMaterial) {
    followupList.innerHTML = "";
    if (followUpAreas && followUpAreas.length) {
      followUpAreas.forEach((fa) => {
        const row = document.createElement("div");
        row.className = "followup-row";
        row.innerHTML = `
          <input type="text" class="editable-field followup-name" value="${escapeAttr(fa.name)}">
          <span class="followup-dash">&mdash;</span>
          <input type="text" class="editable-field followup-reason" value="${escapeAttr(fa.reason)}">
        `;
        followupList.appendChild(row);
      });
    } else {
      followupList.innerHTML = '<p class="summary-empty">No one was flagged for follow-up.</p>';
    }

    materialList.innerHTML = "";
    if (relevantMaterial && relevantMaterial.length) {
      relevantMaterial.forEach((m) => {
        const row = document.createElement("div");
        row.className = "material-row";
        row.innerHTML = `
          <input type="text" class="editable-field material-title" value="${escapeAttr(m.title)}">
          <textarea class="editable-field material-summary" rows="2">${escapeHtml(m.summary)}</textarea>
          <input type="text" class="editable-field material-url" placeholder="Source URL (optional)" value="${escapeAttr(m.url || "")}">
        `;
        materialList.appendChild(row);
      });
    } else {
      materialList.innerHTML = '<p class="summary-empty">No KPMG Reference Library material was cited for this dinner’s attendees.</p>';
    }

    summaryEl.style.display = "block";
  }

  function collectFollowUpAreas() {
    return Array.from(followupList.querySelectorAll(".followup-row")).map((row) => ({
      name: row.querySelector(".followup-name").value,
      reason: row.querySelector(".followup-reason").value,
    }));
  }

  function collectRelevantMaterial() {
    return Array.from(materialList.querySelectorAll(".material-row")).map((row) => ({
      title: row.querySelector(".material-title").value,
      summary: row.querySelector(".material-summary").value,
      url: row.querySelector(".material-url").value,
    }));
  }

  // ---- Persona-style result cards ----
  function renderResults(sections) {
    resultsEl.innerHTML = "";
    sections.forEach((section) => {
      const color = SECTOR_COLORS[section.sector] || SECTOR_COLORS.Other;
      const initials = (section.name || "")
        .split(" ")
        .filter(Boolean)
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();
      const avatarInner = section.photoThumb
        ? `<img src="${escapeAttr(section.photoThumb)}">`
        : `<span>${escapeHtml(initials)}</span>`;

      const senderOptions = kpmgAttendees
        .map((k) => `<option value="${escapeAttr(k.name)}" ${k.name === section.sender ? "selected" : ""}>${escapeHtml(k.name)}</option>`)
        .join("");

      const card = document.createElement("div");
      card.className = "result-card";
      card.dataset.attendeeId = section.attendeeId;
      card.dataset.name = section.name || "";
      card.dataset.role = section.role || "";
      card.dataset.org = section.org || "";
      card.dataset.sector = section.sector || "";
      card.dataset.photoThumb = section.photoThumb || "";

      card.innerHTML = `
        <div class="result-sidebar" style="background:${color};">
          <div class="result-avatar">${avatarInner}</div>
          <div class="result-name">${escapeHtml(section.name)}</div>
          <div class="result-role">${escapeHtml([section.role, section.org].filter(Boolean).join(" · "))}</div>
        </div>
        <div class="result-content">
          <div class="result-section">
            <div class="result-label">Why Now</div>
            <textarea class="result-textarea why-now" rows="3">${escapeHtml(section.whyNow)}</textarea>
          </div>
          <div class="result-section">
            <div class="result-label">KPMG Angle</div>
            <textarea class="result-textarea kpmg-angle" rows="4">${escapeHtml(section.kpmgAngle)}</textarea>
          </div>
          <div class="result-section email-box">
            <div class="result-label">Draft Follow-Up</div>
            <select class="email-sender-select">${senderOptions}</select>
            <input type="text" class="email-subject-input" value="${escapeAttr(section.emailSubject)}">
            <textarea class="email-body-textarea" rows="8">${escapeHtml(section.emailBody)}</textarea>
          </div>
        </div>
      `;
      resultsEl.appendChild(card);

      // Auto-grow textareas, matching app.js's inline-edit behavior.
      card.querySelectorAll("textarea").forEach((el) => {
        const grow = () => { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; };
        el.addEventListener("input", grow);
        grow();
      });
    });
  }

  function collectSections() {
    return Array.from(resultsEl.querySelectorAll(".result-card")).map((card) => ({
      attendeeId: card.dataset.attendeeId,
      name: card.dataset.name,
      role: card.dataset.role,
      org: card.dataset.org,
      sector: card.dataset.sector,
      photoThumb: card.dataset.photoThumb || null,
      whyNow: card.querySelector(".why-now").value,
      kpmgAngle: card.querySelector(".kpmg-angle").value,
      sender: card.querySelector(".email-sender-select").value,
      emailSubject: card.querySelector(".email-subject-input").value,
      emailBody: card.querySelector(".email-body-textarea").value,
    }));
  }

  // ---- Export to PDF ----
  document.getElementById("export-pdf-btn").addEventListener("click", (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    fetch(`/dinner/${dinnerId}/brief/pdf`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dinner: { name: dinnerName, theme: document.getElementById("theme-1").value },
        sections: collectSections(),
        followUpAreas: collectFollowUpAreas(),
        relevantMaterial: collectRelevantMaterial(),
      }),
    })
      .then((r) => {
        if (!r.ok) throw new Error("PDF export failed");
        return r.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        window.open(url, "_blank");
      })
      .catch((err) => alert(err.message))
      .finally(() => { btn.disabled = false; });
  });

  // ---- Log to Touchpoints ----
  document.getElementById("log-touchpoint-btn").addEventListener("click", (e) => {
    const btn = e.currentTarget;
    const followUpAreas = collectFollowUpAreas();
    const touchpointStatus = document.getElementById("touchpoint-status");
    touchpointStatus.textContent = "Logging…";
    touchpointStatus.className = "save-status";
    btn.disabled = true;

    fetch(`/dinner/${dinnerId}/brief/touchpoint`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dinnerName, followUpAreas }),
    })
      .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "Logging failed");
        touchpointStatus.textContent = "Logged to Touchpoints.";
        touchpointStatus.className = "save-status ok";
      })
      .catch((err) => {
        touchpointStatus.textContent = err.message;
        touchpointStatus.className = "save-status err";
      })
      .finally(() => { btn.disabled = false; });
  });
});
