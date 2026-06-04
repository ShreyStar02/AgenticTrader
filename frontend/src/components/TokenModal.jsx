import React, { useState } from "react";
import { getToken, setToken, clearToken, repoSlug } from "../cloud";

export default function TokenModal({ onClose, onSaved }) {
  const [token, setTok] = useState(getToken());
  const slug = repoSlug() || "your repo";

  const save = (e) => {
    e.preventDefault();
    const t = token.trim();
    if (!t) return;
    setToken(t);
    onSaved && onSaved(t);
  };

  const remove = () => {
    clearToken();
    setTok("");
    onSaved && onSaved("");
    onClose();
  };

  return (
    <div className="modal-bg" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
        <h3>Connect your GitHub key</h3>
        <p className="sub" style={{ marginTop: 0 }}>
          To add/withdraw funds and change settings from this cloud dashboard, the
          UI triggers the <code>manage</code> / <code>trade</code> GitHub Actions
          workflows in <b>{slug}</b>. Paste a personal access token below — it is
          stored only in <b>this browser</b> and sent only to api.github.com.
        </p>
        <div className="field">
          <label>GitHub personal access token</label>
          <input
            type="password"
            autoFocus
            value={token}
            onChange={(e) => setTok(e.target.value)}
            placeholder="ghp_… or github_pat_…"
          />
        </div>
        <div className="sub">
          Create one at{" "}
          <a
            href="https://github.com/settings/personal-access-tokens/new"
            target="_blank"
            rel="noreferrer"
          >
            github.com/settings → fine-grained tokens
          </a>
          . Give it access to this repo with <b>Actions: Read and write</b> (a
          classic token with the <code>repo</code> + <code>workflow</code> scopes
          also works).
        </div>
        <div className="row" style={{ justifyContent: "space-between", marginTop: 14 }}>
          <button type="button" className="ghost danger" onClick={remove}>
            Remove key
          </button>
          <div className="row">
            <button type="button" className="ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit">Save</button>
          </div>
        </div>
      </form>
    </div>
  );
}
