from __future__ import annotations

from services.slack_service import SlackService
from services.welcome_service import WelcomeService


class WelcomeHandler:
    def __init__(self, slack_service: SlackService, welcome_service: WelcomeService):
        self.slack_service = slack_service
        self.welcome_service = welcome_service

    def handle_member_joined(self, channel: str, user_id: str) -> None:
        self.slack_service.post_message(channel=channel, text=self.welcome_service.build_public_message(user_id))
        self.slack_service.post_message(channel=user_id, text=self.welcome_service.build_private_message())
