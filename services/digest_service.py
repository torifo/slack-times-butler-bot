from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from models.digest import DigestResult
from repositories.digest_repository import DigestRepository
from repositories.message_repository import MessageRepository
from services.llm_service import LlmService


@dataclass(slots=True)
class DailyDigestSnapshot:
    day_label: str
    message_count: int
    digest: DigestResult


class DigestService:
    def __init__(
        self,
        message_repository: MessageRepository,
        digest_repository: DigestRepository,
        llm_service: LlmService,
    ):
        self.message_repository = message_repository
        self.digest_repository = digest_repository
        self.llm_service = llm_service

    def build_digest(self, digest_key: str, period_label: str, start_at: datetime, end_at: datetime) -> DigestResult:
        cached = self.digest_repository.get(digest_key)
        if cached:
            return cached

        messages = self.message_repository.list_messages_between(start_at=start_at, end_at=end_at)
        digest = self.llm_service.build_digest(period_label=period_label, messages=messages)
        self.digest_repository.save(digest_key=digest_key, digest=digest)
        return digest

    def build_daily_snapshots(self, start_at: datetime, end_at: datetime) -> list[DailyDigestSnapshot]:
        snapshots: list[DailyDigestSnapshot] = []
        current = start_at
        while current < end_at:
            day_end = current + timedelta(days=1)
            messages = self.message_repository.list_messages_between(start_at=current, end_at=day_end)
            if messages:
                day_label = current.date().isoformat()
                digest = self.build_digest(
                    digest_key=f"daily:{day_label}",
                    period_label=f"{day_label} daily",
                    start_at=current,
                    end_at=day_end,
                )
                snapshots.append(
                    DailyDigestSnapshot(
                        day_label=day_label,
                        message_count=len(messages),
                        digest=digest,
                    )
                )
            current = day_end
        return snapshots

    def format_digest(self, digest: DigestResult) -> str:
        sections = [
            f"*{digest.period_label} digest*",
            digest.summary,
        ]
        if digest.activity_metrics:
            sections.append("活動サマリ:\n" + "\n".join(f"• {item}" for item in digest.activity_metrics))
        if digest.themes:
            sections.append("主なテーマ:\n" + "\n".join(f"• {item}" for item in digest.themes))
        if digest.theme_breakdown:
            sections.append("テーマ配分:\n" + "\n".join(f"• {item}" for item in digest.theme_breakdown))
        if digest.learnings:
            sections.append("気づき:\n" + "\n".join(f"• {item}" for item in digest.learnings))
        if digest.momentum_signals:
            sections.append("流れの変化:\n" + "\n".join(f"• {item}" for item in digest.momentum_signals))
        if digest.notable_points:
            sections.append("印象的な論点:\n" + "\n".join(f"• {item}" for item in digest.notable_points))
        if digest.action_candidates:
            sections.append("アクション候補:\n" + "\n".join(f"• {item}" for item in digest.action_candidates))
        if digest.url_summaries:
            sections.append("共有URL:\n" + "\n".join(f"• {item}" for item in digest.url_summaries))
        return "\n".join(sections)

    def format_canvas_weekly_summary(self, snapshots: list[DailyDigestSnapshot], generated_at: datetime) -> str:
        lines = [
            "# Weekly Daily Summary",
            f"更新日時: {generated_at.strftime('%Y-%m-%d %H:%M')}",
            "",
        ]
        for snapshot in snapshots:
            lines.extend(
                [
                    f"## {snapshot.day_label}",
                    f"- 投稿数: {snapshot.message_count} 件",
                    f"- 要約: {snapshot.digest.summary}",
                ]
            )
            if snapshot.digest.themes:
                lines.append("- 主なテーマ: " + " / ".join(snapshot.digest.themes[:3]))
            if snapshot.digest.learnings:
                lines.append("- 気づき: " + " / ".join(snapshot.digest.learnings[:2]))
            if snapshot.digest.action_candidates:
                lines.append("- 次の一手: " + " / ".join(snapshot.digest.action_candidates[:2]))
            lines.append("")
        return "\n".join(lines).strip()
