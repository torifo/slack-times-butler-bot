from __future__ import annotations

from models.url_summary import UrlSummary
from repositories.url_summary_repository import UrlSummaryRepository
from services.llm_service import LlmService


class UrlSummaryService:
    def __init__(self, repository: UrlSummaryRepository, llm_service: LlmService):
        self.repository = repository
        self.llm_service = llm_service

    def get_or_create(self, url: str, context_text: str, explanation_level: int = 2) -> UrlSummary:
        cached = self.repository.get(url)
        if cached and cached.explanation_level == explanation_level:
            return cached
        summary = self.llm_service.summarize_url(url=url, context_text=context_text, explanation_level=explanation_level)
        self.repository.save(summary)
        return summary

    def format_thread_reply(self, summary: UrlSummary) -> str:
        bullets = "\n".join(f"• {bullet}" for bullet in summary.bullets[:4])
        return (
            f"[{summary.audience_label}] 概要をまとめました\n"
            f"{summary.summary}\n"
            f"{bullets}\n"
            f"価値: {summary.value_line}"
        ).strip()
