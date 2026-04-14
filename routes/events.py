from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from dependencies import (
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
        channel = event.get("channel") or get_settings().source_channel
        message_ts = event.get("ts", "")
        text = event.get("text", "")
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
            channel=event.get("channel", get_settings().post_target_channel),
            user_id=event.get("user", ""),
        )

    return {"status": "accepted"}
