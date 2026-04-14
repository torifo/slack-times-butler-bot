from __future__ import annotations

from pathlib import Path

from repositories.message_repository import MessageRepository


class TagRepository:
    def __init__(self, database_path: Path):
        self._repository = MessageRepository(database_path)

    def initialize(self) -> None:
        self._repository.initialize()

    def replace_tags(self, message_ts: str, tags: list[str]) -> None:
        with self._repository.connect() as connection:
            connection.execute("DELETE FROM tags WHERE message_ts = ?", (message_ts,))
            if tags:
                connection.executemany(
                    "INSERT OR IGNORE INTO tags (message_ts, tag) VALUES (?, ?)",
                    [(message_ts, tag) for tag in sorted(set(tags))],
                )

    def list_tags(self, message_ts: str) -> list[str]:
        with self._repository.connect() as connection:
            rows = connection.execute(
                "SELECT tag FROM tags WHERE message_ts = ? ORDER BY tag ASC",
                (message_ts,),
            ).fetchall()
        return [row["tag"] for row in rows]
