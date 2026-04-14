from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from handlers.tag_handler import TagHandler
from models.message import MessageRecord
from repositories.digest_repository import DigestRepository
from repositories.message_repository import MessageRepository
from repositories.tag_repository import TagRepository
from repositories.url_summary_repository import UrlSummaryRepository
from services.digest_service import DigestService
from services.kidzuki_service import KidzukiService
from services.llm_service import LlmService
from services.search_service import SearchService
from services.tag_service import TagService
from services.url_summary_service import UrlSummaryService
from settings import Settings


def seed_message(repository: MessageRepository, message: MessageRecord) -> None:
    repository.initialize()
    repository.upsert_message(message)


class ServicesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.database_path = Path(self.temp_dir.name) / "test.sqlite3"

    def make_settings(self) -> Settings:
        return Settings(
            DATABASE_PATH=self.database_path,
            JAPAN_AI_API_KEY="",
        )

    def test_search_service_filters_keyword_and_tag(self) -> None:
        repository = MessageRepository(self.database_path)
        seed_message(
            repository,
            MessageRecord(
                message_ts="1.0",
                thread_ts=None,
                channel_id="C1",
                user_id="U1",
                text="Python API の学びを整理した",
                normalized_text="python api の学びを整理した",
                permalink="https://example.com/1",
                has_url=False,
                extracted_urls=[],
                created_at=datetime(2026, 4, 15, 10, 0, 0),
                tags=["技術"],
                kidzuki_flag=True,
            ),
        )
        seed_message(
            repository,
            MessageRecord(
                message_ts="2.0",
                thread_ts=None,
                channel_id="C1",
                user_id="U1",
                text="営業フロー改善のメモ",
                normalized_text="営業フロー改善のメモ",
                permalink="https://example.com/2",
                has_url=False,
                extracted_urls=[],
                created_at=datetime(2026, 4, 15, 11, 0, 0),
                tags=["業務改善"],
                kidzuki_flag=False,
            ),
        )

        service = SearchService(repository)
        results = service.search(query="Python", tags=["技術"])

        self.assertEqual(1, len(results))
        self.assertEqual("1.0", results[0].message_ts)

    def test_tag_handler_applies_thread_instruction(self) -> None:
        repository = MessageRepository(self.database_path)
        repository.initialize()
        repository.upsert_message(
            MessageRecord(
                message_ts="1.0",
                thread_ts=None,
                channel_id="C1",
                user_id="U1",
                text="API の調査",
                normalized_text="api の調査",
                permalink="https://example.com/1",
                has_url=False,
                extracted_urls=[],
                created_at=datetime(2026, 4, 15, 10, 0, 0),
                tags=["技術"],
                kidzuki_flag=False,
            )
        )

        handler = TagHandler(TagService(), TagRepository(self.database_path))
        updated = handler.apply_instruction("1.0", "tag: +法務 -技術")

        self.assertEqual(["法務"], updated)

    def test_url_summary_service_uses_cache(self) -> None:
        settings = self.make_settings()
        service = UrlSummaryService(UrlSummaryRepository(settings.database_path), LlmService(settings))
        service.repository.initialize()

        first = service.get_or_create("https://example.com", "Slack API の記事", explanation_level=2)
        second = service.get_or_create("https://example.com", "別文脈", explanation_level=2)

        self.assertEqual(first.summary, second.summary)
        self.assertEqual("エンジニア向け", second.audience_label)

    def test_digest_service_builds_digest(self) -> None:
        settings = self.make_settings()
        message_repository = MessageRepository(settings.database_path)
        digest_repository = DigestRepository(settings.database_path)
        message_repository.initialize()
        digest_repository.initialize()
        message_repository.upsert_message(
            MessageRecord(
                message_ts="1.0",
                thread_ts=None,
                channel_id="C1",
                user_id="U1",
                text="気づき: Python API の設計を改善した",
                normalized_text="気づき python api の設計を改善した",
                permalink="https://example.com/1",
                has_url=True,
                extracted_urls=["https://example.com/article"],
                created_at=datetime.now(UTC),
                tags=["技術", "業務改善"],
                kidzuki_flag=KidzukiService().is_kidzuki("気づき: Python API の設計を改善した"),
            )
        )
        service = DigestService(message_repository, digest_repository, LlmService(settings))

        digest = service.build_digest(
            digest_key="daily:2026-04-15",
            period_label="2026-04-15 daily",
            start_at=datetime.now(UTC) - timedelta(days=1),
            end_at=datetime.now(UTC) + timedelta(days=1),
        )

        self.assertIn("投稿 1 件", digest.summary)
        self.assertTrue(digest.themes)

    def test_llm_service_parses_japan_ai_non_stream_response(self) -> None:
        parsed = LlmService._extract_chat_message(
            {
                "status": "succeeded",
                "sessionId": "abc123",
                "chatMessage": "summary: 要約\n"
                "themes:\n- API\n- Slack\n"
                "learnings:\n- 学び1\n"
                "action_candidates:\n- 行動1\n"
                "url_summaries:\n- https://example.com",
                "references": [],
            }
        )

        self.assertEqual(
            "summary: 要約\nthemes:\n- API\n- Slack\nlearnings:\n- 学び1\naction_candidates:\n- 行動1\nurl_summaries:\n- https://example.com",
            parsed,
        )

    def test_llm_service_rejects_failed_response(self) -> None:
        parsed = LlmService._extract_chat_message(
            {"status": "failed", "errorMessage": "model not found", "references": []}
        )
        self.assertIsNone(parsed)


if __name__ == "__main__":
    unittest.main()
