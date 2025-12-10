// Get current tab info and populate form
browser.tabs.query({ active: true, currentWindow: true }).then(tabs => {
  const tab = tabs[0];
  document.getElementById('url').value = tab.url;
  document.getElementById('title').value = tab.title;
});

// Handle configure link
document.getElementById('configureLink').addEventListener('click', (e) => {
  e.preventDefault();
  browser.runtime.openOptionsPage();
});

// Handle form submission
document.getElementById('bookmarkForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const submitBtn = document.getElementById('submitBtn');
  const statusDiv = document.getElementById('status');
  
  // Get URL
  const url = document.getElementById('url').value;
  
  // Get server URL from storage
  const config = await browser.storage.local.get({ serverUrl: 'http://localhost:5001' });
  const serverUrl = config.serverUrl.replace(/\/$/, ''); // Remove trailing slash
  
  // Disable button
  submitBtn.disabled = true;
  submitBtn.textContent = 'Adding...';
  
  try {
    // Send to bookmarks API endpoint (generates title/description and saves)
    const response = await fetch(`${serverUrl}/api/bookmarks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url: url })
    });
    
    if (response.ok) {
      const result = await response.json();
      showStatus('Bookmark added successfully!', 'success');
      
      // Close popup after short delay
      setTimeout(() => window.close(), 1500);
    } else {
      const errorData = await response.json();
      showStatus(`Error: ${errorData.error || response.status}`, 'error');
    }
  } catch (error) {
    showStatus(`Failed to connect to server: ${error.message}`, 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Add Bookmark';
  }
});

function showStatus(message, type) {
  const statusDiv = document.getElementById('status');
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
  
  if (type === 'error') {
    setTimeout(() => {
      statusDiv.className = 'status';
    }, 5000);
  }
}
