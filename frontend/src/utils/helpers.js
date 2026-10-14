/**
 * SWM-ICS Operational Dashboard Utility Helpers
 * Pure functions for string escaping, time formatting, priority/badge markup, and fill styling.
 */

/** Safely HTML-escape a value. */
export function h(v) {
  if (v == null) return "";
  return String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** Format ISO timestamp as relative time. Never throws. */
export function relTime(iso, now = Date.now()) {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  const s = Math.floor((now - d.getTime()) / 1000);
  if (s < 0)    return "just now";
  if (s < 60)   return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400)return `${Math.floor(s / 3600)}h ago`;
  return d.toLocaleDateString();
}

/** Format ISO timestamp for display. */
export function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

export const PRIORITY_LABEL = { CRITICAL: "Critical", HIGH: "High", MEDIUM: "Medium", NORMAL: "Normal", UNKNOWN: "Unknown" };
export const PRIORITY_CLASS = { CRITICAL: "critical", HIGH: "high", MEDIUM: "medium", NORMAL: "normal", UNKNOWN: "unknown" };
export const PRIORITY_ICON  = { CRITICAL: "🔴", HIGH: "🟠", MEDIUM: "🟡", NORMAL: "🟢", UNKNOWN: "⚪" };

export const SEVERITY_ICON  = { CRITICAL: "🔴", ERROR: "🟠", WARNING: "🟡", INFO: "🔵" };
export const SEVERITY_CLASS = { CRITICAL: "critical", ERROR: "error", WARNING: "warning", INFO: "info" };

export const ALERT_STATUS_CLASS = { OPEN: "open", ACKNOWLEDGED: "acknowledged", RESOLVED: "resolved", DISMISSED: "dismissed" };
export const HEALTH_CLASS = { OK: "ok", DEGRADED: "degraded", FAULT: "fault" };
export const BIN_STATUS_CLASS = { ACTIVE: "active", INACTIVE: "inactive", MAINTENANCE: "maintenance", DRAFT: "draft", RETIRED: "retired" };

/** Compute fill indicator color based on percentage thresholds. */
export function getFillColor(pct) {
  if (pct == null) return "#64748B";
  const v = Math.min(100, Math.max(0, pct));
  if (v > 95) return "#B42318";      // red / critical
  if (v > 85) return "#C2410C";      // orange / high
  if (v >= 70) return "#8F5F10";     // amber / medium
  return "#16A34A";                  // green / normal
}

/** Render a priority badge <span>. */
export function priorityBadge(p) {
  const cls  = PRIORITY_CLASS[p] || "unknown";
  const icon = PRIORITY_ICON[p]  || "⚪";
  const lbl  = PRIORITY_LABEL[p] || (p || "Unknown");
  return `<span class="badge badge-${cls}">${icon} ${h(lbl)}</span>`;
}

/** Render fill bar. Null fill_percent → "No reading" display. */
export function fillBar(pct) {
  if (pct == null) {
    return `<span class="null-fill">— Unavailable</span>`;
  }
  const v = Math.min(100, Math.max(0, pct));
  const color = getFillColor(v);
  return `
    <div class="fill-wrap">
      <div class="fill-track">
        <div class="fill-bar" style="width:${v.toFixed(1)}%;background:${color}"></div>
      </div>
      <span class="fill-label" style="color:${color}">${v.toFixed(0)}%</span>
    </div>`;
}

/** Larger fill bar for detail drawer. */
export function bigFillBar(pct) {
  if (pct == null) {
    return `<div class="big-fill-label null-fill">— No valid reading (sensor fault or no data)</div>`;
  }
  const v = Math.min(100, Math.max(0, pct));
  const color = getFillColor(v);
  return `
    <div class="big-fill-wrap">
      <div class="big-fill-track">
        <div class="big-fill-bar" style="width:${v.toFixed(1)}%;background:${color}"></div>
      </div>
      <div class="big-fill-label" style="color:${color}">${v.toFixed(0)}%</div>
    </div>`;
}

/** Sensor health badge. */
export function healthBadge(val) {
  const cls = HEALTH_CLASS[val] || "unknown";
  return `<span class="badge badge-${cls}">${h(val || "—")}</span>`;
}

/** Device state dot + text. */
export function deviceState(val) {
  const cls = { ONLINE: "online", OFFLINE: "offline", FAULT: "fault", MAINTENANCE: "maintenance" }[val] || "offline";
  return `<span class="device-dot ${cls}"></span> ${h(val || "—")}`;
}

/** SIM badge if is_simulated. */
export function simBadge(is_sim) {
  return is_sim ? `<span class="badge badge-sim">SIM</span>` : "";
}

/** Bin status badge. */
export function binStatusBadge(val) {
  const cls = BIN_STATUS_CLASS[val] || "inactive";
  return `<span class="badge badge-${cls}">${h(val || "—")}</span>`;
}
