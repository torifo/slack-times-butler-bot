from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from models.digest import DigestResult
from repositories.message_repository import MessageRepository


class DigestRepository:
    def __init__(self, database_path: Path):
        self._repository = MessageRepository(database_path)

    def initialize(self) -> None:
        self._repository.initialize()

    def get(self, digest_key: str) -> DigestResult | None:
        with self._repository.connect() as connection:
            row = connection.execute(
                "SELECT * FROM digests WHERE digest_key = ?",
                (digest_key,),
            ).fetchone()
        if not row:
            return None
        return DigestResult(
            period_label=row["period_label"],
            summary=row["summary"],
            activity_metrics=json.loads(row["activity_metrics"]) if "activity_metrics" in row.keys() else [],
            themes=json.loads(row["themes"]),
            theme_breakdown=json.loads(row["theme_breakdown"]) if "theme_breakdown" in row.keys() else [],
            learnings=json.loads(row["learnings"]),
            momentum_signals=json.loads(row["momentum_signals"]) if "momentum_signals" in row.keys() else [],
            notable_points=json.loads(row["notable_points"]) if "notable_points" in row.keys() else [],
            action_candidates=json.loads(row["action_candidates"]),
            url_summaries=json.loads(row["url_summaries"]),
        )

    def save(self, digest_key: str, digest: DigestResult) -> None:
        with self._repository.connect() as connection:
            connection.execute(
                """
                INSERT INTO digests (
                    digest_key, period_label, summary, activity_metrics, themes, theme_breakdown,
                    learnings, momentum_signals, notable_points, action_candidates, url_summaries, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(digest_key) DO UPDATE SET
                    period_label = excluded.period_label,
                    summary = excluded.summary,
                    activity_metrics = excluded.activity_metrics,
                    themes = excluded.themes,
                    theme_breakdown = excluded.theme_breakdown,
                    learnings = excluded.learnings,
                    momentum_signals = excluded.momentum_signals,
                    notable_points = excluded.notable_points,
                    action_candidates = excluded.action_candidates,
                    url_summaries = excluded.url_summaries,
                    created_at = excluded.created_at
                """,
                (
                    digest_key,
                    digest.period_label,
                    digest.summary,
                    json.dumps(digest.activity_metrics, ensure_ascii=False),
                    json.dumps(digest.themes, ensure_ascii=False),
                    json.dumps(digest.theme_breakdown, ensure_ascii=False),
                    json.dumps(digest.learnings, ensure_ascii=False),
                    json.dumps(digest.momentum_signals, ensure_ascii=False),
                    json.dumps(digest.notable_points, ensure_ascii=False),
                    json.dumps(digest.action_candidates, ensure_ascii=False),
                    json.dumps(digest.url_summaries, ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
