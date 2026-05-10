from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from dependencies import (
    get_history_service,
    get_reaction_service,
    get_settings,
    get_slack_service,
    get_tag_repository,
    get_tag_service,
    get_url_summary_service,
    get_welcome_service,
)
from handlers.tag_handler import TagHandler
from handlers.url_handler import UrlHandler
from handlers.welcome_handler import WelcomeHandler

router = APIRouter(prefix="/slack")
logger = logging.getLogger(__name__)


class SlackEnvelope(BaseModel):
    type: str
    challenge: str | None = None
    event: dict = Field(default_factory=dict)


@router.post("/events")
def handle_events(payload: SlackEnvelope) -> dict[str, str]:
    if payload.type == "url_verification":
        return {"challenge": payload.challenge or ""}

    event = payload.event
    event_type = event.get("type")
    if event_type == "message" and not event.get("bot_id"):
        url_handler = UrlHandler(
            url_summary_service=get_url_summary_service(),
            reaction_service=get_reaction_service(),
        )
        tag_handler = TagHandler(
            tag_service=get_tag_service(),
            tag_repository=get_tag_repository(),
        )
        channel = get_slack_service().resolve_channel_id(event, fallback=get_settings().source_channel)
        message_ts = event.get("ts", "")
        text = event.get("text", "")
        if not channel:
            logger.warning("Skipping message event because channel id could not be resolved. ts=%s", message_ts)
            return {"status": "accepted"}
        get_history_service().ingest_event_message(channel=channel, payload=event)
        if event.get("thread_ts") and text.lower().startswith("tag:"):
            tag_handler.apply_instruction(message_ts=event["thread_ts"], text=text)
        else:
            reply = url_handler.handle_message(
                channel=channel,
                message_ts=message_ts,
                text=text,
                explanation_level=get_settings().default_explanation_level,
            )
            if reply:
                get_slack_service().post_message(channel=channel, text=reply, thread_ts=message_ts)

    if event_type == "member_joined_channel":
        WelcomeHandler(
            slack_service=get_slack_service(),
            welcome_service=get_welcome_service(),
        ).handle_member_joined(
            channel=get_slack_service().resolve_channel_id(event, fallback=get_settings().post_target_channel),
            user_id=event.get("user", ""),
        )

    return {"status": "accepted"}
