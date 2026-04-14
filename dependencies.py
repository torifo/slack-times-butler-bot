from __future__ import annotations

from functools import lru_cache

from repositories.digest_repository import DigestRepository
from repositories.message_repository import MessageRepository
from repositories.settings_repository import SettingsRepository
from repositories.tag_repository import TagRepository
from repositories.url_summary_repository import UrlSummaryRepository
from services.digest_service import DigestService
from services.history_service import HistoryService
from services.kidzuki_service import KidzukiService
from services.llm_service import LlmService
from services.reaction_service import ReactionService
from services.search_service import SearchService
from services.slack_service import SlackService
from services.tag_service import TagService
from services.url_summary_service import UrlSummaryService
from services.welcome_service import WelcomeService
from settings import get_settings


@lru_cache(maxsize=1)
def get_message_repository() -> MessageRepository:
    repository = MessageRepository(get_settings().database_path)
    repository.initialize()
    return repository


@lru_cache(maxsize=1)
def get_digest_repository() -> DigestRepository:
    repository = DigestRepository(get_settings().database_path)
    repository.initialize()
    return repository


@lru_cache(maxsize=1)
def get_url_summary_repository() -> UrlSummaryRepository:
    repository = UrlSummaryRepository(get_settings().database_path)
    repository.initialize()
    return repository


@lru_cache(maxsize=1)
def get_tag_repository() -> TagRepository:
    repository = TagRepository(get_settings().database_path)
    repository.initialize()
    return repository


@lru_cache(maxsize=1)
def get_settings_repository() -> SettingsRepository:
    repository = SettingsRepository(get_settings().database_path)
    repository.initialize()
    return repository


@lru_cache(maxsize=1)
def get_slack_service() -> SlackService:
    return SlackService(bot_token=get_settings().slack_bot_token)


@lru_cache(maxsize=1)
def get_tag_service() -> TagService:
    return TagService()


@lru_cache(maxsize=1)
def get_kidzuki_service() -> KidzukiService:
    return KidzukiService()


@lru_cache(maxsize=1)
def get_llm_service() -> LlmService:
    return LlmService(get_settings())


@lru_cache(maxsize=1)
def get_history_service() -> HistoryService:
    return HistoryService(
        slack_service=get_slack_service(),
        repository=get_message_repository(),
        tag_service=get_tag_service(),
        kidzuki_service=get_kidzuki_service(),
    )


@lru_cache(maxsize=1)
def get_digest_service() -> DigestService:
    return DigestService(
        message_repository=get_message_repository(),
        digest_repository=get_digest_repository(),
        llm_service=get_llm_service(),
    )


@lru_cache(maxsize=1)
def get_url_summary_service() -> UrlSummaryService:
    return UrlSummaryService(
        repository=get_url_summary_repository(),
        llm_service=get_llm_service(),
    )


@lru_cache(maxsize=1)
def get_search_service() -> SearchService:
    return SearchService(repository=get_message_repository())


@lru_cache(maxsize=1)
def get_reaction_service() -> ReactionService:
    return ReactionService(
        slack_service=get_slack_service(),
        reaction_name=get_settings().url_reaction_name,
    )


@lru_cache(maxsize=1)
def get_welcome_service() -> WelcomeService:
    return WelcomeService()
