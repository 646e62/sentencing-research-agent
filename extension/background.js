// background.js

// Listen for browser action (extension icon) click
let extractionInProgress = false;
let resultPopupWindowId = null;

browser.browserAction.onClicked.addListener(async (tab) => {
    if (extractionInProgress) {
        console.log("[Sentencing Research Agent] Extraction already in progress, ignoring click.");
        return;
    }
    extractionInProgress = true;
    console.log("[Sentencing Research Agent] Icon clicked on tab", tab.id);
    try {
        // Clear previous result before starting extraction
        await browser.storage.local.remove('markdown_result');
        console.log("[Sentencing Research Agent] Cleared previous markdown_result from storage.");
        console.log("[Sentencing Research Agent] Injecting content script...");
        await browser.tabs.executeScript(tab.id, { file: "content.js" });
        console.log("[Sentencing Research Agent] Sending TRIGGER_EXTRACTION message to content script...");
        browser.tabs.sendMessage(tab.id, { type: 'TRIGGER_EXTRACTION' });
    } catch (err) {
        extractionInProgress = false;
        console.error("[Sentencing Research Agent] Error injecting script or sending message:", err);
    }
});

// Listen for HTML from content script
browser.runtime.onMessage.addListener(async (message, sender) => {
    if (message.type === "PAGE_HTML") {
        if (!extractionInProgress) {
            console.log("[Sentencing Research Agent] Ignoring PAGE_HTML: no extraction in progress.");
            return;
        }
        extractionInProgress = false; // Only process the first PAGE_HTML per extraction
        console.log("[Sentencing Research Agent] Received HTML from content script:", message.html.slice(0, 500), "...");
        try {
            console.log("[Sentencing Research Agent] Sending HTML to backend /extract-markdown endpoint...");
            const response = await fetch("http://localhost:8000/extract-markdown", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ html: message.html })
            });
            console.log("[Sentencing Research Agent] Fetch completed. Status:", response.status);
            if (!response.ok) {
                throw new Error("Backend returned status " + response.status);
            }
            const data = await response.json();
            console.log("[Sentencing Research Agent] Received data from backend:", data);
            // Save markdown to storage
            await browser.storage.local.set({ markdown_result: data.markdown });
            const url = browser.runtime.getURL("result.html");
            console.log("[Sentencing Research Agent] Opening result.html as popup window...");
            // Close previous popup if it exists
            if (resultPopupWindowId !== null) {
                try {
                    await browser.windows.remove(resultPopupWindowId);
                } catch (e) {
                    // Window may already be closed
                }
            }
            // Open new popup and track its window ID
            const popupWindow = await browser.windows.create({ url, type: "popup", width: 800, height: 600 });
            resultPopupWindowId = popupWindow.id;
        } catch (err) {
            console.error("[Sentencing Research Agent] Error during extraction:", err, err.stack);
            const errorHtml = `<pre style='color: red;'>Error: ${err.toString()}</pre>`;
            const url = "data:text/html;charset=utf-8," + encodeURIComponent(errorHtml);
            browser.windows.create({ url, type: "popup", width: 600, height: 200 });
        }
    }
});
