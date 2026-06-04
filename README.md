# AgenticTrader 🤖📈

An **autonomous, multi-agent paper-trading platform for the Indian stock market (NSE)**.
Multiple cooperating agents understand the market, score stocks on technicals + news
sentiment + market regime, and autonomously place **paper** (fake-money) trades under a
strict risk manager. Real market & news data; **no paid APIs**. Real broker/Demat
integration is intentionally deferred until paper results are trustworthy.

> ⚠️ Paper trading only. No real orders are placed. Educational use.

---

## What it does

1. You **Add Funds** (fake money) with a system password.
2. You pick a **risk profile** (Conservative / Moderate / Aggressive).
3. A scheduler runs the **autonomous agent loop** every N minutes (and on demand):
   fetch data → analyze → decide → **risk-check** → paper-trade → alert → log.
4. The web dashboard shows equity, P&L, holdings, signals, trades, alerts, news,
   and an **AI market briefing**.

## Agents

| Agent | Role |
|-------|------|
| **MarketData** | OHLCV from Yahoo (curl_cffi client), NSE constituents via `nselib`, India VIX |
| **Technical** | SMA/RSI/MACD/ATR → trend + momentum + volatility score |
| **News/Sentiment** | Free RSS (Google News + Moneycontrol) → lexicon sentiment |
| **Regime** | NIFTY trend + VIX → bullish/bearish/volatile/sideways + risk-on flag |
| **Strategy** | Fuses technical + sentiment + regime into a composite score |
| **RiskManager** | Mandatory gate: sizing, stop-loss/take-profit, alloc caps, whole-share, cash buffer |
| **PaperBroker** | Simulated fills with slippage + brokerage, positions, P&L |
| **Analyst (LLM)** | Natural-language briefing — explainability only, never gates trades |
| **Supervisor** | Orchestrates the whole loop and records every decision |

## Zero-cost data sources

- **Prices / indices / VIX:** Yahoo Finance chart API (free)
- **NSE constituents / market activity:** `nselib` (free)
- **News:** Google News RSS + Moneycontrol RSS via `feedparser` (free)
- **LLM:** pluggable — NVIDIA NIM / HuggingFace / OpenAI-compatible (your key in `.env`)

---

## Tech stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite, APScheduler
- **Frontend:** React + Vite
- **Data/Analytics:** pandas, `ta`, `nselib`, `feedparser`, `curl_cffi`

---

## Setup

### 1. Backend

```powershell
cd backend
py -m venv .venv                      # or: python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env           # then edit .env (set FUNDS_PASSWORD, LLM keys)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Backend runs at http://127.0.0.1:8000 (API docs at `/docs`).

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (the dev server proxies `/api` → backend).

---

## Run it 24/7 for free (GitHub Actions)

Don't want to keep your PC on? Deploy the agent to **GitHub Actions** (free, no
credit card, personal GitHub account). It runs every 15 min during NSE market
hours and publishes a live read-only dashboard to **GitHub Pages**.
See **[DEPLOY_GITHUB_ACTIONS.md](DEPLOY_GITHUB_ACTIONS.md)** for the 10-minute setup.

---

## Configuration (`backend/.env`)

| Variable | Purpose |
|----------|---------|
| `FUNDS_PASSWORD` | Password to authorize add/withdraw funds (default `trade123`) |
| `SCAN_INTERVAL_MINUTES` | Autonomous loop interval (default 15) |
| `DEFAULT_RISK_PROFILE` | conservative / moderate / aggressive |
| `LLM_PROVIDER` | `nvidia` \| `huggingface` \| `openai` \| `none` |
| `LLM_MODEL` | e.g. `meta/llama-3.1-8b-instruct` |
| `NVIDIA_API_KEY` | NVIDIA NIM key (used when provider=nvidia) |
| `HF_API_KEY` | HuggingFace key (used when provider=huggingface) |
| `CA_BUNDLE` | PEM bundle for SSL (auto-exported for corporate proxies) |

### Swapping the LLM provider

Change `LLM_PROVIDER` and the matching key in `.env`. NVIDIA NIM and OpenAI use the
same OpenAI-compatible schema; HuggingFace uses its Inference API. To add a new
provider, implement `_call_<provider>` in `app/services/llm.py` and register it.
The LLM is **optional** — if disabled or unreachable, the deterministic pipeline and
a fallback briefing keep working.

### Corporate networks / SSL

If you're behind an SSL-inspection proxy, the app trusts a combined CA bundle at
`backend/data/corp_ca.pem` (Windows root store + certifi). Re-export it if your
network's CA changes. Public market-data fetches can optionally fall back to an
unverified request (`DATA_SSL_FALLBACK_INSECURE=true`) since no secrets are sent there.

---

## Guardrails

- **Paper only** in v1 — no broker credentials, no real orders.
- **No trade without RiskManager approval.**
- **No LLM-only decisions** — the LLM only explains; deterministic agents decide.
- **Hold cash** when no setup fits risk + cash (whole-share constraint enforced).
- Every decision is logged (`agent_runs`, `signals`, `audit_logs`) for explainability.

## Roadmap

- [ ] Backtesting (`backtesting.py`) vs NIFTY benchmark
- [ ] RL sandbox (Gymnasium + Stable-Baselines3), must beat baseline before influencing trades
- [ ] Intraday data + finer scheduling
- [ ] Real broker/Demat integration with a hard kill-switch (only after trustworthy paper results)
