from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class MessageRecord:
    message_ts: str
    channel_id: str
    user_id: str
    text: str
    normalized_text: str
    permalink: str
    created_at: datetime
    thread_ts: str | None = None
    has_url: bool = False
    extracted_urls: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    kidzuki_flag: bool = False
