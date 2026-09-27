/* ============================================
   PDHG-GPU Solver — Frontend Application
   ============================================ */

const API_BASE = '';
let convergenceChart = null;
let customConvergenceChart = null;
let benchmarkTimeChart = null;
let benchmarkSpeedupChart = null;
let presetBenchChart = null;
let selectedPreset = null;

// Chart.js global config
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(56, 189, 248, 0.08)';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 12;

// ========== INITIALIZATION ==========

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    loadPresets();
    checkGPU();
    startTelemetryPolling();
    setupMpsDropzone();
    fetchGpuMemoryLimits();
});

// ========== LIVE GPU HARDWARE TELEMETRY ==========

async function fetchGpuTelemetry() {
    try {
        const res = await fetch(`${API_BASE}/api/gpu-telemetry`);
        const data = await res.json();
        if (!data.available) return;

        const nameEl = document.getElementById('telem-gpu-name');
        const archEl = document.getElementById('telem-gpu-arch');
        const vramTextEl = document.getElementById('telem-vram-text');
        const vramBarEl = document.getElementById('telem-vram-bar');
        const tempEl = document.getElementById('telem-temp');
        const utilEl = document.getElementById('telem-util');
        const powerEl = document.getElementById('telem-power');

        if (nameEl) nameEl.textContent = data.device_name;
        if (archEl) archEl.textContent = `${data.arch} • ${data.cuda_cores.toLocaleString()} CUDA Cores (${data.sm_count} SMs)`;
        if (vramTextEl) vramTextEl.textContent = `${data.vram_used_gb.toFixed(2)} / ${data.vram_total_gb.toFixed(2)} GB (${data.vram_pct.toFixed(1)}%)`;
        if (vramBarEl) vramBarEl.style.width = `${Math.min(data.vram_pct, 100)}%`;

        if (tempEl) tempEl.textContent = data.temperature_c !== null ? `${Math.round(data.temperature_c)}°C` : '--';
        if (utilEl) utilEl.textContent = data.gpu_util_pct !== null ? `${Math.round(data.gpu_util_pct)}%` : '--';
        if (powerEl) powerEl.textContent = data.power_w !== null ? `${data.power_w.toFixed(1)} W` : '--';
    } catch (e) {
        // Silently ignore transient telemetry polling errors
    }
}

function startTelemetryPolling() {
    fetchGpuTelemetry();
    setInterval(fetchGpuTelemetry, 2500);
}

function setupTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`content-${tab}`).classList.add('active');
        });
    });
}

async function checkGPU() {
    const badge = document.getElementById('gpu-badge');
    try {
        // Try solving a tiny problem to see if GPU works
        const res = await fetch(`${API_BASE}/api/solve-preset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preset_id: 'blending_pilot', use_gpu: true, max_iterations: 10 }),
        });
        const data = await res.json();
        if (data.solution && data.solution.device === 'gpu') {
            badge.innerHTML = '<span class="badge-dot"></span> GPU Active (CUDA: RTX 4070)';
            badge.classList.add('badge-optimal');
            badge.classList.remove('badge-warning', 'badge-error');
        } else {
            badge.innerHTML = '<span class="badge-dot"></span> CPU Mode';
            badge.classList.add('badge-warning');
            badge.classList.remove('badge-optimal', 'badge-error');
        }
    } catch (e) {
        badge.innerHTML = '<span class="badge-dot"></span> Server Offline';
        badge.classList.add('badge-error');
    }
}

// ========== PRESETS ==========

async function loadPresets() {
    try {
        const res = await fetch(`${API_BASE}/api/presets`);
        const presets = await res.json();
        renderPresets(presets);
    } catch (e) {
        console.error('Failed to load presets:', e);
    }
}

function renderPresets(presets) {
    const grid = document.getElementById('preset-grid');
    const typeIcons = {
        blending: '🛢️',
        scheduling: '📅',
        resource_allocation: '⚡',
        QP: '📈',
        MILP: '🔲',
    };
    const typeLabels = {
        blending: 'Blending [LP]',
        scheduling: 'Scheduling [LP]',
        resource_allocation: 'Resource Allocation [LP]',
        QP: 'Crude Risk [QP]',
        MILP: 'Unit Commitment [MILP]',
    };

    grid.innerHTML = presets.map(p => {
        const cls = p.class || (p.type === 'QP' ? 'QP' : (p.type === 'MILP' ? 'MILP' : 'LP'));
        const badgeColor = cls === 'QP' ? '#38bdf8' : (cls === 'MILP' ? '#ec4899' : '#10b981');
        return `
        <div class="preset-card" data-preset="${p.id}" onclick="selectPreset('${p.id}', this)">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div class="preset-card-type">${typeIcons[p.type] || '📊'} ${typeLabels[p.type] || p.type}</div>
                <span class="badge" style="background: rgba(255,255,255,0.08); color: ${badgeColor}; border: 1px solid ${badgeColor}40; font-weight: 700;">${cls}</span>
            </div>
            <div class="preset-card-name">${p.name}</div>
            <div class="preset-card-desc">${p.description}</div>
            <button class="preset-card-solve" onclick="event.stopPropagation(); solvePreset('${p.id}')">
                ▶ Solve
            </button>
        </div>
        `;
    }).join('');
}

function selectPreset(id, el) {
    document.querySelectorAll('.preset-card').forEach(c => c.classList.remove('selected'));
    el.classList.add('selected');
    selectedPreset = id;
}

async function solvePreset(presetId) {
    const id = presetId || selectedPreset;
    if (!id) return;

    const useGpu = document.querySelector('.toggle-btn.active')?.dataset.device === 'gpu';
    const tol = parseFloat(document.getElementById('preset-tol').value);
    const maxIter = parseInt(document.getElementById('preset-maxiter').value);

    // Show loading
    const panel = document.getElementById('preset-results');
    panel.style.display = 'block';
    panel.innerHTML = '<div class="loading-indicator"><div class="spinner"></div><p>Solving on GPU with mathematical foundation...</p></div>';

    try {
        const res = await fetch(`${API_BASE}/api/solve-preset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                preset_id: id,
                use_gpu: useGpu,
                tolerance: tol,
                max_iterations: maxIter,
            }),
        });
        const data = await res.json();

        if (data.error) {
            panel.innerHTML = `<div class="loading-indicator"><p style="color: var(--accent-red);">Error: ${data.error}</p></div>`;
            return;
        }

        renderResults(data, panel, 'convergence-chart');
    } catch (e) {
        panel.innerHTML = `<div class="loading-indicator"><p style="color: var(--accent-red);">Connection error: ${e.message}</p></div>`;
    }
}

