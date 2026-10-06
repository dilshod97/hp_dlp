import { useState, useEffect } from "react";
import {
  Kpi, Panel, Chip, Empty, Pager, usePaged,
  SEV, TYPE_LABEL, timeAgo, hhmm, eventDesc,
} from "./ui.jsx";
import { api, mediaUrl } from "./api.js";

const nm = (amap, id) => amap[id] || `#${id}`;
function fmtDur(sec) {
  sec = Math.round(sec || 0);
  if (sec < 60) return `${sec}s`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ${sec % 60}s`;
  return `${Math.floor(sec / 3600)}h ${Math.floor((sec % 3600) / 60)}m`;
}
function fmtSize(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
const KIND_LABEL = { card: "Karta", passport: "Pasport", keyword: "Kalit so'z" };
const kindText = (kinds) => (kinds || "").split(",").filter(Boolean).map((k) => KIND_LABEL[k] || k).join(", ");

function SearchBox({ value, onChange, placeholder }) {
  return <input className="search" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder || "Qidirish..."} />;
}

// ---------- Boshqaruv paneli ----------
export function Overview({ overview, eventTypes, amap }) {
  const o = overview;
  const det = usePaged(api.detections, { size: 6 });
  const ev = usePaged(api.events, { size: 8 });
  const max = Math.max(1, ...eventTypes.map((e) => e.count));

  return (
    <div className="view">
      <div className="kpis">
        <Kpi label="Faol agentlar" value={o ? `${o.agents_online}/${o.agents_total}` : "—"} hint="so'nggi 5 daqiqada" />
        <Kpi label="Bugungi hodisalar" value={o ? o.events_today : "—"} />
        <Kpi label="Maxfiy ma'lumot" value={o ? o.detections_today : "—"} accent="crit" hint="bugun aniqlangan" />
        <Kpi label="Ogohlantirishlar" value={o ? o.alerts_today : "—"} hint="O'rta va Yuqori" />
      </div>

      <div className="grid-2">
        <Panel title="Hodisalar turlari bo'yicha" sub="so'nggi 24 soat">
          {eventTypes.length === 0 ? <Empty>Hali hodisa yo'q</Empty> : (
            <div className="bars">
              {eventTypes.map((e) => (
                <div className="bar-row" key={e.type}>
                  <span className="bar-name">{TYPE_LABEL[e.type] || e.type}</span>
                  <div className="bar-track"><div className="bar-fill" style={{ width: `${(e.count / max) * 100}%` }} /></div>
                  <span className="bar-val">{e.count}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="So'nggi maxfiy ma'lumotlar">
          {det.items.length === 0 ? <Empty>Aniqlanmagan</Empty> : (
            <div className="feed">
              {det.items.map((d) => (
                <div className="feed-item" key={d.id}>
                  <span className="sev crit" />
                  <div className="feed-main">
                    <div className="feed-title">{d.snippet}</div>
                    <div className="feed-meta">{nm(amap, d.agent_id)} · {kindText(d.kinds)} · {d.source === "file" ? "fayl" : "yozishma"} · {hhmm(d.occurred_at)}</div>
                  </div>
                  <Chip sev="crit" />
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel title="So'nggi hodisalar">
        <EventsTable events={ev.items} amap={amap} />
      </Panel>
    </div>
  );
}

// ---------- Agentlar ----------
export function Agents({ role }) {
  const canEdit = role === "superadmin" || role === "admin";
  const { items, total, page, setPage, size, reload } = usePaged(api.agents, { size: 25 });
  const [editing, setEditing] = useState(null);
  const [q, setQ] = useState("");
  const name = (a) => a.display_name || a.full_name || a.hostname;
  const list = items.filter((a) => `${name(a)} ${a.hostname} ${a.ip_address || ""} ${a.note || ""}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <>
      <Panel title="Agentlar" sub={`${total} ta`} right={<SearchBox value={q} onChange={setQ} placeholder="Ism, kompyuter, IP..." />}>
        <div className="tbl-wrap">
          <table>
            <thead><tr><th>Xodim</th><th>Kompyuter</th><th>IP</th><th>OT</th><th>Versiya</th><th>Faollik</th><th>Holat</th>{canEdit && <th></th>}</tr></thead>
            <tbody>
              {list.map((a) => (
                <tr key={a.id} className={a.active ? "" : "row-off"}>
                  <td><b>{name(a)}</b>{a.note && <div className="sub">{a.note}</div>}</td>
                  <td className="mono">{a.hostname}</td>
                  <td className="mono">{a.ip_address || "—"}</td>
                  <td>{a.os_name || "—"}</td>
                  <td className="mono">{a.agent_version || "—"}</td>
                  <td>{timeAgo(a.last_seen)}</td>
                  <td>{a.active ? <Chip sev="info">Faol</Chip> : <span className="chip off">Ishdan bo'shagan</span>}</td>
                  {canEdit && <td><button className="mini" onClick={() => setEditing(a)}>Tahrirlash</button></td>}
                </tr>
              ))}
              {list.length === 0 && <tr><td colSpan="7"><Empty>Topilmadi</Empty></td></tr>}
            </tbody>
          </table>
        </div>
        <Pager page={page} size={size} total={total} onPage={setPage} />
      </Panel>
      {editing && <AgentEdit agent={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload(); }} />}
    </>
  );
}

