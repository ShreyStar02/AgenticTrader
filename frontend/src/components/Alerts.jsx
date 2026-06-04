import React from "react";

const ago = (iso) => {
  const d = (Date.now() - new Date(iso + "Z").getTime()) / 1000;
  if (d < 60) return "just now";
  if (d < 3600) return Math.floor(d / 60) + "m ago";
  if (d < 86400) return Math.floor(d / 3600) + "h ago";
  return Math.floor(d / 86400) + "d ago";
};

export default function Alerts({ alerts, onRead, full }) {
  return (
    <div className="card">
      <div className="row between">
        <h3 style={{ margin: 0 }}>Alerts &amp; Notifications</h3>
        <button className="ghost" onClick={onRead} style={{ padding: "4px 10px", fontSize: 12 }}>
          Mark all read
        </button>
      </div>
      <div style={{ marginTop: 12, maxHeight: full ? "none" : 380, overflowY: "auto" }}>
        {alerts.length === 0 && <div className="muted" style={{ fontSize: 13 }}>No alerts yet.</div>}
        {alerts.map((a) => (
          <div key={a.id} className={"alert-item " + a.level} style={{ opacity: a.read ? 0.6 : 1 }}>
            <div className="row between">
              <span className="t">{a.title}</span>
              <span className={"badge " + a.category}>{a.category}</span>
            </div>
            {a.message && <div className="m">{a.message}</div>}
            <div className="d">{ago(a.created_at)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