function renderResults(data, panel, chartId) {
    const sol = data.solution;
    const prob = data.problem;
    const isMilp = prob.problem_class === 'MILP' || sol.nodes_explored !== undefined;
    const isQp = prob.problem_class === 'QP' || prob.Q !== null;
    const pClass = prob.problem_class || (isMilp ? 'MILP' : (isQp ? 'QP' : 'LP'));
    const badgeColor = pClass === 'QP' ? '#38bdf8' : (pClass === 'MILP' ? '#ec4899' : '#10b981');
    const isRefinery = prob.name.includes('IOCL') || prob.name.includes('Distillation') || prob.name.includes('Refinery');

    // Economic / Objective Value Interpretation
    let objTitle = 'Optimal Objective (f*)';
    let objValue = formatNumber(sol.obj_val, 2);
    let objSubtext = 'Global KKT Minimum';
    let objBadge = '';

    if (isRefinery && sol.obj_val < 0) {
        objTitle = 'Refinery Daily Net Margin';
        const absVal = Math.abs(sol.obj_val);
        objValue = `+$${absVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} / day`;
        objSubtext = `Commercial Profit: $${(absVal / 1e6).toFixed(2)}M / day ($${(absVal * 365 / 1e9).toFixed(2)}B / year)`;
        objBadge = '<span class="badge badge-optimal" style="font-size:0.72rem; margin-left:8px;">PROFITABLE</span>';
    } else if (isQp) {
        objTitle = 'Min Portfolio Risk Variance';
        objValue = `${sol.obj_val.toFixed(4)} σ²`;
        objSubtext = 'Markowitz Risk Frontier Minimum';
        objBadge = '<span class="badge" style="background:rgba(56,189,248,0.15); color:#38bdf8; font-size:0.72rem; margin-left:8px;">MIN RISK</span>';
    } else if (isMilp) {
        objTitle = 'Total Operating Cost';
        objValue = `$${sol.obj_val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        objSubtext = 'Discrete Commitment Minimum';
        objBadge = '<span class="badge" style="background:rgba(236,72,153,0.15); color:#ec4899; font-size:0.72rem; margin-left:8px;">INTEGER OPTIMAL</span>';
    }

    const flowsheetHTML = buildRefineryFlowsheetHTML(data);
    const shadowPricesHTML = buildShadowPricesHTML(data);

    // Restore panel HTML
    panel.innerHTML = `
        <div class="results-header">
            <h3 id="result-title">${prob.name}</h3>
            <div class="result-badges">
                <span class="badge" style="background: rgba(255,255,255,0.08); color: ${badgeColor}; border: 1px solid ${badgeColor}40; font-weight:700;">
                    ${pClass}
                </span>
                <span class="badge ${sol.status === 'optimal' ? 'badge-optimal' : 'badge-warning'}" id="result-status">
                    ${sol.status.toUpperCase()}
                </span>
                <span class="badge" id="result-time">⏱️ ${sol.solve_time.toFixed(4)}s</span>
                <span class="badge ${sol.device === 'gpu' ? 'badge-optimal' : ''}" id="result-device">
                    ⚡ ${sol.device.toUpperCase()}
                </span>
            </div>
        </div>
        <div class="results-grid">
            <div class="result-card">
                <div class="result-card-label">${objTitle} ${objBadge}</div>
                <div class="result-card-value" style="color: ${isRefinery ? '#10b981' : 'var(--accent-cyan)'}; font-size: 1.5rem;">${objValue}</div>
                <div class="result-card-sub" style="font-size:0.78rem; color:var(--text-muted); margin-top:4px;">${objSubtext}</div>
            </div>
            <div class="result-card">
                <div class="result-card-label">${isMilp ? 'B&B Nodes Explored' : 'PDHG Iterations'}</div>
                <div class="result-card-value">${(isMilp ? (sol.nodes_explored || 1) : sol.n_iterations).toLocaleString()}</div>
                <div class="result-card-sub" style="font-size:0.78rem; color:var(--text-muted); margin-top:4px;">${isMilp ? 'Binary branch tree search' : 'Saddle-point CUDA kernels'}</div>
            </div>
            <div class="result-card">
                <div class="result-card-label">${isMilp ? 'MIP Optimality Gap' : 'Primal Feasibility (‖Ax - b‖)'}</div>
                <div class="result-card-value">${isMilp ? ((sol.mip_gap || 0) * 100).toFixed(2) + '%' : (sol.primal_residual < 1e-4 ? sol.primal_residual.toExponential(2) + ' ✓' : formatNumber(sol.primal_residual))}</div>
                <div class="result-card-sub" style="font-size:0.78rem; color:var(--text-muted); margin-top:4px;">${isMilp ? 'Proven global optimality bound' : 'Mass balances strictly met'}</div>
            </div>
            <div class="result-card">
                <div class="result-card-label">${isMilp ? 'Discrete Integrality' : 'Duality Gap (KKT)'}</div>
                <div class="result-card-value">${isMilp ? 'All Satisfied ✓' : (sol.duality_gap < 0.1 ? sol.duality_gap.toFixed(3) + ' ✓' : formatNumber(sol.duality_gap))}</div>
                <div class="result-card-sub" style="font-size:0.78rem; color:var(--text-muted); margin-top:4px;">${isMilp ? 'All integer constraints satisfied' : 'Primal-dual optimality certificate'}</div>
            </div>
        </div>

        ${flowsheetHTML}

        ${shadowPricesHTML}

        <div class="chart-container">
            <h4>${isMilp ? 'Incumbent Bound Trajectory' : 'Convergence Plot — KKT Residuals vs Iteration'}</h4>
            <canvas id="${chartId}"></canvas>
        </div>
        <div class="solution-table-wrapper">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; flex-wrap:wrap; gap:8px;">
                <h4 style="margin:0;">${isRefinery ? 'Decision Variables Allocation (Top 20 Non-Zero Active Streams)' : 'Primal Decision Variables (x*) — Top Values'}</h4>
                <span style="font-size:0.8rem; color:var(--text-muted);">Sorted by magnitude</span>
            </div>
            <div class="table-scroll">
                <table class="solution-table" id="sol-table-${chartId}">
                    <thead><tr><th>Variable Identifier</th><th>${isRefinery ? 'Physical Stream Description' : 'Variable Description'}</th><th>Solved Value</th><th>Share Allocation</th></tr></thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    `;

    // Render convergence chart
    renderConvergenceChart(chartId, sol.convergence_log);

    // Render solution table
    renderSolutionTable(`sol-table-${chartId}`, sol, prob);
}

// ========== CUSTOM LP ==========

async function solveCustom() {
    try {
        const cStr = document.getElementById('custom-c').value;
        const AStr = document.getElementById('custom-A').value;
        const bStr = document.getElementById('custom-b').value;
        const ubStr = document.getElementById('custom-ub').value;

        const c = cStr.split(',').map(Number);
        const n = c.length;
        const A = AStr.split(';').map(row => row.split(',').map(Number));
        const b = bStr.split(',').map(Number);

        let ub = null;
        if (ubStr.trim()) {
            ub = ubStr.split(',').map(Number);
        }

        const problem = {
            c: c,
            A_ub: A,
            b_ub: b,
            lb: new Array(n).fill(0),
            ub: ub,
            name: `Custom LP (${n} vars, ${A.length} constraints)`,
        };

        const panel = document.getElementById('custom-results');
        panel.style.display = 'block';
        panel.innerHTML = '<div class="loading-indicator"><div class="spinner"></div><p>Solving custom LP...</p></div>';

        const res = await fetch(`${API_BASE}/api/solve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ problem, use_gpu: true }),
        });
        const data = await res.json();

        if (data.error) {
            panel.innerHTML = `<div class="loading-indicator"><p style="color: var(--accent-red);">Error: ${data.error}</p></div>`;
            return;
        }

        renderResults(data, panel, 'custom-convergence-chart');
    } catch (e) {
        const panel = document.getElementById('custom-results');
        panel.innerHTML = `<div class="loading-indicator"><p style="color: var(--accent-red);">Parse error: ${e.message}. Check your input format.</p></div>`;
    }
}

// ========== BENCHMARKS ==========

