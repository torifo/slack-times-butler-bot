from __future__ import annotations

from services.reaction_service import ReactionService
from services.url_summary_service import UrlSummaryService
from services.text_utils import extract_urls


class UrlHandler:
    def __init__(self, url_summary_service: UrlSummaryService, reaction_service: ReactionService):
        self.url_summary_service = url_summary_service
        self.reaction_service = reaction_service

    def handle_message(self, channel: str, message_ts: str, text: str, explanation_level: int = 2) -> str | None:
        urls = extract_urls(text)
        if not urls:
            return None

        url = urls[0]
        summary = self.url_summary_service.get_or_create(
            url=url,
            context_text=text,
            explanation_level=explanation_level,
        )
        self.reaction_service.add_url_reaction(channel=channel, timestamp=message_ts)
        return self.url_summary_service.format_thread_reply(summary)
