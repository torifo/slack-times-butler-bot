from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:  # pragma: no cover
    BaseSettings = None
    SettingsConfigDict = None
    Field = None


if BaseSettings:
    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

        app_name: str = "times-butler"
        environment: str = "local"
        database_path: Path = Field(default=Path("data/times_butler.sqlite3"), alias="DATABASE_PATH")

        slack_signing_secret: str = Field(default="", alias="SLACK_SIGNING_SECRET")
        slack_bot_token: str = Field(default="", alias="SLACK_BOT_TOKEN")
        slack_app_token: str = Field(default="", alias="SLACK_APP_TOKEN")
        source_channel: str = Field(default="", alias="SOURCE_CHANNEL")
        source_channel_name: str = Field(default="", alias="SOURCE_CHANNEL_NAME")
        post_target_channel: str = Field(default="", alias="POST_TARGET_CHANNEL")
        weekly_summary_canvas_id: str = Field(default="", alias="WEEKLY_SUMMARY_CANVAS_ID")

        daily_digest_cron: str = Field(default="30 18 * * *", alias="DAILY_DIGEST_CRON")
        weekly_digest_cron: str = Field(default="0 19 * * FRI", alias="WEEKLY_DIGEST_CRON")
        default_explanation_level: int = Field(default=2, alias="DEFAULT_EXPLANATION_LEVEL")
        url_reaction_name: str = Field(default="eyes", alias="URL_REACTION_NAME")

        japan_ai_api_key: str = Field(default="", alias="JAPAN_AI_API_KEY")
        japan_ai_user_id: str = Field(default="", alias="JAPAN_AI_USER_ID")
        japan_ai_base_url: str = Field(default="https://api.japan-ai.co.jp", alias="JAPAN_AI_BASE_URL")
        japan_ai_model: str = Field(default="gpt-4o", alias="JAPAN_AI_MODEL")
        japan_ai_artifact_ids: str = Field(default="", alias="JAPAN_AI_ARTIFACT_IDS")
        japan_ai_chat_endpoint: str = Field(default="/chat/v2", alias="JAPAN_AI_CHAT_ENDPOINT")
        japan_ai_temperature: float = Field(default=0.1, alias="JAPAN_AI_TEMPERATURE")
        request_timeout_seconds: float = Field(default=20.0, alias="REQUEST_TIMEOUT_SECONDS")

        llm_backend: str = Field(default="japan_ai", alias="LLM_BACKEND")
        llm_gateway_url: str = Field(default="http://127.0.0.1:8100", alias="LLM_GATEWAY_URL")
        llm_gateway_url_backup: str = Field(default="http://127.0.0.1:8101", alias="LLM_GATEWAY_URL_BACKUP")
        llm_gateway_timeout_seconds: float = Field(default=180.0, alias="LLM_GATEWAY_TIMEOUT_SECONDS")


