// =========================================================
//  SWM-ICS — Operational Dashboard
//  Vanilla JS, single-page, three sections:
//    • Dashboard
//    • Smart Bins
//    • Collection Priority & Alerts
//
//  API base: VITE_API_BASE_URL or http://127.0.0.1:8000
//  All endpoints verified against backend source code.
// =========================================================

import "./styles/main.css";

// ─── Config ────────────────────────────────────────────────
const BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const V1   = `${BASE}/api/v1`;

// ─── Utilities & Helpers ────────────────────────────────────
import {
  h,
  relTime,
  fmtDateTime,
  PRIORITY_LABEL,
  PRIORITY_CLASS,
  PRIORITY_ICON,
  SEVERITY_ICON,
  SEVERITY_CLASS,
  ALERT_STATUS_CLASS,
  HEALTH_CLASS,
  BIN_STATUS_CLASS,
  priorityBadge,
  fillBar,
  bigFillBar,
  healthBadge,
  deviceState,
  simBadge,
  binStatusBadge,
} from "./utils/helpers.js";

// ─── API client ─────────────────────────────────────────────

async function api(method, path, body = null) {
  const opts = { method, headers: { Accept: "application/json" } };
  if (body !== null) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  try {
    const res = await fetch(path, opts);
    const ct = res.headers.get("content-type") || "";
    const data = ct.includes("application/json") ? await res.json() : await res.text();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    return { ok: false, status: null, data: null, networkError: err.message };
  }
}

const get    = (path) => api("GET", path);
const post   = (path, body) => api("POST", path, body);
const del    = (path) => api("DELETE", path);

// ─── Toast ──────────────────────────────────────────────────

function toast(msg, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  const icon = { success: "✓", error: "✗", info: "ℹ" }[type] || "ℹ";
  el.innerHTML = `<span>${icon}</span><span>${h(msg)}</span>`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3800);
}

// ─── Connection indicator ────────────────────────────────────

let healthInterval;

async function checkHealth() {
  const dot   = document.getElementById("conn-dot");
  const label = document.getElementById("conn-label");
  if (!dot) return;
  const result = await get(`${BASE}/health/live`);
  if (result.ok) {
    dot.className = "status-dot connected";
    label.textContent = "Backend connected";
  } else {
    dot.className = "status-dot disconnected";
    label.textContent = result.networkError ? "Backend unreachable" : `Backend error (${result.status})`;
  }
}

// ─── Router (hash-based SPA) ─────────────────────────────────

const ROUTES = { dashboard: showDashboard, bins: showBins, priority: showPriority };

