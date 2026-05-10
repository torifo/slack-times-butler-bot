from __future__ import annotations

from handlers.digest_handler import DigestHandler
from services.business_calendar import is_last_business_day_of_week, now_jst
from services.history_service import HistoryService
from services.slack_service import SlackService


def run_weekly_digest(
    digest_handler: DigestHandler,
    history_service: HistoryService,
    slack_service: SlackService,
    source_channel: str,
    post_channel: str,
) -> str:
    current = now_jst()
    if not is_last_business_day_of_week(current.date()):
        return f"skip weekly digest before last business day: {current.date().isoformat()}"
    if source_channel:
        history_service.sync_history(channel=source_channel, limit=500)
    body = digest_handler.build_weekly(current)
    slack_service.post_message(channel=post_channel, text=body)
    return body
