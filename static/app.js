// Drag-and-drop + click-to-upload photo handling for the attendee editor.
// Uploads go straight to Airtable's Photo attachment field via our /photo
// endpoint; on success we swap the dropzone to show the new thumbnail.

document.addEventListener("DOMContentLoaded", () => {
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
});
