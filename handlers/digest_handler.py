from __future__ import annotations

from datetime import datetime, timedelta

from services.digest_service import DailyDigestSnapshot, DigestService


class DigestHandler:
    def __init__(self, digest_service: DigestService):
        self.digest_service = digest_service

    def build_daily(self, base_time: datetime) -> str:
        start_at = base_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_at = start_at + timedelta(days=1)
        digest = self.digest_service.build_digest(
            digest_key=f"daily:{start_at.date().isoformat()}",
            period_label=f"{start_at.date().isoformat()} daily",
            start_at=start_at,
            end_at=end_at,
        )
        return self.digest_service.format_digest(digest)

    def build_weekly(self, base_time: datetime) -> str:
        start_at = base_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=base_time.weekday())
        end_at = start_at + timedelta(days=7)
        digest = self.digest_service.build_digest(
            digest_key=f"weekly:{start_at.date().isoformat()}",
            period_label=f"{start_at.date().isoformat()} weekly",
            start_at=start_at,
            end_at=end_at,
        )
        return self.digest_service.format_digest(digest)

    def build_weekly_canvas(self, base_time: datetime) -> str | None:
        start_at = base_time.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=base_time.weekday())
        end_at = start_at + timedelta(days=7)
        snapshots = self.digest_service.build_daily_snapshots(start_at=start_at, end_at=end_at)
        if not snapshots:
            return None
        return self.digest_service.format_canvas_weekly_summary(snapshots=snapshots, generated_at=base_time)
