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
        prompt = self._build_url_prompt(url=url, context_text=context_text, explanation_level=explanation_level)
        if httpx is None:
            return None
        try:
            with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                response = client.post(
                    self._chat_url(),
                    headers=self._headers(),
                    json=prompt,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            return None
        content = self._extract_chat_message(data)
        if not content:
            return None
        parsed = self._parse_key_value_block(content)
        bullets = self._split_list_field(parsed.get("bullets", ""))
        return UrlSummary(
            url=url,
            title=parsed.get("title", url),
            summary=parsed.get("summary", context_text[:180]),
            audience_label=parsed.get("audience_label", "両方"),
            explanation_level=explanation_level,
            bullets=bullets[:4] if bullets else [context_text[:80]],
            value_line=parsed.get("value_line", "共有された理由を短く確認できる内容です。"),
        )

    def _request_digest(self, period_label: str, messages: list[MessageRecord]) -> DigestResult | None:
        prompt = self._build_digest_prompt(period_label=period_label, messages=messages)
        if httpx is None:
            return None
        try:
            with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                response = client.post(
                    self._chat_url(),
                    headers=self._headers(),
                    json=prompt,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            return None
        content = self._extract_chat_message(data)
        if not content:
            return None
        parsed = self._parse_key_value_block(content)
        return DigestResult(
            period_label=period_label,
            summary=parsed.get("summary", f"{period_label} の投稿をまとめました。"),
            themes=self._split_list_field(parsed.get("themes", ""))[:5],
            learnings=self._split_list_field(parsed.get("learnings", ""))[:5],
            action_candidates=self._split_list_field(parsed.get("action_candidates", ""))[:5],
            url_summaries=self._split_list_field(parsed.get("url_summaries", ""))[:5],
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.japan_ai_api_key}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _chat_url(self) -> str:
        return self.settings.japan_ai_base_url.rstrip("/") + self.settings.japan_ai_chat_endpoint

    def _artifact_ids(self) -> list[str]:
        return [item.strip() for item in self.settings.japan_ai_artifact_ids.split(",") if item.strip()]

    def _build_url_prompt(self, url: str, context_text: str, explanation_level: int) -> dict[str, object]:
        return {
            "prompt": (
                "次のURL共有投稿について、Slackスレッド返信用の要約を作成してください。\n"
                "JSONではなく、次のキーを含むプレーンテキストで返してください。\n"
                "title:\nsummary:\naudience_label:\nbullets:\nvalue_line:\n"
                "audience_label は エンジニア向け / ビジネス向け / 両方 のいずれかに限定してください。\n"
                f"URL: {url}\n"
                f"共有文脈: {context_text}\n"
                f"説明レベル: {explanation_level}\n"
                "bullets は 1 行 1 項目で、先頭に '- ' を付けてください。"
            ),
            "systemPrompt": (
                "あなたは Slack times 投稿を整理するアシスタントです。"
                "日本語で簡潔に、Slack にそのまま貼れる出力だけを返してください。"
            ),
            "artifactIds": self._artifact_ids(),
            "model": self.settings.japan_ai_model,
            "chatContextLimit": 10,
            "stream": False,
            "temperature": self.settings.japan_ai_temperature,
        }

    def _build_digest_prompt(self, period_label: str, messages: list[MessageRecord]) -> dict[str, object]:
        message_block = "\n".join(f"- {message.text}" for message in messages) or "- 投稿なし"
        return {
            "prompt": (
                "次の投稿群から digest を作成してください。\n"
                "JSONではなく、次のキーを含むプレーンテキストで返してください。\n"
                "summary:\nthemes:\nlearnings:\naction_candidates:\nurl_summaries:\n"
                "themes, learnings, action_candidates, url_summaries は 1 行 1 項目で、先頭に '- ' を付けてください。\n"
                f"対象期間: {period_label}\n"
                f"投稿一覧:\n{message_block}"
            ),
            "systemPrompt": (
                "あなたは Slack times の digest 編集者です。"
                "日本語で簡潔に、Slack 投稿向けの要点だけを返してください。"
            ),
            "artifactIds": self._artifact_ids(),
            "model": self.settings.japan_ai_model,
            "chatContextLimit": 10,
            "stream": False,
            "temperature": self.settings.japan_ai_temperature,
        }

    @staticmethod
    def _extract_chat_message(data: dict[str, object]) -> str | None:
        status = data.get("status")
        if status != "succeeded":
            return None
        message = data.get("chatMessage")
        return message.strip() if isinstance(message, str) else None

    @staticmethod
    def _parse_key_value_block(content: str) -> dict[str, str]:
        parsed: dict[str, str] = {}
        current_key: str | None = None
        for raw_line in content.splitlines():
            line = raw_line.rstrip()
            if not line:
                continue
            if ":" in line and not line.lstrip().startswith("- "):
                key, value = line.split(":", 1)
                normalized_key = key.strip().lower()
                current_key = normalized_key
                parsed[current_key] = value.strip()
            elif current_key:
                existing = parsed.get(current_key, "")
                parsed[current_key] = f"{existing}\n{line}".strip()
        return parsed

    @staticmethod
    def _split_list_field(value: str) -> list[str]:
        items: list[str] = []
        for line in value.splitlines():
            normalized = line.strip()
            if not normalized:
                continue
            if normalized.startswith("- "):
                normalized = normalized[2:].strip()
            items.append(normalized)
        return items

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
