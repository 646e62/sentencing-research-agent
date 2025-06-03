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
            let citationHtml = data.citation ? `<div><b>Citation:</b> ${data.citation.replace(/</g, '&lt;')}</div>` : '';
            let citationMetaHtml = '';
            if (data.citation_metadata && typeof data.citation_metadata === 'object' && Object.keys(data.citation_metadata).length > 0) {
                let rows = Object.entries(data.citation_metadata)
                    .filter(([k, v]) => v !== undefined && v !== null && v !== '')
                    .map(([k, v]) => `<tr><td><b>${k}</b></td><td>${String(v).replace(/</g, '&lt;')}</td></tr>`)
                    .join('');
                citationMetaHtml = `<div><b>Citation Metadata:</b></div><table style="border-collapse:collapse;width:100%;table-layout:auto;font-size:13px;"><tbody>${rows}</tbody></table><hr>`;
                // Add CSS to style td elements
                // Style first td (field name) in each row with min-width and nowrap
                citationMetaHtml = citationMetaHtml.replace(/<tr><td style="/g, '<tr><td style="min-width:120px;white-space:nowrap;');
                citationMetaHtml = citationMetaHtml.replace(/<td>/g, '<td style="border:1px solid #ccc;padding:4px 8px;text-align:left;vertical-align:top;">');
            }
            contentDiv.innerHTML = `
                ${citationHtml}
                ${citationMetaHtml}
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
