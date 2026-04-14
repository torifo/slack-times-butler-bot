from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from dependencies import get_digest_service, get_settings, get_slack_service
from handlers.digest_handler import DigestHandler
from jobs.daily_digest_job import run_daily_digest
from jobs.weekly_digest_job import run_weekly_digest
from routes.commands import router as commands_router
from routes.events import router as events_router
from routes.health import router as health_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    app.include_router(events_router)
    app.include_router(commands_router)

    scheduler = BackgroundScheduler(timezone="Asia/Tokyo")

    @app.on_event("startup")
    def startup() -> None:
        digest_handler = DigestHandler(get_digest_service())
        slack_service = get_slack_service()
        daily_minute, daily_hour, *_ = settings.daily_digest_cron.split()
        weekly_minute, weekly_hour, *_weekly_rest = settings.weekly_digest_cron.split()
        weekly_day = settings.weekly_digest_cron.split()[-1]

        scheduler.add_job(
            run_daily_digest,
            "cron",
            hour=int(daily_hour),
            minute=int(daily_minute),
            kwargs={
                "digest_handler": digest_handler,
                "slack_service": slack_service,
                "post_channel": settings.post_target_channel,
            },
            id="daily-digest",
            replace_existing=True,
        )
        scheduler.add_job(
            run_weekly_digest,
            "cron",
            day_of_week=weekly_day.lower(),
            hour=int(weekly_hour),
            minute=int(weekly_minute),
            kwargs={
                "digest_handler": digest_handler,
                "slack_service": slack_service,
                "post_channel": settings.post_target_channel,
            },
            id="weekly-digest",
            replace_existing=True,
        )
        if not scheduler.running:
            scheduler.start()

    @app.on_event("shutdown")
    def shutdown() -> None:
        if scheduler.running:
            scheduler.shutdown(wait=False)

    return app


app = create_app()
