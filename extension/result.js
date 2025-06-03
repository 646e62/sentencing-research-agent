// result.js
// Display markdown passed via browser.storage.local and clear after use

document.addEventListener('DOMContentLoaded', async () => {
    const contentDiv = document.getElementById('content');
    try {
        const result = await browser.storage.local.get('markdown_result');
        let data = null;
        try {
            data = JSON.parse(result.markdown_result);
        } catch (e) {
            // fallback for old format
        }
        if (data && data.cleaned_header !== undefined && Array.isArray(data.body_paragraphs)) {
            let statsHtml = '';
            if (data.statistics && typeof data.statistics.paragraph_count === 'number') {
                statsHtml = `<div><b>Statistics:</b></div><div>Paragraph count: ${data.statistics.paragraph_count}</div><hr>`;
            }
            let paragraphsHtml = data.body_paragraphs.map(p => `<p>${p.replace(/</g, '&lt;')}</p>`).join('');
            contentDiv.innerHTML = `
                ${statsHtml}
                <div><b>Cleaned Header:</b></div><pre>${data.cleaned_header.replace(/</g, '&lt;')}</pre>
                <hr>
                <div><b>Body Paragraphs:</b></div>${paragraphsHtml}
            `;
            await browser.storage.local.remove('markdown_result');
        } else if (result.markdown_result) {
            contentDiv.textContent = result.markdown_result;
            await browser.storage.local.remove('markdown_result');
        } else {
            contentDiv.textContent = 'No result found.';
        }
    } catch (e) {
        contentDiv.textContent = 'Error loading result: ' + e;
    }
});
