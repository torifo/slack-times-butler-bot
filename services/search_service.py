from __future__ import annotations

from datetime import datetime

from models.message import MessageRecord
from repositories.message_repository import MessageRepository


class SearchService:
    def __init__(self, repository: MessageRepository):
        self.repository = repository

    def search(
        self,
        query: str,
        tags: list[str] | None = None,
        has_url: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        use_or: bool = False,
        limit: int = 10,
    ) -> list[MessageRecord]:
        keywords = [part.lower() for part in query.split() if part]
        return self.repository.search_messages(
            keywords=keywords,
            use_or=use_or,
            tags=tags,
            has_url=has_url,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    def format_results(self, results: list[MessageRecord]) -> str:
        lines = [f"該当 {len(results)} 件"]
        for message in results:
            tags = f" tags={','.join(message.tags)}" if message.tags else ""
            lines.append(f"- {message.created_at.date()} {message.text[:60]} {message.permalink}{tags}".rstrip())
        return "\n".join(lines)
