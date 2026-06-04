import React from "react";

export default function Briefing({ run }) {
  return (
    <div className="card" style={{ marginBottom: 16, borderLeft: "3px solid var(--accent)" }}>
      <div className="row between">
        <h3 style={{ margin: 0 }}>🧠 AI Market Briefing</h3>
        <span className={"badge " + (run.regime || "info")}>{run.regime || "—"}</span>
      </div>
      <p style={{ margin: "12px 0 6px", lineHeight: 1.6, fontSize: 14 }}>
        {run.briefing || run.summary || "No briefing available."}
      </p>
      <div className="sub">
        Scanned {run.candidates_scanned} · {run.actions_taken} action(s) ·{" "}
        {run.finished_at ? new Date(run.finished_at + "Z").toLocaleString("en-IN") : "running…"}
      </div>
    </div>
  );
}
