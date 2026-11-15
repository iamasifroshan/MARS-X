const http = require('http');

async function main() {
    const tabs = await new Promise((resolve, reject) => {
        http.get('http://localhost:9222/json', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });

    console.log("Found tabs:", tabs.map(t => ({ id: t.id, url: t.url, title: t.title })));
    const pageTab = tabs.find(t => t.type === 'page' && t.url.includes('3005')) || tabs[0];
    if (!pageTab) {
        console.log("No page tab found!");
        return;
    }

    console.log("Attaching to tab:", pageTab.url);
    const ws = new WebSocket(pageTab.webSocketDebuggerUrl);

    await new Promise((resolve) => ws.onopen = resolve);

    let id = 1;
    function send(method, params = {}) {
        return new Promise((resolve) => {
            const reqId = id++;
            const handler = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.id === reqId) {
                    ws.removeEventListener('message', handler);
                    resolve(msg.result);
                }
            };
            ws.addEventListener('message', handler);
            ws.send(JSON.stringify({ id: reqId, method, params }));
        });
    }

    ws.addEventListener('message', (event) => {
        const msg = JSON.parse(event.data);
        if (msg.method === 'Console.messageAdded') {
            console.log('[BROWSER CONSOLE]', msg.params.message.level, msg.params.message.text);
        } else if (msg.method === 'Runtime.consoleAPICalled') {
            const args = msg.params.args.map(a => a.value || a.description || JSON.stringify(a)).join(' ');
            console.log('[CONSOLE]', msg.params.type, args);
        } else if (msg.method === 'Network.responseReceived') {
            const res = msg.params.response;
            if (res.status >= 400 || res.url.includes('8000')) {
                console.log('[NETWORK RESPONSE]', res.status, res.url);
            }
        } else if (msg.method === 'Network.loadingFailed') {
            console.log('[NETWORK FAILED]', msg.params.errorText, msg.params.type);
        }
    });

    await send('Console.enable');
    await send('Runtime.enable');
    await send('Network.enable');

    console.log("Waiting 3s for events...");
    await new Promise(r => setTimeout(r, 3000));

    // Evaluate health check status and state in DOM
    const evalRes = await send('Runtime.evaluate', {
        expression: `
            ({
                title: document.title,
                headerText: document.querySelector('header')?.innerText,
                apiStatusText: document.querySelector('header span.text-\\\\[11px\\\\]')?.innerText || 'Not found'
            })
        `,
        returnByValue: true
    });
    console.log("DOM State:", evalRes?.result?.value);

    ws.close();
}

main().catch(console.error);
