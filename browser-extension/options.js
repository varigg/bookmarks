// Load saved settings
browser.storage.local.get({ serverUrl: 'http://localhost:5001' }).then(config => {
  document.getElementById('serverUrl').value = config.serverUrl;
});

// Save settings
document.getElementById('optionsForm').addEventListener('submit', (e) => {
  e.preventDefault();
  
  const serverUrl = document.getElementById('serverUrl').value.replace(/\/$/, ''); // Remove trailing slash
  
  browser.storage.local.set({ serverUrl }).then(() => {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = 'Settings saved successfully!';
    statusDiv.className = 'status success';
    
    setTimeout(() => {
      statusDiv.className = 'status';
    }, 3000);
  }).catch(error => {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = 'Error saving settings: ' + error.message;
    statusDiv.className = 'status error';
    statusDiv.style.display = 'block';
  });
});
