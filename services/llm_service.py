from __future__ import annotations

from collections import Counter

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    httpx = None

from models.digest import DigestResult
from models.message import MessageRecord
from models.url_summary import UrlSummary
from services.text_utils import top_keywords
from settings import Settings


class LlmService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def summarize_url(self, url: str, context_text: str, explanation_level: int = 2) -> UrlSummary:
        if self.settings.japan_ai_api_key:
            summary = self._request_url_summary(url=url, context_text=context_text, explanation_level=explanation_level)
            if summary:
                return summary
        return self._fallback_url_summary(url=url, context_text=context_text, explanation_level=explanation_level)

    def build_digest(self, period_label: str, messages: list[MessageRecord]) -> DigestResult:
        if self.settings.japan_ai_api_key:
            digest = self._request_digest(period_label=period_label, messages=messages)
            if digest:
                return digest
        return self._fallback_digest(period_label=period_label, messages=messages)

    def _request_url_summary(self, url: str, context_text: str, explanation_level: int) -> UrlSummary | None:
        prompt = {
            "model": self.settings.japan_ai_model,
            "input": {
                "task": "summarize_url",
                "url": url,
                "context_text": context_text,
                "explanation_level": explanation_level,
            },
        }
        if httpx is None:
            return None
        try:
            with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                response = client.post(
                    self.settings.japan_ai_base_url.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.japan_ai_api_key}"},
                    json=prompt,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            return None

        output = data.get("output", {})
        if not isinstance(output, dict):
            return None
        return UrlSummary(
            url=url,
            title=output.get("title", url),
            summary=output.get("summary", context_text[:180]),
            audience_label=output.get("audience_label", "両方"),
            explanation_level=explanation_level,
            bullets=list(output.get("bullets", []))[:4],
            value_line=output.get("value_line", "共有された理由を短く確認できる内容です。"),
        )

    def _request_digest(self, period_label: str, messages: list[MessageRecord]) -> DigestResult | None:
        prompt = {
            "model": self.settings.japan_ai_model,
            "input": {
                "task": "build_digest",
                "period_label": period_label,
                "messages": [message.text for message in messages],
            },
        }
        if httpx is None:
            return None
        try:
            with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                response = client.post(
                    self.settings.japan_ai_base_url.rstrip("/") + "/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.japan_ai_api_key}"},
                    json=prompt,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            return None

        output = data.get("output", {})
        if not isinstance(output, dict):
            return None
        return DigestResult(
            period_label=period_label,
            summary=output.get("summary", f"{period_label} の投稿をまとめました。"),
            themes=list(output.get("themes", []))[:5],
            learnings=list(output.get("learnings", []))[:5],
            action_candidates=list(output.get("action_candidates", []))[:5],
            url_summaries=list(output.get("url_summaries", []))[:5],
        )

    def _fallback_url_summary(self, url: str, context_text: str, explanation_level: int) -> UrlSummary:
        lowered = context_text.lower()
        if any(word in lowered for word in ("api", "python", "sql", "slack", "fastapi", "ai")):
            audience_label = "エンジニア向け"
        elif any(word in lowered for word in ("sales", "marketing", "biz", "事業", "稟議", "経営")):
            audience_label = "ビジネス向け"
        else:
            audience_label = "両方"

        bullets = [
            f"共有文脈: {context_text[:60]}".strip(),
            f"説明レベル {explanation_level} を前提に確認しやすくしています。",
            "本文確認前に論点を把握できるように短く整理しています。",
        ]
        summary = context_text[:180] if context_text else "共有された URL の要点確認用メモです。"
        return UrlSummary(
            url=url,
            title=url,
            summary=summary,
            audience_label=audience_label,
            explanation_level=explanation_level,
            bullets=bullets,
            value_line="先に概要を押さえてから本文に入れる構成です。",
        )

    def _fallback_digest(self, period_label: str, messages: list[MessageRecord]) -> DigestResult:
        texts = [message.text for message in messages]
        keywords = top_keywords(texts, limit=5)
        url_counter = Counter(url for message in messages for url in message.extracted_urls)

        themes = [f"{keyword} が複数回登場" for keyword in keywords[:3]]
        learnings = [message.text[:60] for message in messages if message.kidzuki_flag][:3]
        if not learnings and messages:
            learnings = [messages[-1].text[:60]]
        action_candidates = [f"{keyword} に関するメモを整理する" for keyword in keywords[:2]]
        url_summaries = [f"{url} が {count} 回共有" for url, count in url_counter.most_common(3)]
        summary = f"{period_label} の投稿 {len(messages)} 件から主要トピックを整理しました。"
        return DigestResult(
            period_label=period_label,
            summary=summary,
            themes=themes,
            learnings=learnings,
            action_candidates=action_candidates,
            url_summaries=url_summaries,
        )
