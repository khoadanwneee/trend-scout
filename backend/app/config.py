from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    db_path: str = str(ROOT / "data" / "trend_scout.db")
    github_token: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Honest, identifiable user agent. Never spoofed.
    user_agent: str = "TrendScout/0.1 (personal trend tool; polite, rate-limited)"
    request_delay_seconds: float = 3.0
    itviec_pages: int = 3
    topdev_pages: int = 2

    scheduler_enabled: bool = True
    scrape_hour: int = 8  # local time, daily scrape
    digest_hour: int = 9  # local time, daily Telegram digest
    enable_linkedin: bool = False  # disabled: robots.txt/ToS forbid scraping

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"


settings = Settings()