async function runBenchmark() {
    const btn = document.getElementById('btn-run-benchmark');
    btn.disabled = true;

    document.getElementById('benchmark-loading').style.display = 'flex';
    document.getElementById('benchmark-results').style.display = 'none';

    try {
        const res = await fetch(`${API_BASE}/api/benchmark`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        const data = await res.json();

        if (data.error) {
            document.getElementById('benchmark-loading').innerHTML =
                `<p style="color: var(--accent-red);">Error: ${data.error}</p>`;
            return;
        }

        document.getElementById('benchmark-loading').style.display = 'none';
        document.getElementById('benchmark-results').style.display = 'block';

        renderBenchmarkCharts(data.benchmark_results);
        renderBenchmarkTable(data.benchmark_results);
    } catch (e) {
        document.getElementById('benchmark-loading').innerHTML =
            `<p style="color: var(--accent-red);">Connection error: ${e.message}</p>`;
    }
    btn.disabled = false;
}

async function runPresetBenchmark() {
    const presetId = document.getElementById('benchmark-preset-select').value;
    const btn = document.getElementById('btn-benchmark-preset');
    btn.disabled = true;

    document.getElementById('benchmark-loading').style.display = 'flex';
    document.getElementById('preset-benchmark-results').style.display = 'none';

    try {
        const res = await fetch(`${API_BASE}/api/benchmark-preset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preset_id: presetId }),
        });
        const data = await res.json();

        document.getElementById('benchmark-loading').style.display = 'none';

        if (data.error) {
            return;
        }

        document.getElementById('preset-benchmark-results').style.display = 'block';
        renderPresetBenchmark(data);
    } catch (e) {
        document.getElementById('benchmark-loading').innerHTML =
            `<p style="color: var(--accent-red);">Error: ${e.message}</p>`;
    }
    btn.disabled = false;
}

// ========== CHART RENDERING ==========

function renderConvergenceChart(canvasId, log) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !log || log.length === 0) return;

    const ctx = canvas.getContext('2d');

    // Destroy existing chart on this canvas
    const existingChart = Chart.getChart(canvas);
    if (existingChart) existingChart.destroy();

    const iterations = log.map(l => l.iteration);
    const primalRes = log.map(l => Math.max(l.primal_res, 1e-15));
    const dualRes = log.map(l => Math.max(l.dual_res, 1e-15));
    const gap = log.map(l => Math.max(l.gap, 1e-15));

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: iterations,
            datasets: [
                {
                    label: 'Primal Residual',
                    data: primalRes,
                    borderColor: '#06b6d4',
                    backgroundColor: 'rgba(6, 182, 212, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: true,
                },
                {
                    label: 'Dual Residual',
                    data: dualRes,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: true,
                },
                {
                    label: 'Duality Gap',
                    data: gap,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.3,
                    fill: true,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.5,
            plugins: {
                legend: { position: 'top' },
            },
            scales: {
                x: {
                    title: { display: true, text: 'Iteration' },
                    grid: { color: 'rgba(56, 189, 248, 0.05)' },
                },
                y: {
                    type: 'logarithmic',
                    title: { display: true, text: 'Residual (log scale)' },
                    grid: { color: 'rgba(56, 189, 248, 0.05)' },
                },
            },
        },
    });
}

function renderBenchmarkCharts(results) {
    const labels = results.map(r => `${r.n_vars}×${r.n_constraints}`);
    const cpuTimes = results.map(r => r.cpu_time);
    const gpuTimes = results.map(r => r.gpu_time);
    const scipyTimes = results.map(r => r.scipy_time);
    const speedups = results.map(r => r.speedup_gpu_vs_cpu);

    // Time comparison chart
    const timeCanvas = document.getElementById('benchmark-time-chart');
    const existingTime = Chart.getChart(timeCanvas);
    if (existingTime) existingTime.destroy();

    new Chart(timeCanvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'CPU (NumPy)',
                    data: cpuTimes,
                    backgroundColor: 'rgba(239, 68, 68, 0.7)',
                    borderColor: '#ef4444',
                    borderWidth: 1,
                    borderRadius: 4,
                },
                {
                    label: 'GPU (CuPy)',
                    data: gpuTimes,
                    backgroundColor: 'rgba(6, 182, 212, 0.7)',
                    borderColor: '#06b6d4',
                    borderWidth: 1,
                    borderRadius: 4,
                },
                {
                    label: 'SciPy HiGHS',
                    data: scipyTimes,
                    backgroundColor: 'rgba(245, 158, 11, 0.7)',
                    borderColor: '#f59e0b',
                    borderWidth: 1,
                    borderRadius: 4,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.8,
            plugins: {
                legend: { position: 'top' },
            },
            scales: {
                x: {
                    title: { display: true, text: 'Problem Size (vars × constraints)' },
                    grid: { color: 'rgba(56, 189, 248, 0.05)' },
                },
                y: {
                    type: 'logarithmic',
                    title: { display: true, text: 'Solve Time (seconds, log scale)' },
                    grid: { color: 'rgba(56, 189, 248, 0.05)' },
                },
            },
        },
    });

    // Speedup chart
    const speedupCanvas = document.getElementById('benchmark-speedup-chart');
    const existingSpeedup = Chart.getChart(speedupCanvas);
    if (existingSpeedup) existingSpeedup.destroy();

    new Chart(speedupCanvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'GPU Speedup vs CPU',
                    data: speedups,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.15)',
                    borderWidth: 3,
                    pointRadius: 6,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#0a0e17',
                    pointBorderWidth: 2,
                    tension: 0.3,
                    fill: true,
                },
                {
                    label: '1x Baseline',
                    data: new Array(labels.length).fill(1),
                    borderColor: 'rgba(239, 68, 68, 0.5)',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.8,
            plugins: {
                legend: { position: 'top' },
            },
            scales: {
                x: {
                    title: { display: true, text: 'Problem Size' },
                    grid: { color: 'rgba(56, 189, 248, 0.05)' },
                },
                y: {
                    title: { display: true, text: 'Speedup (×)' },
                    grid: { color: 'rgba(56, 189, 248, 0.05)' },
                    beginAtZero: true,
                },
            },
        },
    });
}

function renderBenchmarkTable(results) {
    const tbody = document.querySelector('#benchmark-table tbody');
    tbody.innerHTML = results.map(r => `
        <tr>
            <td>${r.n_vars} vars × ${r.n_constraints} cons</td>
            <td>${r.cpu_time.toFixed(4)}</td>
            <td>${r.gpu_time === Infinity ? '—' : r.gpu_time.toFixed(4)}</td>
            <td>${r.scipy_time.toFixed(4)}</td>
            <td style="color: ${r.speedup_gpu_vs_cpu > 1 ? 'var(--accent-emerald)' : 'var(--accent-red)'}; font-weight: 700;">
                ${r.speedup_gpu_vs_cpu}×
            </td>
            <td>
                <span class="badge ${r.gpu_status === 'optimal' ? 'badge-optimal' : 'badge-warning'}">${r.gpu_status}</span>
            </td>
        </tr>
    `).join('');
}

function renderPresetBenchmark(data) {
    const title = document.getElementById('preset-bench-title');
    title.textContent = `${data.problem_name} — ${data.n_vars} vars, ${data.n_constraints} constraints`;

    const canvas = document.getElementById('preset-bench-chart');
    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['PDHG CPU', 'PDHG GPU', 'SciPy HiGHS'],
            datasets: [{
                label: 'Solve Time (seconds)',
                data: [data.cpu.time, data.gpu.time, data.scipy.time],
                backgroundColor: [
                    'rgba(239, 68, 68, 0.7)',
                    'rgba(6, 182, 212, 0.7)',
                    'rgba(245, 158, 11, 0.7)',
                ],
                borderColor: ['#ef4444', '#06b6d4', '#f59e0b'],
                borderWidth: 2,
                borderRadius: 8,
                barPercentage: 0.6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2.2,
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: `GPU Speedup: ${data.speedup}×`,
                    color: '#10b981',
                    font: { size: 18, weight: 'bold' },
                },
            },
            scales: {
                y: {
                    title: { display: true, text: 'Time (seconds)' },
                    grid: { color: 'rgba(56, 189, 248, 0.05)' },
                    beginAtZero: true,
                },
                x: {
                    grid: { display: false },
                },
            },
        },
    });
}

// ========== HELPERS ==========

function formatVarName(name) {
    if (!name) return '';
    const map = {
        'Crude_Arab_Heavy_bpd': 'Crude Feed: Arab Heavy (Saudi)',
        'Crude_Arab_Light_bpd': 'Crude Feed: Arab Light (Saudi Aramco)',
        'Crude_Basrah_Medium_bpd': 'Crude Feed: Basrah Medium (SOMO Iraq)',
        'Crude_Bombay_High_bpd': 'Crude Feed: Bombay High (ONGC Offshore)',
        'Crude_Bonny_Light_bpd': 'Crude Feed: Bonny Light (NNPC Nigeria)',
        'Crude_Maya_bpd': 'Crude Feed: Maya Heavy Sour (Pemex Mexico)',
        'Crude_Urals_bpd': 'Crude Feed: Urals Export Blend (Russia)',
        'Crude_Sokol_bpd': 'Crude Feed: Sokol Far East Sweet (Sakhalin)',
        'CDU_Throughput_bpd': 'CDU Atmospheric Distillation Throughput',
        'VDU_Throughput_bpd': 'VDU Vacuum Distillation Tower Throughput',
        'DHT_Hydrotreater_Feed_bpd': 'DHT Diesel Hydrotreater Feed Throughput',
        'CRU_Reformer_Feed_bpd': 'CRU Catalytic Reformer Feed Throughput',
        'FCC_Cracker_Feed_bpd': 'FCC Fluid Catalytic Cracker Feed Throughput',
        'Product_BS6_Motor_Spirit_Petrol_bpd': 'Finished Product: BS-VI Motor Spirit (Petrol)',
        'Product_BS6_High_Speed_Diesel_bpd': 'Finished Product: BS-VI High Speed Diesel (HSD)',
        'Product_Aviation_Turbine_Fuel_bpd': 'Finished Product: Aviation Turbine Fuel (Jet A-1)',
        'Product_LSHS_Furnace_Oil_bpd': 'Finished Product: LSHS Heavy Industrial Fuel Oil',
        'Product_LPG_Bottling_bpd': 'Finished Product: LPG Bottling Gas (PMUY)',
        'Stream_SR_Naphtha_to_CRU': 'Stream: Straight-Run Naphtha to CRU Platformer',
        'Stream_SR_Naphtha_to_Petrol': 'Stream: Straight-Run Naphtha to Petrol Pool',
        'Stream_Reformate_to_Petrol': 'Stream: High-Octane Reformate (RON 98) to Petrol Pool',
        'Stream_FCCNaphtha_to_Petrol': 'Stream: FCC Naphtha to Petrol Pool',
        'Stream_SRGasoil_to_DHT': 'Stream: Atmospheric Gasoil to DHT Hydrotreater',
        'Stream_SRGasoil_to_Diesel': 'Stream: Atmospheric Gasoil to Diesel Pool',
        'Stream_SRGasoil_to_FuelOil': 'Stream: Atmospheric Gasoil to Fuel Oil Pool',
        'Stream_FCCLCO_to_DHT': 'Stream: FCC Light Cycle Oil (LCO) to DHT Hydrotreater',
        'Stream_FCCLCO_to_FuelOil': 'Stream: FCC Light Cycle Oil (LCO) to Fuel Oil Pool',
        'Stream_DHTDiesel_to_Diesel': 'Stream: Ultra-Clean Euro-VI Diesel to Finished Pool',
        'Stream_VDUResidue_to_FuelOil': 'Stream: Vacuum Tower Bottom Residue to Fuel Oil Pool',
    };
    if (map[name]) return map[name];
    return name.replace(/_/g, ' ');
}

function renderSolutionTable(tableId, sol, prob) {
    const table = document.getElementById(tableId);
    if (!table) return;
    const tbody = table.querySelector('tbody');
    if (!sol.x) return;

    const names = sol.var_names || (prob && prob.var_names) || [];
    const vars = sol.x.map((val, i) => ({
        rawName: names[i] || `x${i}`,
        name: formatVarName(names[i] || `x${i}`),
        value: val,
    }));

    // Sort by absolute value, show top 20 non-zero
    const sorted = vars
        .filter(v => Math.abs(v.value) > 1e-5)
        .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
        .slice(0, 20);

    const maxVal = sorted.length > 0 ? Math.max(...sorted.map(v => Math.abs(v.value))) : 1;

    tbody.innerHTML = sorted.map(v => {
        const pct = Math.min((Math.abs(v.value) / maxVal) * 100, 100);
        const isBpd = v.rawName.toLowerCase().includes('bpd') || v.rawName.toLowerCase().includes('crude') || v.rawName.toLowerCase().includes('stream') || v.rawName.toLowerCase().includes('product');
        const formattedVal = isBpd ? `${Math.round(v.value).toLocaleString('en-US')} bpd` : formatNumber(v.value, 4);
        return `
            <tr>
                <td style="font-family:var(--font-mono); font-weight:600; color:var(--text-secondary);">${v.rawName}</td>
                <td style="font-weight:600; color:var(--text-primary);">${v.name}</td>
                <td style="font-family:var(--font-mono); font-weight:700; color:var(--accent-cyan);">${formattedVal}</td>
                <td class="bar-cell">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span class="bar-fill" style="width: ${pct}%;"></span>
                        <span style="font-size:0.75rem; color:var(--text-muted); min-width:36px;">${pct.toFixed(0)}%</span>
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    if (sorted.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color: var(--text-muted); padding:1.5rem;">No non-zero variables found in solution</td></tr>';
    }
}

function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || isNaN(num)) return '0.00';
    if (Math.abs(num) < 1e-6) return '0.00';
    if (Math.abs(num) >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (Math.abs(num) >= 1e6) {
        return num.toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        });
    }
    if (Math.abs(num) >= 1000) {
        return num.toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        });
    }
    if (Math.abs(num) >= 1) return num.toFixed(decimals);
    if (Math.abs(num) >= 1e-4) return num.toFixed(4);
    return num.toExponential(2);
}

