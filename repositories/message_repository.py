from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from models.message import MessageRecord


class MessageRepository:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_ts TEXT PRIMARY KEY,
                    thread_ts TEXT,
                    channel_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    normalized_text TEXT NOT NULL,
                    permalink TEXT NOT NULL,
                    has_url INTEGER NOT NULL DEFAULT 0,
                    extracted_urls TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    kidzuki_flag INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_ts TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    UNIQUE(message_ts, tag)
                );

                CREATE TABLE IF NOT EXISTS url_summaries (
                    url TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    audience_label TEXT NOT NULL,
                    explanation_level INTEGER NOT NULL,
                    bullets TEXT NOT NULL DEFAULT '[]',
                    value_line TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS digests (
                    digest_key TEXT PRIMARY KEY,
                    period_label TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    activity_metrics TEXT NOT NULL DEFAULT '[]',
                    themes TEXT NOT NULL DEFAULT '[]',
                    theme_breakdown TEXT NOT NULL DEFAULT '[]',
                    learnings TEXT NOT NULL DEFAULT '[]',
                    momentum_signals TEXT NOT NULL DEFAULT '[]',
                    notable_points TEXT NOT NULL DEFAULT '[]',
                    action_candidates TEXT NOT NULL DEFAULT '[]',
                    url_summaries TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(digests)").fetchall()}
            for name in ("activity_metrics", "theme_breakdown", "momentum_signals", "notable_points"):
                if name not in columns:
                    connection.execute(f"ALTER TABLE digests ADD COLUMN {name} TEXT NOT NULL DEFAULT '[]'")

    def upsert_message(self, message: MessageRecord) -> None:
        created_at = self._normalize_datetime(message.created_at)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO messages (
                    message_ts, thread_ts, channel_id, user_id, text, normalized_text,
                    permalink, has_url, extracted_urls, created_at, kidzuki_flag
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_ts) DO UPDATE SET
                    thread_ts = excluded.thread_ts,
                    channel_id = excluded.channel_id,
                    user_id = excluded.user_id,
                    text = excluded.text,
                    normalized_text = excluded.normalized_text,
                    permalink = excluded.permalink,
                    has_url = excluded.has_url,
                    extracted_urls = excluded.extracted_urls,
                    created_at = excluded.created_at,
                    kidzuki_flag = excluded.kidzuki_flag
                """,
                (
                    message.message_ts,
                    message.thread_ts,
                    message.channel_id,
                    message.user_id,
                    message.text,
                    message.normalized_text,
                    message.permalink,
                    int(message.has_url),
                    json.dumps(message.extracted_urls, ensure_ascii=False),
                    created_at.isoformat(),
                    int(message.kidzuki_flag),
                ),
            )
            connection.execute("DELETE FROM tags WHERE message_ts = ?", (message.message_ts,))
            if message.tags:
                connection.executemany(
                    "INSERT OR IGNORE INTO tags (message_ts, tag) VALUES (?, ?)",
                    [(message.message_ts, tag) for tag in sorted(set(message.tags))],
                )

    def list_messages_between(self, start_at: datetime, end_at: datetime) -> list[MessageRecord]:
        start_at = self._normalize_datetime(start_at)
        end_at = self._normalize_datetime(end_at)
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    m.*,
                    COALESCE(json_group_array(t.tag), '[]') AS tags_json
                FROM messages m
                LEFT JOIN tags t ON t.message_ts = m.message_ts
                WHERE m.created_at >= ? AND m.created_at < ?
                GROUP BY m.message_ts
                ORDER BY m.created_at ASC
                """,
                (start_at.isoformat(), end_at.isoformat()),
            ).fetchall()
        return [self._row_to_message(row) for row in rows]

    def search_messages(
        self,
        keywords: list[str],
        use_or: bool = False,
        tags: list[str] | None = None,
        has_url: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 20,
    ) -> list[MessageRecord]:
        clauses: list[str] = []
        params: list[object] = []

        if keywords:
            operator = " OR " if use_or else " AND "
            like_clauses = []
            for keyword in keywords:
                like_clauses.append("normalized_text LIKE ?")
                params.append(f"%{keyword.lower()}%")
            clauses.append(f"({' '.join([operator.join(like_clauses)])})")

        if tags:
            tag_placeholders = ",".join("?" for _ in tags)
            clauses.append(
                f"m.message_ts IN (SELECT message_ts FROM tags WHERE tag IN ({tag_placeholders}) GROUP BY message_ts HAVING COUNT(DISTINCT tag) >= ?)"
            )
            params.extend(tags)
            params.append(len(tags))

        if has_url is not None:
            clauses.append("has_url = ?")
            params.append(int(has_url))

        if start_date:
            start_date = self._normalize_datetime(start_date)
            clauses.append("created_at >= ?")
            params.append(start_date.isoformat())

        if end_date:
            end_date = self._normalize_datetime(end_date)
            clauses.append("created_at < ?")
            params.append(end_date.isoformat())

        where_clause = "WHERE " + " AND ".join(clauses) if clauses else ""
        query = f"""
            SELECT
                m.*,
                COALESCE(json_group_array(t.tag), '[]') AS tags_json
            FROM messages m
            LEFT JOIN tags t ON t.message_ts = m.message_ts
            {where_clause}
            GROUP BY m.message_ts
            ORDER BY m.created_at DESC
            LIMIT ?
        """
        params.append(limit)

        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_message(row) for row in rows]

    def _row_to_message(self, row: sqlite3.Row) -> MessageRecord:
        raw_tags = [tag for tag in json.loads(row["tags_json"]) if tag is not None]
        return MessageRecord(
            message_ts=row["message_ts"],
            thread_ts=row["thread_ts"],
            channel_id=row["channel_id"],
            user_id=row["user_id"],
            text=row["text"],
            normalized_text=row["normalized_text"],
            permalink=row["permalink"],
            has_url=bool(row["has_url"]),
            extracted_urls=json.loads(row["extracted_urls"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            tags=sorted(set(raw_tags)),
            kidzuki_flag=bool(row["kidzuki_flag"]),
        )

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
