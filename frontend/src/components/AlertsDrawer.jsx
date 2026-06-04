import React from "react";

const ago = (iso) => {
  const d = (Date.now() - new Date(iso + "Z").getTime()) / 1000;
  if (d < 60) return "just now";
  if (d < 3600) return Math.floor(d / 60) + "m ago";
  if (d < 86400) return Math.floor(d / 3600) + "h ago";
  return Math.floor(d / 86400) + "d ago";
};

// Precedence: info < success < warning < danger  (blue < green < yellow < red)
const LEVEL_RANK = { info: 0, success: 1, warning: 2, danger: 3 };
const LEVEL_COLOR = {
  info: "var(--accent)",
  success: "var(--green)",
  warning: "var(--amber)",
  danger: "var(--red)",
};

export function badgeColorFor(alerts) {
  let top = -1;
  for (const a of alerts) {
    const r = LEVEL_RANK[a.level] ?? 0;
    if (r > top) top = r;
  }
  const name = Object.keys(LEVEL_RANK).find((k) => LEVEL_RANK[k] === top) || "info";
  return LEVEL_COLOR[name];
}

export default function AlertsDrawer({ open, alerts, unread, onClose, onRead }) {
  return (
    <>
      <div className={"drawer-overlay" + (open ? " show" : "")} onClick={onClose} />
      <aside className={"drawer" + (open ? " open" : "")} role="dialog" aria-label="Alerts">
        <div className="drawer-head">
          <h3 style={{ margin: 0 }}>Alerts &amp; Notifications</h3>
          <div className="row" style={{ gap: 8 }}>
            <button
              className="ghost"
              onClick={onRead}
              disabled={unread === 0}
              style={{ padding: "4px 10px", fontSize: 12 }}
            >
              Mark all read
            </button>
            <button className="ghost" onClick={onClose} style={{ padding: "4px 10px" }}>✕</button>
          </div>
        </div>
        <div className="drawer-body">
          {alerts.length === 0 && (
            <div className="muted" style={{ fontSize: 13 }}>No alerts yet.</div>
          )}
          {alerts.map((a) => (
            <div key={a.id} className={"alert-item " + a.level} style={{ opacity: a.read ? 0.55 : 1 }}>
              <div className="row between">
                <span className="t">{a.title}</span>
                <span className={"badge " + a.category}>{a.category}</span>
              </div>
              {a.message && <div className="m">{a.message}</div>}
              <div className="d">{ago(a.created_at)}</div>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}
