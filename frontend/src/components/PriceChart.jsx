import React, { useMemo, useState } from "react";

// Dependency-free SVG chart: close price + SMA20 + SMA50 with a volume strip.
// `chart` shape: { dates:[], close:[], sma20:[], sma50:[], volume:[] }.
export default function PriceChart({ chart }) {
  const [hover, setHover] = useState(null);

  const W = 720;
  const H = 300;
  const PAD = { l: 52, r: 16, t: 14, b: 64 };
  const volH = 46;

  const model = useMemo(() => {
    if (!chart || !Array.isArray(chart.close) || chart.close.length < 2) return null;
    const n = chart.close.length;
    const dates = chart.dates || [];
    const series = ["close", "sma20", "sma50"];

    let min = Infinity;
    let max = -Infinity;
    for (const k of series) {
      for (const v of chart[k] || []) {
        if (v == null) continue;
        if (v < min) min = v;
        if (v > max) max = v;
      }
    }
    if (!isFinite(min) || !isFinite(max)) return null;
    const span = max - min || 1;
    min -= span * 0.05;
    max += span * 0.05;

    const plotW = W - PAD.l - PAD.r;
    const plotH = H - PAD.t - PAD.b;
    const x = (i) => PAD.l + (n === 1 ? 0 : (i / (n - 1)) * plotW);
    const y = (v) => PAD.t + plotH - ((v - min) / (max - min)) * plotH;

    const path = (key) => {
      let d = "";
      let started = false;
      (chart[key] || []).forEach((v, i) => {
        if (v == null) {
          started = false;
          return;
        }
        d += `${started ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)} `;
        started = true;
      });
      return d.trim();
    };

    const vols = chart.volume || [];
    const vmax = Math.max(1, ...vols.filter((v) => v != null));
    const volBase = H - PAD.b + 16 + volH;
    const volBar = (i) => {
      const v = vols[i];
      if (v == null) return null;
      const h = (v / vmax) * volH;
      return { x: x(i) - 1, y: volBase - h, h };
    };

    const yTicks = [];
    for (let t = 0; t <= 4; t++) {
      const val = min + ((max - min) * t) / 4;
      yTicks.push({ val, y: y(val) });
    }

    const xTickIdx = [0, Math.floor((n - 1) / 2), n - 1];

    return { n, dates, x, y, path, volBar, yTicks, xTickIdx, plotW };
  }, [chart]);

  if (!model) {
    return (
      <div className="muted" style={{ fontSize: 13, padding: "20px 0" }}>
        Price chart will be available after the next scan captures history for this symbol.
      </div>
    );
  }

  const fmt = (v) =>
    v == null ? "—" : "₹" + v.toLocaleString("en-IN", { maximumFractionDigits: 2 });

  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const i = Math.round(((px - PAD.l) / model.plotW) * (model.n - 1));
    if (i >= 0 && i < model.n) setHover(i);
  };

  const lines = [
    { key: "close", color: "var(--accent)", label: "Close" },
    { key: "sma20", color: "var(--amber)", label: "SMA20" },
    { key: "sma50", color: "var(--green)", label: "SMA50" },
  ];

  return (
    <div>
      <div className="row" style={{ gap: 16, marginBottom: 6, flexWrap: "wrap" }}>
        {lines.map((l) => (
          <span key={l.key} className="row" style={{ gap: 6, fontSize: 12 }}>
            <span style={{ width: 14, height: 3, background: l.color, borderRadius: 2 }} />
            <span className="muted">{l.label}</span>
            {hover != null && (
              <span style={{ color: l.color }}>{fmt(chart[l.key]?.[hover])}</span>
            )}
          </span>
        ))}
        {hover != null && (
          <span className="muted" style={{ fontSize: 12 }}>
            {model.dates[hover]}
          </span>
        )}
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        style={{ display: "block", touchAction: "none" }}
      >
        {model.yTicks.map((t, i) => (
          <g key={i}>
            <line
              x1={PAD.l}
              x2={W - PAD.r}
              y1={t.y}
              y2={t.y}
              stroke="var(--border)"
              strokeWidth="1"
            />
            <text x={PAD.l - 8} y={t.y + 4} textAnchor="end" fontSize="10" fill="var(--muted)">
              {t.val.toFixed(0)}
            </text>
          </g>
        ))}

        {(chart.volume || []).map((v, i) => {
          const b = model.volBar(i);
          return b ? (
            <rect key={i} x={b.x} y={b.y} width="2" height={b.h} fill="var(--border)" />
          ) : null;
        })}

        {lines.map((l) => (
          <path
            key={l.key}
            d={model.path(l.key)}
            fill="none"
            stroke={l.color}
            strokeWidth={l.key === "close" ? 1.8 : 1.2}
            opacity={l.key === "close" ? 1 : 0.85}
          />
        ))}

        {model.xTickIdx.map((i) => (
          <text
            key={i}
            x={model.x(i)}
            y={H - PAD.b + 14}
            textAnchor={i === 0 ? "start" : i === model.n - 1 ? "end" : "middle"}
            fontSize="10"
            fill="var(--muted)"
          >
            {model.dates[i]}
          </text>
        ))}

        {hover != null && (
          <line
            x1={model.x(hover)}
            x2={model.x(hover)}
            y1={PAD.t}
            y2={H - PAD.b}
            stroke="var(--muted)"
            strokeWidth="1"
            strokeDasharray="3 3"
          />
        )}
      </svg>
    </div>
  );
}
