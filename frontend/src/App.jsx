import React, { useEffect, useState, useCallback } from "react";
import { api, isStatic } from "./api";
import StatCards from "./components/StatCards";
import Holdings from "./components/Holdings";
import Alerts from "./components/Alerts";
import Signals from "./components/Signals";
import FundsModal from "./components/FundsModal";
import SettingsBar from "./components/SettingsBar";
import Briefing from "./components/Briefing";
import NewsPanel from "./components/NewsPanel";
import Trades from "./components/Trades";

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
  const [toast, setToast] = useState(null);
  const [running, setRunning] = useState(false);
  const [tab, setTab] = useState("overview");

  const notify = (message, type = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const refresh = useCallback(async () => {
    try {
      const [p, w, a, s, r, t, st] = await Promise.all([
        api.portfolio(), api.wallet(), api.alerts(), api.signals(40),
        api.runs(10), api.trades(), api.settings(),
      ]);
      setPortfolio(p); setWallet(w); setAlerts(a); setSignals(s);
      setRuns(r); setTrades(t); setSettings(st);
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

  const handleFunds = async (kind, amount, password) => {
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
    setRunning(true);
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

  const latestRun = runs[0];
  const unread = alerts.filter((a) => !a.read).length;

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
          {isStatic && <span className="tag">Cloud · Read-only</span>}
        </div>
        <div className="row">
          {!isStatic && (
            <>
              <button className="ghost" onClick={() => setFundsModal("withdraw")}>Withdraw</button>
              <button onClick={() => setFundsModal("add")}>+ Add Funds</button>
              <button className="ghost" onClick={runNow} disabled={running}>
                {running ? "Running…" : "Run Agent Now"}
              </button>
            </>
          )}
        </div>
      </div>

      {isStatic && (
        <div className="banner">
          Live cloud dashboard — updates automatically during market hours via GitHub Actions.
          To add/withdraw funds or change settings, run the <b>“manage”</b> workflow in the
          repo’s <b>Actions</b> tab.
        </div>
      )}

      {settings && (
        <SettingsBar
          settings={settings}
          onRisk={async (r) => {
            if (isStatic) return notify("Read-only: use the manage workflow to change risk", "error");
            await api.setRisk(r); notify(`Risk: ${r}`, "success"); refresh();
          }}
          onAutonomous={async (v) => {
            if (isStatic) return notify("Read-only: use the manage workflow to toggle autonomous", "error");
            await api.setAutonomous(v); notify(`Autonomous ${v ? "on" : "off"}`, "success"); refresh();
          }}
        />
      )}

      <StatCards portfolio={portfolio} wallet={wallet} />

      {latestRun && <Briefing run={latestRun} />}

      <div className="tabs">
        {["overview", "signals", "trades", "alerts", "news"].map((t) => (
          <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {t === "alerts" && unread > 0 ? `Alerts (${unread})` : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid cols-2">
          <Holdings portfolio={portfolio} />
          <Alerts alerts={alerts} onRead={async () => { await api.readAllAlerts(); refresh(); }} />
        </div>
      )}
      {tab === "signals" && <Signals signals={signals} />}
      {tab === "trades" && <Trades trades={trades} />}
      {tab === "alerts" && (
        <Alerts alerts={alerts} full onRead={async () => { await api.readAllAlerts(); refresh(); }} />
      )}
      {tab === "news" && <NewsPanel news={news} onRefresh={loadNews} />}

      {fundsModal && (
        <FundsModal
          kind={fundsModal}
          onClose={() => setFundsModal(null)}
          onSubmit={handleFunds}
        />
      )}

      {toast && <div className={"toast " + toast.type}>{toast.message}</div>}
    </div>
  );
}
