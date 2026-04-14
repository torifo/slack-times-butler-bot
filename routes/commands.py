from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Form

from dependencies import get_digest_service, get_search_service
from handlers.digest_handler import DigestHandler
from handlers.search_handler import SearchHandler

router = APIRouter(prefix="/slack")


@router.post("/commands/times")
def handle_times_command(text: str = Form(default="")) -> dict[str, str]:
    command_text = text.strip()
    now = datetime.utcnow()

    if command_text.startswith("digest today"):
        body = DigestHandler(get_digest_service()).build_daily(now)
    elif command_text.startswith("digest week"):
        body = DigestHandler(get_digest_service()).build_weekly(now)
    elif command_text.startswith("search"):
        query = command_text.removeprefix("search").strip()
        body = SearchHandler(get_search_service()).handle(query=query)
    else:
        body = "使えるコマンド: /times digest today | /times digest week | /times search <keyword>"
    return {"response_type": "ephemeral", "text": body}