function navigate(page) {
  document.querySelectorAll(".nav-item").forEach(el => {
    el.classList.toggle("active", el.dataset.page === page);
  });
  const main = document.getElementById("main-content");
  main.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading…</span></div>`;
  const fn = ROUTES[page];
  if (fn) fn(main); else main.innerHTML = `<div class="error-state"><strong>Page not found</strong></div>`;
}

// ─── App shell ───────────────────────────────────────────────

function buildShell() {
  document.getElementById("app").innerHTML = `
    <!-- Top bar -->
    <header class="topbar">
      <div class="topbar-brand">
        <div class="brand-icon">🗑</div>
        SWM-ICS
      </div>
      <span class="text-sm text-muted" style="font-weight:500">Smart Waste Management &amp; Intelligent Collection System</span>
      <div class="topbar-sep"></div>
      <div class="topbar-status">
        <div class="status-dot" id="conn-dot"></div>
        <span id="conn-label">Checking…</span>
      </div>
      <span class="demo-badge" id="demo-badge" style="display:none">Demo Mode</span>
    </header>

    <!-- Layout -->
    <div class="layout">
      <!-- Sidebar -->
      <nav class="sidebar">
        <div class="sidebar-group">
          <div class="sidebar-group-label">Navigation</div>
        </div>
        <button class="nav-item active" data-page="dashboard">
          <span class="nav-icon">📊</span> Dashboard
        </button>
        <button class="nav-item" data-page="bins">
          <span class="nav-icon">🗑</span> Smart Bins
        </button>
        <button class="nav-item" data-page="priority">
          <span class="nav-icon">🚛</span> Collection Priority &amp; Alerts
        </button>
        <div class="sidebar-footer">
          <div class="text-xs text-muted" style="margin-bottom:6px">Demo data</div>
          <button class="btn btn-primary btn-sm" id="sidebar-seed-btn" style="width:100%">Load Demo Data</button>
        </div>
      </nav>

      <!-- Content -->
      <main class="main" id="main-content">
        <div class="loading-state"><div class="spinner"></div><span>Loading…</span></div>
      </main>
    </div>

    <!-- Modals / Drawers (rendered into these placeholders) -->
    <div id="drawer-root"></div>
    <div id="modal-root"></div>

    <!-- Toasts -->
    <div class="toast-container" id="toast-container"></div>`;

  // Nav clicks
  document.querySelectorAll(".nav-item[data-page]").forEach(btn => {
    btn.addEventListener("click", () => navigate(btn.dataset.page));
  });

  // Sidebar seed
  document.getElementById("sidebar-seed-btn").addEventListener("click", seedDemoData);

  // Start health polling
  checkHealth();
  healthInterval = setInterval(checkHealth, 8000);
}

// ─── Demo status check ───────────────────────────────────────

async function checkDemoStatus() {
  const result = await get(`${V1}/demo/status`);
  const badge = document.getElementById("demo-badge");
  if (result.ok && result.data?.seeded) {
    if (badge) badge.style.display = "";
    return true;
  }
  if (badge) badge.style.display = "none";
  return false;
}

async function seedDemoData() {
  const btn = document.getElementById("sidebar-seed-btn");
  if (btn) { btn.disabled = true; btn.textContent = "Seeding…"; }
  const result = await post(`${V1}/demo/seed`, null);
  if (btn) { btn.disabled = false; btn.textContent = "Load Demo Data"; }
  if (result.ok) {
    toast(`Demo seeded: ${result.data.message}`, "success");
    await checkDemoStatus();
    // Refresh whichever page is active
    const active = document.querySelector(".nav-item.active");
    if (active) navigate(active.dataset.page);
  } else if (result.status === 409) {
    toast("Demo data already seeded.", "info");
  } else {
    toast(`Seed failed: ${result.data?.detail || result.status || result.networkError}`, "error");
  }
}

// ─────────────────────────────────────────────────────────────
//  SECTION A — DASHBOARD
// ─────────────────────────────────────────────────────────────

async function showDashboard(container) {
  // Fetch summary + alerts in parallel
  const [summaryRes, alertsRes, priorityRes] = await Promise.all([
    get(`${V1}/bins/summary`),
    get(`${V1}/alerts?status=OPEN&page_size=5`),
    get(`${V1}/collection/priority`),
  ]);

  await checkDemoStatus();

  // Handle complete backend failure
  if (summaryRes.networkError) {
    container.innerHTML = renderNetworkError(summaryRes.networkError);
    return;
  }

  const summary  = summaryRes.ok  ? summaryRes.data  : null;
  const alerts   = alertsRes.ok   ? alertsRes.data   : null;
  const priority = priorityRes.ok ? priorityRes.data : null;

  const noData = !summary || summary.total === 0;

  container.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title">Dashboard</div>
        <div class="page-sub">Operational overview — all values from live backend</div>
      </div>
      <button class="btn btn-secondary btn-sm" id="dash-refresh">↻ Refresh</button>
    </div>

    ${noData ? renderEmptyDashboard() : `
    <!-- KPI Row -->
    <div class="kpi-row" id="kpi-row">
      ${renderKpiTiles(summary)}
    </div>

    <!-- Two-column grid: priority bins + recent alerts -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--s2)">
      <!-- Highest priority bins -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">🚨 Needs Attention</span>
          <button class="btn btn-secondary btn-sm" data-page="priority">View All →</button>
        </div>
        <div id="dash-priority-list">
          ${priority ? renderDashPriorityList(priority.items?.slice(0, 5) || []) : renderLoadError("Could not load priority data.")}
        </div>
      </div>

      <!-- Recent OPEN alerts -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">🔔 Recent Alerts</span>
          <button class="btn btn-secondary btn-sm" data-page="priority">View All →</button>
        </div>
        <div id="dash-alerts-list">
          ${alerts ? renderDashAlertsList(alerts.items || []) : renderLoadError("Could not load alerts.")}
        </div>
      </div>
    </div>

    <!-- Quick action -->
    <div style="text-align:right">
      <button class="btn btn-primary" data-page="bins">Open Smart Bins →</button>
    </div>`}`;

  // Events
  container.querySelectorAll("[data-page]").forEach(btn => {
    btn.addEventListener("click", () => navigate(btn.dataset.page));
  });
  container.querySelector("#dash-refresh")?.addEventListener("click", () => showDashboard(container));

  if (noData) {
    container.querySelector("#seed-btn")?.addEventListener("click", async () => {
      await seedDemoData();
      showDashboard(container);
    });
  }
}

function renderEmptyDashboard() {
  return `
    <div class="empty-state" style="padding:var(--s6) var(--s3)">
      <div style="font-size:48px">🗑</div>
      <h3>No bins registered yet</h3>
      <p>The database has no bin data. Load the demo dataset to see the dashboard in action.</p>
      <button class="btn btn-primary" id="seed-btn">Load Demo Data</button>
    </div>`;
}

function renderKpiTiles(s) {
  const bp = s.by_priority || {};
  const critical = bp.CRITICAL ?? 0;
  const high = bp.HIGH ?? 0;
  const needsCollection = critical + high;
  const tiles = [
    { label: "Total Bins",           value: s.total,         cls: "teal"   },
    { label: "Active",               value: s.active_count,  cls: "green"  },
    { label: "Needs Collection",     value: needsCollection, cls: needsCollection > 0 ? "orange" : "green" },
    { label: "Critical",             value: critical,         cls: critical > 0 ? "red" : "green" },
    { label: "High Priority",        value: high,             cls: high > 0 ? "orange" : "green" },
    { label: "Demo / Simulated",     value: s.simulated_count ?? "—", cls: "teal" },
  ];
  return tiles.map(t => `
    <div class="kpi-tile">
      <div class="kpi-label">${h(t.label)}</div>
      <div class="kpi-value ${t.cls}">${t.value}</div>
    </div>`).join("");
}

