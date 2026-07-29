// Drag-and-drop photo upload + inline auto-save for guest/dinner text
// fields. Every editable-field saves back to Airtable on blur (or on
// change, for the Sector <select>) via /field endpoints.

document.addEventListener("DOMContentLoaded", () => {
  // ---- Photo upload ----
  document.querySelectorAll(".dropzone").forEach((zone) => {
    const attendeeId = zone.dataset.attendeeId;
    const dinnerId = zone.dataset.dinnerId;
    const statusEl = document.querySelector(`.upload-status[data-attendee-id="${attendeeId}"]`);
    const fileInput = zone.querySelector("input[type=file]");

    const upload = (file) => {
      if (!file) return;
      statusEl.textContent = "Uploading…";
      statusEl.className = "upload-status";

      const formData = new FormData();
      formData.append("photo", file);

      fetch(`/dinner/${dinnerId}/attendee/${attendeeId}/photo`, {
        method: "POST",
        body: formData,
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.error) throw new Error(data.error);
          zone.innerHTML = `<img src="${URL.createObjectURL(file)}" />`;
          statusEl.textContent = "Saved to Airtable";
          statusEl.className = "upload-status ok";
        })
        .catch((err) => {
          statusEl.textContent = err.message || "Upload failed";
          statusEl.className = "upload-status err";
        });
    };

    zone.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (e) => upload(e.target.files[0]));

    ["dragenter", "dragover"].forEach((evt) =>
      zone.addEventListener(evt, (e) => {
        e.preventDefault();
        zone.classList.add("dragover");
      })
    );
    ["dragleave", "drop"].forEach((evt) =>
      zone.addEventListener(evt, (e) => {
        e.preventDefault();
        zone.classList.remove("dragover");
      })
    );
    zone.addEventListener("drop", (e) => {
      const file = e.dataTransfer.files[0];
      upload(file);
    });
  });

  // ---- Inline text editing ----
  document.querySelectorAll(".editable-field").forEach((el) => {
    const scope = el.dataset.scope; // "attendee" or "dinner"
    const field = el.dataset.field;
    const recordId = scope === "attendee" ? el.dataset.attendeeId : el.dataset.dinnerId;
    const statusKey = scope === "attendee" ? `attendee:${recordId}` : `dinner:${field}`;
    const statusEl = document.querySelector(`.save-status[data-field-key="${statusKey}"]`);
    let lastSaved = el.value;

    const save = () => {
      if (el.value === lastSaved) return;
      const url = scope === "attendee"
        ? `/dinner/${el.dataset.dinnerId}/attendee/${recordId}/field`
        : `/dinner/${recordId}/field`;

      if (statusEl) { statusEl.textContent = "Saving…"; statusEl.className = "save-status"; }

      fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field, value: el.value }),
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.error) throw new Error(data.error);
          lastSaved = el.value;
          if (statusEl) { statusEl.textContent = "Saved"; statusEl.className = "save-status ok"; }
          setTimeout(() => { if (statusEl) statusEl.textContent = ""; }, 1500);
        })
        .catch((err) => {
          if (statusEl) { statusEl.textContent = err.message || "Save failed"; statusEl.className = "save-status err"; }
        });
    };

    el.addEventListener("blur", save);
    if (el.tagName === "SELECT") el.addEventListener("change", save);

    // Auto-grow textareas so long bios aren't cramped in a tiny box.
    if (el.tagName === "TEXTAREA") {
      const grow = () => { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; };
      el.addEventListener("input", grow);
      grow();
    }
  });
});
