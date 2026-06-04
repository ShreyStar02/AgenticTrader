# AgenticTrader — Full Project Context & Handoff

> **Purpose of this file:** The chat session was not appearing in the user's session
> list, so this document captures the _entire_ context (what was built, why, how, and
> current state) to seed a fresh chat. Paste/point to this file at the start of the
> next session so the assistant can resume seamlessly.
>
> **Last updated:** 2026-06-04 (IST)
> **Working dir:** `c:\Users\VY538FP\EY_Workstation\AgenticTrader` (NOT a git repo yet)
> **OS:** Windows. Use Windows-style backslash paths. PowerShell 5.x (no `&&`, `||`, `??`).

---

## 1. What the user asked for (original vision)

Build an **autonomous, multi-agent paper-trading platform for the Indian stock
market (NSE)**. Multiple cooperating agents understand the market, stocks,
patterns, trends, and expert opinions, then **autonomously buy/sell** stocks.

Key requirements:

- Start with a **risk level** filter and an **initial investment amount** (e.g. ₹1000).
- Maximize returns using all available knowledge (RL allowed in roadmap).
- **Zero cost** — must NOT spend a single penny on data, even one-time. Use only
  free APIs/libraries (replicate Bloomberg/yfinance-style research for free).
- **Everything is real APIs except the Demat account + actual buy/sell.** Use
  **fake money** for now: click "Add Funds", enter amount + a system password, app
  shows funds added.
- Webapp shows **alerts/notifications**: trades done, add/withdraw funds, etc.
- Later (once paper profits are trustworthy) → integrate real Demat for live trading.
- The user **approved a plan first**, then said "Start Implementation."

Then the user shared an **NVIDIA NIM API key** for LLM use, requiring:

- Store key in `.env` (changeable later).
- Make the LLM provider **easily swappable** (e.g. to HuggingFace).
- NVIDIA key: `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`
  (stored in `backend/.env`, which is gitignored).

### Latest request (this session)

The user wants the platform to **run 24/7**. After discussion they chose
**GitHub Actions cron** (free, no credit card, personal GitHub) over an always-on
server, because this is an **office computer** they shouldn't misuse. That work is
now **implemented and locally validated** (see §6–§7).

---

## 2. Tech stack & environment

- **Backend:** Python 3.12.10 + FastAPI + SQLAlchemy 2.0 + SQLite + APScheduler.
    - Python was NOT preinstalled; installed via `winget install Python.Python.3.12 --scope user`.
    - Path: `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`.
    - **Use the venv:** `backend\.venv\Scripts\python.exe` (no `py`/`python` on PATH in fresh shells).
- **Frontend:** React 18.3.1 + Vite 5.4.21 (Node v24.13.0, npm 11.12.1 present).
- **DB:** SQLite at `backend/data/agentictrader.db`. Uses `Base.metadata.create_all`
  (NO migrations) → **delete the .db file if you change the schema**.
- **Installed pkg versions:** fastapi 0.115.14, SQLAlchemy 2.0.50, pydantic 2.13.4,
  nselib 2.5.1, pandas 2.3.3, numpy 2.1.3, ta 0.11.0, curl_cffi 0.15.0, bcrypt 5.0.0,
  APScheduler 3.11.2.

### Run locally (dev)

```powershell
# Backend
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
# Frontend (separate shell)
cd frontend
npm run dev   # http://localhost:5173, proxies /api -> 127.0.0.1:8000
```

Helper scripts: `start-backend.ps1`, `start-frontend.ps1`.

### Environment quirks (IMPORTANT)

- **Corporate SSL inspection (MITM proxy):** the network re-signs TLS, so
  `curl_cffi`/yfinance fail with `CertificateVerifyError`. **Fix:**
  `backend/data/corp_ca.pem` = Windows Root+CA stores (exported via PowerShell
  `Get-ChildItem Cert:\LocalMachine\Root` → base64 PEM) concatenated with certifi's
  cacert.pem. `config.py` sets `REQUESTS_CA_BUNDLE`/`SSL_CERT_FILE`/`CURL_CA_BUNDLE`
  env vars at import. `yahoo_client.py` uses `verify=ca_bundle` with fallback to
  `verify=False` (public market data only). **This CA file is gitignored and absent
  in the cloud, where it's simply skipped (clean certs).**
