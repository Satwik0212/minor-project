import "./styles/main.css";
const app=document.querySelector("#app");
app.innerHTML=`<main class="shell"><p class="eyebrow">SWM-ICS · Smart Waste Management</p><h1>Operations dashboard</h1><p>Frontend scaffold. Connect screens to the versioned REST API as each feature is implemented.</p><section class="status-card"><strong>API status</strong><span id="api-status">Checking…</span></section></main>`;
const status=document.querySelector("#api-status");
fetch(`${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}/health/live`).then(r=>{if(!r.ok)throw Error();return r.json()}).then(d=>status.textContent=d.status).catch(()=>status.textContent="Not connected");
