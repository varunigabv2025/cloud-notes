const apiUrl = "/api/notes";
const el = (id) => document.getElementById(id);
const notesList = el("notes-list"), loading = el("loading-state"), empty = el("empty-state"), error = el("error-state"), modal = el("modal-backdrop"), form = el("note-form");
let editingId = null;
let notes = [];

function showToast(message) { const toast = el("toast"); toast.textContent = message; toast.classList.add("show"); setTimeout(() => toast.classList.remove("show"), 2800); }
function formatDate(value) { return new Intl.DateTimeFormat(undefined, { month:"short", day:"numeric", year:"numeric" }).format(new Date(value)); }
function setState(state) { loading.hidden = state !== "loading"; notesList.hidden = state !== "notes"; empty.hidden = state !== "empty"; error.hidden = state !== "error"; el("notes-region").setAttribute("aria-busy", state === "loading"); }
function escapeHtml(value) { const temp = document.createElement("div"); temp.textContent = value; return temp.innerHTML; }
function renderNotes() {
  // This is the only function that changes the note-card DOM.
  notesList.replaceChildren();
  if (!notes.length) {
    setState("empty");
    return;
  }
  notesList.innerHTML = notes.map(note => `<article class="note-card" tabindex="0" data-id="${note.id}"><h2>${escapeHtml(note.title)}</h2><p class="note-preview">${escapeHtml(note.content || "No content yet.")}</p><footer class="card-footer"><span>${note.updated_at !== note.created_at ? "Updated" : "Created"} ${formatDate(note.updated_at)}</span><span class="card-actions"><button class="card-button" data-action="edit" data-id="${note.id}">Edit</button><button class="card-button delete" data-action="delete" data-id="${note.id}">Delete</button></span></footer></article>`).join("");
  setState("notes");
}
async function request(path = "", options = {}) { const response = await fetch(`${apiUrl}${path}`, { headers:{ "Content-Type":"application/json" }, ...options }); if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || "Something went wrong."); } return response.status === 204 ? null : response.json(); }
async function loadNotes() { setState("loading"); try { notes = await request(); renderNotes(); } catch (err) { el("error-message").textContent = err.message || "Please check that the server is running, then try again."; setState("error"); } }
function openModal(note = null) { editingId = note?.id ?? null; el("modal-kicker").textContent = note ? "EDIT NOTE" : "NEW NOTE"; el("modal-title").textContent = note ? "Refine your thought." : "Make a little room for a thought."; el("save-button").textContent = note ? "Save Changes" : "Save Note"; el("note-title").value = note?.title ?? ""; el("note-content").value = note?.content ?? ""; el("title-error").textContent = ""; modal.hidden = false; setTimeout(() => el("note-title").focus(), 0); }
function closeModal() { modal.hidden = true; form.reset(); editingId = null; }
async function editNote(id) { try { openModal(await request(`/${id}`)); } catch (err) { showToast(err.message); } }
async function deleteNote(id) {
  if (!window.confirm("Are you sure you want to delete this note?")) return;
  try {
    await request(`/${id}`, { method:"DELETE" });
    notes = notes.filter(note => note.id !== Number(id));
    renderNotes();
    showToast("Note deleted.");
  } catch (err) {
    // Keep the current state and cards intact when the API rejects deletion.
    showToast(err.message);
  }
}
el("new-note-button").onclick = () => openModal(); el("empty-new-note").onclick = () => openModal(); el("close-modal").onclick = closeModal; el("cancel-button").onclick = closeModal; el("retry-button").onclick = loadNotes;
modal.onclick = (event) => { if (event.target === modal) closeModal(); };
notesList.onclick = (event) => { const button = event.target.closest("button[data-action]"); if (!button) return; button.dataset.action === "edit" ? editNote(button.dataset.id) : deleteNote(button.dataset.id); };
notesList.onkeydown = (event) => { if ((event.key === "Enter" || event.key === " ") && !event.target.closest("button")) editNote(event.currentTarget.querySelector(":focus")?.dataset.id); };
form.onsubmit = async (event) => { event.preventDefault(); const title = el("note-title").value.trim(), content = el("note-content").value; if (!title) { el("title-error").textContent = "A title gives this note a home."; el("note-title").focus(); return; } const save = el("save-button"), noteId = editingId; save.disabled = true; save.textContent = "Saving…"; try { const wasEditing = Boolean(noteId); const savedNote = await request(noteId ? `/${noteId}` : "", { method:noteId ? "PUT" : "POST", body:JSON.stringify({ title, content }) }); notes = wasEditing ? notes.map(note => note.id === savedNote.id ? savedNote : note) : [savedNote, ...notes]; closeModal(); renderNotes(); showToast(wasEditing ? "Changes saved." : "Note saved."); } catch (err) { el("title-error").textContent = err.message; } finally { save.disabled = false; save.textContent = noteId ? "Save Changes" : "Save Note"; } };
document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !modal.hidden) closeModal(); });
loadNotes();