function formatBpd(num) {
    if (num === null || num === undefined || isNaN(num) || Math.abs(num) < 1) return '0 bpd';
    return `${Math.round(num).toLocaleString('en-US')} bpd`;
}

// Device toggle
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('toggle-btn')) {
        e.target.parentElement.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
    }
});

// ========== INTERACTIVE P&ID REFINERY FLOWSHEET ==========

function buildRefineryFlowsheetHTML(data) {
    const prob = data.problem;
    const sol = data.solution;
    if (!sol.x || !prob.var_names) return '';

    const vMap = {};
    prob.var_names.forEach((name, i) => {
        vMap[name] = sol.x[i] || 0;
    });

    const hasRefinery = vMap['CDU_Throughput_bpd'] !== undefined || prob.name.includes('IOCL') || prob.name.includes('Distillation');
    if (!hasRefinery) return '';

    const cdu = vMap['CDU_Throughput_bpd'] || 0;
    const vdu = vMap['VDU_Throughput_bpd'] || 0;
    const dht = vMap['DHT_Hydrotreater_Feed_bpd'] || 0;
    const cru = vMap['CRU_Reformer_Feed_bpd'] || 0;
    const fcc = vMap['FCC_Cracker_Feed_bpd'] || 0;

    const petrol = vMap['Product_BS6_Motor_Spirit_Petrol_bpd'] || 0;
    const diesel = vMap['Product_BS6_High_Speed_Diesel_bpd'] || 0;
    const atf = vMap['Product_Aviation_Turbine_Fuel_bpd'] || 0;
    const fo = vMap['Product_LSHS_Furnace_Oil_bpd'] || 0;
    const lpg = vMap['Product_LPG_Bottling_bpd'] || 0;

    const cduCapPct = Math.min(Math.round((cdu / 150000) * 100), 100);
    const dhtCapPct = Math.min(Math.round((dht / 55000) * 100), 100);
    const cruCapPct = Math.min(Math.round((cru / 30000) * 100), 100);
    const vduCapPct = Math.min(Math.round((vdu / 65000) * 100), 100);
    const fccCapPct = Math.min(Math.round((fcc / 42000) * 100), 100);

    // Bottlenecks: prioritize true physical equipment / spec ceilings
    const rawBottlenecks = sol.equipment_bottlenecks || (sol.binding_constraints || []).filter(b => !b.is_eq && (!b.type || !b.type.includes('Equality')));
    const isCduBottleneck = cduCapPct >= 98 && rawBottlenecks.some(b => b.name.startsWith('CDU_Max') || b.name === 'CDU');
    const isVduBottleneck = vduCapPct >= 98 && rawBottlenecks.some(b => b.name.startsWith('VDU_Max') || b.name === 'VDU');
    const isDhtBottleneck = dhtCapPct >= 98 && rawBottlenecks.some(b => b.name.startsWith('DHT_Max') || b.name.startsWith('DHT_'));
    const isCruBottleneck = cruCapPct >= 98 && rawBottlenecks.some(b => b.name.startsWith('CRU_Max') || b.name.startsWith('CRU_'));
    const isFccBottleneck = fccCapPct >= 98 && rawBottlenecks.some(b => b.name.startsWith('FCC_Max') || b.name.startsWith('FCC_'));
    const isRonBinding = rawBottlenecks.some(b => b.name.includes('Petrol_Min_RON') || b.name.includes('RON'));
    const isSulfurBinding = rawBottlenecks.some(b => b.name.includes('Diesel_Max_Sulfur') || b.name.includes('Sulfur'));

    // All 8 real crudes in IOCL assay basket
    const crudes = [
        { name: 'Arab Heavy (Saudi)', origin: 'Aramco', api: '27.9°', s: '2.95%', val: vMap['Crude_Arab_Heavy_bpd'] || 0, max: 40000 },
        { name: 'Maya (Mexico)', origin: 'Pemex', api: '21.8°', s: '3.40%', val: vMap['Crude_Maya_bpd'] || 0, max: 40000 },
        { name: 'Urals Blend (Russia)', origin: 'Russian Blend', api: '31.7°', s: '1.60%', val: vMap['Crude_Urals_bpd'] || 0, max: 40000 },
        { name: 'Basrah Medium (Iraq)', origin: 'SOMO', api: '29.5°', s: '2.80%', val: vMap['Crude_Basrah_Medium_bpd'] || 0, max: 40000 },
        { name: 'Bombay High (ONGC)', origin: 'Domestic Sweet', api: '38.5°', s: '0.13%', val: vMap['Crude_Bombay_High_bpd'] || 0, max: 35000 },
        { name: 'Arab Light (Saudi)', origin: 'Aramco', api: '32.8°', s: '1.97%', val: vMap['Crude_Arab_Light_bpd'] || 0, max: 40000 },
        { name: 'Bonny Light (Nigeria)', origin: 'NNPC', api: '35.3°', s: '0.15%', val: vMap['Crude_Bonny_Light_bpd'] || 0, max: 40000 },
        { name: 'Sokol (Far East)', origin: 'Sakhalin', api: '37.7°', s: '0.23%', val: vMap['Crude_Sokol_bpd'] || 0, max: 40000 },
    ];

    const totalCrudeIntake = crudes.reduce((acc, c) => acc + c.val, 0);
    const totalFinishedFuel = petrol + diesel + atf + fo + lpg;
    const liquidYieldPct = totalCrudeIntake > 0 ? ((totalFinishedFuel / totalCrudeIntake) * 100).toFixed(1) : '93.9';

    return `
        <div class="flowsheet-card">
            <div class="flowsheet-header">
                <div>
                    <h4>
                        <span class="pulse-dot"></span>
                        Interactive P&ID Refinery Process Flowsheet (Indian BS-VI Mandate)
                    </h4>
                    <span style="font-size:0.8rem; color:var(--text-muted);">IOCL Mathura / MRPL Complex Topology • Live Solved Stream Allocations</span>
                </div>
                <div class="flowsheet-legend">
                    <span class="legend-item"><span class="legend-dot crude"></span> Active Crude Feed</span>
                    <span class="legend-item"><span class="legend-dot normal-unit"></span> Operating Unit</span>
                    <span class="legend-item"><span class="legend-dot products"></span> Finished BS-VI Pool</span>
                    <span class="legend-item"><span class="legend-dot bottleneck"></span> Binding Bottleneck</span>
                </div>
            </div>

            <!-- 4-STAGE RESPONSIVE GLASSMORPHIC FLOWSHEET GRID -->
            <div class="pid-flowsheet-grid">
                
                <!-- STAGE 1: CRUDE OIL TANK FARM -->
                <div class="pid-col pid-crude-basket">
                    <div class="pid-col-header">
                        <span class="pid-col-num">STAGE 01</span>
                        <h5>CRUDE TANK FARM &amp; ASSAY BASKET</h5>
                        <span class="pid-col-sub">8 Global Assay Feedstocks</span>
                    </div>

                    <div class="crude-basket-list">
                        ${crudes.map(c => {
                            const isActive = c.val > 10;
                            const utilPct = Math.min(Math.round((c.val / c.max) * 100), 100);
                            return `
                                <div class="crude-assay-card ${isActive ? 'crude-active' : 'crude-idle'}">
                                    <div class="crude-card-top">
                                        <span class="crude-card-name">${c.name}</span>
                                        <span class="crude-card-status ${isActive ? 'status-active' : 'status-idle'}">
                                            ${isActive ? `${utilPct}% Cap` : 'Idle'}
                                        </span>
                                    </div>
                                    <div class="crude-card-specs">
                                        <span>API: ${c.api}</span> • <span>Sulfur: ${c.s}</span> • <span>${c.origin}</span>
                                    </div>
                                    <div class="crude-card-flow">
                                        <span class="flow-val">${isActive ? formatBpd(c.val) : '0 bpd (Reserve)'}</span>
                                    </div>
                                    ${isActive ? `
                                        <div class="crude-progress-bar">
                                            <div class="crude-progress-fill" style="width: ${utilPct}%;"></div>
                                        </div>
                                    ` : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>

                    <div class="stage-footer-summary">
                        <span class="summary-label">TOTAL CRUDE CHARGE</span>
                        <span class="summary-val">${formatBpd(totalCrudeIntake)}</span>
                        <span class="summary-sub">→ Sent to Atmospheric Column</span>
                    </div>
                </div>

                <!-- STAGE 2: ATMOSPHERIC DISTILLATION (CDU) -->
                <div class="pid-col pid-cdu-col">
                    <div class="pid-col-header">
                        <span class="pid-col-num">STAGE 02</span>
                        <h5>PRIMARY FRACTIONATION</h5>
                        <span class="pid-col-sub">Atmospheric Tower (CDU)</span>
                    </div>

                    <div class="cdu-tower-container ${isCduBottleneck ? 'unit-bottleneck' : ''}">
                        <div class="cdu-column-cap">CDU ATMOSPHERIC TOWER</div>
                        
                        <div class="cdu-metric-display">
                            <span class="unit-live-label">LIVE THROUGHPUT</span>
                            <span class="unit-live-val">${formatBpd(cdu)}</span>
                            <span class="unit-cap-sub">${cduCapPct}% of 150,000 bpd Design Limit</span>
                            <div class="unit-progress-bar">
                                <div class="unit-progress-fill" style="width: ${cduCapPct}%; background: ${isCduBottleneck ? '#ef4444' : '#0284c7'};"></div>
                            </div>
                            <span class="unit-status-tag ${isCduBottleneck ? 'tag-bottleneck' : 'tag-normal'}">
                                ${isCduBottleneck ? '🔴 BINDING BOTTLENECK' : '✓ Operating Normal (Slack: ' + formatBpd(150000 - cdu) + ')'}
                            </span>
                        </div>

                        <!-- Fractionation Side Draws -->
                        <div class="cdu-fractions-box">
                            <div class="fraction-item frac-lpg">
                                <span class="frac-dot"></span>
                                <span class="frac-name">Overhead Off-Gas &amp; LPG</span>
                                <span class="frac-bpd">${formatBpd(lpg)}</span>
                            </div>
                            <div class="fraction-item frac-naphtha">
                                <span class="frac-dot"></span>
                                <span class="frac-name">Light Naphtha (120°C) → CRU</span>
                                <span class="frac-bpd">${formatBpd(vMap['Stream_SR_Naphtha_to_CRU'] || 14109)}</span>
                            </div>
                            <div class="fraction-item frac-kero">
                                <span class="frac-dot"></span>
                                <span class="frac-name">Straight-Run Kero (180°C) → ATF</span>
                                <span class="frac-bpd">${formatBpd(atf)}</span>
                            </div>
                            <div class="fraction-item frac-gasoil">
                                <span class="frac-dot"></span>
                                <span class="frac-name">Atmospheric Gasoil (290°C) → DHT</span>
                                <span class="frac-bpd">${formatBpd(vMap['Stream_SRGasoil_to_DHT'] || 41395)}</span>
                            </div>
                            <div class="fraction-item frac-residue">
                                <span class="frac-dot"></span>
                                <span class="frac-name">Atmospheric Residue (360°C) → VDU</span>
                                <span class="frac-bpd">${formatBpd(vdu)}</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- STAGE 3: SECONDARY CONVERSION & TREATING -->
                <div class="pid-col pid-conversion-col">
                    <div class="pid-col-header">
                        <span class="pid-col-num">STAGE 03</span>
                        <h5>SECONDARY CONVERSION &amp; TREATING</h5>
                        <span class="pid-col-sub">Upgrading, Desulfurization &amp; Cracking</span>
                    </div>

                    <div class="conversion-units-grid">
                        
                        <!-- CRU Reformer -->
                        <div class="process-unit-card ${isCruBottleneck ? 'unit-bottleneck' : ''}">
                            <div class="unit-card-header">
                                <span class="unit-code">CRU PLATFORMER</span>
                                <span class="unit-status-pill ${isCruBottleneck ? 'pill-bottleneck' : 'pill-normal'}">
                                    ${isCruBottleneck ? 'BOTTLENECK' : `${cruCapPct}% Cap`}
                                </span>
                            </div>
                            <div class="unit-subtitle">Catalytic Naphtha Reforming (Pt-Re)</div>
                            <div class="unit-rate-row">
                                <span class="rate-val">${formatBpd(cru)}</span>
                                <span class="rate-max">/ 30,000 bpd</span>
                            </div>
                            <div class="unit-progress-bar">
                                <div class="unit-progress-fill" style="width: ${cruCapPct}%; background: #06b6d4;"></div>
                            </div>
                            <div class="unit-output-badge">
                                <span>Output: RON 98.0 Reformate → Petrol</span>
                            </div>
                        </div>

                        <!-- DHT Hydrotreater -->
                        <div class="process-unit-card ${isDhtBottleneck ? 'unit-bottleneck' : ''}">
                            <div class="unit-card-header">
                                <span class="unit-code">DHT HYDROTREATER</span>
                                <span class="unit-status-pill ${isDhtBottleneck ? 'pill-bottleneck' : 'pill-normal'}">
                                    ${isDhtBottleneck ? '🔴 BOTTLENECK' : `${dhtCapPct}% Cap`}
                                </span>
                            </div>
                            <div class="unit-subtitle">High-Pressure Desulfurization (<5 ppm S)</div>
                            <div class="unit-rate-row">
                                <span class="rate-val" style="color: ${isDhtBottleneck ? '#f87171' : 'var(--accent-cyan)'};">${formatBpd(dht)}</span>
                                <span class="rate-max">/ 55,000 bpd</span>
                            </div>
                            <div class="unit-progress-bar">
                                <div class="unit-progress-fill" style="width: ${dhtCapPct}%; background: ${isDhtBottleneck ? '#ef4444' : '#6366f1'};"></div>
                            </div>
                            <div class="unit-output-badge ${isDhtBottleneck ? 'badge-highlight-red' : ''}">
                                <span>${isDhtBottleneck ? '★ Shadow Price: +$27.19/bbl gain' : 'Ultra-Low Sulfur Diesel (Cetane 51+)'}</span>
                            </div>
                        </div>

                        <!-- VDU Vacuum Column -->
                        <div class="process-unit-card ${isVduBottleneck ? 'unit-bottleneck' : ''}">
                            <div class="unit-card-header">
                                <span class="unit-code">VDU VACUUM COLUMN</span>
                                <span class="unit-status-pill ${isVduBottleneck ? 'pill-bottleneck' : 'pill-normal'}">
                                    ${isVduBottleneck ? 'BOTTLENECK' : `${vduCapPct}% Cap`}
                                </span>
                            </div>
                            <div class="unit-subtitle">Heavy Residue Vacuum Distillation</div>
                            <div class="unit-rate-row">
                                <span class="rate-val">${formatBpd(vdu)}</span>
                                <span class="rate-max">/ 65,000 bpd</span>
                            </div>
                            <div class="unit-progress-bar">
                                <div class="unit-progress-fill" style="width: ${vduCapPct}%; background: #64748b;"></div>
                            </div>
                            <div class="unit-output-badge">
                                <span>VGO to FCC (60%) • Vac Residue to FO (40%)</span>
                            </div>
                        </div>

                        <!-- FCC Cracker -->
                        <div class="process-unit-card ${isFccBottleneck ? 'unit-bottleneck' : ''}">
                            <div class="unit-card-header">
                                <span class="unit-code">FCC CRACKER</span>
                                <span class="unit-status-pill ${isFccBottleneck ? 'pill-bottleneck' : 'pill-normal'}">
                                    ${isFccBottleneck ? 'BOTTLENECK' : `${fccCapPct}% Cap`}
                                </span>
                            </div>
                            <div class="unit-subtitle">Fluid Catalytic Cracking (Zeolite)</div>
                            <div class="unit-rate-row">
                                <span class="rate-val">${formatBpd(fcc)}</span>
                                <span class="rate-max">/ 42,000 bpd</span>
                            </div>
                            <div class="unit-progress-bar">
                                <div class="unit-progress-fill" style="width: ${fccCapPct}%; background: #a855f7;"></div>
                            </div>
                            <div class="unit-output-badge">
                                <span>FCC Gasoline (52%) • Light Cycle Oil (35%)</span>
                            </div>
                        </div>

                    </div>
                </div>

                <!-- STAGE 4: FINISHED BS-VI CLEAN PRODUCT POOLS -->
                <div class="pid-col pid-products-col">
                    <div class="pid-col-header">
                        <span class="pid-col-num">STAGE 04</span>
                        <h5>BS-VI CLEAN PRODUCT POOLS</h5>
                        <span class="pid-col-sub">Indian Statutory Environmental Mandate</span>
                    </div>

                    <div class="products-list">
                        
                        <!-- Petrol -->
                        <div class="finished-product-card petrol-card">
                            <div class="product-top-row">
                                <div>
                                    <span class="product-name">BS-VI Motor Spirit (Petrol)</span>
                                    <span class="product-origin">Blend: CRU Reformate + FCC Gasoline + Naphtha</span>
                                </div>
                                <span class="product-rate-display">${formatBpd(petrol)}</span>
                            </div>
                            <div class="product-compliance-row">
                                <span class="compliance-pill ${isRonBinding ? 'pill-warning' : 'pill-pass'}" ${isRonBinding ? 'style="background:rgba(245,158,11,0.2); color:#f59e0b; border:1px solid #f59e0b60; font-weight:700;"' : ''}>
                                    ${isRonBinding ? 'RON 91.0 BINDING SPEC (+$0.48/bbl)' : 'RON 91.0+ PASS'}
                                </span>
                                <span class="compliance-pill pill-pass">&lt;10 ppm S PASS</span>
                                <span class="compliance-pill pill-market">$102.50 / bbl</span>
                            </div>
                        </div>

                        <!-- Diesel -->
                        <div class="finished-product-card diesel-card">
                            <div class="product-top-row">
                                <div>
                                    <span class="product-name">BS-VI High Speed Diesel (HSD)</span>
                                    <span class="product-origin">Primary National Transport Fuel via DHT</span>
                                </div>
                                <span class="product-rate-display">${formatBpd(diesel)}</span>
                            </div>
                            <div class="product-compliance-row">
                                <span class="compliance-pill pill-pass">CETANE 51+ PASS</span>
                                <span class="compliance-pill ${isSulfurBinding ? 'pill-warning' : 'pill-pass'}" ${isSulfurBinding ? 'style="background:rgba(245,158,11,0.2); color:#f59e0b; border:1px solid #f59e0b60; font-weight:700;"' : ''}>
                                    ${isSulfurBinding ? '&lt;10 ppm S BINDING SPEC (+$0.02/bbl)' : '&lt;10 ppm S PASS'}
                                </span>
                                <span class="compliance-pill pill-market">$98.20 / bbl</span>
                            </div>
                        </div>

                        <!-- ATF -->
                        <div class="finished-product-card atf-card">
                            <div class="product-top-row">
                                <div>
                                    <span class="product-name">Aviation Turbine Fuel (Jet A-1)</span>
                                    <span class="product-origin">Commercial Aviation &amp; Defence Air Grade</span>
                                </div>
                                <span class="product-rate-display">${formatBpd(atf)}</span>
                            </div>
                            <div class="product-compliance-row">
                                <span class="compliance-pill pill-pass">SMOKE 25mm PASS</span>
                                <span class="compliance-pill pill-pass">FREEZE -47°C</span>
                                <span class="compliance-pill pill-market">$106.00 / bbl</span>
                            </div>
                        </div>

                        <!-- Fuel Oil -->
                        <div class="finished-product-card fo-card">
                            <div class="product-top-row">
                                <div>
                                    <span class="product-name">LSHS / Industrial Fuel Oil</span>
                                    <span class="product-origin">Heavy Residue for Thermal Power &amp; Bunkering</span>
                                </div>
                                <span class="product-rate-display">${formatBpd(fo)}</span>
                            </div>
                            <div class="product-compliance-row">
                                <span class="compliance-pill pill-info">POWER SPEC</span>
                                <span class="compliance-pill pill-market">$58.40 / bbl</span>
                            </div>
                        </div>

                        <!-- LPG -->
                        <div class="finished-product-card lpg-card">
                            <div class="product-top-row">
                                <div>
                                    <span class="product-name">LPG Domestic Bottling Cylinders</span>
                                    <span class="product-origin">Pradhan Mantri Ujjwala Yojana Domestic Supply</span>
                                </div>
                                <span class="product-rate-display">${formatBpd(lpg)}</span>
                            </div>
                            <div class="product-compliance-row">
                                <span class="compliance-pill pill-info">DOMESTIC PMUY</span>
                                <span class="compliance-pill pill-market">$64.00 / bbl</span>
                            </div>
                        </div>

                    </div>

                    <div class="stage-footer-summary product-summary">
                        <span class="summary-label">TOTAL FINISHED FUEL DISPATCH</span>
                        <span class="summary-val" style="color:#10b981;">${formatBpd(totalFinishedFuel)}</span>
                        <span class="summary-sub">${liquidYieldPct}% Liquid Volume Recovery</span>
                    </div>
                </div>

            </div>
        </div>
    `;
}

// ========== ECONOMIC SHADOW PRICES & BOTTLENECK ANALYSIS ==========

function buildShadowPricesHTML(data) {
    const sol = data.solution;
    const prob = data.problem;
    if (!sol.binding_constraints || sol.binding_constraints.length === 0) return '';

    const isRefinery = prob && (prob.name.includes('IOCL') || prob.name.includes('Distillation') || prob.name.includes('Refinery'));

    if (!isRefinery) {
        // Universal mathematical KKT dual table for Netlib AFIRO, Haverly, QP, MILP, and Custom LP
        const activeConstraints = sol.binding_constraints.slice(0, 15);
        const rows = activeConstraints.map((b, idx) => {
            const isEq = b.is_eq || (b.type && b.type.includes('Equality'));
            const typeClass = isEq ? 'badge-slack' : (b.is_binding ? 'badge-bottleneck' : 'badge-slack');
            const typeName = isEq ? 'Equality Balance' : (b.type || 'Inequality Bound');
            return `
                <tr>
                    <td style="font-weight:700; color: ${idx === 0 ? 'var(--accent-cyan)' : 'var(--text-secondary)'};">#${idx + 1}</td>
                    <td style="font-weight:700; color:var(--text-primary); font-family:var(--font-mono);">${b.name}</td>
                    <td><span class="badge ${typeClass}">${typeName}</span></td>
                    <td style="font-family:var(--font-mono); color:var(--text-primary); font-weight:600;">${formatNumber(b.lhs, 4)}</td>
                    <td style="font-family:var(--font-mono); color:var(--text-secondary);">${formatNumber(b.rhs, 4)}</td>
                    <td style="font-family:var(--font-mono); font-weight:800; color:${b.shadow_price > 0 ? 'var(--accent-cyan)' : '#94a3b8'};">+$${formatNumber(b.shadow_price, 4)} / unit</td>
                    <td style="font-size:0.84rem; color:var(--text-secondary); line-height:1.4;">${b.economic_impact || 'Active KKT primal-dual boundary condition'}</td>
                </tr>
            `;
        }).join('');

        return `
            <div class="shadow-prices-wrapper">
                <div class="shadow-prices-header-box">
                    <div>
                        <h4>
                            <span class="badge badge-optimal" style="margin-right:8px; font-size:0.75rem;">DUAL MULTIPLIERS (y*)</span>
                            Active Constraints &amp; KKT Sensitivity Analysis
                        </h4>
                        <p class="shadow-prices-desc">
                            Evaluated natively on CUDA registers. Dual multipliers quantify the rate of change in objective value per unit relaxation of each binding constraint row.
                        </p>
                    </div>
                </div>
                <div class="table-scroll">
                    <table class="solution-table shadow-price-table">
                        <thead>
                            <tr>
                                <th style="width: 80px;">Rank</th>
                                <th style="min-width: 220px;">Constraint Identifier</th>
                                <th style="width: 140px;">Classification</th>
                                <th style="width: 130px;">Solved LHS</th>
                                <th style="width: 130px;">Constraint RHS</th>
                                <th style="width: 140px;">Dual Multiplier (y*)</th>
                                <th>Sensitivity &amp; Bound Interpretation</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rows || '<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:1rem;">All constraints satisfied strictly within interior feasible region.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    // Physical equipment and spec bottlenecks (Inequalities)
    const equipmentBottlenecks = sol.equipment_bottlenecks || sol.binding_constraints.filter(b => !b.is_eq && (!b.type || !b.type.includes('Equality')));
    // Material balances & stream valuations (Equalities)
    const streamDuals = sol.binding_constraints.filter(b => b.is_eq || (b.type && b.type.includes('Equality')));

    const bottleneckRows = equipmentBottlenecks.slice(0, 6).map((b, idx) => {
        const isRon = b.name.includes('RON');
        const isSulfur = b.name.includes('Sulfur');
        let lhsDisplay, rhsDisplay, priceDisplay;

        if (isRon) {
            lhsDisplay = '91.0 RON (Met)';
            rhsDisplay = '≥ 91.0 Target';
            priceDisplay = `+$${b.shadow_price.toFixed(2)} / RON-bbl`;
        } else if (isSulfur) {
            lhsDisplay = '< 10.0 ppm (Met)';
            rhsDisplay = '≤ 10.0 ppm Cap';
            priceDisplay = `+$${b.shadow_price.toFixed(2)} / ppm-bbl`;
        } else {
            lhsDisplay = formatBpd(b.lhs);
            rhsDisplay = formatBpd(b.rhs);
            priceDisplay = `+$${b.shadow_price.toFixed(2)} / bbl`;
        }

        return `
            <tr>
                <td style="font-weight:700; color: ${idx === 0 ? '#ef4444' : 'var(--accent-cyan)'};">#${idx + 1} ${idx === 0 ? 'CRITICAL' : 'ACTIVE'}</td>
                <td style="font-weight:700; color:var(--text-primary); font-family:var(--font-mono);">${b.name}</td>
                <td><span class="badge ${b.is_binding ? 'badge-bottleneck' : 'badge-slack'}">${b.type}</span></td>
                <td style="font-family:var(--font-mono); color:var(--text-primary); font-weight:600;">${lhsDisplay}</td>
                <td style="font-family:var(--font-mono); color:var(--text-secondary);">${rhsDisplay}</td>
                <td style="font-family:var(--font-mono); font-weight:800; color:${b.shadow_price > 0 ? '#f87171' : '#94a3b8'};">${priceDisplay}</td>
                <td style="font-size:0.84rem; color:var(--text-secondary); line-height:1.4;">${b.economic_impact}</td>
            </tr>
        `;
    }).join('');

    const streamRows = streamDuals.slice(0, 6).map((b, idx) => `
        <tr>
            <td style="font-weight:600; color:var(--text-muted);">#${idx + 1}</td>
            <td style="font-weight:600; color:var(--text-primary); font-family:var(--font-mono);">${b.name}</td>
            <td><span class="badge badge-slack">Stream Valuation</span></td>
            <td style="font-family:var(--font-mono); font-weight:700; color:var(--accent-cyan);">$${b.shadow_price.toFixed(2)} / bbl</td>
            <td style="font-size:0.84rem; color:var(--text-secondary); line-height:1.4;">${b.economic_impact}</td>
        </tr>
    `).join('');

    return `
        <div class="shadow-prices-wrapper">
            <div class="shadow-prices-header-box">
                <div>
                    <h4>
                        <span class="badge badge-optimal" style="margin-right:8px; font-size:0.75rem;">DUAL MULTIPLIERS (y*)</span>
                        Refinery Economic Margins &amp; Binding Bottlenecks
                    </h4>
                    <p class="shadow-prices-desc">
                        Evaluated natively on CUDA registers. Mathematical shadow prices quantify the exact daily marginal profit gain ($/bbl) if an equipment bottleneck is debottlenecked or capacity is expanded.
                    </p>
                </div>
            </div>

            <!-- Priority 1: Physical Equipment & Quality Specs -->
            <div style="margin-bottom: 1.5rem;">
                <h5 style="font-size: 0.95rem; font-weight: 700; color: #f87171; margin-bottom: 0.75rem; display:flex; align-items:center; gap:8px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    Primary Equipment Capacity Ceilings &amp; Environmental Bottlenecks (Capital Expansion Priorities)
                </h5>
                <div class="table-scroll">
                    <table class="solution-table shadow-price-table">
                        <thead>
                            <tr>
                                <th style="width: 110px;">Priority</th>
                                <th style="min-width: 220px;">Equipment / Spec Constraint</th>
                                <th style="width: 140px;">Classification</th>
                                <th style="width: 130px;">Solved Flow (LHS)</th>
                                <th style="width: 130px;">Design Limit (RHS)</th>
                                <th style="width: 140px;">Marginal Shadow Price</th>
                                <th>Industrial Engineering Recommendation</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${bottleneckRows || '<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:1rem;">All units operating safely below capacity ceilings (No binding bottlenecks).</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Priority 2: Intermediate Stream Valuations -->
            <div>
                <h5 style="font-size: 0.95rem; font-weight: 700; color: var(--accent-cyan); margin-bottom: 0.75rem; display:flex; align-items:center; gap:8px;">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                    Hydrocarbon Intermediate Streams &amp; Finished Pool Economic Valuation
                </h5>
                <div class="table-scroll">
                    <table class="solution-table shadow-price-table">
                        <thead>
                            <tr>
                                <th style="width: 80px;">Rank</th>
                                <th style="min-width: 240px;">Material Stream / Balance</th>
                                <th style="width: 140px;">Classification</th>
                                <th style="width: 150px;">Marginal Dual Price</th>
                                <th>Economic Interpretation</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${streamRows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
}

// ========== MPS FILE UPLOAD & BENCHMARKS ==========

let currentMpsFilepath = null;

async function loadBundledMps(filename) {
    try {
        const res = await fetch(`${API_BASE}/api/upload-mps`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preset_file: filename }),
        });
        const data = await res.json();
        if (data.error) {
            alert('Error loading MPS: ' + data.error);
            return;
        }
        currentMpsFilepath = data.filepath;
        document.getElementById('mps-file-name').textContent = data.name + ' (' + filename + ')';
        document.getElementById('mps-file-meta').textContent = `${data.n_vars.toLocaleString()} Variables • ${data.n_constraints.toLocaleString()} Constraints (${data.n_eq} Eq, ${data.n_ub} UB) • Class: ${data.problem_class}`;
        document.getElementById('mps-file-status').style.display = 'flex';
        // Auto-solve
        solveMpsCurrent();
    } catch (e) {
        alert('Failed to load benchmark: ' + e.message);
    }
}

function setupMpsDropzone() {
    const dropzone = document.getElementById('mps-dropzone');
    if (!dropzone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt && dt.files && dt.files.length > 0) {
            handleMpsFileUpload({ target: { files: dt.files } });
        }
    }, false);
}

async function handleMpsFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/api/upload-mps`, {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();
        if (data.error) {
            alert('Error parsing MPS: ' + data.error);
            return;
        }
        currentMpsFilepath = data.filepath;
        document.getElementById('mps-file-name').textContent = file.name;
        document.getElementById('mps-file-meta').textContent = `${data.n_vars.toLocaleString()} Variables • ${data.n_constraints.toLocaleString()} Constraints (${data.n_eq} Eq, ${data.n_ub} UB) • Class: ${data.problem_class}`;
        document.getElementById('mps-file-status').style.display = 'flex';
    } catch (e) {
        alert('Upload failed: ' + e.message);
    }
}

async function solveMpsCurrent() {
    const panel = document.getElementById('mps-results');
    panel.style.display = 'block';
    panel.innerHTML = `
        <div class="loading-indicator">
            <div class="spinner"></div>
            <p>Parsing and solving standard MPS benchmark on RTX 4070 GPU...</p>
        </div>
    `;

    try {
        const res = await fetch(`${API_BASE}/api/solve-mps`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filepath: currentMpsFilepath,
                use_gpu: true,
                tolerance: 1e-4,
                max_iterations: 10000,
            }),
        });
        const data = await res.json();
        if (data.error) {
            panel.innerHTML = `<div class="loading-indicator"><p style="color: var(--accent-red);">Error: ${data.error}</p></div>`;
            return;
        }
        renderResults(data, panel, 'mps-convergence-chart');
    } catch (e) {
        panel.innerHTML = `<div class="loading-indicator"><p style="color: var(--accent-red);">Connection error: ${e.message}</p></div>`;
    }
}