function AgentEdit({ agent, onClose, onSaved }) {
  const [name, setName] = useState(agent.display_name || "");
  const [note, setNote] = useState(agent.note || "");
  const [active, setActive] = useState(agent.active);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  async function save() {
    setBusy(true); setErr("");
    try { await api.updateAgent(agent.id, { display_name: name, note, active }); onSaved(); }
    catch { setErr("Saqlab bo'lmadi"); } finally { setBusy(false); }
  }
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Agentni tahrirlash</h3>
        <div className="auto-row"><span>Kompyuter</span><b className="mono">{agent.hostname}</b></div>
        <div className="auto-row"><span>IP</span><b className="mono">{agent.ip_address || "—"}</b></div>
        <label className="fld">Ism-familiya<input value={name} onChange={(e) => setName(e.target.value)} placeholder="masalan: Alisher Karimov" /></label>
        <label className="fld">Izoh<input value={note} onChange={(e) => setNote(e.target.value)} placeholder="masalan: 2026-10-05 da ishdan bo'shadi" /></label>
        <label className="chk"><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /> Faol xodim (belgini olsangiz — ishdan bo'shagan)</label>
        {err && <div className="err">{err}</div>}
        <div className="modal-actions">
          <button className="ghost" onClick={onClose}>Bekor</button>
          <button className="primary" disabled={busy} onClick={save}>{busy ? "..." : "Saqlash"}</button>
        </div>
      </div>
    </div>
  );
}

// ---------- Hodisalar ----------
function EventsTable({ events, amap }) {
  return (
    <div className="tbl-wrap">
      <table>
        <thead><tr><th>Vaqt</th><th>Xodim</th><th>Daraja</th><th>Tur</th><th>Tavsif</th></tr></thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.id}>
              <td className="mono">{hhmm(e.occurred_at)}</td>
              <td>{nm(amap, e.agent_id)}</td>
              <td><Chip sev={e.severity} /></td>
              <td>{TYPE_LABEL[e.type] || e.type}</td>
              <td>{e.app ? <span className="muted">{e.app} · </span> : null}{eventDesc(e)}</td>
            </tr>
          ))}
          {events.length === 0 && <tr><td colSpan="5"><Empty>Hodisa yo'q</Empty></td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export function Events({ amap }) {
  const [sev, setSev] = useState("all");
  const [q, setQ] = useState("");
  const { items, total, page, setPage, size } = usePaged(
    (l, o) => api.events(l, o, sev === "all" ? {} : { severity: sev }),
    { size: 25, deps: [sev] },
  );
  const list = q ? items.filter((e) => `${nm(amap, e.agent_id)} ${e.app || ""} ${e.title || ""} ${e.text || ""}`.toLowerCase().includes(q.toLowerCase())) : items;
  const btn = (k, l) => <button className={`filter ${sev === k ? "on" : ""}`} onClick={() => { setSev(k); setPage(0); }}>{l}</button>;
  return (
    <Panel title="Barcha hodisalar" sub={`${total} ta`}
      right={<div className="toolbar">{btn("all", "Hammasi")}{btn("crit", "Yuqori")}{btn("warn", "O'rta")}{btn("info", "Past")}<SearchBox value={q} onChange={setQ} /></div>}>
      <EventsTable events={list} amap={amap} />
      <Pager page={page} size={size} total={total} onPage={setPage} />
    </Panel>
  );
}

// ---------- Maxfiy ma'lumot (DLP aniqlashlar) ----------
export function Detections({ amap }) {
  const { items, total, page, setPage, size } = usePaged(api.detections, { size: 25 });
  const [q, setQ] = useState("");
  const list = q ? items.filter((d) => `${nm(amap, d.agent_id)} ${d.snippet || ""} ${kindText(d.kinds)}`.toLowerCase().includes(q.toLowerCase())) : items;
  return (
    <div className="view">
      <p className="note">Siyosatda belgilangan kalit so'zlar, karta va pasport raqamlari yozishma va fayllarda topilsa, shu yerda chiqadi.</p>
      <Panel title="Maxfiy ma'lumot aniqlashlari" sub={`${total} ta`} right={<SearchBox value={q} onChange={setQ} placeholder="Xodim, so'z..." />}>
        <div className="tbl-wrap">
          <table>
            <thead><tr><th>Vaqt</th><th>Xodim</th><th>Manba</th><th>Tur</th><th>Topilgan</th></tr></thead>
            <tbody>
              {list.map((d) => (
                <tr key={d.id}>
                  <td className="mono">{hhmm(d.occurred_at)}</td>
                  <td>{nm(amap, d.agent_id)}</td>
                  <td>{d.source === "file" ? "Fayl" : "Yozishma"}</td>
                  <td><Chip sev="crit">{kindText(d.kinds)}</Chip></td>
                  <td className="snippet">{d.snippet}</td>
                </tr>
              ))}
              {list.length === 0 && <tr><td colSpan="5"><Empty>Aniqlanmagan</Empty></td></tr>}
            </tbody>
          </table>
        </div>
        <Pager page={page} size={size} total={total} onPage={setPage} />
      </Panel>
    </div>
  );
}

