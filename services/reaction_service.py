from __future__ import annotations

from services.slack_service import SlackService


class ReactionService:
    def __init__(self, slack_service: SlackService, reaction_name: str):
        self.slack_service = slack_service
        self.reaction_name = reaction_name

    def add_url_reaction(self, channel: str, timestamp: str) -> None:
        self.slack_service.add_reaction(channel=channel, timestamp=timestamp, reaction=self.reaction_name)
