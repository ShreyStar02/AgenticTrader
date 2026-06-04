import React, { useState } from "react";

export default function FundsModal({ kind, onClose, onSubmit, isCloud }) {
  const [amount, setAmount] = useState("");
  const [password, setPassword] = useState("");
  const isAdd = kind === "add";

  const submit = (e) => {
    e.preventDefault();
    const amt = parseFloat(amount);
    if (!amt || amt <= 0) return;
    onSubmit(kind, amt, password);
  };

  return (
    <div className="modal-bg" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={submit}>
        <h3>{isAdd ? "Add Funds" : "Withdraw Funds"}</h3>
        <div className="field">
          <label>Amount (₹)</label>
          <input
            type="number" min="1" step="1" autoFocus value={amount}
            onChange={(e) => setAmount(e.target.value)} placeholder="e.g. 1000"
          />
        </div>
        <div className="field">
          <label>System password</label>
          <input
            type="password" value={password}
            onChange={(e) => setPassword(e.target.value)} placeholder="Authorize transaction"
          />
        </div>
        <div className="row" style={{ justifyContent: "flex-end", marginTop: 8 }}>
          <button type="button" className="ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className={isAdd ? "" : "danger"}>
            {isAdd ? "Add Funds" : "Withdraw"}
          </button>
        </div>
        <div className="sub" style={{ marginTop: 10 }}>
          Paper money only. Default password: <code>trade123</code> (set via FUNDS_PASSWORD in .env).
        </div>
        {isCloud && (
          <div className="sub note" style={{ marginTop: 10 }}>
            ☁️ Applied via GitHub Actions using your saved key — changes take
            <b> ~1–2 minutes</b> to appear on the dashboard.
          </div>
        )}
      </form>
    </div>
  );
}
