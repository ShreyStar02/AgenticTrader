"""Application configuration loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Central settings. Override via backend/.env."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "AgenticTrader"
    environment: str = "dev"

    database_url: str = f"sqlite:///{(DATA_DIR / 'agentictrader.db').as_posix()}"

    # Local "system password" used to authorize fund add/withdraw (paper money only).
    # Default is a hash of "trade123". Change via FUNDS_PASSWORD env (plaintext) -> hashed on boot.
    funds_password: str = "trade123"

    # Trading universe / scheduler
    scan_interval_minutes: int = 5
    autonomous_enabled: bool = True

    # Paper execution assumptions
    brokerage_pct: float = 0.0003  # 0.03% per side (discount broker-ish)
    slippage_pct: float = 0.0010  # 0.10% adverse slippage

    # Default starting risk profile
    default_risk_profile: str = "aggressive"

    # --- Data fetch / SSL ---
    # Path to a CA bundle (PEM). If the file exists it is used for verification
    # (supports corporate SSL-inspection proxies via exported root CAs).
    ca_bundle: str = str(DATA_DIR / "corp_ca.pem")
    # If verification still fails, fall back to unverified fetch of PUBLIC market
    # data only (no secrets are ever sent to these endpoints).
    data_ssl_fallback_insecure: bool = True

    # --- LLM (provider-agnostic) ---
    # Switch providers by changing LLM_PROVIDER: "nvidia" | "huggingface" | "openai" | "none".
    # Keys live in .env (never committed). The LLM only enhances analysis/explanations;
    # it never overrides the deterministic risk manager.
    llm_provider: str = "nvidia"
    llm_model: str = "meta/llama-3.1-8b-instruct"
    llm_enabled: bool = True
    llm_timeout: int = 40

    # NVIDIA NIM (OpenAI-compatible) -- https://integrate.api.nvidia.com/v1
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    # HuggingFace Inference API (used when llm_provider == "huggingface")
    hf_api_key: str = ""
    hf_base_url: str = "https://api-inference.huggingface.co/models"

    # Generic OpenAI-compatible endpoint (used when llm_provider == "openai")
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # --- Notifications (optional, free) ---
    # If both are set, trade/funds events are pushed to Telegram. Leave blank to disable.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # --- Cloud / unattended runs ---
    # On the very first run, if the wallet has never been funded and this is > 0,
    # the agent seeds this amount once (system-authorized) so the dashboard is populated.
    initial_funds: float = 0.0

    # CORS for the Vite dev server
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Make `requests`/`urllib`-based libs (nselib, feedparser) trust the same CA bundle.
if settings.ca_bundle and Path(settings.ca_bundle).exists():
    import os

    os.environ.setdefault("REQUESTS_CA_BUNDLE", settings.ca_bundle)
    os.environ.setdefault("SSL_CERT_FILE", settings.ca_bundle)
    os.environ.setdefault("CURL_CA_BUNDLE", settings.ca_bundle)
