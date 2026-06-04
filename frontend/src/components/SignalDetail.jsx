import React from "react";
import PriceChart from "./PriceChart";

const fmt = (n) =>
  n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const pct = (n) => (n == null ? "—" : (n * 100).toFixed(1) + "%");
const num = (n, d = 2) => (n == null ? "—" : Number(n).toFixed(d));

function Stat({ label, value, cls }) {
  return (
    <div className="card" style={{ padding: 12 }}>
      <h3 style={{ marginBottom: 6 }}>{label}</h3>
      <div className={"stat small " + (cls || "")}>{value}</div>
    </div>
  );
}

export default function SignalDetail({ signal, onBack }) {
  const d = signal.details || {};
  const chart = d.chart;
  const scoreCls = signal.score >= 0 ? "pos" : "neg";

  return (
    <div>
      <div className="row between" style={{ marginBottom: 14, flexWrap: "wrap", gap: 10 }}>
        <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
          <button className="ghost" onClick={onBack}>← Back to signals</button>
          <span className="brand" style={{ fontSize: 22 }}>{signal.symbol}</span>
          {signal.action && <span className={"badge " + signal.action}>{signal.action}</span>}
          {signal.trend && <span className={"badge " + signal.trend}>{signal.trend}</span>}
          {d.sector && <span className="tag">{d.sector}</span>}
        </div>
        <div className="row" style={{ gap: 16 }}>
          <div style={{ textAlign: "right" }}>
            <div className="muted" style={{ fontSize: 11 }}>Last price</div>
            <div className="stat small">{fmt(signal.last_price ?? d.last_price)}</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="muted" style={{ fontSize: 11 }}>Composite</div>
            <div className={"stat small " + scoreCls}>{signal.score.toFixed(2)}</div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3>Price &amp; moving averages (6-month daily)</h3>
        <PriceChart chart={chart} />
      </div>

      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Stat label="Technical" value={num(signal.technical_score)} cls={signal.technical_score >= 0 ? "pos" : "neg"} />
        <Stat label="Sentiment" value={num(signal.sentiment_score)} cls={signal.sentiment_score >= 0 ? "pos" : "neg"} />
        <Stat label="RSI (14)" value={num(d.rsi, 1)} />
        <Stat label="ATR %" value={pct(d.atr_pct)} />
        <Stat label="SMA 20" value={fmt(d.sma20)} />
        <Stat label="SMA 50" value={fmt(d.sma50)} />
        <Stat label="MACD hist" value={num(d.macd_hist, 3)} cls={(d.macd_hist ?? 0) >= 0 ? "pos" : "neg"} />
        <Stat label="News headlines" value={d.news_count ?? 0} />
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3>Why this score</h3>
        <p style={{ lineHeight: 1.6, fontSize: 14, margin: 0 }}>
          {signal.rationale || "No rationale recorded."}
        </p>
        {Array.isArray(d.components) && d.components.length > 0 && (
          <div className="sub" style={{ marginTop: 10 }}>
            Technical components: {d.components.map((c) => c.toFixed(2)).join(" · ")}
          </div>
        )}
        <div className="sub" style={{ marginTop: 6 }}>
          Generated {new Date(signal.created_at + "Z").toLocaleString("en-IN")}
        </div>
      </div>
    </div>
  );
}
