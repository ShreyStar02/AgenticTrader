import React, { useState } from "react";

// Watchlist tab: research a symbol on demand, add/remove symbols the agent
// should always evaluate, and jump into a symbol's detail/research view.
export default function Watchlist({
  symbols = [], busy, isCloud, onResearch, onAdd, onRemove,
}) {
  const [input, setInput] = useState("");

  const research = (e) => {
    e.preventDefault();
    const s = input.trim().toUpperCase();
    if (s) onResearch(s);
  };

  return (
    <div>
      <div className="card" style={{ marginBottom: 14 }}>
        <h3>Research a stock</h3>
        <form className="row" style={{ gap: 8, flexWrap: "wrap" }} onSubmit={research}>
          <input
            className="grow" type="text" value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            placeholder="Enter an NSE symbol, e.g. TCS, INFY, RELIANCE"
          />
          <button type="submit" disabled={busy}>{busy ? "Researching…" : "Research"}</button>
          <button
            type="button" className="ghost" disabled={busy || !input.trim()}
            onClick={() => onAdd(input.trim().toUpperCase())}
          >
            + Add to watchlist
          </button>
        </form>
        <div className="sub" style={{ marginTop: 8 }}>
          The agents analyze technicals and news for the symbol.{" "}
          {isCloud
            ? "Research runs via GitHub Actions (~1–2 min); the result then appears in Signals."
            : "The result opens automatically with a full chart and rationale."}
        </div>
      </div>

      <div className="card">
        <h3>Watchlist ({symbols.length})</h3>
        {symbols.length === 0 ? (
          <div className="muted" style={{ fontSize: 13 }}>
            No watchlisted symbols yet. Add one above and the agent will always
            evaluate it — and you'll get signals for it.
          </div>
        ) : (
          <table>
            <thead>
              <tr><th>Symbol</th><th style={{ textAlign: "right" }}>Actions</th></tr>
            </thead>
            <tbody>
              {symbols.map((s) => (
                <tr key={s}>
                  <td><b>{s}</b></td>
                  <td style={{ textAlign: "right" }}>
                    <button className="ghost sm" disabled={busy} onClick={() => onResearch(s)}>
                      Research
                    </button>{" "}
                    <button className="ghost sm danger" disabled={busy} onClick={() => onRemove(s)}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
