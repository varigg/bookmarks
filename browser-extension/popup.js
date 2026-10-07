// Save the active tab: url, title, the rendered html and an optional note.
// Every capture-API reply is shown as the server worded it; there is no retry.

const status = document.getElementById('status');
const saveButton = document.getElementById('save');
let tab;

browser.tabs.query({ active: true, currentWindow: true }).then(([active]) => {
  tab = active;
  document.getElementById('url').textContent = tab.url;
});

function show(text, kind) {
  status.textContent = text;
  status.className = kind;
}

// The page as the browser holds it, so logged-in pages and single-page apps
// arrive rendered. Pages scripts cannot reach (about:, the add-ons site) send
// no html and the server fetches the URL itself.
async function renderedHtml(tabId) {
  try {
    const [frame] = await browser.scripting.executeScript({
      target: { tabId },
      func: () => document.documentElement.outerHTML,
    });
    return frame.result;
  } catch {
    return null;
  }
}

async function save() {
  const serverUrl = await loadServer();
  if (!serverUrl) {
    show('Not saved: set the server address in the extension options.', 'error');
    return;
  }
  if (!(await browser.permissions.contains(serverOrigins(serverUrl)))) {
    show('Not saved: allow access to the server in the extension options.', 'error');
    return;
  }
  const note = document.getElementById('note').value.trim();
  const payload = {
    url: tab.url,
    title: tab.title,
    html: await renderedHtml(tab.id),
    note: note || null,
  };
  let response;
  try {
    response = await fetch(`${serverUrl}/api/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    show('Not saved: server unreachable', 'error');
    return;
  }
  const body = await response.json().catch(() => ({}));
  if (response.ok) {
    show(body.message, body.outcome);
  } else {
    const detail = typeof body.detail === 'string' ? body.detail : `HTTP ${response.status}`;
    show(`Not saved: ${detail}`, 'error');
  }
}

saveButton.addEventListener('click', async () => {
  saveButton.disabled = true;
  try {
    await save();
  } finally {
    saveButton.disabled = false;
  }
});
