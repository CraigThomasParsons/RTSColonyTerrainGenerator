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

    setupNavigation();
}

function setupNavigation() {
    const buttons = document.querySelectorAll('.tactical-btn[data-target]');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');

            // Toggle Content Sections
            document.querySelectorAll('.tab-section').forEach(section => {
                if (section.id === targetId) {
                    section.classList.remove('hidden');
                } else {
                    section.classList.add('hidden');
                }
            });

            // Update active state
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
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

        // document.getElementById('pipeline-name').innerText = currentConfig.name; // Removed in Cyberpunk
    } catch (e) {
        console.error(e);
        // document.getElementById('pipeline-name').innerText = "ERROR";
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
    fetchStages();
    fetchSystemd();
    fetchLogs();
}

async function fetchStages() {
    try {
        const res = await fetch('/api/queues');
        const data = await res.json();
        renderStages(data);
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

function renderStages(data) {
    const container = document.getElementById('stages-container');
    container.innerHTML = '';

    let stages = Object.keys(data);
    if (currentConfig && currentConfig.stages) {
        stages.sort((a, b) => {
            const ia = currentConfig.stages.indexOf(a);
            const ib = currentConfig.stages.indexOf(b);
            return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
        });
    }

    stages.forEach(stage => {
        const queues = data[stage];
        const unit = document.createElement('div');
        unit.className = 'stage-unit';

        const header = document.createElement('div');
        header.className = 'stage-header';
        header.innerText = stage;
        unit.appendChild(header);

        const queueOrder = ['inbox', 'pending', 'in_progress', 'outbox', 'done', 'failed'];
        let qKeys = Object.keys(queues).sort((a, b) => {
            const ia = queueOrder.indexOf(a);
            const ib = queueOrder.indexOf(b);
            return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
        });

        // Calculate total for percentages
        let total = 0;
        qKeys.forEach(q => total += queues[q]);
        if (total === 0) total = 1; // Avoid divide by zero

        qKeys.forEach(q => {
            const count = queues[q];
            const div = document.createElement('div');
            let type = 'inbox';
            if (q.includes('out') || q.includes('done')) type = 'outbox';
            if (q.includes('fail')) type = 'failed';

            div.className = `stage-metric ${type}`;

            // Bar calculation
            let percent = Math.min(100, Math.round((count / total) * 100));

            div.innerHTML = `
                <span>${q}</span>
                <div class="bar-container">
                    <div class="bar-fill" style="width: ${count > 0 ? (percent < 10 ? 10 : percent) : 0}%"></div>
                </div>
                <span class="metric-count">${count}</span>
            `;
            unit.appendChild(div);
        });

        container.appendChild(unit);
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
}

// Start
init();
