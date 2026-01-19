const REFRESH_RATE = 3000;
let currentConfig = null;

async function init() {
    updateClock();
    setInterval(updateClock, 1000);

    // Load initial config
    await loadConfig();
    await loadPipelines();

    // Start polling
    fetchData();
    setInterval(fetchData, REFRESH_RATE);

    // Setup events
    document.getElementById('pipeline-select').addEventListener('change', (e) => {
        switchPipeline(e.target.value);
    });
}

function updateClock() {
    const now = new Date();
    document.getElementById('clock').innerText = now.toLocaleTimeString();
}

async function loadConfig() {
    try {
        const res = await fetch('/api/config');
        if (!res.ok) throw new Error('Failed to load config');
        currentConfig = await res.json();

        document.getElementById('pipeline-name').innerText = currentConfig.name;
    } catch (e) {
        console.error(e);
        document.getElementById('pipeline-name').innerText = "ERROR";
    }
}

async function loadPipelines() {
    try {
        const res = await fetch('/api/pipelines');
        const pipelines = await res.json();

        const select = document.getElementById('pipeline-select');
        select.innerHTML = '';

        pipelines.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.path;
            opt.innerText = p.name;
            if (currentConfig && p.id === currentConfig.id) {
                opt.selected = true;
            }
            select.appendChild(opt);
        });
    } catch (e) {
        console.error("Failed to load pipelines list", e);
    }
}

async function switchPipeline(path) {
    try {
        const res = await fetch('/api/pipeline/switch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        });
        if (res.ok) {
            // Reload config and refresh data immediately
            await loadConfig();
            fetchData();
        } else {
            alert("Failed to switch pipeline");
        }
    } catch (e) {
        alert("Error switching pipeline: " + e);
    }
}

async function fetchData() {
    fetchQueues();
    fetchSystemd();
    fetchLogs();
}

async function fetchQueues() {
    try {
        const res = await fetch('/api/queues');
        const data = await res.json();
        renderQueues(data);
    } catch (e) {
        console.error(e);
    }
}

async function fetchSystemd() {
    try {
        const res = await fetch('/api/systemd');
        const data = await res.json();
        renderSystemd(data);
    } catch (e) {
        console.error(e);
    }
}

async function fetchLogs() {
    try {
        const res = await fetch('/api/logs');
        const data = await res.json();
        renderLogs(data);
    } catch (e) {
        console.error(e);
    }
}

function renderQueues(data) {
    const container = document.getElementById('queues-container');
    container.innerHTML = '';

    // Data is { stage: { queue: count } }
    // If multistage, order might matter. 
    // currentConfig.stages has order if provided.

    let stages = Object.keys(data);
    // Sort by config stages order if available
    if (currentConfig && currentConfig.stages) {
        stages.sort((a, b) => {
            const ia = currentConfig.stages.indexOf(a);
            const ib = currentConfig.stages.indexOf(b);
            return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
        });
    }

    stages.forEach(stage => {
        const queues = data[stage];
        const lane = document.createElement('div');
        lane.className = 'lane';

        const header = document.createElement('div');
        header.className = 'lane-header';
        header.innerText = stage;
        lane.appendChild(header);

        // Normalize queue display
        // MapGen: inbox, outbox, failed
        // Bandcamp: pending, in_progress, failed, done

        const queueOrder = ['inbox', 'pending', 'in_progress', 'outbox', 'done', 'failed'];

        let qKeys = Object.keys(queues).sort((a, b) => {
            const ia = queueOrder.indexOf(a);
            const ib = queueOrder.indexOf(b);
            return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
        });

        qKeys.forEach(q => {
            const count = queues[q];
            const div = document.createElement('div');
            // Assign class based on queue name for color
            let type = 'inbox';
            if (q.includes('out') || q.includes('done')) type = 'outbox';
            if (q.includes('fail')) type = 'failed';

            div.className = `metric ${type}`;
            div.innerHTML = `<span>${q}</span> <span>${count}</span>`;
            lane.appendChild(div);
        });

        container.appendChild(lane);
    });
}

function renderSystemd(data) {
    const container = document.getElementById('systemd-container');
    container.innerHTML = '';

    for (const [unit, status] of Object.entries(data)) {
        const div = document.createElement('div');
        div.className = `unit-status ${status}`; // active, inactive, failed
        div.innerHTML = `<strong>${unit}</strong><br>${status}`;
        container.appendChild(div);
    }
}

function renderLogs(data) {
    const container = document.getElementById('logs-container');
    // Only update if content changed? 
    // For simplicity, just wipe and redraw. Text selection might reset though.
    // Ideally we diff, but 'Boring Code'.

    // To preserve scroll, save it.
    const scrollTop = container.scrollTop;

    container.innerHTML = '';
    for (const [file, content] of Object.entries(data)) {
        const div = document.createElement('div');
        div.className = 'log-file';

        // Simple HTML escaping
        const safeContent = content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

        div.innerHTML = `<div class="log-title">${file}</div><pre>${safeContent}</pre>`;
        container.appendChild(div);
    }

    // Restore scroll if user wasn't at bottom? 
    // Actually log tails usually want to follow.
    // If user is at bottom, scroll to bottom. 
    // Let's just leave it natural.
}

// Start
init();