- **PowerShell `Invoke-WebRequest` hangs** on Vite's chunked responses → use `curl.exe`.
- **`₹` renders as mojibake** in the Windows PS console and can throw a logging
  traceback fragment, but data is stored correctly and cloud runners (UTF-8) are fine.
- **bcrypt/passlib:** passlib 1.7.4 breaks on bcrypt 5.x → `security.py` uses bcrypt
  directly with a SHA-256→base64 pre-hash (handles arbitrary-length passwords).

---

## 3. The agents & trading logic

Agents (in `backend/app/agents/` and `services/`):
**MarketData · Technical · News/Sentiment · Fundamental · Regime · Strategy ·
RiskManager (mandatory gate) · PaperBroker · RL (roadmap) · Analyst (LLM) · Supervisor.**

- **Supervisor** (`agents/supervisor.py`) orchestrates each cycle:
  fetch → assess regime → manage exits → scan universe (MAX_SCAN=25) → score signals
  → risk-gate buys → execute paper trades → analyst briefing → persist AgentRun.
- **Strategy score** = `0.7*technical + 0.3*sentiment + regime_bias`, clamped [-1,1].
- **RiskManager** (`agents/risk_manager.py`) is a HARD gate: whole-share
  `affordable_qty`, allocation caps, cash buffer, stop-loss/take-profit, daily trade
  cap, min score. In risk-off regimes (bearish/volatile) the supervisor breaks the
  buy loop → holds cash.
- **LLM never gates trades.** `analyst_agent.py` only writes an explanatory briefing
  with a deterministic fallback.
- **Paper execution** (`services/portfolio.py`): immediate fills at last price ±
  slippage (0.10%), brokerage 0.03%/side, whole-share constraint, positions & P&L.
- **Market hours:** `is_market_open` = Mon–Fri 09:15–15:30 IST.

### Verified behavior (real data)

Live NIFTY ~23,417, India VIX ~15.9 → regime **bearish** → agent correctly **held
cash** (risk-off). 25 real signals from real technicals (SMA/RSI/MACD/ATR) + real
news sentiment (Google/Moneycontrol RSS). Buy/sell math verified (e.g. bought 3
@250.25, sold @269.73, realized P&L ₹58.20 — slippage/fees/whole-share all correct).
Funds add ₹1000 OK; wrong password → 403.

---

## 4. LLM provider layer (swappable)

- `backend/app/services/llm.py` — provider-agnostic. `LLM_PROVIDER` env =
  `nvidia | huggingface | openai | none`. Add a provider via `_call_<provider>` +
  dispatch in `complete()`. Best-effort with None fallback.
- **NVIDIA NIM** (OpenAI-compatible): base `https://integrate.api.nvidia.com/v1`,
  model `meta/llama-3.1-8b-instruct`, `/chat/completions`. Tested working (HTTP 200).
- Keys in `backend/.env` (gitignored); `.env.example` documents all vars.

---

## 5. Project structure / key files

