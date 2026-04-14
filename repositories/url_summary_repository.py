from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from models.url_summary import UrlSummary
from repositories.message_repository import MessageRepository


class UrlSummaryRepository:
    def __init__(self, database_path: Path):
        self._repository = MessageRepository(database_path)

    def initialize(self) -> None:
        self._repository.initialize()

    def get(self, url: str) -> UrlSummary | None:
        with self._repository.connect() as connection:
            row = connection.execute(
                "SELECT * FROM url_summaries WHERE url = ?",
                (url,),
            ).fetchone()
        if not row:
            return None
        return UrlSummary(
            url=row["url"],
            title=row["title"],
            summary=row["summary"],
            audience_label=row["audience_label"],
            explanation_level=row["explanation_level"],
            bullets=json.loads(row["bullets"]),
            value_line=row["value_line"],
        )

    def save(self, summary: UrlSummary) -> None:
        with self._repository.connect() as connection:
            connection.execute(
                """
                INSERT INTO url_summaries (
                    url, title, summary, audience_label, explanation_level, bullets, value_line, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    summary = excluded.summary,
                    audience_label = excluded.audience_label,
                    explanation_level = excluded.explanation_level,
                    bullets = excluded.bullets,
                    value_line = excluded.value_line,
                    updated_at = excluded.updated_at
                """,
                (
                    summary.url,
                    summary.title,
                    summary.summary,
                    summary.audience_label,
                    summary.explanation_level,
                    json.dumps(summary.bullets, ensure_ascii=False),
                    summary.value_line,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
