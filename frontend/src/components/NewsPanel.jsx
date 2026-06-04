import React from "react";

const sentBadge = (s) => (s > 0.15 ? "BUY" : s < -0.15 ? "SELL" : "HOLD");

export default function NewsPanel({ news, onRefresh }) {
  return (
    <div className="card">
      <div className="row between">
        <h3 style={{ margin: 0 }}>Market News &amp; Sentiment ({news.length})</h3>
        <button className="ghost" onClick={onRefresh} style={{ padding: "4px 10px", fontSize: 12 }}>
          Refresh
        </button>
      </div>
      <div style={{ marginTop: 12 }}>
        {news.length === 0 && <div className="muted" style={{ fontSize: 13 }}>Loading headlines…</div>}
        {news.map((n, i) => (
          <div key={i} className="alert-item info">
            <div className="row between">
              <a href={n.link} target="_blank" rel="noreferrer"
                 style={{ color: "var(--text)", textDecoration: "none", fontSize: 13, fontWeight: 600 }}>
                {n.title}
              </a>
              <span className={"badge " + sentBadge(n.sentiment)} style={{ marginLeft: 8 }}>
                {n.sentiment >= 0 ? "+" : ""}{n.sentiment.toFixed(2)}
              </span>
            </div>
            <div className="d">{n.source}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