else:
    @dataclass(slots=True)
    class Settings:
        app_name: str = "times-butler"
        environment: str = "local"
        database_path: Path = Path("data/times_butler.sqlite3")
        slack_signing_secret: str = ""
        slack_bot_token: str = ""
        slack_app_token: str = ""
        source_channel: str = ""
        source_channel_name: str = ""
        post_target_channel: str = ""
        weekly_summary_canvas_id: str = ""
        daily_digest_cron: str = "30 18 * * *"
        weekly_digest_cron: str = "0 19 * * FRI"
        default_explanation_level: int = 2
        url_reaction_name: str = "eyes"
        japan_ai_api_key: str = ""
        japan_ai_user_id: str = ""
        japan_ai_base_url: str = "https://api.japan-ai.co.jp"
        japan_ai_model: str = "gpt-4o"
        japan_ai_artifact_ids: str = ""
        japan_ai_chat_endpoint: str = "/chat/v2"
        japan_ai_temperature: float = 0.1
        request_timeout_seconds: float = 20.0
        llm_backend: str = "japan_ai"
        llm_gateway_url: str = "http://127.0.0.1:8100"
        llm_gateway_url_backup: str = "http://127.0.0.1:8101"
        llm_gateway_timeout_seconds: float = 180.0

        def __init__(self, **overrides: object):
            env_map = {
                "app_name": os.getenv("APP_NAME", "times-butler"),
                "environment": os.getenv("ENVIRONMENT", "local"),
                "database_path": Path(os.getenv("DATABASE_PATH", "data/times_butler.sqlite3")),
                "slack_signing_secret": os.getenv("SLACK_SIGNING_SECRET", ""),
                "slack_bot_token": os.getenv("SLACK_BOT_TOKEN", ""),
                "slack_app_token": os.getenv("SLACK_APP_TOKEN", ""),
                "source_channel": os.getenv("SOURCE_CHANNEL", ""),
                "source_channel_name": os.getenv("SOURCE_CHANNEL_NAME", ""),
                "post_target_channel": os.getenv("POST_TARGET_CHANNEL", ""),
                "weekly_summary_canvas_id": os.getenv("WEEKLY_SUMMARY_CANVAS_ID", ""),
                "daily_digest_cron": os.getenv("DAILY_DIGEST_CRON", "30 18 * * *"),
                "weekly_digest_cron": os.getenv("WEEKLY_DIGEST_CRON", "0 19 * * FRI"),
                "default_explanation_level": int(os.getenv("DEFAULT_EXPLANATION_LEVEL", "2")),
                "url_reaction_name": os.getenv("URL_REACTION_NAME", "eyes"),
                "japan_ai_api_key": os.getenv("JAPAN_AI_API_KEY", ""),
                "japan_ai_user_id": os.getenv("JAPAN_AI_USER_ID", ""),
                "japan_ai_base_url": os.getenv("JAPAN_AI_BASE_URL", "https://api.japan-ai.co.jp"),
                "japan_ai_model": os.getenv("JAPAN_AI_MODEL", "gpt-4o"),
                "japan_ai_artifact_ids": os.getenv("JAPAN_AI_ARTIFACT_IDS", ""),
                "japan_ai_chat_endpoint": os.getenv("JAPAN_AI_CHAT_ENDPOINT", "/chat/v2"),
                "japan_ai_temperature": float(os.getenv("JAPAN_AI_TEMPERATURE", "0.1")),
                "request_timeout_seconds": float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20.0")),
                "llm_backend": os.getenv("LLM_BACKEND", "japan_ai"),
                "llm_gateway_url": os.getenv("LLM_GATEWAY_URL", "http://127.0.0.1:8100"),
                "llm_gateway_url_backup": os.getenv("LLM_GATEWAY_URL_BACKUP", "http://127.0.0.1:8101"),
                "llm_gateway_timeout_seconds": float(os.getenv("LLM_GATEWAY_TIMEOUT_SECONDS", "180.0")),
            }
            aliases = {
                "DATABASE_PATH": "database_path",
                "SLACK_SIGNING_SECRET": "slack_signing_secret",
                "SLACK_BOT_TOKEN": "slack_bot_token",
                "SLACK_APP_TOKEN": "slack_app_token",
                "SOURCE_CHANNEL": "source_channel",
                "SOURCE_CHANNEL_NAME": "source_channel_name",
                "POST_TARGET_CHANNEL": "post_target_channel",
                "WEEKLY_SUMMARY_CANVAS_ID": "weekly_summary_canvas_id",
                "DAILY_DIGEST_CRON": "daily_digest_cron",
                "WEEKLY_DIGEST_CRON": "weekly_digest_cron",
                "DEFAULT_EXPLANATION_LEVEL": "default_explanation_level",
                "URL_REACTION_NAME": "url_reaction_name",
                "JAPAN_AI_API_KEY": "japan_ai_api_key",
                "JAPAN_AI_USER_ID": "japan_ai_user_id",
                "JAPAN_AI_BASE_URL": "japan_ai_base_url",
                "JAPAN_AI_MODEL": "japan_ai_model",
                "JAPAN_AI_ARTIFACT_IDS": "japan_ai_artifact_ids",
                "JAPAN_AI_CHAT_ENDPOINT": "japan_ai_chat_endpoint",
                "JAPAN_AI_TEMPERATURE": "japan_ai_temperature",
                "REQUEST_TIMEOUT_SECONDS": "request_timeout_seconds",
                "LLM_BACKEND": "llm_backend",
                "LLM_GATEWAY_URL": "llm_gateway_url",
                "LLM_GATEWAY_URL_BACKUP": "llm_gateway_url_backup",
                "LLM_GATEWAY_TIMEOUT_SECONDS": "llm_gateway_timeout_seconds",
            }
            normalized = dict(env_map)
            for key, value in overrides.items():
                normalized[aliases.get(key, key)] = value

            for key, value in normalized.items():
                if key == "database_path" and not isinstance(value, Path):
                    value = Path(value)
                setattr(self, key, value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
