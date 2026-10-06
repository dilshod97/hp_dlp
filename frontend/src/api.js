// Server bilan aloqa. Token localStorage'da saqlanadi.
export const BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export function getToken() { try { return localStorage.getItem("hp_dlp_token") || ""; } catch { return ""; } }
export function setToken(t) { try { localStorage.setItem("hp_dlp_token", t); } catch { /* */ } }
export function getUser() { try { return JSON.parse(localStorage.getItem("hp_dlp_user") || "null"); } catch { return null; } }
export function setUser(u) { try { localStorage.setItem("hp_dlp_user", JSON.stringify(u)); } catch { /* */ } }

async function req(path, { method = "GET", body } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { Authorization: `Bearer ${getToken()}`, ...(body ? { "Content-Type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

const qs = (o) => Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== "").map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");

export const api = {
  login: async (username, password) => {
    const res = await fetch(`${BASE}/api/v1/auth/login`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  },
  overview: () => req("/api/v1/stats/overview"),
  eventTypes: (hours = 24) => req(`/api/v1/stats/event-types?hours=${hours}`),
  appUsage: (agentId, hours = 24) => req(`/api/v1/stats/app-usage?${qs({ hours, agent_id: agentId })}`),
  siteUsage: (agentId, hours = 24) => req(`/api/v1/stats/site-usage?${qs({ hours, agent_id: agentId })}`),
  messageApps: () => req("/api/v1/stats/message-apps"),
  worktime: (day) => req(`/api/v1/stats/worktime?${qs({ day })}`),
  agents: (limit = 200, offset = 0) => req(`/api/v1/agents?${qs({ limit, offset })}`),
  updateAgent: (id, body) => req(`/api/v1/agents/${id}`, { method: "PATCH", body }),
  events: (limit = 25, offset = 0, extra = {}) => req(`/api/v1/events?${qs({ limit, offset, ...extra })}`),
  screenshots: (limit = 24, offset = 0, agentId) => req(`/api/v1/screenshots?${qs({ limit, offset, agent_id: agentId })}`),
  files: (limit = 25, offset = 0) => req(`/api/v1/files?${qs({ limit, offset })}`),
  detections: (limit = 25, offset = 0) => req(`/api/v1/detections?${qs({ limit, offset })}`),
  getPolicy: () => req("/api/v1/policy"),
  updatePolicy: (body) => req("/api/v1/policy", { method: "PUT", body }),
  fileOpen: (id) => req(`/api/v1/files/${id}`),
  audit: (limit = 25, offset = 0) => req(`/api/v1/audit?${qs({ limit, offset })}`),
  users: () => req("/api/v1/users"),
  createUser: (body) => req("/api/v1/users", { method: "POST", body }),
  updateUser: (id, body) => req(`/api/v1/users/${id}`, { method: "PATCH", body }),
  deleteUser: (id) => req(`/api/v1/users/${id}`, { method: "DELETE" }),
  cleanup: (days) => req(`/api/v1/maintenance/cleanup${days ? `?days=${days}` : ""}`, { method: "POST" }),
  releases: () => req("/api/v1/agent/releases"),
  uploadRelease: async (version, notes, file) => {
    const fd = new FormData();
    fd.append("version", version);
    fd.append("notes", notes || "");
    fd.append("file", file);
    const res = await fetch(`${BASE}/api/v1/agent/releases`, {
      method: "POST",
      headers: { Authorization: `Bearer ${getToken()}` },
      body: fd,
    });
    if (!res.ok) throw new Error(`${res.status}`);
    return res.json();
  },
};

export function mediaUrl(url) { return `${BASE}${url}`; }