function renderDashPriorityList(items) {
  if (!items.length) return `<div class="empty-state" style="padding:var(--s4) var(--s2)"><p>No bins require collection.</p></div>`;
  return items.map((b, i) => `
    <div class="queue-row">
      <span class="queue-rank">${i + 1}</span>
      <div style="flex:1;min-width:0">
        <div style="display:flex;align-items:center;gap:6px">
          ${priorityBadge(b.priority)}
          <span class="font-mono text-sm">${h(b.bin_id)}</span>
        </div>
        <div class="text-xs text-muted" style="margin-top:2px">${h(b.name)} · ${h(b.area_name || "—")}</div>
      </div>
      <div>${fillBar(b.fill_percent)}</div>
    </div>`).join("");
}

function renderDashAlertsList(items) {
  if (!items.length) return `<div class="empty-state" style="padding:var(--s4) var(--s2)"><p>No open alerts.</p></div>`;
  return items.map(a => `
    <div class="alert-item">
      <span class="alert-icon">${SEVERITY_ICON[a.severity] || "⚪"}</span>
      <div class="alert-body">
        <div class="alert-title">${h(a.type?.replace(/_/g," "))}</div>
        <div class="alert-meta">
          <span class="badge badge-${SEVERITY_CLASS[a.severity] || "info"}">${h(a.severity)}</span>
          ${a.bin_label ? `<span class="font-mono text-xs">${h(a.bin_label)}</span>` : ""}
          <span class="text-muted">${relTime(a.opened_at) ?? fmtDateTime(a.opened_at)}</span>
        </div>
        <div class="alert-msg">${h(a.message)}</div>
      </div>
    </div>`).join("");
}

function renderLoadError(msg) {
  return `<div class="error-state" style="margin:var(--s1)"><strong>Error</strong><p>${h(msg)}</p></div>`;
}

function renderNetworkError(msg) {
  return `
    <div class="error-state">
      <strong>Cannot reach backend</strong>
      <p>${h(msg)}</p>
      <p>Make sure the backend is running:<br><code>python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000</code></p>
      <button class="btn btn-secondary btn-sm" onclick="location.reload()">Retry</button>
    </div>`;
}

// ─────────────────────────────────────────────────────────────
//  SECTION B — SMART BINS
// ─────────────────────────────────────────────────────────────

let binsPage = 1;
let binsFilters = { priority: "", status: "" };