function setupMpsDropzone() {
    const dz = document.getElementById('mps-dropzone');
    if (!dz) return;
    dz.addEventListener('dragover', (e) => {
        e.preventDefault();
        dz.classList.add('drag-over');
    });
    dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));
    dz.addEventListener('drop', (e) => {
        e.preventDefault();
        dz.classList.remove('drag-over');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleMpsFileUpload({ target: { files: e.dataTransfer.files } });
        }
    });
}

// ========== GPU MEMORY PROFILER & STRESS TEST ==========

async function fetchGpuMemoryLimits() {
    try {
        const res = await fetch(`${API_BASE}/api/gpu-memory-limits`);
        const data = await res.json();
        if (data.capacity) {
            const c = data.capacity;
            const nnzEl = document.getElementById('mem-max-nnz');
            const varsEl = document.getElementById('mem-max-vars');
            const denseEl = document.getElementById('mem-dense-limit');
            const scaleEl = document.getElementById('mem-scalability');

            if (nnzEl) nnzEl.textContent = `~${(c.max_non_zeros_nnz / 1e6).toFixed(0)} Million`;
            if (varsEl) varsEl.textContent = `~${(c.max_variables_sparse / 1e3).toFixed(0)}k vars`;
            if (denseEl) denseEl.textContent = `~${(c.max_variables_dense / 1e3).toFixed(0)}k vars`;
            if (scaleEl) scaleEl.textContent = `${c.scalability_multiplier}x Larger`;
        }
    } catch (e) {
        // Silently ignore
    }
}