// ---------- Dasturlar ----------
export function AppUsage({ agents }) {
  const [agentId, setAgentId] = useState("all");
  const [rows, setRows] = useState([]);
  useEffect(() => {
    let on = true;
    api.appUsage(agentId === "all" ? undefined : Number(agentId)).then((r) => { if (on) setRows(r); }).catch(() => {});
    return () => { on = false; };
  }, [agentId]);
  const max = Math.max(1, ...rows.map((r) => r.seconds));
  const grand = rows.reduce((s, r) => s + r.seconds, 0);
  const name = (a) => a.display_name || a.full_name || a.hostname;
  return (
    <div className="view">
      <p className="note">Dasturlarda o'tkazilgan vaqt (so'nggi 24 soat). Jami: {fmtDur(grand)}.</p>
      <Panel title="Dasturlar bo'yicha vaqt" sub={`${rows.length} ta dastur`}
        right={<select className="select" value={agentId} onChange={(e) => setAgentId(e.target.value)}>
          <option value="all">Barcha xodimlar</option>
          {agents.map((a) => <option key={a.id} value={a.id}>{name(a)}</option>)}
        </select>}>
        {rows.length === 0 ? <Empty>Ma'lumot yo'q</Empty> : (
          <div className="bars">
            {rows.map((r) => (
              <div className="bar-row wide-name" key={r.app}>
                <span className="bar-name" title={r.app}>{r.app}</span>
                <div className="bar-track"><div className="bar-fill" style={{ width: `${(r.seconds / max) * 100}%` }} /></div>
                <span className="bar-val">{fmtDur(r.seconds)}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

// ---------- Skrinshotlar ----------
export function Screenshots({ amap }) {
  const { items, total, page, setPage, size } = usePaged(api.screenshots, { size: 24 });
  return (
    <div className="view">
      <p className="note">Agent oyna almashganda ekran suratini oladi va shu yerda ko'rinadi.</p>
      {items.length === 0 ? (
        <Panel><Empty>Hali skrinshot yo'q. (Docker demo agentida o'chirilgan; Mac/Windows agentida yoqilgan.)</Empty></Panel>
      ) : (
        <>
          <div className="shots">
            {items.map((s) => (
              <div className="shot" key={s.id}>
                <img src={mediaUrl(s.url)} alt={s.title || "skrinshot"} loading="lazy" />
                <div className="shot-meta"><div className="shot-app">{nm(amap, s.agent_id)}</div><div className="shot-time">{s.app || "Ekran"} · {hhmm(s.occurred_at)}</div></div>
              </div>
            ))}
          </div>
          <Pager page={page} size={size} total={total} onPage={setPage} />
        </>
      )}
    </div>
  );
}

// ---------- Yozishmalar (klaviatura, clipboard, telegram, email) ----------
const APP_NAME = {
  "telegram.exe": "Telegram", "chrome.exe": "Chrome", "msedge.exe": "Edge",
  "firefox.exe": "Firefox", "outlook.exe": "Outlook", "code.exe": "VS Code",
  "excel.exe": "Excel", "winword.exe": "Word", "windowsterminal.exe": "Terminal",
};
function appLabel(app) {
  if (!app) return "—";
  return APP_NAME[app.toLowerCase()] || app.replace(/\.exe$/i, "");
}
// Oyna sarlavhasidan kontekst (kim bilan): "‎Malika – (2)" -> "Malika"
function msgContext(e) {
  let t = (e.title || "").replace(/[‎‏‪-‮]/g, "").trim(); // ko'rinmas belgilar
  if (!t) return "";
  t = t.replace(/^\(\d+\)\s*/, "").trim(); // boshida "(1) " - o'qilmagan xabar soni
  t = t.replace(/\s*[—–-]\s*(Telegram|Google Chrome|Microsoft\s*Edge|Mozilla Firefox|Opera|Brave|Outlook).*$/i, "").trim();
  t = t.replace(/\s*[—–-]?\s*\(\d+\)\s*$/, "").trim(); // "Py – (2)" / "Py (2)" -> "Py"
  return t;
}

export function Messages({ amap }) {
  const [q, setQ] = useState("");
  const [app, setApp] = useState("all");
  const [apps, setApps] = useState([]);
  useEffect(() => { api.messageApps().then(setApps).catch(() => {}); }, []);
  const { items, total, page, setPage, size } = usePaged(
    (l, o) => api.events(l, o, { types: "keyboard,clipboard,telegram,email", ...(app !== "all" ? { app } : {}) }),
    { size: 25, deps: [app] });
  const list = q ? items.filter((e) => `${nm(amap, e.agent_id)} ${e.text || ""} ${e.title || ""} ${appLabel(e.app)}`.toLowerCase().includes(q.toLowerCase())) : items;

  return (
    <div className="view">
      <p className="note">Klaviatura, clipboard, Telegram va e-mail orqali yozilgan matnlar. Kontekst = oyna sarlavhasi (masalan Telegram'да kim bilan yozishayotgani).</p>
      <Panel title="Yozishmalar" sub={`${total} ta`}
        right={<div className="toolbar">
          <select className="select" value={app} onChange={(e) => { setApp(e.target.value); setPage(0); }}>
            <option value="all">Barcha dasturlar</option>
            {apps.map((a) => <option key={a} value={a}>{appLabel(a)}</option>)}
          </select>
          <SearchBox value={q} onChange={setQ} />
        </div>}>
        {list.length === 0 ? <Empty>Topilmadi</Empty> : (
          <div className="feed">
            {list.map((e) => {
              const ctx = msgContext(e);
              return (
                <div className="feed-item" key={e.id}>
                  <span className={`sev ${SEV[e.severity]?.cls || "info"}`} />
                  <div className="feed-main">
                    <div className="feed-title">
                      {ctx && <span className="msg-ctx">{ctx}:</span>} {e.text || e.title}
                    </div>
                    <div className="feed-meta">{nm(amap, e.agent_id)} · {appLabel(e.app)} · {TYPE_LABEL[e.type] || e.type} · {hhmm(e.occurred_at)}</div>
                  </div>
                  {e.severity === "crit" && <Chip sev="crit">Maxfiy</Chip>}
                </div>
              );
            })}
          </div>
        )}
        <Pager page={page} size={size} total={total} onPage={setPage} />
      </Panel>
    </div>
  );
}

// ---------- Umumiy: tur bo'yicha hodisalar jadvali ----------
function EventsByType({ amap, types, title, note, cols }) {
  const { items, total, page, setPage, size } = usePaged((l, o) => api.events(l, o, { types }), { size: 25 });
  const [q, setQ] = useState("");
  const list = q ? items.filter((e) => `${nm(amap, e.agent_id)} ${e.title || ""} ${e.app || ""}`.toLowerCase().includes(q.toLowerCase())) : items;
  return (
    <div className="view">
      {note && <p className="note">{note}</p>}
      <Panel title={title} sub={`${total} ta`} right={<SearchBox value={q} onChange={setQ} />}>
        <div className="tbl-wrap">
          <table>
            <thead><tr><th>Vaqt</th><th>Xodim</th><th>Daraja</th>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>
              {list.map((e) => (
                <tr key={e.id}>
                  <td className="mono">{hhmm(e.occurred_at)}</td>
                  <td>{nm(amap, e.agent_id)}</td>
                  <td><Chip sev={e.severity} /></td>
                  <td>{e.title || eventDesc(e)}{e.app && cols.length > 1 ? <div className="sub">{e.app}</div> : null}</td>
                  {cols.length > 1 && <td className="muted">{e.details?.action || e.channel || "—"}</td>}
                </tr>
              ))}
              {list.length === 0 && <tr><td colSpan={3 + cols.length}><Empty>Topilmadi</Empty></td></tr>}
            </tbody>
          </table>
        </div>
        <Pager page={page} size={size} total={total} onPage={setPage} />
      </Panel>
    </div>
  );
}

export function WebSites({ amap }) {
  const [sites, setSites] = useState([]);
  useEffect(() => {
    let on = true;
    api.siteUsage().then((r) => { if (on) setSites(r); }).catch(() => {});
    const id = setInterval(() => api.siteUsage().then((r) => on && setSites(r)).catch(() => {}), 5000);
    return () => { on = false; clearInterval(id); };
  }, []);
  const max = Math.max(1, ...sites.map((s) => s.seconds));
  return (
    <div className="view">
      <p className="note">Tashrif buyurilgan saytlar va ularда o'tkazilgan vaqt (masalan kun.uz'da qancha). To'liq URL — brauzer kengaytmasi bilan keyingi bosqichда.</p>
      <Panel title="Saytlar bo'yicha vaqt" sub={`${sites.length} ta sayt · so'nggi 24 soat`}>
        {sites.length === 0 ? <Empty>Ma'lumot yo'q</Empty> : (
          <div className="bars">
            {sites.slice(0, 15).map((s) => (
              <div className="bar-row wide-name" key={s.site}>
                <span className="bar-name" title={s.site}>{s.site}</span>
                <div className="bar-track"><div className="bar-fill" style={{ width: `${(s.seconds / max) * 100}%` }} /></div>
                <span className="bar-val">{fmtDur(s.seconds)}</span>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <EventsByType amap={amap} types="web" title="Tashriflar" cols={["Sayt"]} />
    </div>
  );
}

// ---------- Ish vaqti (qachondan qachongacha) ----------
function ymd(d) { return d.toISOString().slice(0, 10); }
export function WorkTime() {
  const [day, setDay] = useState(ymd(new Date()));
  const [rows, setRows] = useState([]);
  useEffect(() => {
    let on = true;
    api.worktime(day).then((r) => on && setRows(r)).catch(() => {});
    return () => { on = false; };
  }, [day]);
  const hm = (iso) => iso ? new Date(iso).toLocaleTimeString("uz", { hour: "2-digit", minute: "2-digit" }) : "—";
  return (
    <div className="view">
      <p className="note">Har bir xodim tanlangan kunda qachondan qachongacha faol bo'lgani va jami faol vaqti.</p>
      <Panel title="Ish vaqti" sub={day}
        right={<input type="date" className="select" value={day} onChange={(e) => setDay(e.target.value)} />}>
        <div className="tbl-wrap">
          <table>
            <thead><tr><th>Xodim</th><th>Boshlanish</th><th>Tugash</th><th>Faol vaqt</th><th>Hodisalar</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.agent_id}>
                  <td><b>{r.name}</b></td>
                  <td className="mono">{hm(r.first)}</td>
                  <td className="mono">{hm(r.last)}</td>
                  <td>{fmtDur(r.active_seconds)}</td>
                  <td className="mono">{r.events}</td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan="5"><Empty>Bu kunda faollik yo'q</Empty></td></tr>}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

export function FileActivity({ amap }) {
  return <EventsByType amap={amap} types="file_monitor" title="Fayl harakatlari" cols={["Fayl", "Harakat"]}
    note="Foydalanuvchi papkalarida fayl yaratish, o'zgartirish, o'chirish, ko'chirish." />;
}

// ---------- Ushlangan fayllar ----------
function fileOrigin(f) {
  if (f.source_url) {
    try { return new URL(f.source_url).hostname || f.source_url; } catch { return f.source_url; }
  }
  return [appLabel(f.context_app), f.context_title].filter(Boolean).join(" · ");
}

export function Files({ amap }) {
  const { items, total, page, setPage, size } = usePaged(api.files, { size: 25 });
  const [open, setOpen] = useState(null);
  const [q, setQ] = useState("");
  const list = q ? items.filter((f) => `${f.filename} ${nm(amap, f.agent_id)} ${f.channel || ""}`.toLowerCase().includes(q.toLowerCase())) : items;
  return (
    <div className="view">
      <p className="note">Agent orqali o'tgan fayllar (USB, Telegram, e-mail). Ko'rish uchun bosing.</p>
      <Panel title="Ushlangan fayllar" sub={`${total} ta`} right={<SearchBox value={q} onChange={setQ} placeholder="Fayl, xodim..." />}>
        {list.length === 0 ? <Empty>Topilmadi</Empty> : (
          <div className="tbl-wrap">
            <table>
              <thead><tr><th>Fayl</th><th>Xodim</th><th>Qayerdan / kontekst</th><th>Manzil</th><th>Kanal</th><th>Daraja</th><th>Hajm</th><th>Vaqt</th><th></th></tr></thead>
              <tbody>
                {list.map((f) => (
                  <tr key={f.id}>
                    <td><b>{f.filename}</b></td>
                    <td>{nm(amap, f.agent_id)}</td>
                    <td className="snippet-path" title={fileOrigin(f)}>{fileOrigin(f) || "—"}</td>
                    <td className="mono snippet-path" title={f.source_path || ""}>{f.source_path || "—"}</td>
                    <td><Chip sev="info">{f.channel || "—"}</Chip></td>
                    <td>{f.severity === "crit" ? <Chip sev="crit">Maxfiy</Chip> : <span className="muted">—</span>}</td>
                    <td className="mono">{fmtSize(f.size)}</td>
                    <td>{hhmm(f.occurred_at)}</td>
                    <td><button className="mini" onClick={() => { api.fileOpen(f.id).catch(() => {}); setOpen(f); }}>Ko'rish</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pager page={page} size={size} total={total} onPage={setPage} />
      </Panel>
      {open && <FileViewer file={open} onClose={() => setOpen(null)} />}
    </div>
  );
}

function FileViewer({ file, onClose }) {
  const [text, setText] = useState("");
  const [state, setState] = useState("loading");
  const url = mediaUrl(file.url);
  const isImage = (file.mime || "").startsWith("image/");
  const isText = (file.mime || "").startsWith("text/") || /\.(txt|csv|log|json|md)$/i.test(file.filename);
  useEffect(() => {
    if (!isText) { setState("done"); return; }
    let on = true;
    fetch(url).then((r) => r.text()).then((t) => { if (on) { setText(t); setState("done"); } }).catch(() => { if (on) setState("error"); });
    return () => { on = false; };
  }, [url, isText]);
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head"><h3>{file.filename}</h3><span className="muted">{fmtSize(file.size)} · {file.channel || "—"}</span></div>
        {file.source_url && <div className="auto-row"><span>Qayerdan (URL)</span><b className="mono">{file.source_url}</b></div>}
        {(file.context_app || file.context_title) && <div className="auto-row"><span>Kontekst</span><b>{[appLabel(file.context_app), file.context_title].filter(Boolean).join(" · ")}</b></div>}
        {file.source_path && <div className="auto-row"><span>Manzil (disk)</span><b className="mono">{file.source_path}</b></div>}
        <div className="viewer">
          {isImage && <img src={url} alt={file.filename} />}
          {isText && state === "loading" && <div className="muted">Yuklanmoqda...</div>}
          {isText && state === "done" && <pre>{text}</pre>}
          {isText && state === "error" && <div className="err">O'qib bo'lmadi</div>}
          {!isImage && !isText && <div className="muted">Bu fayl turini ko'rsatib bo'lmaydi. <a href={url} target="_blank" rel="noreferrer">Yuklab olish</a></div>}
        </div>
        <div className="modal-actions"><a className="ghost" href={url} target="_blank" rel="noreferrer">Yangi oynada</a><button className="primary" onClick={onClose}>Yopish</button></div>
      </div>
    </div>
  );
}

// ---------- Siyosat (kalit so'zlar + saqlash muddati) ----------
export function PolicyView({ role }) {
  const canEdit = role === "superadmin" || role === "admin";
  const isSuper = role === "superadmin";
  const [p, setP] = useState(null);
  const [kw, setKw] = useState("");
  const [ret, setRet] = useState(90);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [cleanMsg, setCleanMsg] = useState("");
  useEffect(() => {
    api.getPolicy().then((pol) => { setP(pol); setKw(pol.keywords); setRet(pol.retention_days); }).catch(() => {});
  }, []);
  if (!p) return <Panel><Empty>Yuklanmoqda...</Empty></Panel>;

  async function save() {
    setBusy(true); setSaved(false);
    try {
      const upd = await api.updatePolicy({ keywords: kw, detect_cards: p.detect_cards, detect_passport: p.detect_passport, block_usb: p.block_usb, retention_days: Number(ret) });
      setP(upd); setSaved(true);
    } catch { /* */ } finally { setBusy(false); }
  }
  async function runCleanup() {
    setCleanMsg("Tozalanmoqda...");
    try {
      const r = await api.cleanup();
      const d = r.deleted || {};
      setCleanMsg(`Tozalandi: ${Object.values(d).reduce((s, n) => s + n, 0)} yozuv o'chirildi`);
    } catch { setCleanMsg("Xatolik"); }
  }
  const toggle = (field) => canEdit && setP({ ...p, [field]: !p[field] });

  return (
    <div className="view">
      <p className="note">Kalit so'zlarni vergul bilan kiriting (masalan: <b>Pora, Rais, maxfiy</b>). Shu so'zlar qatnashgan har qanday yozishma yoki fayl "Maxfiy ma'lumot" bo'limida alohida chiqadi.{!canEdit && " (Sizning rolingiz faqat ko'rish.)"}</p>
      <Panel title="DLP siyosati">
        <label className="fld">Kalit so'zlar (vergul bilan)
          <textarea className="ta" rows={3} value={kw} disabled={!canEdit} onChange={(e) => { setKw(e.target.value); setSaved(false); }} placeholder="Pora, Rais, maxfiy, shartnoma" />
        </label>
        <label className="chk"><input type="checkbox" checked={p.detect_cards} disabled={!canEdit} onChange={() => toggle("detect_cards")} /> Bank karta raqamlarini aniqlash</label>
        <label className="chk"><input type="checkbox" checked={p.detect_passport} disabled={!canEdit} onChange={() => toggle("detect_passport")} /> Pasport raqamlarini aniqlash</label>
        <label className="chk"><input type="checkbox" checked={p.block_usb} disabled={!canEdit} onChange={() => toggle("block_usb")} /> USB orqali chiqishni bloklash <span className="muted">(enforcement — keyingi bosqich)</span></label>
        <label className="fld">Ma'lumotni saqlash muddati (kun)
          <input type="number" min="1" className="num" value={ret} disabled={!canEdit} onChange={(e) => { setRet(e.target.value); setSaved(false); }} />
        </label>
        {canEdit && (
          <div className="modal-actions">
            {saved && <span className="ok-text">Saqlandi ✓</span>}
            <button className="primary" disabled={busy} onClick={save}>{busy ? "..." : "Saqlash"}</button>
          </div>
        )}
      </Panel>
      {isSuper && (
        <Panel title="Ma'lumotni tozalash" sub={`Saqlash muddatidan (${p.retention_days} kun) oshgan ma'lumotni o'chirish`}>
          <div className="modal-actions">
            {cleanMsg && <span className="ok-text">{cleanMsg}</span>}
            <button className="ghost" onClick={runCleanup}>Eskilarni tozalash</button>
          </div>
        </Panel>
      )}
    </div>
  );
}

// ---------- Foydalanuvchilar (superadmin) ----------
const ALL_ROLES = ["superadmin", "admin", "operator", "auditor"];
export function Users({ me }) {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({ username: "", password: "", role: "operator" });
  const [err, setErr] = useState("");
  const load = () => api.users().then(setUsers).catch(() => {});
  useEffect(() => { load(); }, []);

  async function add() {
    setErr("");
    if (!form.username || !form.password) { setErr("Login va parol kiriting"); return; }
    try { await api.createUser(form); setForm({ username: "", password: "", role: "operator" }); load(); }
    catch (e) { setErr(e.message === "400" ? "Login band yoki noto'g'ri" : "Xatolik"); }
  }
  async function del(u) {
    if (u.username === me?.username) return;
    try { await api.deleteUser(u.id); load(); } catch { /* */ }
  }
  async function setRole(u, role) { try { await api.updateUser(u.id, { role }); load(); } catch { /* */ } }

  return (
    <div className="view">
      <p className="note">Foydalanuvchilarni yarating va rol bering. <b>Superadmin</b> — to'liq, <b>Admin</b> — siyosat+agent, <b>Operator</b> — faqat kuzatish, <b>Auditor</b> — hisobot+audit.</p>
      <Panel title="Yangi foydalanuvchi">
        <div className="form-row">
          <input className="search" placeholder="Login" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
          <input className="search" type="password" placeholder="Parol" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <select className="select" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {ALL_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <button className="primary" onClick={add}>Qo'shish</button>
        </div>
        {err && <div className="err">{err}</div>}
      </Panel>
      <Panel title="Foydalanuvchilar" sub={`${users.length} ta`}>
        <div className="tbl-wrap">
          <table>
            <thead><tr><th>Login</th><th>Rol</th><th>Holat</th><th></th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td><b>{u.username}</b>{u.username === me?.username && <span className="muted"> (siz)</span>}</td>
                  <td>
                    <select className="select sm" value={u.role} onChange={(e) => setRole(u, e.target.value)} disabled={u.username === me?.username}>
                      {ALL_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </td>
                  <td>{u.active ? <Chip sev="info">Faol</Chip> : <span className="chip off">O'chirilgan</span>}</td>
                  <td>{u.username !== me?.username && <button className="mini danger" onClick={() => del(u)}>O'chirish</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

// ---------- Audit jurnali ----------
const ACTION_LABEL = {
  login: "Tizimga kirdi", policy_update: "Siyosatni o'zgartirdi", agent_update: "Agentni tahrirladi",
  user_create: "Foydalanuvchi yaratdi", user_update: "Foydalanuvchini o'zgartirdi",
  user_delete: "Foydalanuvchini o'chirdi", file_view: "Faylni ko'rdi", cleanup: "Ma'lumotni tozaladi",
};
export function Audit() {
  const { items, total, page, setPage, size } = usePaged(api.audit, { size: 25 });
  return (
    <div className="view">
      <p className="note">Kim nima qildi va nimani ko'rdi — barcha admin harakatlari.</p>
      <Panel title="Audit jurnali" sub={`${total} ta`}>
        <div className="tbl-wrap">
          <table>
            <thead><tr><th>Vaqt</th><th>Kim</th><th>Harakat</th><th>Nimaga</th></tr></thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id}>
                  <td className="mono">{hhmm(a.created_at)}</td>
                  <td><b>{a.actor}</b></td>
                  <td>{ACTION_LABEL[a.action] || a.action}</td>
                  <td className="muted">{a.target || "—"}</td>
                </tr>
              ))}
              {items.length === 0 && <tr><td colSpan="4"><Empty>Bo'sh</Empty></td></tr>}
            </tbody>
          </table>
        </div>
        <Pager page={page} size={size} total={total} onPage={setPage} />
      </Panel>
    </div>
  );
}

// ---------- Agent yangilash (superadmin) ----------
export function AgentUpdates() {
  const [releases, setReleases] = useState([]);
  const [version, setVersion] = useState("");
  const [notes, setNotes] = useState("");
  const [file, setFile] = useState(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => api.releases().then(setReleases).catch(() => {});
  useEffect(() => { load(); }, []);

  async function upload() {
    setMsg("");
    if (!version || !file) { setMsg("Versiya va exe faylni tanlang"); return; }
    setBusy(true);
    try {
      await api.uploadRelease(version, notes, file);
      setVersion(""); setNotes(""); setFile(null);
      setMsg("Yuklandi ✓ — agentlar 1 soat ichida avtomatik yangilanadi");
      load();
    } catch (e) {
      setMsg(e.message === "400" ? "Bu versiya allaqachon mavjud" : "Xatolik");
    } finally { setBusy(false); }
  }

  return (
    <div className="view">
      <p className="note">Yangi agent versiyasini (hp-dlp-agent.exe) yuklang. O'rnatilgan agentlar uni serverdan avtomatik olib, o'zini yangilaydi (SHA256 tekshiruvi bilan).</p>
      <Panel title="Yangi versiya yuklash">
        <div className="form-row">
          <input className="search" placeholder="Versiya (masalan 0.5.0)" value={version} onChange={(e) => setVersion(e.target.value)} />
          <input className="search" placeholder="Izoh (ixtiyoriy)" value={notes} onChange={(e) => setNotes(e.target.value)} />
          <input type="file" accept=".exe" onChange={(e) => setFile(e.target.files[0])} />
          <button className="primary" disabled={busy} onClick={upload}>{busy ? "..." : "Yuklash"}</button>
        </div>
        {msg && <div className={msg.includes("✓") ? "ok-text" : "err"} style={{ marginTop: 8 }}>{msg}</div>}
      </Panel>
      <Panel title="Chiqarilgan versiyalar" sub={`${releases.length} ta`}>
        <div className="tbl-wrap">
          <table>
            <thead><tr><th>Versiya</th><th>Izoh</th><th>SHA256</th><th>Sana</th></tr></thead>
            <tbody>
              {releases.map((r) => (
                <tr key={r.id}>
                  <td><b>{r.version}</b></td>
                  <td>{r.notes || "—"}</td>
                  <td className="mono snippet">{r.sha256.slice(0, 16)}…</td>
                  <td>{hhmm(r.created_at)}</td>
                </tr>
              ))}
              {releases.length === 0 && <tr><td colSpan="4"><Empty>Hali versiya yuklanmagan</Empty></td></tr>}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

// ---------- Imkoniyatlar ----------
const CAPS = [
  { t: "Ekran suratlari", s: "ok" }, { t: "Klaviatura nazorati", s: "ok" },
  { t: "Dastur faolligi va vaqt", s: "ok" }, { t: "USB disklar nazorati", s: "ok" },
  { t: "Printer (hodisa)", s: "ok" }, { t: "O'rnatilgan dasturlar", s: "ok" },
  { t: "Ushlangan fayllarni o'qish", s: "ok" }, { t: "Login/parol va rollar", s: "ok" },
  { t: "Audit jurnali", s: "ok" }, { t: "Agentni avtomatik yangilash", s: "ok" },
  { t: "Maxfiy ma'lumot aniqlash (kalit so'z, karta, pasport)", s: "ok" },
  { t: "DLP siyosati (kalit so'zlar)", s: "ok" },
  { t: "Clipboard nazorati", s: "ok" }, { t: "Fayl monitoringi", s: "ok" },
  { t: "Veb-sayt nazorati (sarlavha)", s: "ok" },
  { t: "USB/fayl chiqishini bloklash (enforcement)", s: "plan" },
  { t: "Veb to'liq URL (kengaytma/proksi)", s: "plan" },
  { t: "E-mail nazorati (haqiqiy)", s: "plan" }, { t: "Telegram nazorati (haqiqiy)", s: "plan" },
  { t: "OCR (rasmdagi matn)", s: "plan" }, { t: "Ekran suv belgisi", s: "plan" },
];
const CAP_LABEL = { ok: "Tayyor", plan: "Rejada" };

export function Capabilities() {
  const done = CAPS.filter((c) => c.s === "ok").length;
  return (
    <div className="view">
      <Panel title="Imkoniyatlar qamrovi" sub={`${done}/${CAPS.length} modul tayyor`}>
        <div className="caps">
          {CAPS.map((c) => (
            <div className="cap" key={c.t}>
              <span className={`cap-dot ${c.s}`} /><span className="cap-name">{c.t}</span><span className={`cap-lbl ${c.s}`}>{CAP_LABEL[c.s]}</span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

// ---------- Superadmin ----------
const ROLES = [
  { r: "Superadmin", perm: "To'liq nazorat", sev: "crit" },
  { r: "Administrator", perm: "Hodisa + siyosat", sev: "info" },
  { r: "Operator", perm: "Faqat kuzatish", sev: "info" },
  { r: "Auditor", perm: "Faqat hisobot", sev: "info" },
];

export function Superadmin({ user }) {
  return (
    <div className="view">
      <p className="note">Hozirgi foydalanuvchi: <b>{user?.username}</b> ({user?.role}). To'liq rol boshqaruvi — Bosqich 4.</p>
      <Panel title="Rollar (reja)" sub="kim nimani ko'ra oladi">
        <div className="tbl-wrap">
          <table>
            <thead><tr><th>Rol</th><th>Ruxsatlar</th></tr></thead>
            <tbody>{ROLES.map((x) => (<tr key={x.r}><td><Chip sev={x.sev}>{x.r}</Chip></td><td>{x.perm}</td></tr>))}</tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
