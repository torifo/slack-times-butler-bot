from __future__ import annotations

from datetime import datetime

from models.digest import DigestResult
from repositories.digest_repository import DigestRepository
from repositories.message_repository import MessageRepository
from services.llm_service import LlmService


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

    def format_digest(self, digest: DigestResult) -> str:
        sections = [
            f"*{digest.period_label} digest*",
            digest.summary,
        ]
        if digest.themes:
            sections.append("主なテーマ: " + " / ".join(digest.themes))
        if digest.learnings:
            sections.append("気づき: " + " / ".join(digest.learnings))
        if digest.action_candidates:
            sections.append("アクション候補: " + " / ".join(digest.action_candidates))
        if digest.url_summaries:
            sections.append("共有URL: " + " / ".join(digest.url_summaries))
        return "\n".join(sections)
