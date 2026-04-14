from __future__ import annotations

from datetime import datetime

from handlers.digest_handler import DigestHandler
from handlers.search_handler import SearchHandler


class MentionHandler:
    def __init__(self, digest_handler: DigestHandler, search_handler: SearchHandler):
        self.digest_handler = digest_handler
        self.search_handler = search_handler

    def handle(self, text: str, now: datetime | None = None) -> str:
        now = now or datetime.utcnow()
        lowered = text.lower()
        if "今日" in text or "daily" in lowered:
            return self.digest_handler.build_daily(now)
        if "今週" in text or "weekly" in lowered:
            return self.digest_handler.build_weekly(now)
        if "search" in lowered or "検索" in text:
            query = text.replace("検索", "").replace("search", "").strip()
            return self.search_handler.handle(query=query)
        return "使えるコマンド: daily / weekly / search"
