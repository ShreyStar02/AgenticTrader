import React from "react";

const fmt = (n) => "₹" + (n ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });

export default function StatCards({ portfolio, wallet }) {
  const p = portfolio || {};
  const pnl = (p.unrealized_pnl ?? 0) + (p.realized_pnl ?? 0);
  const pnlClass = pnl >= 0 ? "pos" : "neg";
  return (
    <div className="grid cols-4" style={{ marginBottom: 16 }}>
      <div className="card">
        <h3>Equity</h3>
        <div className="stat">{fmt(p.equity)}</div>
        <div className="sub">Cash + holdings</div>
      </div>
      <div className="card">
        <h3>Cash</h3>
        <div className="stat">{fmt(wallet?.cash ?? p.cash)}</div>
        <div className="sub">Available to invest</div>
      </div>
      <div className="card">
        <h3>Invested</h3>
        <div className="stat small">{fmt(p.market_value)}</div>
        <div className="sub">Cost {fmt(p.invested)}</div>
      </div>
      <div className="card">
        <h3>Total P&amp;L</h3>
        <div className={"stat " + pnlClass}>{pnl >= 0 ? "+" : ""}{fmt(pnl)}</div>
        <div className="sub">
          Unreal {fmt(p.unrealized_pnl)} · Real {fmt(p.realized_pnl)}
        </div>
      </div>
    </div>
  );
}
