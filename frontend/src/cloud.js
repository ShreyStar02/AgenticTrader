// Cloud management for the static (GitHub Pages) dashboard.
//
// The static site has no backend, so write operations (add/withdraw funds,
// change settings, run the agent) are performed by triggering the repo's
// existing GitHub Actions workflows via the REST API's workflow_dispatch
// endpoint. Authentication uses a personal access token the user stores once
// in their own browser (localStorage) — it is never committed or sent anywhere
// except api.github.com.

const REPO_ENV = import.meta.env.VITE_REPO; // optional "owner/repo" override
const TOKEN_KEY = "at_gh_token";

// Derive "owner/repo" from the GitHub Pages URL: https://<owner>.github.io/<repo>/
export function repoSlug() {
  if (REPO_ENV && REPO_ENV.includes("/")) return REPO_ENV;
  try {
    const host = window.location.hostname; // <owner>.github.io
    const owner = host.split(".")[0];
    const seg = window.location.pathname.split("/").filter(Boolean)[0] || "";
    if (owner && seg) return `${owner}/${seg}`;
  } catch (e) {
    /* ignore */
  }
  return null;
}

export const getToken = () => (localStorage.getItem(TOKEN_KEY) || "").trim();
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, (t || "").trim());
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);
export const hasToken = () => !!getToken();

async function dispatch(workflowFile, inputs) {
  const slug = repoSlug();
  if (!slug) throw new Error("Could not determine the repository from the page URL.");
  const token = getToken();
  if (!token) throw new Error("NO_TOKEN");

  const url = `https://api.github.com/repos/${slug}/actions/workflows/${workflowFile}/dispatches`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({ ref: "main", inputs }),
  });

  if (res.status === 204) return true;

  let detail = `${res.status} ${res.statusText}`;
  try {
    const body = await res.json();
    if (body && body.message) detail = body.message;
  } catch (e) {
    /* ignore */
  }
  if (res.status === 401 || res.status === 403) throw new Error("BAD_TOKEN: " + detail);
  throw new Error(detail);
}

export const cloud = {
  repoSlug,
  hasToken,
  addFunds: (amount, password) =>
    dispatch("manage.yml", { operation: "add-funds", amount: String(amount), password: password || "" }),
  withdrawFunds: (amount, password) =>
    dispatch("manage.yml", { operation: "withdraw-funds", amount: String(amount), password: password || "" }),
  setRisk: (value) => dispatch("manage.yml", { operation: "set-risk", value }),
  setAutonomous: (value) => dispatch("manage.yml", { operation: "set-autonomous", value: String(value) }),
  runAgent: () => dispatch("trade.yml", { force: "true" }),
  research: (symbol) =>
    dispatch("manage.yml", { operation: "research", symbol: String(symbol).toUpperCase() }),
  watchlistAdd: (symbol) =>
    dispatch("manage.yml", { operation: "watchlist-add", symbol: String(symbol).toUpperCase() }),
  watchlistRemove: (symbol) =>
    dispatch("manage.yml", { operation: "watchlist-remove", symbol: String(symbol).toUpperCase() }),
  buy: (symbol, qty, password) =>
    dispatch("manage.yml", {
      operation: "buy", symbol: String(symbol).toUpperCase(),
      amount: String(qty), password: password || "",
    }),
  sell: (symbol, qty, password) =>
    dispatch("manage.yml", {
      operation: "sell", symbol: String(symbol).toUpperCase(),
      amount: String(qty), password: password || "",
    }),
};