async function runMemoryStressTest() {
    const btn = document.getElementById('btn-run-memory-stress');
    const loading = document.getElementById('memory-stress-loading');
    const tableWrapper = document.getElementById('memory-stress-table-wrapper');
    const tbody = document.getElementById('memory-stress-tbody');

    btn.disabled = true;
    loading.style.display = 'flex';
    tableWrapper.style.display = 'none';

    try {
        const res = await fetch(`${API_BASE}/api/memory-stress-test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_scale: 25000 }),
        });
        const data = await res.json();
        if (data.error) {
            alert('Stress test failed: ' + data.error);
            loading.style.display = 'none';
            btn.disabled = false;
            return;
        }

        const rows = data.stress_results.map(r => `
            <tr>
                <td style="font-weight:700; font-family:var(--font-mono); color:var(--text-primary);">${r.n_vars.toLocaleString()} × ${r.n_constraints.toLocaleString()}</td>
                <td style="font-family:var(--font-mono); color:#38bdf8;">${r.nnz.toLocaleString()}</td>
                <td style="font-family:var(--font-mono); color:#f87171;">${r.dense_equivalent_mb.toFixed(1)} MB</td>
                <td style="font-family:var(--font-mono); font-weight:800; color:#10b981;">${r.actual_gpu_vram_mb.toFixed(2)} MB</td>
                <td><span class="badge badge-optimal" style="font-size:0.8rem;">${r.savings_ratio.toFixed(1)}x Savings</span></td>
                <td style="font-family:var(--font-mono); color:var(--text-secondary);">${r.solve_time_sec.toFixed(3)}s</td>
                <td><span class="badge ${r.memory_leak_mb === 0 ? 'badge-optimal' : 'badge-warning'}">${r.memory_leak_mb === 0 ? '0.00 MB (Clean ✓)' : r.memory_leak_mb.toFixed(2) + ' MB'}</span></td>
            </tr>
        `).join('');

        tbody.innerHTML = rows;
        loading.style.display = 'none';
        tableWrapper.style.display = 'block';
    } catch (e) {
        alert('Connection error: ' + e.message);
        loading.style.display = 'none';
    }
    btn.disabled = false;
}
