import React from "react";

const fmt = (n) => "₹" + (n ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });

export default function Holdings({ portfolio, onBuy, onSell }) {
  const holdings = portfolio?.holdings || [];
  const actions = !!(onBuy || onSell);
  return (
    <div className="card">
      <h3>Holdings ({holdings.length})</h3>
      {holdings.length === 0 ? (
        <div className="muted" style={{ fontSize: 13 }}>
          No open positions. The agent holds cash until a setup matches your risk profile.
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Symbol</th><th>Qty</th><th>Avg</th><th>LTP</th>
              <th>Value</th><th>P&amp;L</th><th>SL / TP</th>
              {actions && <th style={{ textAlign: "right" }}>Trade</th>}
            </tr>
          </thead>
          <tbody>
            {holdings.map((h) => (
              <tr key={h.symbol}>
                <td>
                  <b>{h.symbol}</b>
                  {h.side === "SHORT" && (
                    <span className="sub" style={{ color: "#e0708a" }}> SHORT</span>
                  )}
                </td>
                <td>{h.qty}</td>
                <td>{fmt(h.avg_price)}</td>
                <td>{fmt(h.last_price)}</td>
                <td>{fmt(h.market_value)}</td>
                <td className={h.unrealized_pnl >= 0 ? "pos" : "neg"}>
                  {h.unrealized_pnl >= 0 ? "+" : ""}{fmt(h.unrealized_pnl)}
                  <span className="sub"> ({h.unrealized_pct}%)</span>
                </td>
                <td className="muted">
                  {h.stop_loss ? fmt(h.stop_loss) : "—"} / {h.take_profit ? fmt(h.take_profit) : "—"}
                </td>
                {actions && (
                  <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                    {onBuy && (
                      <button className="ghost sm" onClick={() => onBuy(h.symbol)}>Buy</button>
                    )}{" "}
                    {onSell && (
                      <button className="ghost sm danger" onClick={() => onSell(h.symbol)}>Sell</button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
