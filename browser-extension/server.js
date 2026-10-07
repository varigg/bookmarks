// The configured server address, shared by the popup and the options page.

async function loadServer() {
  const { serverUrl } = await browser.storage.local.get({ serverUrl: '' });
  return serverUrl;
}

// Host permission for the server: match patterns carry no port, so this
// covers the host on any port.
function serverOrigins(serverUrl) {
  const { protocol, hostname } = new URL(serverUrl);
  return { origins: [`${protocol}//${hostname}/*`] };
}
