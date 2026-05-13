from __future__ import annotations

import unittest
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from handlers.tag_handler import TagHandler
from handlers.digest_handler import DigestHandler
from jobs.daily_digest_job import run_daily_digest
from jobs.weekly_digest_job import run_weekly_digest
from models.message import MessageRecord
from repositories.digest_repository import DigestRepository
from repositories.message_repository import MessageRepository
from repositories.tag_repository import TagRepository
from repositories.url_summary_repository import UrlSummaryRepository
from services.business_calendar import is_business_day, is_last_business_day_of_week
from services.digest_service import DigestService
from services.kidzuki_service import KidzukiService
from services.llm_service import LlmService
from services.search_service import SearchService
from services.slack_service import SlackService
from services.tag_service import TagService
from services.url_summary_service import UrlSummaryService
from settings import Settings
from zoneinfo import ZoneInfo


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

    def test_search_service_can_collect_may_business_day_messages(self) -> None:
        repository = MessageRepository(self.database_path)
        for message_ts, text, created_at in (
            ("1.0", "5月1日の平日データ", datetime(2026, 5, 1, 9, 0, tzinfo=UTC)),
            ("2.0", "5月3日の休日データ", datetime(2026, 5, 3, 9, 0, tzinfo=UTC)),
            ("3.0", "5月6日の祝日データ", datetime(2026, 5, 6, 9, 0, tzinfo=UTC)),
            ("4.0", "5月7日の平日データ", datetime(2026, 5, 7, 9, 0, tzinfo=UTC)),
            ("5.0", "6月1日の月跨ぎデータ", datetime(2026, 6, 1, 9, 0, tzinfo=UTC)),
        ):
            seed_message(
                repository,
                MessageRecord(
                    message_ts=message_ts,
                    thread_ts=None,
                    channel_id="C1",
                    user_id="U1",
                    text=text,
                    normalized_text=text,
                    permalink=f"https://example.com/{message_ts}",
                    has_url=False,
                    extracted_urls=[],
                    created_at=created_at,
                    tags=[],
                    kidzuki_flag=False,
                ),
            )

        service = SearchService(repository)
        may_results = service.search(
            query="",
            start_date=datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
            end_date=datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
            limit=10,
        )

        may_business_day_results = [
            message for message in may_results if is_business_day(message.created_at.astimezone(ZoneInfo("Asia/Tokyo")).date())
        ]

        self.assertEqual(["4.0", "1.0"], [message.message_ts for message in may_business_day_results])

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
        self.assertTrue(digest.activity_metrics)
        self.assertTrue(digest.themes)
        self.assertTrue(digest.notable_points)
        snapshots = service.build_daily_snapshots(
            start_at=datetime.now(UTC) - timedelta(days=1),
            end_at=datetime.now(UTC) + timedelta(days=1),
        )
        self.assertEqual(1, len(snapshots))
        self.assertIn("投稿数: 1 件", service.format_canvas_weekly_summary(snapshots, datetime.now(UTC)))

    def test_daily_digest_uses_jst_day_boundary(self) -> None:
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
                text="朝の投稿",
                normalized_text="朝の投稿",
                permalink="https://example.com/1",
                has_url=False,
                extracted_urls=[],
                created_at=datetime(2026, 5, 10, 23, 30, tzinfo=UTC),
                tags=[],
                kidzuki_flag=False,
            )
        )
        service = DigestService(message_repository, digest_repository, LlmService(settings))
        handler = DigestHandler(service)

        body = handler.build_daily(datetime(2026, 5, 11, 18, 30, tzinfo=ZoneInfo("Asia/Tokyo")))

        self.assertIn("投稿数 1 件", body)

    def test_open_digest_is_rebuilt_instead_of_returning_stale_cache(self) -> None:
        settings = self.make_settings()
        message_repository = MessageRepository(settings.database_path)
        digest_repository = DigestRepository(settings.database_path)
        message_repository.initialize()
        digest_repository.initialize()
        service = DigestService(message_repository, digest_repository, LlmService(settings))

        start_at = datetime.now(UTC) - timedelta(hours=1)
        end_at = datetime.now(UTC) + timedelta(hours=1)
        first = service.build_digest(
            digest_key="daily:open",
            period_label="open daily",
            start_at=start_at,
            end_at=end_at,
        )
        self.assertIn("投稿 0 件", first.summary)

        message_repository.upsert_message(
            MessageRecord(
                message_ts="1.0",
                thread_ts=None,
                channel_id="C1",
                user_id="U1",
                text="途中で増えた投稿",
                normalized_text="途中で増えた投稿",
                permalink="https://example.com/1",
                has_url=False,
                extracted_urls=[],
                created_at=datetime.now(UTC),
                tags=[],
                kidzuki_flag=False,
            )
        )

        second = service.build_digest(
            digest_key="daily:open",
            period_label="open daily",
            start_at=start_at,
            end_at=end_at,
        )

        self.assertIn("投稿 1 件", second.summary)

    def test_llm_service_parses_japan_ai_non_stream_response(self) -> None:
        parsed = LlmService._extract_chat_message(
            {
                "status": "succeeded",
                "sessionId": "abc123",
                "chatMessage": "summary: 要約\n"
                "activity_metrics:\n- 投稿数 12 件\n"
                "themes:\n- API\n- Slack\n"
                "theme_breakdown:\n- 技術 60%\n"
                "learnings:\n- 学び1\n"
                "momentum_signals:\n- 前半は調査、後半は実装\n"
                "notable_points:\n- API 設計の迷いが見えた\n"
                "action_candidates:\n- 行動1\n"
                "url_summaries:\n- https://example.com",
                "references": [],
            }
        )

        self.assertEqual(
            "summary: 要約\nactivity_metrics:\n- 投稿数 12 件\nthemes:\n- API\n- Slack\ntheme_breakdown:\n- 技術 60%\nlearnings:\n- 学び1\nmomentum_signals:\n- 前半は調査、後半は実装\nnotable_points:\n- API 設計の迷いが見えた\naction_candidates:\n- 行動1\nurl_summaries:\n- https://example.com",
            parsed,
        )

    def test_llm_service_rejects_failed_response(self) -> None:
        parsed = LlmService._extract_chat_message(
            {"status": "failed", "errorMessage": "model not found", "references": []}
        )
        self.assertIsNone(parsed)

    def test_business_calendar_skips_weekend_and_holiday(self) -> None:
        self.assertFalse(is_business_day(date(2026, 5, 10)))
        self.assertFalse(is_business_day(date(2026, 5, 6)))
        self.assertTrue(is_business_day(date(2026, 5, 7)))
        self.assertTrue(is_last_business_day_of_week(date(2026, 5, 8)))
        self.assertFalse(is_last_business_day_of_week(date(2026, 5, 7)))
        self.assertTrue(is_last_business_day_of_week(date(2026, 5, 1)))
        self.assertTrue(is_last_business_day_of_week(date(2026, 12, 31)))
        self.assertFalse(is_last_business_day_of_week(date(2027, 1, 1)))
        self.assertTrue(is_last_business_day_of_week(date(2026, 9, 18)))
        self.assertFalse(is_last_business_day_of_week(date(2026, 9, 21)))
        self.assertFalse(is_last_business_day_of_week(date(2026, 9, 22)))
        self.assertFalse(is_last_business_day_of_week(date(2026, 9, 23)))
        self.assertFalse(is_last_business_day_of_week(date(2026, 9, 24)))
        self.assertTrue(is_last_business_day_of_week(date(2026, 9, 25)))

    def test_slack_service_resolves_channel_id_from_multiple_shapes(self) -> None:
        self.assertEqual("C123", SlackService.resolve_channel_id({"channel": "C123"}))
        self.assertEqual("C234", SlackService.resolve_channel_id({"channel": {"id": "C234"}}))
        self.assertEqual("C345", SlackService.resolve_channel_id({"item": {"channel": "C345"}}))
        self.assertEqual(
            "C567",
            SlackService.resolve_channel_id({"authorizations": [{"channel_id": "C567"}]}),
        )
        self.assertEqual("C456", SlackService.resolve_channel_id({}, fallback="C456"))

    def test_daily_digest_skips_holiday_without_posting(self) -> None:
        class DummyDigestHandler:
            def build_daily(self, base_time: datetime) -> str:
                raise AssertionError("build_daily should not be called on a holiday")

        class DummySlackService:
            def __init__(self) -> None:
                self.called = False

            def post_message(self, channel: str, text: str, thread_ts: str | None = None) -> None:
                self.called = True

        from unittest.mock import patch

        slack_service = DummySlackService()
        with patch("jobs.daily_digest_job.now_jst", return_value=datetime(2026, 5, 6, 9, 0)):
            result = run_daily_digest(DummyDigestHandler(), object(), slack_service, "C-src", "C1")

        self.assertIn("skip daily digest on holiday", result)
        self.assertFalse(slack_service.called)

    def test_weekly_digest_syncs_and_posts_on_last_business_day(self) -> None:
        class DummyDigestHandler:
            def build_weekly(self, base_time: datetime) -> str:
                return f"weekly:{base_time.date().isoformat()}"

            def build_weekly_canvas(self, base_time: datetime) -> str | None:
                return "# Weekly Daily Summary\n## 2026-05-08"

        class DummyHistoryService:
            def __init__(self) -> None:
                self.calls: list[tuple[str, int]] = []

            def sync_history(self, channel: str, limit: int = 200) -> int:
                self.calls.append((channel, limit))
                return 3

        class DummySlackService:
            def __init__(self) -> None:
                self.posts: list[tuple[str, str]] = []
                self.canvas_updates: list[tuple[str, str]] = []

            def post_message(self, channel: str, text: str, thread_ts: str | None = None) -> None:
                self.posts.append((channel, text))

            def replace_canvas(self, canvas_id: str, markdown: str) -> None:
                self.canvas_updates.append((canvas_id, markdown))

        from unittest.mock import patch

        history_service = DummyHistoryService()
        slack_service = DummySlackService()
        with patch("jobs.weekly_digest_job.now_jst", return_value=datetime(2026, 5, 8, 19, 0)):
            result = run_weekly_digest(
                DummyDigestHandler(),
                history_service,
                slack_service,
                "C-src",
                "C-post",
                "F0B2DHP5A3Z",
            )

        self.assertEqual([("C-src", 500)], history_service.calls)
        self.assertEqual([("C-post", "weekly:2026-05-08")], slack_service.posts)
        self.assertEqual([("F0B2DHP5A3Z", "# Weekly Daily Summary\n## 2026-05-08")], slack_service.canvas_updates)
        self.assertEqual("weekly:2026-05-08", result)

    def test_weekly_digest_skips_before_last_business_day(self) -> None:
        class DummyDigestHandler:
            def build_weekly(self, base_time: datetime) -> str:
                raise AssertionError("build_weekly should not run before the last business day")

        class DummyHistoryService:
            def sync_history(self, channel: str, limit: int = 200) -> int:
                raise AssertionError("sync_history should not run before the last business day")

        class DummySlackService:
            def post_message(self, channel: str, text: str, thread_ts: str | None = None) -> None:
                raise AssertionError("post_message should not run before the last business day")

        from unittest.mock import patch

        with patch("jobs.weekly_digest_job.now_jst", return_value=datetime(2026, 5, 7, 19, 0)):
            result = run_weekly_digest(DummyDigestHandler(), DummyHistoryService(), DummySlackService(), "C-src", "C-post")

        self.assertIn("skip weekly digest before last business day", result)


if __name__ == "__main__":
    unittest.main()
