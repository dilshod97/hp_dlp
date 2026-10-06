import { useEffect, useState, useCallback } from "react";
import { api, getToken, setToken, getUser, setUser } from "./api.js";
import {
  Overview, Agents, Events, Detections, AppUsage, Screenshots, Messages, WebSites,
  FileActivity, Files, PolicyView, Capabilities, Users, Audit, AgentUpdates, WorkTime,
} from "./views.jsx";

const NAV = [
  { key: "overview", label: "Boshqaruv paneli" },
  { key: "agents", label: "Agentlar" },
  { key: "events", label: "Hodisalar" },
  { key: "dlp", label: "Maxfiy ma'lumot" },
  { key: "appusage", label: "Dasturlar" },
  { key: "worktime", label: "Ish vaqti" },
  { key: "web", label: "Veb-saytlar" },
  { key: "filemon", label: "Fayl harakatlari" },
  { key: "screenshots", label: "Skrinshotlar" },
  { key: "messages", label: "Yozishmalar" },
  { key: "files", label: "Ushlangan fayllar" },
  { key: "policy", label: "Siyosat", roles: ["superadmin", "admin"] },
  { key: "audit", label: "Audit jurnali", roles: ["superadmin", "admin", "auditor"] },
  { key: "users", label: "Foydalanuvchilar", roles: ["superadmin"] },
  { key: "updates", label: "Agent yangilash", roles: ["superadmin"] },
  { key: "capabilities", label: "Imkoniyatlar" },
];

function Login({ onDone }) {
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const res = await api.login(u, p);
      setToken(res.token); setUser({ username: res.username, role: res.role }); onDone();
    } catch (ex) {
      setErr(ex.message === "401" ? "Login yoki parol noto'g'ri" : "Serverga ulanib bo'lmadi");
    } finally { setBusy(false); }
  }
  return (
    <div className="login">
      <form className="login-card" onSubmit={submit}>
        <h1>HP DLP</h1>
        <p>Panelga kirish</p>
        <input value={u} onChange={(e) => setU(e.target.value)} placeholder="Login" autoComplete="username" />
        <input type="password" value={p} onChange={(e) => setP(e.target.value)} placeholder="Parol" autoComplete="current-password" />
        {err && <div className="err">{err}</div>}
        <button disabled={busy}>{busy ? "..." : "Kirish"}</button>
        <small>Standart: <code>admin</code> / <code>admin123</code></small>
      </form>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [view, setView] = useState("overview");
  const [overview, setOverview] = useState(null);
  const [eventTypes, setEventTypes] = useState([]);
  const [agents, setAgents] = useState([]);
  const [error, setError] = useState("");
  const user = getUser();

  const loadGlobal = useCallback(async () => {
    try {
      const [ov, et, ag] = await Promise.all([api.overview(), api.eventTypes(), api.agents(200, 0)]);
      setOverview(ov); setEventTypes(et); setAgents(ag.items); setError("");
    } catch (e) {
      if (e.message === "401") { logout(); return; }
      setError("Serverga ulanib bo'lmadi");
    }
  }, []);

  useEffect(() => {
    if (!authed) return;
    loadGlobal();
    const id = setInterval(loadGlobal, 5000);
    return () => clearInterval(id);
  }, [authed, loadGlobal]);

  function logout() { setToken(""); setUser(null); setAuthed(false); }

  if (!authed) return <Login onDone={() => setAuthed(true)} />;

  const amap = {};
  agents.forEach((a) => { amap[a.id] = a.display_name || a.full_name || a.hostname; });

  const role = user?.role;
  const navItems = NAV.filter((n) => !n.roles || n.roles.includes(role));

  const views = {
    overview: <Overview overview={overview} eventTypes={eventTypes} amap={amap} />,
    agents: <Agents role={role} />,
    events: <Events amap={amap} />,
    dlp: <Detections amap={amap} />,
    appusage: <AppUsage agents={agents} />,
    worktime: <WorkTime />,
    web: <WebSites amap={amap} />,
    filemon: <FileActivity amap={amap} />,
    screenshots: <Screenshots amap={amap} agents={agents} />,
    messages: <Messages amap={amap} />,
    files: <Files amap={amap} />,
    policy: <PolicyView role={role} />,
    audit: <Audit />,
    users: <Users me={user} />,
    updates: <AgentUpdates />,
    capabilities: <Capabilities />,
  };
  const current = views[view] ? view : "overview";

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">● HP DLP<span>Nazorat markazi</span></div>
        <nav>
          {navItems.map((n) => (
            <button key={n.key} className={`nav-item ${current === n.key ? "on" : ""}`} onClick={() => setView(n.key)}>{n.label}</button>
          ))}
        </nav>
        <div className="side-foot">
          <div className="whoami">{user?.username} <span>{user?.role}</span></div>
          <div className="live">● jonli · 5s</div>
          <button className="ghost" onClick={logout}>Chiqish</button>
        </div>
      </aside>
      <main className="main">
        <header className="top">
          <h1>{NAV.find((n) => n.key === current)?.label}</h1>
          {error && <span className="err">{error}</span>}
        </header>
        <div className="content">{views[current]}</div>
      </main>
    </div>
  );
}
