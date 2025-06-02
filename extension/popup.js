// popup.js

document.addEventListener('DOMContentLoaded', function() {
    const extractBtn = document.getElementById('extractBtn');
    const statusDiv = document.getElementById('status');

    extractBtn.addEventListener('click', async () => {
        statusDiv.textContent = 'Extracting...';
        // Ask the content script to send the HTML
        try {
            const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
            browser.tabs.sendMessage(tab.id, { type: 'TRIGGER_EXTRACTION' });
        } catch (err) {
            statusDiv.textContent = 'Could not trigger extraction: ' + err;
        }
    });

    // Listen for extraction result from background
    browser.runtime.onMessage.addListener((message) => {
        if (message.type === 'EXTRACTION_RESULT') {
            statusDiv.textContent = message.text ? message.text.slice(0, 1000) : '(No text extracted)';
        } else if (message.type === 'EXTRACTION_ERROR') {
            statusDiv.textContent = 'Error: ' + message.error;
        }
    });
});
