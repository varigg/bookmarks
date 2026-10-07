// The server address, and Firefox's permission to post to it.

const input = document.getElementById('serverUrl');
const status = document.getElementById('status');

loadServer().then((serverUrl) => {
  input.value = serverUrl;
});

document.getElementById('options').addEventListener('submit', (event) => {
  event.preventDefault();
  const serverUrl = input.value.trim().replace(/\/+$/, '');
  // permissions.request must be called directly in the user's gesture,
  // before anything is awaited.
  browser.permissions.request(serverOrigins(serverUrl)).then(async (granted) => {
    if (!granted) {
      status.textContent = 'Not saved: Firefox access to the server was refused.';
      status.className = 'error';
      return;
    }
    await browser.storage.local.set({ serverUrl });
    status.textContent = 'Saved.';
    status.className = '';
  });
});
