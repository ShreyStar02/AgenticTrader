import React, { useMemo, useState, useCallback } from "react";
import { AgGridReact } from "ag-grid-react";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

const fmtMoney = (n) =>
  n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const fmtTime = (iso) =>
  iso ? new Date(iso + "Z").toLocaleString("en-IN", { dateStyle: "short", timeStyle: "short" }) : "—";

function BadgeCell({ value }) {
  if (!value) return "—";
  return <span className={"badge " + value}>{value}</span>;
}

function ScoreCell({ value }) {
  const score = Number(value || 0);
  const pct = Math.min(100, Math.abs(score) * 100);
  const color = score >= 0 ? "var(--green)" : "var(--red)";
  const left = score >= 0 ? "50%" : `${50 - pct / 2}%`;
  return (
    <div className="scorebar" title={score.toFixed(3)} style={{ marginTop: 14 }}>
      <div style={{ left, width: `${pct / 2}%`, background: color }} />
      <div style={{ left: "50%", width: 1, background: "var(--muted)" }} />
    </div>
  );
}

export default function Signals({ signals, onSelect }) {
  const [quick, setQuick] = useState("");

  const columnDefs = useMemo(
    () => [
      { headerName: "Symbol", field: "symbol", minWidth: 120,
        cellRenderer: (p) => <b>{p.value}</b>, filter: "agTextColumnFilter", pinned: "left" },
      { headerName: "Action", field: "action", minWidth: 110, cellRenderer: BadgeCell },
      { headerName: "Trend", field: "trend", minWidth: 120, cellRenderer: BadgeCell },
      { headerName: "LTP", field: "last_price", minWidth: 110, type: "rightAligned",
        filter: "agNumberColumnFilter", valueFormatter: (p) => fmtMoney(p.value) },
      { headerName: "Composite", field: "score", colId: "composite", minWidth: 120,
        type: "rightAligned", sort: "desc", filter: "agNumberColumnFilter",
        valueFormatter: (p) => Number(p.value).toFixed(2),
        cellClass: (p) => (p.value >= 0 ? "ag-pos" : "ag-neg") },
      { headerName: "Score", field: "score", colId: "scorebar", minWidth: 120,
        sortable: false, filter: false, cellRenderer: ScoreCell },
      { headerName: "Tech", field: "technical_score", minWidth: 100, type: "rightAligned",
        filter: "agNumberColumnFilter", valueFormatter: (p) => Number(p.value).toFixed(2) },
      { headerName: "Sentiment", field: "sentiment_score", minWidth: 110, type: "rightAligned",
        filter: "agNumberColumnFilter", valueFormatter: (p) => Number(p.value).toFixed(2) },
      { headerName: "Time", field: "created_at", minWidth: 150,
        filter: "agTextColumnFilter", valueFormatter: (p) => fmtTime(p.value) },
      { headerName: "Rationale", field: "rationale", minWidth: 280, flex: 2,
        filter: "agTextColumnFilter", tooltipField: "rationale",
        cellStyle: { fontSize: "11px", color: "var(--muted)", whiteSpace: "normal", lineHeight: 1.35 } },
    ],
    []
  );

  const defaultColDef = useMemo(
    () => ({ sortable: true, filter: true, resizable: true, flex: 1, minWidth: 90 }),
    []
  );

  const onRowClicked = useCallback((e) => onSelect && onSelect(e.data), [onSelect]);

  return (
    <div className="card">
      <div className="row between" style={{ flexWrap: "wrap", gap: 10, marginBottom: 10 }}>
        <h3 style={{ margin: 0 }}>
          Agent Signals ({signals.length}) · tap a row for charts &amp; details
        </h3>
        <input
          type="text" value={quick} onChange={(e) => setQuick(e.target.value)}
          placeholder="🔍 Quick filter…" style={{ maxWidth: 240 }}
        />
      </div>
      <div className="ag-theme-quartz-dark grid-wrap" style={{ width: "100%" }}>
        <AgGridReact
          rowData={signals}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          quickFilterText={quick}
          rowHeight={44}
          onRowClicked={onRowClicked}
          pagination
          paginationPageSize={20}
          paginationPageSizeSelector={[10, 20, 50, 100]}
          tooltipShowDelay={300}
          domLayout="autoHeight"
          getRowId={(p) => String(p.data.id)}
          rowClass="clickable"
        />
      </div>
    </div>
  );
}