```
AgenticTrader/
├─ backend/
│  ├─ .env                 # real config incl. NVIDIA_API_KEY, FUNDS_PASSWORD=trade123 (GITIGNORED)
│  ├─ .env.example         # template, no secrets (now includes TELEGRAM_*, INITIAL_FUNDS)
│  ├─ requirements.txt     # relaxed pins; uses `ta` (not pandas-ta), `bcrypt` (not passlib)
│  ├─ data/
│  │  ├─ agentictrader.db  # SQLite (GITIGNORED)
│  │  └─ corp_ca.pem       # exported CA bundle (GITIGNORED; office-only)
│  └─ app/
│     ├─ main.py           # FastAPI app + lifespan(bootstrap + scheduler)
│     ├─ bootstrap.py      # init_db + seed wallet/password/instruments (idempotent)
│     ├─ core/{config,security,logging_config,universe,risk_profiles}.py
│     ├─ db/session.py
│     ├─ models/__init__.py   # ORM: Setting,Instrument,PriceBar,NewsItem,Wallet,FundEvent,
│     │                       #      Order,Trade,Position,AgentRun(+briefing),Signal,Alert,AuditLog
│     ├─ schemas/__init__.py  # Pydantic out-models (mirror the JSON shapes the UI expects)
│     ├─ services/{market_data,yahoo_client,indicators,news,wallet,alerts,
│     │            portfolio,settings_store,llm,notify}.py
│     ├─ agents/{regime_agent,strategy_agent,risk_manager,supervisor,analyst_agent}.py
│     ├─ api/routes.py     # /wallet,/funds/*,/portfolio,/trades,/alerts,/signals,/runs,
│     │                    # /agent/run-now,/news,/settings,/settings/risk|autonomous,/health
│     ├─ scheduler/__init__.py  # APScheduler BackgroundScheduler (interval=scan_interval, IST)
│     └─ jobs/             # NEW (for unattended/cloud runs)
│        ├─ run_once.py        # one cycle; market-closed guard; seeds INITIAL_FUNDS once; Telegram summary
│        ├─ export_snapshots.py# dumps DB -> static JSON (shapes mirror live API exactly)
│        └─ funds_op.py        # CLI: add/withdraw/set-risk/set-autonomous (for manage workflow)
├─ frontend/
│  ├─ vite.config.js       # base=process.env.VITE_BASE||"/"; proxies /api -> backend
│  ├─ src/
│  │  ├─ api.js            # NEW dual-mode: live (/api) OR static (VITE_STATIC=1 -> /data/*.json), exports isStatic
│  │  ├─ App.jsx           # dashboard; hides mutating controls + shows banner when isStatic
│  │  ├─ styles.css        # +.banner style
│  │  └─ components/{StatCards,Holdings,Alerts,Signals,Trades,Briefing,SettingsBar,FundsModal,NewsPanel}.jsx
├─ .github/workflows/
│  ├─ trade.yml            # NEW cron (*/15 3-10 * * 1-5) + manual; runs agent, builds+publishes dashboard, persists state
│  └─ manage.yml           # NEW workflow_dispatch: add/withdraw funds, set risk/autonomous
├─ README.md               # full docs (+ link to deploy guide)
├─ DEPLOY_GITHUB_ACTIONS.md# NEW 24/7 free hosting setup guide
├─ start-backend.ps1, start-frontend.ps1
└─ .gitignore              # ignores .venv, *.db, *.pem, .env, node_modules, dist, site/
```

---

## 6. 24/7 free hosting — GitHub Actions (IMPLEMENTED THIS SESSION)

**Decision:** GitHub Actions cron (no credit card, personal GitHub, office PC unused).
Rationale: the agent only needs ~25 short runs/day during market hours — a scheduled
job is a perfect free fit. (Oracle Cloud Always-Free VM was the alternative but needs
a card for verification.)

**Architecture — "serverless agent + static dashboard":**

