"""Agent package: autonomous trading agents for AgenticTrader.

Agents:
- RegimeAgent: classifies overall market regime (NIFTY trend + India VIX).
- StrategyAgent: combines technical + sentiment into per-symbol composite signal.
- RiskManager: gates every proposed trade against the active risk profile.
- Supervisor: orchestrates the full fetch -> analyze -> decide -> execute loop.
"""
