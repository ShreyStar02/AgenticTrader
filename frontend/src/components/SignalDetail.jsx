import React, { useState } from "react";
import PriceChart from "./PriceChart";

const fmt = (n) =>
  n == null ? "—" : "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const pct = (n) => (n == null ? "—" : (n * 100).toFixed(1) + "%");
const num = (n, d = 2) => (n == null ? "—" : Number(n).toFixed(d));

function Stat({ label, value, cls, info }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="card" style={{ padding: 12 }}>
      <div className="stat-head">
        <h3 style={{ marginBottom: 6 }}>{label}</h3>
        {info && (
          <button
            type="button"
            className="info-btn"
            aria-label={`What is ${label}?`}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
            onBlur={() => setOpen(false)}
          >
            i
          </button>
        )}
        {info && <div className={"info-pop " + (open ? "show" : "")}>{info}</div>}
      </div>
      <div className={"stat small " + (cls || "")}>{value}</div>
    </div>
  );
}

export default function SignalDetail({ signal, onBack, onBuy, onWatch }) {
  const d = signal.details || {};
  const chart = d.chart;
  const scoreCls = signal.score >= 0 ? "pos" : "neg";
  const metricInfo = {
    technical: "Technical score combines trend and momentum indicators. Higher positive values suggest stronger bullish setup.",
    sentiment: "Sentiment score comes from recent news tone. Positive means headlines are more favorable; negative means more cautious tone.",
    rsi: "RSI (14) measures momentum from 0 to 100. Above 70 can indicate overbought, below 30 can indicate oversold.",
    atr: "ATR % is daily volatility as a percentage of price. Higher values mean larger typical price swings.",
    sma20: "SMA 20 is the 20-day average close price, often used for short-term trend direction.",
    sma50: "SMA 50 is the 50-day average close price, commonly used to track medium-term trend strength.",
    macd: "MACD histogram shows momentum acceleration. Positive values suggest bullish momentum, negative values suggest bearish momentum.",
    newsCount: "Number of recent news headlines considered by the sentiment model for this symbol.",
  };

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

      {(onBuy || onWatch) && (
        <div className="row" style={{ gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
          {onBuy && <button onClick={() => onBuy(signal.symbol)}>Buy {signal.symbol}</button>}
          {onWatch && (
            <button className="ghost" onClick={() => onWatch(signal.symbol)}>
              + Add to watchlist
            </button>
          )}
        </div>
      )}

      <div className="card" style={{ marginBottom: 16 }}>
        <h3>Price &amp; moving averages (6-month daily)</h3>
        <PriceChart chart={chart} />
      </div>

      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <Stat label="Technical" value={num(signal.technical_score)} cls={signal.technical_score >= 0 ? "pos" : "neg"} info={metricInfo.technical} />
        <Stat label="Sentiment" value={num(signal.sentiment_score)} cls={signal.sentiment_score >= 0 ? "pos" : "neg"} info={metricInfo.sentiment} />
        <Stat label="RSI (14)" value={num(d.rsi, 1)} info={metricInfo.rsi} />
        <Stat label="ATR %" value={pct(d.atr_pct)} info={metricInfo.atr} />
        <Stat label="SMA 20" value={fmt(d.sma20)} info={metricInfo.sma20} />
        <Stat label="SMA 50" value={fmt(d.sma50)} info={metricInfo.sma50} />
        <Stat label="MACD hist" value={num(d.macd_hist, 3)} cls={(d.macd_hist ?? 0) >= 0 ? "pos" : "neg"} info={metricInfo.macd} />
        <Stat label="News headlines" value={d.news_count ?? 0} info={metricInfo.newsCount} />
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
