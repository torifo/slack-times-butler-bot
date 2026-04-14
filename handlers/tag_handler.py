from __future__ import annotations

from repositories.tag_repository import TagRepository
from services.tag_service import TagService


class TagHandler:
    def __init__(self, tag_service: TagService, tag_repository: TagRepository):
        self.tag_service = tag_service
        self.tag_repository = tag_repository

    def apply_instruction(self, message_ts: str, text: str) -> list[str] | None:
        operation = self.tag_service.parse_tag_instruction(text)
        if not operation:
            return None
        current = set(self.tag_repository.list_tags(message_ts))
        current.update(operation.add)
        current.difference_update(operation.remove)
        updated = sorted(current)
        self.tag_repository.replace_tags(message_ts, updated)
        return updated
