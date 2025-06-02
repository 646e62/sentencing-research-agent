// result.js
// Display markdown passed via browser.storage.local and clear after use

document.addEventListener('DOMContentLoaded', async () => {
    const contentDiv = document.getElementById('content');
    try {
        const result = await browser.storage.local.get('markdown_result');
        if (result.markdown_result) {
            contentDiv.textContent = result.markdown_result;
            // Optionally clear the value after displaying
            await browser.storage.local.remove('markdown_result');
        } else {
            contentDiv.textContent = 'No result found.';
        }
    } catch (e) {
        contentDiv.textContent = 'Error loading result: ' + e;
    }
});
