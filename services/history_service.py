from __future__ import annotations

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
            text = payload.get("text", "").strip()
            if not text:
                continue
            urls = extract_urls(text)
            message = MessageRecord(
                message_ts=payload["ts"],
                thread_ts=payload.get("thread_ts"),
                channel_id=channel,
                user_id=payload.get("user", "unknown"),
                text=text,
                normalized_text=normalize_text(text),
                permalink=self.slack_service.get_permalink(channel=channel, message_ts=payload["ts"]),
                has_url=bool(urls),
                extracted_urls=urls,
                created_at=self.slack_service.unix_ts_to_datetime(payload["ts"]),
                tags=self.tag_service.infer_tags(text),
                kidzuki_flag=self.kidzuki_service.is_kidzuki(text),
            )
            self.repository.upsert_message(message)
            imported += 1
        return imported
