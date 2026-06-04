// Works in two modes:
//   * Live mode (local dev): talks to the FastAPI backend at /api (Vite proxy).
//   * Static mode (GitHub Pages): reads pre-generated JSON snapshots. Mutations
//     are disabled with a friendly message (use the GitHub Actions workflows).
const STATIC = import.meta.env.VITE_STATIC === "1";
const BASE = "/api";
const DATA = `${import.meta.env.BASE_URL}data/`;

const READ_ONLY_MSG =
  "This is a read-only cloud dashboard. Use the GitHub Actions \u201cmanage\u201d workflow " +
  "(Run workflow) to add/withdraw funds or change settings.";

function staticFileFor(path) {
  const clean = path.split("?")[0];
  const map = {
    "/wallet": "wallet.json",
    "/portfolio": "portfolio.json",
    "/trades": "trades.json",
    "/alerts": "alerts.json",
    "/signals": "signals.json",
    "/runs": "runs.json",
    "/news": "news.json",
    "/settings": "settings.json",
    "/funds/history": "funds_history.json",
    "/watchlist": "watchlist.json",
    "/health": "meta.json",
  };
  return map[clean] || null;
}

async function getStatic(path) {
  const file = staticFileFor(path);
  if (!file) return null;
  const res = await fetch(DATA + file, { cache: "no-store" });
  if (!res.ok) throw new Error(`Snapshot ${file} unavailable`);
  return res.json();
}

async function req(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();

  if (STATIC) {
    if (method !== "GET") throw new Error(READ_ONLY_MSG);
    return getStatic(path);
  }

  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch (e) {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const isStatic = STATIC;

export const api = {
  health: () => req("/health"),
  wallet: () => req("/wallet"),
  addFunds: (amount, password, note) =>
    req("/funds/add", { method: "POST", body: JSON.stringify({ amount, password, note }) }),
  withdrawFunds: (amount, password, note) =>
    req("/funds/withdraw", { method: "POST", body: JSON.stringify({ amount, password, note }) }),
  fundsHistory: () => req("/funds/history"),
  portfolio: () => req("/portfolio"),
  trades: () => req("/trades"),
  alerts: (unreadOnly = false) => req(`/alerts?unread_only=${unreadOnly}`),
  readAllAlerts: () => req("/alerts/read-all", { method: "POST" }),
  signals: (limit = 50) => req(`/signals?limit=${limit}`),
  runs: (limit = 20) => req(`/runs?limit=${limit}`),
  runNow: () => req("/agent/run-now", { method: "POST" }),
  news: () => req("/news"),
  settings: () => req("/settings"),
  setRisk: (risk_profile) =>
    req("/settings/risk", { method: "PUT", body: JSON.stringify({ risk_profile }) }),
  setAutonomous: (enabled) =>
    req("/settings/autonomous", { method: "PUT", body: JSON.stringify({ enabled }) }),
  research: (symbol) =>
    req("/research", { method: "POST", body: JSON.stringify({ symbol }) }),
  watchlist: () => req("/watchlist"),
  watchlistAdd: (symbol) =>
    req("/watchlist/add", { method: "POST", body: JSON.stringify({ symbol }) }),
  watchlistRemove: (symbol) =>
    req("/watchlist/remove", { method: "POST", body: JSON.stringify({ symbol }) }),
  buyStock: (symbol, qty, password) =>
    req("/trade/buy", { method: "POST", body: JSON.stringify({ symbol, qty, password }) }),
  sellStock: (symbol, qty, password) =>
    req("/trade/sell", { method: "POST", body: JSON.stringify({ symbol, qty, password }) }),
};