async function showBins(container) {
  // Reset page on first load of this section
  binsPage = 1;
  container.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title">Smart Bins</div>
        <div class="page-sub">All registered bins with latest sensor state</div>
      </div>
      <div class="btn-group">
        <button class="btn btn-secondary btn-sm" id="bins-refresh">↻ Refresh</button>
        <button class="btn btn-primary btn-sm" id="simulate-btn">⚡ Simulate Reading</button>
      </div>
    </div>

    <!-- Filters -->
    <div class="card">
      <div class="filters">
        <span class="filter-label">Filter:</span>
        <select class="form-select" id="filter-priority" style="width:140px">
          <option value="">All priorities</option>
          <option>CRITICAL</option><option>HIGH</option>
          <option>MEDIUM</option><option>NORMAL</option><option>UNKNOWN</option>
        </select>
        <select class="form-select" id="filter-status" style="width:140px">
          <option value="">All statuses</option>
          <option>ACTIVE</option><option>INACTIVE</option>
          <option>MAINTENANCE</option><option>DRAFT</option><option>RETIRED</option>
        </select>
        <button class="btn btn-secondary btn-sm" id="filter-apply">Apply</button>
        <button class="btn btn-secondary btn-sm" id="filter-clear">Clear</button>
      </div>
      <div id="bins-table-area">
        <div class="loading-state" style="padding:var(--s5)"><div class="spinner"></div><span>Loading bins…</span></div>
      </div>
    </div>

    <!-- Drawer placeholder -->
    <div class="drawer-overlay hidden" id="bin-drawer-overlay">
      <div class="drawer" id="bin-drawer">
        <div class="drawer-header">
          <span class="modal-title" id="drawer-title">Bin Detail</span>
          <button class="modal-close" id="drawer-close">✕</button>
        </div>
        <div class="drawer-body" id="drawer-body">
          <div class="loading-state"><div class="spinner"></div></div>
        </div>
      </div>
    </div>

    <!-- Simulate reading modal -->
    <div class="overlay hidden" id="sim-modal-overlay">
      <div class="modal" id="sim-modal">
        <div class="modal-header">
          <span class="modal-title">Simulate Sensor Reading</span>
          <button class="modal-close" id="sim-close">✕</button>
        </div>
        <div class="modal-body">
          <p class="text-sm text-muted mb-2">
            Submits a real API request to inject a simulated sensor reading for a demo bin.
            The backend calculates fill % and priority — this frontend does not override those values.
          </p>
          <div id="sim-form">
            <div class="form-group mb-2">
              <label class="form-label">Demo Bin <span class="unit">required</span></label>
              <select class="form-select" id="sim-bin-select" style="width:100%">
                <option value="">Loading demo bins…</option>
              </select>
              <span class="field-error" id="sim-bin-err" style="display:none"></span>
            </div>
            <div class="form-group mb-2">
              <label class="form-label">Distance <span class="unit">cm · 1–400 · omit to simulate sensor fault</span></label>
              <input type="number" class="form-input" id="sim-distance" placeholder="e.g. 8" min="1" max="400" step="0.1" style="width:100%" />
              <div class="form-hint">
                Calibration: empty=100cm full=5cm. Examples: 100→0% · 55→47% · 33→70% · 12→93% · 6→99%
              </div>
              <span class="field-error" id="sim-dist-err" style="display:none"></span>
            </div>
            <div id="sim-result" style="display:none;margin-top:var(--s1)"></div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="sim-cancel">Cancel</button>
          <button class="btn btn-primary" id="sim-submit">Submit Reading</button>
        </div>
      </div>
    </div>`;

  // Wire events
  container.querySelector("#bins-refresh").addEventListener("click",  () => loadBinsTable());
  container.querySelector("#filter-apply").addEventListener("click",  () => {
    binsFilters.priority = document.getElementById("filter-priority").value;
    binsFilters.status   = document.getElementById("filter-status").value;
    binsPage = 1; loadBinsTable();
  });
  container.querySelector("#filter-clear").addEventListener("click",  () => {
    document.getElementById("filter-priority").value = "";
    document.getElementById("filter-status").value   = "";
    binsFilters = { priority:"", status:"" };
    binsPage = 1; loadBinsTable();
  });

  // Drawer close
  container.querySelector("#drawer-close").addEventListener("click", closeDrawer);
  container.querySelector("#bin-drawer-overlay").addEventListener("click", e => {
    if (e.target === e.currentTarget) closeDrawer();
  });

  // Simulate modal
  container.querySelector("#simulate-btn").addEventListener("click", openSimModal);
  container.querySelector("#sim-close").addEventListener("click",  closeSimModal);
  container.querySelector("#sim-cancel").addEventListener("click", closeSimModal);
  container.querySelector("#sim-submit").addEventListener("click", submitSimReading);

  await loadBinsTable();
}

function closeDrawer() {
  document.getElementById("bin-drawer-overlay")?.classList.add("hidden");
}

async function loadBinsTable() {
  const area = document.getElementById("bins-table-area");
  if (!area) return;
  area.innerHTML = `<div class="loading-state" style="padding:var(--s5)"><div class="spinner"></div><span>Loading…</span></div>`;

  let url = `${V1}/bins?page=${binsPage}&page_size=20`;
  if (binsFilters.priority) url += `&priority=${binsFilters.priority}`;
  if (binsFilters.status)   url += `&status=${binsFilters.status}`;

  const result = await get(url);

  if (result.networkError) {
    area.innerHTML = renderNetworkError(result.networkError);
    return;
  }
  if (!result.ok) {
    area.innerHTML = `<div class="error-state" style="margin:var(--s2)">
      <strong>Failed to load bins (${result.status})</strong>
      <p>${h(result.data?.detail || "Unexpected error")}</p>
      <button class="btn btn-secondary btn-sm" onclick="loadBinsTable()">Retry</button>
    </div>`;
    return;
  }

  const { items, total, page, page_size } = result.data;
  if (!items || items.length === 0) {
    area.innerHTML = `
      <div class="empty-state" style="padding:var(--s5)">
        <div style="font-size:40px">🗑</div>
        <h3>No bins found</h3>
        <p>${binsFilters.priority || binsFilters.status ? "No bins match the current filters. Try clearing them." : "No bins are registered. Load demo data to get started."}</p>
        ${!binsFilters.priority && !binsFilters.status ? `<button class="btn btn-primary" id="empty-seed-btn">Load Demo Data</button>` : ""}
      </div>`;
    area.querySelector("#empty-seed-btn")?.addEventListener("click", async () => { await seedDemoData(); loadBinsTable(); });
    return;
  }

  const totalPages = Math.ceil(total / page_size);
  area.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Bin ID</th>
            <th>Name &amp; Area</th>
            <th>Fill Level</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Sensor</th>
            <th>Last Reading</th>
            <th></th>
          </tr>
        </thead>
        <tbody id="bins-tbody">
          ${items.map(b => renderBinRow(b)).join("")}
        </tbody>
      </table>
    </div>
    <div class="pagination">
      <button class="btn btn-secondary btn-sm" id="pg-prev" ${page <= 1 ? "disabled" : ""}>‹ Prev</button>
      <span>Page ${page} of ${totalPages} &nbsp;·&nbsp; ${total} bins total</span>
      <span class="sep"></span>
      <button class="btn btn-secondary btn-sm" id="pg-next" ${page >= totalPages ? "disabled" : ""}>Next ›</button>
    </div>`;

  // Row click: open detail drawer
  area.querySelectorAll("[data-bin-detail]").forEach(btn => {
    btn.addEventListener("click", () => openBinDetail(btn.dataset.binDetail));
  });

  area.querySelector("#pg-prev")?.addEventListener("click", () => { binsPage--; loadBinsTable(); });
  area.querySelector("#pg-next")?.addEventListener("click", () => { binsPage++; loadBinsTable(); });
}

