# Running AgenticTrader 24/7 on GitHub Actions (free, no credit card)

This deploys the autonomous agent so it runs on its own during NSE market hours
and publishes a live read-only dashboard to GitHub Pages — using only your
**personal GitHub account**. No server, no credit card, no cost.

## How it works

- **The agent** runs as a scheduled GitHub Actions workflow (`trade.yml`), every
  15 minutes during market hours (Mon–Fri). Each run analyzes the market, makes
  paper trades, and updates state.
- **State persistence**: GitHub runners are wiped after each run, so the SQLite
  database is saved to a dedicated **`state` branch** and restored on the next run.
- **The dashboard** is a static React build published to **GitHub Pages**. After
  each run, fresh JSON snapshots are exported and deployed. The dashboard is
  **read-only** (no live backend).
- **Funds & settings** are changed by manually running the **`manage`** workflow
  (Actions tab → Run workflow) — still password-protected.
- **Alerts** (optional) are pushed to **Telegram** when trades happen.

> Why not a real always-on server? The agent only needs to act ~25 times a day
> during market hours. A scheduled job is a perfect, truly-free fit.

---

## One-time setup (~10 minutes)

### 1. Push this project to a new GitHub repo
Use a **public** repo — GitHub Actions minutes are **unlimited and free** for
public repos. (Private repos only get 2,000 free minutes/month, which this can
exceed.) No secrets are committed; your API keys live in encrypted GitHub
Secrets, so a public repo is safe.

```bash
cd AgenticTrader
git init
git add .
git commit -m "AgenticTrader"
git branch -M main
git remote add origin https://github.com/<you>/AgenticTrader.git
git push -u origin main
```

### 2. Enable GitHub Pages (source = GitHub Actions)
Repo → **Settings → Pages** → under **Build and deployment**, set
**Source = GitHub Actions**. (No branch selection needed.)

### 3. Add your secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `NVIDIA_API_KEY` | your `nvapi-...` key |
| `TELEGRAM_BOT_TOKEN` | *(optional)* bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | *(optional)* your chat id from @userinfobot |

Optional **Variables** (same screen → *Variables* tab) to tweak defaults:

| Variable | Default | Meaning |
|---|---|---|
| `INITIAL_FUNDS` | `1000` | Paper money seeded once on first run |
| `LLM_PROVIDER` | `nvidia` | `nvidia` \| `huggingface` \| `openai` \| `none` |
| `LLM_MODEL` | `meta/llama-3.1-8b-instruct` | model id |

### 4. Set the funds password
The password that authorizes Add/Withdraw defaults to `trade123`. To change it,
edit `FUNDS_PASSWORD` in `backend/.env.example` **before first run** (or set a
`FUNDS_PASSWORD` repo secret and add it to the workflow env). It is hashed into
the DB on first boot.

### 5. Kick off the first run
Actions tab → **trade** → **Run workflow** → set `force = true` (so it runs even
though the market may be closed) → **Run**.

After it finishes:
- Your dashboard is live at `https://<you>.github.io/<repo>/`
- The `state` branch now holds your trading DB.

---

## Daily operation

- **Automatic**: `trade.yml` runs every 15 min during market hours and updates
  the dashboard. Nothing for you to do.
- **Add / withdraw funds or change risk**: Actions → **manage** → **Run
  workflow** → pick the operation, enter amount + password (for funds) or value
  (for risk/autonomous). It updates state and refreshes the dashboard.
- **Notifications**: if Telegram is configured, you get a message whenever the
  agent trades or you change funds.

---

## Notes & limits

- **Cron timing** is best-effort on GitHub — runs can be delayed 5–15 min under
  load. Fine for a 15-minute loop.
- **Scheduled workflows pause after 60 days** of no repo activity. Just push a
  commit (or run a workflow) to keep them alive.
- **No corporate proxy in the cloud** — the SSL/CA workaround used on your office
  machine is automatically skipped; standard certificates are used.
- **This is still paper trading.** No real broker/Demat is connected.

## Switching the LLM later
Set the `LLM_PROVIDER` variable (and the matching secret: `NVIDIA_API_KEY`,
`HF_API_KEY`, or `OPENAI_API_KEY`). No code changes needed. Set
`LLM_PROVIDER=none` to run with the deterministic fallback (the LLM only writes
explanatory briefings — it never makes trading decisions).
