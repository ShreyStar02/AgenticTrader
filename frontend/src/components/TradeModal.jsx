import React, { useState } from "react";

// Manual buy/sell. `kind` is 'buy' | 'sell'. `symbol` may be pre-filled (and
// locked when selling an existing holding). Quantity is whole shares.
export default function TradeModal({ kind, symbol = "", lockSymbol = false, isCloud, onClose, onSubmit }) {
  const [sym, setSym] = useState(symbol);
  const [qty, setQty] = useState("");
  const [password, setPassword] = useState("");
  const isBuy = kind === "buy";

  const submit = (e) => {
    e.preventDefault();
    const q = parseInt(qty, 10);
    const s = sym.trim().toUpperCase();
    if (!s || !q || q <= 0) return;
    onSubmit(kind, s, q, password);
  };

  return (
    <div className="modal-bg" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <h3>{isBuy ? "Buy Stock" : "Sell Stock"}</h3>
        <div className="field">
          <label>NSE symbol</label>
          <input
            type="text" value={sym} disabled={lockSymbol} autoFocus={!lockSymbol}
            onChange={(e) => setSym(e.target.value.toUpperCase())} placeholder="e.g. TCS"
          />
        </div>
        <div className="field">
          <label>Quantity (shares)</label>
          <input
            type="number" min="1" step="1" autoFocus={lockSymbol} value={qty}
            onChange={(e) => setQty(e.target.value)} placeholder="e.g. 5"
          />
        </div>
        <div className="field">
          <label>System password</label>
          <input
            type="password" value={password}
            onChange={(e) => setPassword(e.target.value)} placeholder="Authorize trade"
          />
        </div>
        <div className="row" style={{ justifyContent: "flex-end", marginTop: 8 }}>
          <button type="button" className="ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className={isBuy ? "" : "danger"}>
            {isBuy ? "Buy" : "Sell"}
          </button>
        </div>
        <div className="sub" style={{ marginTop: 10 }}>
          {isBuy
            ? "Filled at the live price with a stop-loss / target from your risk profile. The agent then manages this position autonomously."
            : "Sells at the live price. Paper money only."}{" "}
          Default password: <code>trade123</code>.
        </div>
        {isCloud && (
          <div className="sub note" style={{ marginTop: 10 }}>
            ☁️ Submitted via GitHub Actions using your saved key — takes
            <b> ~1–2 minutes</b> to appear.
          </div>
        )}
      </form>
    </div>
  );
}