function renderBinRow(b) {
  const ls = b.latest_state;
  const stale = ls?.is_stale;
  const lastRead = ls?.latest_event_at;
  const relativeTime = relTime(lastRead);

  return `<tr>
    <td>
      <span class="font-mono">${h(b.bin_id)}</span>
      ${simBadge(b.is_simulated)}
    </td>
    <td>
      <div style="font-weight:500">${h(b.name)}</div>
      <div class="text-xs text-muted">${h(b.area?.name || "—")}</div>
    </td>
    <td>${fillBar(ls?.fill_percent ?? null)}</td>
    <td>${priorityBadge(ls?.priority)}</td>
    <td>${binStatusBadge(b.status)}</td>
    <td>${healthBadge(ls?.sensor_health)}</td>
    <td class="text-sm">
      ${lastRead
        ? `${h(relativeTime ?? fmtDateTime(lastRead))}${stale ? ' <span class="stale-warn" title="Reading may be outdated">⚠</span>' : ''}`
        : '<span class="null-fill">No reading yet</span>'}
    </td>
    <td>
      <button class="btn btn-secondary btn-sm" data-bin-detail="${h(b.bin_id)}">View Details</button>
    </td>
  </tr>`;
}

async function openBinDetail(binId) {
  const overlay = document.getElementById("bin-drawer-overlay");
  const body    = document.getElementById("drawer-body");
  const title   = document.getElementById("drawer-title");
  if (!overlay) return;
  overlay.classList.remove("hidden");
  title.textContent = `Bin: ${binId}`;
  body.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading…</span></div>`;

  const result = await get(`${V1}/bins/${binId}`);
  if (!result.ok) {
    body.innerHTML = `<div class="error-state">
      <strong>Failed to load bin (${result.status})</strong>
      <p>${h(result.data?.detail || result.networkError || "Error")}</p>
    </div>`;
    return;
  }

  const b  = result.data;
  const ls = b.latest_state;
  const readings = b.recent_readings || [];

  body.innerHTML = `
    <!-- Identification -->
    <div class="detail-section">
      <div class="detail-section-title">Identification</div>
      <div class="detail-grid">
        <div class="detail-pair"><div class="detail-key">Bin ID</div><div class="detail-val mono">${h(b.bin_id)} ${simBadge(b.is_simulated)}</div></div>
        <div class="detail-pair"><div class="detail-key">Name</div><div class="detail-val">${h(b.name)}</div></div>
        <div class="detail-pair"><div class="detail-key">Type</div><div class="detail-val">${h(b.bin_type)}</div></div>
        <div class="detail-pair"><div class="detail-key">Status</div><div class="detail-val">${binStatusBadge(b.status)}</div></div>
        <div class="detail-pair"><div class="detail-key">Area</div><div class="detail-val">${h(b.area?.name || "—")}</div></div>
        <div class="detail-pair"><div class="detail-key">Capacity</div><div class="detail-val">${b.capacity_kg} kg</div></div>
        <div class="detail-pair"><div class="detail-key">Warning threshold</div><div class="detail-val">${b.warning_threshold_pct}%</div></div>
        <div class="detail-pair"><div class="detail-key">Critical threshold</div><div class="detail-val">${b.critical_threshold_pct}%</div></div>
      </div>
    </div>

    <!-- Current State -->
    <div class="detail-section">
      <div class="detail-section-title">Current State</div>
      ${ls ? `
        <div style="margin-bottom:var(--s1)">
          <div class="detail-key">Fill Level</div>
          ${bigFillBar(ls.fill_percent)}
        </div>
        <div class="detail-grid">
          <div class="detail-pair"><div class="detail-key">Priority</div><div class="detail-val">${priorityBadge(ls.priority)}</div></div>
          <div class="detail-pair"><div class="detail-key">Sensor Health</div><div class="detail-val">${healthBadge(ls.sensor_health)}</div></div>
          <div class="detail-pair"><div class="detail-key">Device State</div><div class="detail-val" style="display:flex;align-items:center;gap:6px">${deviceState(ls.device_reported_state)}</div></div>
          <div class="detail-pair"><div class="detail-key">Stale Reading</div><div class="detail-val">${ls.is_stale ? '<span class="stale-warn">⚠ Yes — may be outdated</span>' : "No"}</div></div>
          <div class="detail-pair"><div class="detail-key">Weight</div><div class="detail-val">${ls.weight_kg != null ? `${ls.weight_kg} kg` : "—"}</div></div>
          <div class="detail-pair"><div class="detail-key">Last Reading</div><div class="detail-val text-sm">${fmtDateTime(ls.latest_event_at)}</div></div>
        </div>` :
        `<div class="empty-state" style="padding:var(--s2)"><p>No sensor state recorded yet.</p></div>`}
    </div>

    <!-- Simulated data note -->
    ${b.is_simulated ? `
    <div style="background:var(--amber-bg);border:1px solid var(--amber-border);border-radius:var(--r-md);padding:10px 12px;margin-bottom:var(--s2)">
      <div style="font-weight:600;color:var(--amber);font-size:12.5px">⚠ Simulated Data</div>
      <div class="text-xs text-muted">Readings for this bin were generated by the demo seeder, not physical hardware.</div>
    </div>` : ""}

    <!-- Recent readings -->
    <div class="detail-section">
      <div class="detail-section-title">Recent Readings (last ${readings.length})</div>
      ${readings.length === 0
        ? `<div class="empty-state" style="padding:var(--s2)"><p>No readings recorded.</p></div>`
        : `
        ${renderMiniChart(readings)}
        <div class="table-wrap" style="margin-top:var(--s1)">
          <table>
            <thead><tr><th>Time</th><th>Fill %</th><th>Distance</th><th>Weight</th><th>Temp</th><th>Battery</th><th>Sensor</th></tr></thead>
            <tbody>
              ${readings.slice(0, 20).map(r => `
                <tr>
                  <td class="text-xs">${h(relTime(r.timestamp) ?? fmtDateTime(r.timestamp))}</td>
                  <td>${r.fill_percent != null ? `<span style="font-weight:600">${r.fill_percent.toFixed(1)}%</span>` : `<span class="null-fill">—</span>`}</td>
                  <td class="text-sm">${r.distance_cm != null ? `${r.distance_cm} cm` : "—"}</td>
                  <td class="text-sm">${r.weight_kg != null ? `${r.weight_kg} kg` : "—"}</td>
                  <td class="text-sm">${r.temperature_c != null ? `${r.temperature_c}°C` : "—"}</td>
                  <td class="text-sm">${r.battery_percent != null ? `${r.battery_percent}%` : "—"}</td>
                  <td>${healthBadge(r.sensor_health)}</td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>`}
    </div>

    <!-- Simulate reading shortcut -->
    ${b.is_simulated ? `
    <div style="padding-top:var(--s2);border-top:1px solid var(--border)">
      <button class="btn btn-primary" id="drawer-simulate-btn" data-bin="${h(b.bin_id)}">
        ⚡ Simulate Reading for this bin
      </button>
    </div>` : ""}`;

  body.querySelector("#drawer-simulate-btn")?.addEventListener("click", (e) => {
    closeDrawer();
    openSimModal(null, e.currentTarget.dataset.bin);
  });
}

function renderMiniChart(readings) {
  const reversed = [...readings].reverse(); // oldest first
  if (!reversed.length) return "";
  return `
    <div class="reading-chart">
      ${reversed.map(r => {
        const pct = r.fill_percent;
        const h_px = pct != null ? Math.max(4, (pct / 100) * 48) : 4;
        let col = "#E5E7EB";
        if (pct != null) {
          if (pct > 95) col = "#B42318";
          else if (pct > 85) col = "#C2410C";
          else if (pct >= 70) col = "#8F5F10";
          else col = "#16A34A";
        }
        const tip = pct != null ? `${pct.toFixed(1)}%` : "No reading";
        return `<div class="reading-bar-mini" style="height:${h_px}px;background:${col}" title="${tip}"></div>`;
      }).join("")}
    </div>
    <div class="text-xs text-muted" style="margin-top:2px">↑ Fill % over last ${reversed.length} readings (oldest→newest)</div>`;
}

// ─── Simulate Reading Modal ──────────────────────────────────

async function openSimModal(event, preselectedBinId = null) {
  const overlay = document.getElementById("sim-modal-overlay");
  if (!overlay) return;
  overlay.classList.remove("hidden");

  // Reset form
  document.getElementById("sim-result").style.display = "none";
  document.getElementById("sim-distance").value = "";
  document.getElementById("sim-bin-err").style.display = "none";
  document.getElementById("sim-dist-err").style.display = "none";

  // Populate bin selector from backend
  const select = document.getElementById("sim-bin-select");
  select.innerHTML = `<option value="">Loading…</option>`;

  const result = await get(`${V1}/demo/status`);
  let demoBins = [];
  if (result.ok && result.data?.bins?.length) {
    demoBins = result.data.bins.map(b => b.bin_id).filter(id => id?.startsWith("BIN-DEMO-"));
  }

  if (!demoBins.length) {
    // Fallback: fetch from bins list filtered to demo
    const binsRes = await get(`${V1}/bins?page_size=50`);
    if (binsRes.ok) {
      demoBins = (binsRes.data.items || [])
        .filter(b => b.is_simulated)
        .map(b => b.bin_id);
    }
  }

  if (!demoBins.length) {
    select.innerHTML = `<option value="">No demo bins found — seed demo data first</option>`;
  } else {
    select.innerHTML = demoBins.map(id =>
      `<option value="${h(id)}" ${id === preselectedBinId ? "selected" : ""}>${h(id)}</option>`
    ).join("");
  }
}

function closeSimModal() {
  document.getElementById("sim-modal-overlay")?.classList.add("hidden");
}

async function submitSimReading() {
  const binId    = document.getElementById("sim-bin-select").value;
  const distRaw  = document.getElementById("sim-distance").value.trim();
  const btnEl    = document.getElementById("sim-submit");
  const resultEl = document.getElementById("sim-result");
  const binErrEl = document.getElementById("sim-bin-err");
  const distErrEl= document.getElementById("sim-dist-err");

  // Reset errors
  binErrEl.style.display  = "none";
  distErrEl.style.display = "none";
  resultEl.style.display  = "none";

  // Validate
  let valid = true;
  if (!binId) {
    binErrEl.textContent = "Select a demo bin.";
    binErrEl.style.display = "";
    valid = false;
  }
  if (distRaw !== "") {
    const v = parseFloat(distRaw);
    if (isNaN(v) || v < 1 || v > 400) {
      distErrEl.textContent = "Distance must be between 1 and 400 cm.";
      distErrEl.style.display = "";
      valid = false;
    }
  }
  if (!valid) return;

  // Build payload — only send fields with actual values
  const payload = { bin_id: binId };
  if (distRaw !== "") payload.distance_cm = parseFloat(distRaw);

  btnEl.disabled = true;
  btnEl.textContent = "Submitting…";

  const r = await post(`${V1}/demo/reading`, payload);

  btnEl.disabled = false;
  btnEl.textContent = "Submit Reading";
  resultEl.style.display = "";

  if (r.ok && r.data) {
    const d = r.data;
    const fillText = d.fill_percent != null ? `${d.fill_percent.toFixed(1)}%` : "Unavailable (sensor fault)";
    resultEl.innerHTML = `
      <div style="background:var(--green-bg);border:1px solid var(--green-border);border-radius:var(--r-md);padding:12px var(--s2)">
        <div style="font-weight:600;color:var(--green);margin-bottom:4px">✓ Reading accepted</div>
        <div class="text-sm"><strong>Fill level:</strong> ${h(fillText)}</div>
        <div class="text-sm"><strong>Priority:</strong> ${priorityBadge(d.priority)}</div>
        <div class="text-sm"><strong>Sensor health:</strong> ${healthBadge(d.sensor_health)}</div>
        <div class="text-xs text-muted" style="margin-top:4px">${h(d.message)}</div>
      </div>`;
    toast(`Reading submitted — ${binId} is now ${d.priority}`, "success");

    // Refresh bins table and dashboard data silently
    setTimeout(() => { loadBinsTable(); }, 300);
  } else {
    // Show real backend error — never fake a success
    const detail = r.data?.detail;
    let errorMsg = `HTTP ${r.status}`;
    if (typeof detail === "string") {
      errorMsg = detail;
    } else if (Array.isArray(detail)) {
      // Pydantic validation errors: [{loc, msg, type}, …]
      errorMsg = detail.map(e => `${e.loc?.slice(-1)[0] ?? "field"}: ${e.msg}`).join("; ");
    } else if (r.networkError) {
      errorMsg = r.networkError;
    }
    resultEl.innerHTML = `
      <div style="background:var(--red-bg);border:1px solid var(--red-border);border-radius:var(--r-md);padding:12px var(--s2)">
        <div style="font-weight:600;color:var(--red);margin-bottom:4px">✗ Submission failed</div>
        <div class="text-sm">${h(errorMsg)}</div>
      </div>`;
    toast(`Failed: ${errorMsg}`, "error");
  }
}

// ─────────────────────────────────────────────────────────────
//  SECTION C — COLLECTION PRIORITY & ALERTS
// ─────────────────────────────────────────────────────────────

async function showPriority(container) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <div class="page-title">Collection Priority &amp; Alerts</div>
        <div class="page-sub">Bins sorted by urgency · Open alerts with action controls</div>
      </div>
      <button class="btn btn-secondary btn-sm" id="prio-refresh">↻ Refresh All</button>
    </div>

    <!-- Two-column layout -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--s2)">
      <!-- Priority queue -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">🚛 Collection Queue</span>
          <select class="form-select" id="prio-filter" style="width:130px">
            <option value="">All priorities</option>
            <option>CRITICAL</option><option>HIGH</option>
            <option>MEDIUM</option><option>NORMAL</option>
          </select>
        </div>
        <div id="priority-list">
          <div class="loading-state" style="padding:var(--s5)"><div class="spinner"></div></div>
        </div>
      </div>

      <!-- Alerts -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">🔔 Alerts</span>
          <select class="form-select" id="alert-status-filter" style="width:130px">
            <option value="OPEN">Open only</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="ALL">All statuses</option>
          </select>
        </div>
        <div id="alerts-list">
          <div class="loading-state" style="padding:var(--s5)"><div class="spinner"></div></div>
        </div>
      </div>
    </div>`;

  // Wire events
  container.querySelector("#prio-refresh").addEventListener("click", () => {
    loadPriorityList();
    loadAlertsList();
  });
  container.querySelector("#prio-filter").addEventListener("change", loadPriorityList);
  container.querySelector("#alert-status-filter").addEventListener("change", loadAlertsList);

  await Promise.all([loadPriorityList(), loadAlertsList()]);
}

async function loadPriorityList() {
  const el = document.getElementById("priority-list");
  if (!el) return;
  el.innerHTML = `<div class="loading-state" style="padding:var(--s4)"><div class="spinner"></div></div>`;

  const filter = document.getElementById("prio-filter")?.value;
  let url = `${V1}/collection/priority`;
  if (filter) url += `?priority=${filter}`;

  const result = await get(url);

  if (result.networkError) { el.innerHTML = `<div class="error-state" style="margin:var(--s1)"><strong>Network error</strong><p>${h(result.networkError)}</p></div>`; return; }
  if (!result.ok) { el.innerHTML = `<div class="error-state" style="margin:var(--s1)"><strong>Error ${result.status}</strong><p>${h(result.data?.detail || "")}</p></div>`; return; }

  // Response: { items: PriorityBinItem[], total: int }
  const items = result.data?.items || [];

  if (!items.length) {
    el.innerHTML = `<div class="empty-state" style="padding:var(--s4)"><p>No bins in collection queue${filter ? ` with priority ${filter}` : ""}.</p></div>`;
    return;
  }

  el.innerHTML = items.map((b, i) => `
    <div class="queue-row">
      <span class="queue-rank">${i + 1}</span>
      <div style="flex:1;min-width:0">
        <div class="flex items-center gap-1" style="flex-wrap:wrap">
          ${priorityBadge(b.priority)}
          <span class="font-mono text-sm">${h(b.bin_id)}</span>
          ${b.open_alert_count > 0 ? `<span class="badge badge-critical">${b.open_alert_count} alert${b.open_alert_count > 1?"s":""}</span>` : ""}
        </div>
        <div class="text-xs text-muted" style="margin-top:2px">
          ${h(b.name)} · ${h(b.area_name || "—")}
          · ${healthBadge(b.sensor_health)}
          ${b.is_stale ? '<span class="stale-warn">⚠ stale</span>' : ""}
        </div>
        <div class="text-xs text-muted" style="margin-top:2px">
          Last: ${relTime(b.latest_event_at) ?? fmtDateTime(b.latest_event_at) ?? "No reading"}
        </div>
      </div>
      <div style="min-width:130px">${fillBar(b.fill_percent)}</div>
    </div>`).join("");
}

async function loadAlertsList() {
  const el = document.getElementById("alerts-list");
  if (!el) return;
  el.innerHTML = `<div class="loading-state" style="padding:var(--s4)"><div class="spinner"></div></div>`;

  const statusFilter = document.getElementById("alert-status-filter")?.value || "OPEN";
  const result = await get(`${V1}/alerts?status=${statusFilter}&page_size=50`);

  if (result.networkError) { el.innerHTML = `<div class="error-state" style="margin:var(--s1)"><strong>Network error</strong><p>${h(result.networkError)}</p></div>`; return; }
  if (!result.ok) { el.innerHTML = `<div class="error-state" style="margin:var(--s1)"><strong>Error ${result.status}</strong><p>${h(result.data?.detail || "")}</p></div>`; return; }

  const items = result.data?.items || [];
  if (!items.length) {
    el.innerHTML = `<div class="empty-state" style="padding:var(--s4)"><p>No ${statusFilter === "ALL" ? "" : statusFilter.toLowerCase() + " "}alerts.</p></div>`;
    return;
  }

  el.innerHTML = items.map(a => renderAlertItem(a)).join("");

  // Bind action buttons
  el.querySelectorAll("[data-ack]").forEach(btn => {
    btn.addEventListener("click", () => handleAlertAction("acknowledge", btn.dataset.ack));
  });
  el.querySelectorAll("[data-resolve]").forEach(btn => {
    btn.addEventListener("click", () => handleAlertAction("resolve", btn.dataset.resolve));
  });
}

function renderAlertItem(a) {
  const icon = SEVERITY_ICON[a.severity] || "⚪";
  const sevCls = SEVERITY_CLASS[a.severity] || "info";
  const statCls = ALERT_STATUS_CLASS[a.status] || "open";
  const timeStr = relTime(a.opened_at) ?? fmtDateTime(a.opened_at);

  // Action buttons depend on current status
  let actions = "";
  if (a.status === "OPEN") {
    actions = `
      <button class="btn btn-secondary btn-sm" data-ack="${h(a.alert_id)}" title="Acknowledge">Acknowledge</button>
      <button class="btn btn-danger btn-sm"    data-resolve="${h(a.alert_id)}" title="Resolve">Resolve</button>`;
  } else if (a.status === "ACKNOWLEDGED") {
    actions = `<button class="btn btn-secondary btn-sm" data-resolve="${h(a.alert_id)}" title="Resolve">Resolve</button>`;
  }

  return `
    <div class="alert-item" id="alert-${h(a.alert_id)}">
      <span class="alert-icon">${icon}</span>
      <div class="alert-body">
        <div class="alert-title">${h(a.type?.replace(/_/g," "))}</div>
        <div class="alert-meta">
          <span class="badge badge-${sevCls}">${h(a.severity)}</span>
          <span class="badge badge-${statCls}">${h(a.status)}</span>
          ${a.bin_label ? `<span class="font-mono text-xs">${h(a.bin_label)}</span>` : ""}
          <span>${h(timeStr)}</span>
        </div>
        <div class="alert-msg">${h(a.message)}</div>
      </div>
      ${actions ? `<div class="alert-actions">${actions}</div>` : ""}
    </div>`;
}

async function handleAlertAction(action, alertId) {
  const url = `${V1}/alerts/${alertId}/${action}`;
  const result = await post(url, null);

  if (result.ok) {
    const newStatus = action === "acknowledge" ? "ACKNOWLEDGED" : "RESOLVED";
    toast(`Alert ${alertId}: ${newStatus}`, "success");
    // Reload alerts from server — never assume optimistic state
    await loadAlertsList();
    // Also refresh priority list (alert count changes)
    loadPriorityList();
  } else if (result.status === 409) {
    toast(`Cannot ${action}: ${result.data?.detail || "already in that state"}`, "info");
    await loadAlertsList(); // refresh to show actual state
  } else if (result.status === 404) {
    toast(`Alert not found: ${alertId}`, "error");
  } else {
    toast(`Failed to ${action} alert: ${result.data?.detail || result.status || result.networkError}`, "error");
  }
}

// ─── Boot ────────────────────────────────────────────────────

async function init() {
  buildShell();
  await checkDemoStatus();
  navigate("dashboard");
}

init();
