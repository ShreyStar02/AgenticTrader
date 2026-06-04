import React from "react";

function ScoreBar({ score }) {
  const pct = Math.min(100, Math.abs(score) * 100);
  const color = score >= 0 ? "var(--green)" : "var(--red)";
  const left = score >= 0 ? "50%" : `${50 - pct / 2}%`;
  return (
    <div className="scorebar" title={score.toFixed(3)}>
      <div style={{ left, width: `${pct / 2}%`, background: color }} />
      <div style={{ left: "50%", width: 1, background: "var(--muted)" }} />
    </div>
  );
}

export default function Signals({ signals }) {
  return (
    <div className="card">
      <h3>Agent Signals — latest scan ({signals.length})</h3>
      <table>
        <thead>
          <tr>
            <th>Symbol</th><th>Action</th><th>Trend</th>
            <th>Composite</th><th style={{ width: 120 }}>Score</th>
            <th>Tech</th><th>Sentiment</th><th>Rationale</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((s) => (
            <tr key={s.id}>
              <td><b>{s.symbol}</b></td>
              <td><span className={"badge " + s.action}>{s.action}</span></td>
              <td><span className={"badge " + s.trend}>{s.trend}</span></td>
              <td className={s.score >= 0 ? "pos" : "neg"}>{s.score.toFixed(2)}</td>
              <td><ScoreBar score={s.score} /></td>
              <td className="muted">{s.technical_score.toFixed(2)}</td>
              <td className="muted">{s.sentiment_score.toFixed(2)}</td>
              <td className="muted" style={{ fontSize: 11, maxWidth: 320 }}>{s.rationale}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
