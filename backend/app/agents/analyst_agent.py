"""Analyst agent: LLM-generated, human-readable market briefing.

Pure explainability layer. It summarizes the regime, top signals, and actions into
a short narrative for the dashboard. It NEVER influences buy/sell decisions — those
remain fully deterministic via the StrategyAgent + RiskManager. If the LLM is
disabled or unavailable, a concise deterministic fallback summary is returned.
"""
from __future__ import annotations

from app.core.logging_config import get_logger
from app.services import llm

log = get_logger("agent.analyst")


def market_briefing(regime_label: str, regime_detail: str, top_signals: list[dict],
                    actions: list[str]) -> str:
    """Return a short narrative briefing for the run."""
    lines = [f"- {s['symbol']}: score {s['score']:+.2f}, {s.get('trend','')} "
             f"({s.get('action','HOLD')})" for s in top_signals[:6]]
    signal_block = "\n".join(lines) if lines else "No tradable signals."
    action_block = "; ".join(actions) if actions else "No trades executed."

    prompt = (
        f"Market regime: {regime_label} ({regime_detail}).\n"
        f"Top NSE signals:\n{signal_block}\n"
        f"Actions this cycle: {action_block}\n\n"
        "Write a 3-4 sentence briefing for a retail investor explaining the current "
        "stance, why the agent acted (or held cash), and the main risk to watch. "
        "Be specific and avoid generic disclaimers."
    )
    out = llm.complete(
        prompt,
        system=("You are AgenticTrader's market analyst for Indian equities (NSE). "
                "Be concise, factual, and practical."),
        max_tokens=260,
        temperature=0.4,
    )
    if out:
        return out

    # Deterministic fallback.
    return (
        f"Regime is {regime_label} ({regime_detail}). "
        f"{action_block} "
        f"{'Top idea: ' + top_signals[0]['symbol'] if top_signals else 'No standout ideas; holding cash.'}"
    )