1. **Agent** → `trade.yml` runs `python -m app.jobs.run_once` every 15 min during
   market hours (cron is UTC: `*/15 3-10 * * 1-5` covers ~09:00–15:30 IST window;
   the code's own `is_market_open` gates precisely).
2. **State persistence** → GitHub runners are ephemeral, so the SQLite DB is committed
   to a dedicated **`state` branch** (restored at start, pushed at end of each run).
3. **Dashboard** → static React build (`VITE_STATIC=1`) published to **GitHub Pages**;
   after each run, `export_snapshots.py` writes JSON the static app reads.
4. **Funds/settings** → manual **`manage.yml`** (workflow_dispatch) running `funds_op`
   (still password-protected). It then triggers `trade.yml` to refresh the dashboard.
5. **Alerts** → optional **Telegram** (set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
   secrets); `services/notify.py` is stdlib-only and best-effort (never breaks a cycle).

**Config added** (`core/config.py`): `telegram_bot_token`, `telegram_chat_id`,
`initial_funds` (seed once on a fresh DB if no prior FundEvent). `.env.example` updated.

**Secrets/variables the workflows read:**

- Secrets: `NVIDIA_API_KEY` (required), `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` (optional),
  `HF_API_KEY`/`OPENAI_API_KEY` (optional).
- Variables (optional): `INITIAL_FUNDS` (default 1000), `LLM_PROVIDER`, `LLM_MODEL`.

---

## 7. Local validation done this session (all passed)

- `export_snapshots --out ..\site\data` → wrote wallet/portfolio/trades/alerts/
  signals/runs/funds_history/settings/news/meta JSON. ✅
- `funds_op set-risk --value moderate` → OK; `funds_op add ... --password wrongpw`
  → `DENIED: Invalid system password` (exit 2). ✅
- `run_once` (no force, market closed) → "Market closed; skipping" exit 0. ✅
- `run_once --force` → full real cycle, regime bearish, scanned 25, 0 actions
  (held cash), exit 0. ✅ (Only a cosmetic `₹` console-logging traceback fragment.)
- Frontend static build `VITE_STATIC=1 VITE_BASE=/AgenticTrader/ npm run build` → OK;
  `dist/index.html` references `/AgenticTrader/assets/...`. ✅
- Both workflow YAMLs parse via `yaml.safe_load`. ✅
- Temp `site/` dir cleaned; `.gitignore` updated to ignore `site/`.

---

## 8. What the USER still needs to do to go live (documented in DEPLOY_GITHUB_ACTIONS.md)

1. Create a **public** GitHub repo (public = unlimited free Actions minutes; no
   secrets are committed so it's safe) and push the project:
    ```bash
    cd AgenticTrader
    git init && git add . && git commit -m "AgenticTrader"
    git branch -M main
    git remote add origin https://github.com/<you>/AgenticTrader.git
    git push -u origin main
    ```
2. **Settings → Pages → Source = GitHub Actions.**
3. **Settings → Secrets and variables → Actions:** add `NVIDIA_API_KEY` (+ optional
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`). Optional Variables: `INITIAL_FUNDS`, etc.
4. (Optional) change funds password via `FUNDS_PASSWORD` before first run (default `trade123`).
5. **Actions → trade → Run workflow → force = true** for the first run. Dashboard then
   lives at `https://<you>.github.io/<repo>/` and the `state` branch holds the DB.

**Daily use:** automatic during market hours; use **manage** workflow to add/withdraw
funds or change risk; Telegram pings on trades (if configured).

**Caveats:** GitHub cron is best-effort (can lag 5–15 min); scheduled workflows pause
after 60 days of repo inactivity (push a commit to revive); still 100% paper trading.

---

## 9. Roadmap / not-yet-built (only if user requests)

- Backtesting (`backtesting.py`) vs NIFTY benchmark.
- RL sandbox (Gymnasium + Stable-Baselines3) that must beat baseline before it can
  influence live decisions.
- Price charts (Plotly) on the dashboard.
- Intraday data.
- **Real broker/Demat integration** with a kill-switch — ONLY after trustworthy
  paper results. (Explicitly deferred per the user's original plan.)

---

## 10. Gotchas cheat-sheet for the next session

- Not a git repo yet (`git init` needed before pushing).
- Activate nothing — call the venv python directly: `backend\.venv\Scripts\python.exe`.
- Schema change ⇒ delete `backend/data/agentictrader.db` (no migrations).
- Use `curl.exe`, not `Invoke-WebRequest`, for HTTP checks.
- If office network/CA changes, re-export `backend/data/corp_ca.pem`.
- The `₹`-in-console traceback is cosmetic only.
- Local **live** dev mode is fully intact and unaffected by the static/cloud additions
  (static mode only activates when `VITE_STATIC=1` at build time).
- Background dev servers may exist from earlier: uvicorn :8000, vite :5173.

---

## 11. Suggested opening message for the next chat

> "Resuming AgenticTrader (see AGENTICTRADER_CONTEXT.md in the repo root for full
> context). The GitHub Actions 24/7 deployment is built and locally validated; I
> [have/haven't] pushed to GitHub yet. Next I want to: <your goal>."
