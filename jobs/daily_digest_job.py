from __future__ import annotations

from datetime import datetime

from handlers.digest_handler import DigestHandler
from services.slack_service import SlackService


def run_daily_digest(digest_handler: DigestHandler, slack_service: SlackService, post_channel: str) -> str:
    body = digest_handler.build_daily(datetime.utcnow())
    slack_service.post_message(channel=post_channel, text=body)
    return body
