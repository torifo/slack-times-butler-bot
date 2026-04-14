from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ModuleNotFoundError:  # pragma: no cover
    WebClient = None

    class SlackApiError(Exception):
        def __init__(self, response: dict[str, Any] | None = None):
            self.response = response or {}


@dataclass(slots=True)
class SlackHistoryItem:
    channel: str
    ts: str
    user: str
    text: str
    permalink: str
    thread_ts: str | None = None


class SlackService:
    def __init__(self, bot_token: str):
        self.client = WebClient(token=bot_token) if (WebClient and bot_token) else None

    def fetch_channel_history(self, channel: str, limit: int = 200) -> list[dict[str, Any]]:
        if not self.client or not channel:
            return []
        cursor: str | None = None
        messages: list[dict[str, Any]] = []
        while True:
            response = self.client.conversations_history(channel=channel, limit=min(limit, 200), cursor=cursor)
            messages.extend(response.get("messages", []))
            cursor = response.get("response_metadata", {}).get("next_cursor")
            if not cursor or len(messages) >= limit:
                break
        return messages[:limit]

    def get_permalink(self, channel: str, message_ts: str) -> str:
        if not self.client:
            return f"https://slack.invalid/archives/{channel}/p{message_ts.replace('.', '')}"
        response = self.client.chat_getPermalink(channel=channel, message_ts=message_ts)
        return response["permalink"]

    def post_message(self, channel: str, text: str, thread_ts: str | None = None) -> None:
        if not self.client or not channel:
            return
        kwargs: dict[str, Any] = {"channel": channel, "text": text}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        self.client.chat_postMessage(**kwargs)

    def add_reaction(self, channel: str, timestamp: str, reaction: str) -> None:
        if not self.client:
            return
        try:
            self.client.reactions_add(channel=channel, timestamp=timestamp, name=reaction)
        except SlackApiError as error:
            if error.response.get("error") != "already_reacted":
                raise

    @staticmethod
    def unix_ts_to_datetime(ts: str) -> datetime:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
