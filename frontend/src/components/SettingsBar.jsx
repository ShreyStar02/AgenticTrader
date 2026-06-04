import React from "react";

export default function SettingsBar({ settings, onRisk, onAutonomous, cloud }) {
  return (
    <div className="card" style={{ marginBottom: 16, padding: "12px 16px" }}>
      <div className="row between">
        <div className="row" style={{ gap: 16 }}>
          <div className="row">
            <span className="muted" style={{ fontSize: 13 }}>Risk profile:</span>
            <select value={settings.risk_profile} onChange={(e) => onRisk(e.target.value)}>
              <option value="conservative">Conservative</option>
              <option value="moderate">Moderate</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </div>
          <div className="row">
            <span className="muted" style={{ fontSize: 13 }}>Autonomous:</span>
            <button
              className={settings.autonomous_enabled ? "" : "ghost"}
              onClick={() => onAutonomous(!settings.autonomous_enabled)}
              style={{ padding: "6px 14px" }}
            >
              {settings.autonomous_enabled ? "● Enabled" : "○ Paused"}
            </button>
          </div>
        </div>
        <div className="row" style={{ gap: 12 }}>
          {cloud && (
            <button
              className="ghost"
              onClick={cloud.onKey}
              style={{ padding: "6px 12px" }}
              title="Manage the GitHub key used to control the cloud agent"
            >
              {cloud.hasKey ? "🔑 Key set" : "🔑 Connect key"}
            </button>
          )}
          <div className="muted" style={{ fontSize: 12 }}>
            Auto-scan every {settings.scan_interval_minutes} min
          </div>
        </div>
      </div>
    </div>
  );
}
