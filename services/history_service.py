from __future__ import annotations

from datetime import datetime

from models.message import MessageRecord
from repositories.message_repository import MessageRepository
from services.kidzuki_service import KidzukiService
from services.slack_service import SlackService
from services.tag_service import TagService
from services.text_utils import extract_urls, normalize_text


class HistoryService:
    def __init__(
        self,
        slack_service: SlackService,
        repository: MessageRepository,
        tag_service: TagService,
        kidzuki_service: KidzukiService,
    ):
        self.slack_service = slack_service
        self.repository = repository
        self.tag_service = tag_service
        self.kidzuki_service = kidzuki_service

    def sync_history(self, channel: str, limit: int = 200) -> int:
        imported = 0
        for payload in self.slack_service.fetch_channel_history(channel=channel, limit=limit):
            if self.upsert_payload(channel=channel, payload=payload):
                imported += 1
        return imported

    def ingest_event_message(self, channel: str, payload: dict[str, object]) -> bool:
        return self.upsert_payload(channel=channel, payload=payload)

    def upsert_payload(self, channel: str, payload: dict[str, object]) -> bool:
        text = str(payload.get("text", "")).strip()
        if not text:
            return False
        message_ts = str(payload.get("ts", "")).strip()
        if not message_ts:
            return False
        urls = extract_urls(text)
        self.repository.upsert_message(
            MessageRecord(
                message_ts=message_ts,
                thread_ts=self._optional_str(payload.get("thread_ts")),
                channel_id=channel,
                user_id=self._optional_str(payload.get("user")) or "unknown",
                text=text,
                normalized_text=normalize_text(text),
                permalink=self.slack_service.get_permalink(channel=channel, message_ts=message_ts),
                has_url=bool(urls),
                extracted_urls=urls,
                created_at=self._resolve_created_at(payload, message_ts),
                tags=self.tag_service.infer_tags(text),
                kidzuki_flag=self.kidzuki_service.is_kidzuki(text),
            )
        )
        return True

    def _resolve_created_at(self, payload: dict[str, object], message_ts: str) -> datetime:
        raw = self._optional_str(payload.get("created_at"))
        if raw:
            try:
                return datetime.fromisoformat(raw)
            except ValueError:
                pass
        return self.slack_service.unix_ts_to_datetime(message_ts)

    @staticmethod
    def _optional_str(value: object) -> str | None:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return None
