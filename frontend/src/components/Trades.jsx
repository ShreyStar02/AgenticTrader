import React from "react";

const fmt = (n) => "₹" + (n ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const dts = (iso) => new Date(iso + "Z").toLocaleString("en-IN");

export default function Trades({ trades }) {
  return (
    <div className="card">
      <h3>Trade History ({trades.length})</h3>
      {trades.length === 0 ? (
        <div className="muted" style={{ fontSize: 13 }}>No trades executed yet.</div>
      ) : (
        <table>
          <thead>
            <tr><th>Time</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th><th>Fees</th><th>Realized P&amp;L</th></tr>
          </thead>
          <tbody>
            {trades.map((t) => (
              <tr key={t.id}>
                <td className="muted">{dts(t.created_at)}</td>
                <td><b>{t.symbol}</b></td>
                <td><span className={"badge " + t.side}>{t.side}</span></td>
                <td>{t.qty}</td>
                <td>{fmt(t.price)}</td>
                <td className="muted">{fmt(t.fees)}</td>
                <td className={t.realized_pnl >= 0 ? "pos" : "neg"}>
                  {t.side === "SELL" ? (t.realized_pnl >= 0 ? "+" : "") + fmt(t.realized_pnl) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
