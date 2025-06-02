// content.js

browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'TRIGGER_EXTRACTION') {
        const html = document.documentElement.outerHTML;
        browser.runtime.sendMessage({
            type: "PAGE_HTML",
            html: html
        });
        // For development: also log to console
        console.log("[Sentencing Research Agent] Page HTML captured", html.slice(0, 500), "...");
    }
});
