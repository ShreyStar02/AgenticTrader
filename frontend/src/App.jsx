import React, { useEffect, useState, useCallback } from "react";
import { api, isStatic } from "./api";
import { cloud } from "./cloud";
import StatCards from "./components/StatCards";
import Holdings from "./components/Holdings";
import AlertsDrawer, { badgeColorFor } from "./components/AlertsDrawer";
import Signals from "./components/Signals";
import SignalDetail from "./components/SignalDetail";
import FundsModal from "./components/FundsModal";
import TokenModal from "./components/TokenModal";
import SettingsBar from "./components/SettingsBar";
import Briefing from "./components/Briefing";
import NewsPanel from "./components/NewsPanel";
import Trades from "./components/Trades";
import Watchlist from "./components/Watchlist";
import TradeModal from "./components/TradeModal";

const RUN_COOLDOWN_S = 180; // Run Agent cooldown (matches ~workflow run time)
const RUN_TS_KEY = "at_last_run_ts";

export default function App() {
  const [portfolio, setPortfolio] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [signals, setSignals] = useState([]);
  const [runs, setRuns] = useState([]);
  const [trades, setTrades] = useState([]);
  const [news, setNews] = useState([]);
  const [settings, setSettings] = useState(null);
  const [fundsModal, setFundsModal] = useState(null); // 'add' | 'withdraw' | null
  const [tokenModal, setTokenModal] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [toast, setToast] = useState(null);
  const [running, setRunning] = useState(false);
  const [tab, setTab] = useState("signals");
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [selectedSignal, setSelectedSignal] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
  const [tradeModal, setTradeModal] = useState(null); // {kind, symbol, lockSymbol} | null
  const [researchBusy, setResearchBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0); // seconds remaining on Run Agent

  const notify = (message, type = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // In static (cloud) mode, alert read-state can't be persisted server-side,
  // so remember which alert IDs were read locally and re-apply after each fetch.
  const READ_KEY = "at_read_alert_ids";
  const readSet = () => {
    try { return new Set(JSON.parse(localStorage.getItem(READ_KEY) || "[]")); }
    catch (e) { return new Set(); }
  };
  const applyLocalReads = (list) => {
    if (!isStatic) return list;
    const seen = readSet();
    return list.map((a) => (seen.has(a.id) ? { ...a, read: true } : a));
  };

  const refresh = useCallback(async () => {
    try {
      const [p, w, a, s, r, t, st, wl] = await Promise.all([
        api.portfolio(), api.wallet(), api.alerts(), api.signals(40),
        api.runs(10), api.trades(), api.settings(), api.watchlist().catch(() => null),
      ]);
      setPortfolio(p); setWallet(w); setAlerts(applyLocalReads(a)); setSignals(s);
      setRuns(r); setTrades(t); setSettings(st);
      if (wl && Array.isArray(wl.symbols)) setWatchlist(wl.symbols);
    } catch (e) {
      notify("Backend unreachable: " + e.message, "error");
    }
  }, []);

  const loadNews = useCallback(async () => {
    try { setNews(await api.news()); } catch (e) { /* ignore */ }
  }, []);

  useEffect(() => {
    refresh();
    loadNews();
    const id = setInterval(refresh, 15000);
    return () => clearInterval(id);
  }, [refresh, loadNews]);

  // Run Agent cooldown: derive remaining seconds from a persisted timestamp so
  // it survives reloads and blocks rapid repeat triggers.
  useEffect(() => {
    const tick = () => {
      const ts = parseInt(localStorage.getItem(RUN_TS_KEY) || "0", 10);
      const remain = ts ? Math.ceil((ts + RUN_COOLDOWN_S * 1000 - Date.now()) / 1000) : 0;
      setCooldown(remain > 0 ? remain : 0);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const startCooldown = () => localStorage.setItem(RUN_TS_KEY, String(Date.now()));

  // In static (cloud) mode, writes are performed by dispatching GitHub Actions
  // workflows. If no token is saved yet, stash the action and prompt for one.
  const runCloud = useCallback(async (action) => {
    if (!cloud.hasToken()) {
      setPendingAction(() => action);
      setTokenModal(true);
      return;
    }
    try {
      await action();
    } catch (e) {
      const msg = String(e.message || e);
      if (msg.startsWith("BAD_TOKEN") || msg === "NO_TOKEN") {
        notify("GitHub key missing or invalid — please re-enter it.", "error");
        setPendingAction(() => action);
        setTokenModal(true);
      } else {
        notify(msg, "error");
      }
    }
  }, []);

  const onTokenSaved = async (tok) => {
    setTokenModal(false);
    const act = pendingAction;
    setPendingAction(null);
    if (tok && act) await runCloud(act);
  };

  const handleFunds = async (kind, amount, password) => {
    if (isStatic) {
      return runCloud(async () => {
        if (kind === "add") await cloud.addFunds(amount, password);
        else await cloud.withdrawFunds(amount, password);
        setFundsModal(null);
        notify(
          `${kind === "add" ? "Add" : "Withdraw"} ₹${amount} submitted — applying via GitHub Actions (~1–2 min); the dashboard refreshes automatically.`,
          "success"
        );
      });
    }
    try {
      if (kind === "add") await api.addFunds(amount, password);
      else await api.withdrawFunds(amount, password);
      setFundsModal(null);
      notify(`Funds ${kind === "add" ? "added" : "withdrawn"}: ₹${amount}`, "success");
      refresh();
    } catch (e) {
      notify(e.message, "error");
    }
  };

  const runNow = async () => {
    if (cooldown > 0) return;
    if (isStatic) {
      return runCloud(async () => {
        await cloud.runAgent();
        startCooldown();
        notify("Agent run queued via GitHub Actions (~1–2 min).", "success");
      });
    }
    setRunning(true);
    startCooldown();
    notify("Running agent cycle… (fetching live data)", "info");
    try {
      const res = await api.runNow();
      notify(`Cycle done — ${res.actions} action(s), regime: ${res.regime}`, "success");
      refresh();
    } catch (e) {
      notify("Run failed: " + e.message, "error");
    } finally {
      setRunning(false);
    }
  };

  const handleResearch = async (symbol) => {
    if (isStatic) {
      return runCloud(async () => {
        await cloud.research(symbol);
        notify(`Researching ${symbol} via GitHub Actions (~1–2 min) — it'll appear in Signals.`, "success");
      });
    }
    setResearchBusy(true);
    notify(`Researching ${symbol}…`, "info");
    try {
      const sig = await api.research(symbol);
      setSelectedSignal(sig);
      notify(`Research complete: ${sig.symbol} (${sig.action})`, "success");
    } catch (e) {
      notify("Research failed: " + e.message, "error");
    } finally {
      setResearchBusy(false);
    }
  };

  const handleWatchAdd = async (symbol) => {
    if (isStatic) {
      return runCloud(async () => {
        await cloud.watchlistAdd(symbol);
        notify(`Adding ${symbol} to watchlist (~1–2 min).`, "success");
      });
    }
    try {
      const wl = await api.watchlistAdd(symbol);
      setWatchlist(wl.symbols);
      notify(`Added ${symbol} to watchlist`, "success");
    } catch (e) {
      notify(e.message, "error");
    }
  };

  const handleWatchRemove = async (symbol) => {
    if (isStatic) {
      return runCloud(async () => {
        await cloud.watchlistRemove(symbol);
        notify(`Removing ${symbol} from watchlist (~1–2 min).`, "success");
      });
    }
    try {
      const wl = await api.watchlistRemove(symbol);
      setWatchlist(wl.symbols);
      notify(`Removed ${symbol} from watchlist`, "success");
    } catch (e) {
      notify(e.message, "error");
    }
  };

  const handleTrade = async (kind, symbol, qty, password) => {
    if (isStatic) {
      return runCloud(async () => {
        if (kind === "buy") await cloud.buy(symbol, qty, password);
        else await cloud.sell(symbol, qty, password);
        setTradeModal(null);
        notify(`${kind === "buy" ? "Buy" : "Sell"} ${qty} ${symbol} submitted via GitHub Actions (~1–2 min).`, "success");
      });
    }
    try {
      if (kind === "buy") await api.buyStock(symbol, qty, password);
      else await api.sellStock(symbol, qty, password);
      setTradeModal(null);
      notify(`${kind === "buy" ? "Bought" : "Sold"} ${qty} ${symbol}`, "success");
      refresh();
    } catch (e) {
      notify(e.message, "error");
    }
  };

  const latestRun = runs[0];
  const unread = alerts.filter((a) => !a.read).length;
  const badgeColor = unread > 0 ? badgeColorFor(alerts.filter((a) => !a.read)) : null;

  const markAllRead = async () => {
    if (isStatic) {
      const ids = alerts.map((a) => a.id);
      localStorage.setItem(READ_KEY, JSON.stringify(ids));
      setAlerts((prev) => prev.map((a) => ({ ...a, read: true })));
      return;
    }
    await api.readAllAlerts();
    refresh();
  };

  return (
    <div className="app">
      <div className="topbar">
        <div>
          <span className="brand">Agentic<span>Trader</span></span>
          <span className="tag">NSE · Paper Trading</span>
          {settings && (
            <span className="tag">
              <span className={"dot " + (settings.market_open ? "on" : "off")} />
              Market {settings.market_open ? "Open" : "Closed"}
            </span>
          )}
          {isStatic && <span className="tag">Cloud</span>}
        </div>
        <div className="row">
          <button className="ghost" onClick={() => setFundsModal("withdraw")}>Withdraw</button>
          <button onClick={() => setFundsModal("add")}>+ Add Funds</button>
          <button className="ghost" onClick={() => setTradeModal({ kind: "buy", symbol: "", lockSymbol: false })}>
            Buy Stock
          </button>
          <button className="ghost" onClick={runNow} disabled={running || cooldown > 0}>
            {running ? "Running…" : cooldown > 0 ? `Run Agent (${cooldown}s)` : "Run Agent Now"}
          </button>
          <button
            className="ghost bell"
            onClick={() => setAlertsOpen(true)}
            title="Alerts & notifications"
            aria-label="Alerts"
          >
            🔔
            {unread > 0 && (
              <span className="bell-badge" style={{ background: badgeColor }}>{unread}</span>
            )}
          </button>
        </div>
      </div>

      {settings && (
        <SettingsBar
          settings={settings}
          cloud={isStatic ? { hasKey: cloud.hasToken(), onKey: () => setTokenModal(true) } : null}
          onRisk={async (r) => {
            if (isStatic)
              return runCloud(async () => {
                await cloud.setRisk(r);
                notify(`Risk → ${r} submitted (applying via GitHub Actions ~1–2 min).`, "success");
              });
            await api.setRisk(r); notify(`Risk: ${r}`, "success"); refresh();
          }}
          onAutonomous={async (v) => {
            if (isStatic)
              return runCloud(async () => {
                await cloud.setAutonomous(v);
                notify(`Autonomous ${v ? "on" : "off"} submitted (applying ~1–2 min).`, "success");
              });
            await api.setAutonomous(v); notify(`Autonomous ${v ? "on" : "off"}`, "success"); refresh();
          }}
        />
      )}

      <StatCards portfolio={portfolio} wallet={wallet} />

      {selectedSignal ? (
        <SignalDetail
          signal={selectedSignal}
          onBack={() => setSelectedSignal(null)}
          onBuy={(sym) => setTradeModal({ kind: "buy", symbol: sym, lockSymbol: true })}
          onWatch={handleWatchAdd}
        />
      ) : (
        <>
          <section className="overview">
            <h2 className="section-title">Overview</h2>
            {latestRun && <Briefing run={latestRun} />}
            <Holdings
              portfolio={portfolio}
              onBuy={(sym) => setTradeModal({ kind: "buy", symbol: sym, lockSymbol: true })}
              onSell={(sym) => setTradeModal({ kind: "sell", symbol: sym, lockSymbol: true })}
            />
          </section>

          <div className="tabs">
            {["signals", "watchlist", "trades", "news"].map((t) => (
              <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          {tab === "signals" && <Signals signals={signals} onSelect={setSelectedSignal} />}
          {tab === "watchlist" && (
            <Watchlist
              symbols={watchlist}
              busy={researchBusy}
              isCloud={isStatic}
              onResearch={handleResearch}
              onAdd={handleWatchAdd}
              onRemove={handleWatchRemove}
            />
          )}
          {tab === "trades" && <Trades trades={trades} />}
          {tab === "news" && <NewsPanel news={news} onRefresh={loadNews} />}
        </>
      )}

      <AlertsDrawer
        open={alertsOpen}
        alerts={alerts}
        unread={unread}
        onClose={() => setAlertsOpen(false)}
        onRead={markAllRead}
      />

      {fundsModal && (
        <FundsModal
          kind={fundsModal}
          isCloud={isStatic}
          onClose={() => setFundsModal(null)}
          onSubmit={handleFunds}
        />
      )}

      {tradeModal && (
        <TradeModal
          kind={tradeModal.kind}
          symbol={tradeModal.symbol}
          lockSymbol={tradeModal.lockSymbol}
          isCloud={isStatic}
          onClose={() => setTradeModal(null)}
          onSubmit={handleTrade}
        />
      )}

      {tokenModal && (
        <TokenModal
          onClose={() => setTokenModal(false)}
          onSaved={onTokenSaved}
        />
      )}

      {toast && <div className={"toast " + toast.type}>{toast.message}</div>}
    </div>
  );
}
