// Umumiy kichik komponentlar va yordamchilar.
import { useState, useEffect, useCallback } from "react";

// Sahifalangan ma'lumot uchun hook. fetcher(limit, offset) -> {items, total}
export function usePaged(fetcher, { size = 25, deps = [], live = true } = {}) {
  const [page, setPage] = useState(0);
  const [data, setData] = useState({ items: [], total: 0 });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(async () => {
    try { setData(await fetcher(size, page * size)); } catch { /* */ }
  }, [page, size, ...deps]);
  useEffect(() => {
    load();
    if (!live) return;
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load, live]);
  // sahifa chegaradan oshsa, orqaga
  useEffect(() => {
    const pages = Math.max(1, Math.ceil(data.total / size));
    if (page > pages - 1) setPage(pages - 1);
  }, [data.total, size, page]);
  return { items: data.items, total: data.total, page, setPage, size, reload: load };
}

export function Pager({ page, size, total, onPage }) {
  const pages = Math.max(1, Math.ceil(total / size));
  const from = total ? page * size + 1 : 0;
  const to = Math.min(total, (page + 1) * size);
  return (
    <div className="pager">
      <span className="pager-info">{from}–{to} / {total}</span>
      <button disabled={page <= 0} onClick={() => onPage(page - 1)}>‹</button>
      <span className="pager-num">{page + 1} / {pages}</span>
      <button disabled={page >= pages - 1} onClick={() => onPage(page + 1)}>›</button>
    </div>
  );
}

export const SEV = {
  info: { label: "Past", cls: "info" },
  warn: { label: "O'rta", cls: "warn" },
  crit: { label: "Yuqori", cls: "crit" },
};

export const TYPE_LABEL = {
  active_window: "Faol oyna",
  keyboard: "Klaviatura",
  usb: "USB",
  print: "Printer",
  printer: "Printer",
  software: "Dastur",
  screenshot: "Skrinshot",
  clipboard: "Clipboard",
  file_monitor: "Fayl harakati",
  web: "Veb-sayt",
  telegram: "Telegram",
  email: "E-mail",
};

export function timeAgo(iso) {
  const d = (Date.now() - new Date(iso).getTime()) / 1000;
  if (d < 60) return "hozir";
  if (d < 3600) return `${Math.floor(d / 60)} daqiqa`;
  if (d < 86400) return `${Math.floor(d / 3600)} soat`;
  return `${Math.floor(d / 86400)} kun`;
}

export function hhmm(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString("uz", { hour: "2-digit", minute: "2-digit" });
}

export function eventDesc(e) {
  if (e.type === "keyboard" && e.text) return `"${e.text}"`;
  if (e.title) {
    const dur = e.details && e.details.duration_sec;
    return dur ? `${e.title} (${dur}s)` : e.title;
  }
  return [e.app, e.title].filter(Boolean).join(" · ");
}

export function Kpi({ label, value, hint, accent }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className={`kpi-val ${accent || ""}`}>{value}</div>
      {hint && <div className="kpi-hint">{hint}</div>}
    </div>
  );
}

export function Panel({ title, sub, right, children, pad = true }) {
  return (
    <section className="panel">
      {(title || right) && (
        <div className="panel-head">
          <div>
            {title && <h2>{title}</h2>}
            {sub && <div className="sub">{sub}</div>}
          </div>
          {right}
        </div>
      )}
      <div className={pad ? "panel-body" : ""}>{children}</div>
    </section>
  );
}

export function Chip({ sev = "info", children }) {
  const s = SEV[sev] || SEV.info;
  return <span className={`chip ${s.cls}`}>{children || s.label}</span>;
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}
