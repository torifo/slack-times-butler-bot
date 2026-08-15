from __future__ import annotations

import re
from collections import Counter

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    httpx = None

try:
    from slack_sdk import WebClient as SlackWebClient
except ModuleNotFoundError:  # pragma: no cover
    SlackWebClient = None

from models.digest import DigestResult
from models.message import MessageRecord
from models.url_summary import UrlSummary
from services.text_utils import top_keywords
from settings import Settings


class LlmService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def summarize_url(self, url: str, context_text: str, explanation_level: int = 2) -> UrlSummary:
        if self._gateway_enabled() or self.settings.japan_ai_api_key:
            summary = self._request_url_summary(url=url, context_text=context_text, explanation_level=explanation_level)
            if summary:
                return summary
        return self._fallback_url_summary(url=url, context_text=context_text, explanation_level=explanation_level)

    def build_digest(self, period_label: str, messages: list[MessageRecord]) -> DigestResult:
        if self._gateway_enabled() or self.settings.japan_ai_api_key:
            digest = self._request_digest(period_label=period_label, messages=messages)
            if digest:
                return digest
        return self._fallback_digest(period_label=period_label, messages=messages)

    def _gateway_enabled(self) -> bool:
        return self.settings.llm_backend == "claude_gateway" and httpx is not None

    def _request_gateway_text(self, task: str, prompt_payload: dict[str, object]) -> str | None:
        """llm-gateway（127.0.0.1・Claude Max枠）にタスクラベル付きで依頼する。

        本命ポートに接続できない場合のみ予備ポートを試す。429（枠制御）や
        5xx はゲートウェイ側の判断なので予備は試さず、JAPAN AI フォールバックへ。
        """
        body = {
            "task": task,
            "prompt": str(prompt_payload.get("prompt", "")),
            "system_prompt": str(prompt_payload.get("systemPrompt", "")),
        }
        for base_url in (self.settings.llm_gateway_url, self.settings.llm_gateway_url_backup):
            if not base_url:
                continue
            try:
                with httpx.Client(timeout=self.settings.llm_gateway_timeout_seconds) as client:
                    response = client.post(base_url.rstrip("/") + "/v1/complete", json=body)
            except httpx.ConnectError:
                continue
            except httpx.HTTPError:
                return None
            if response.status_code != 200:
                return None
            try:
                data = response.json()
            except ValueError:
                return None
            text = data.get("text")
            return text.strip() if isinstance(text, str) and text.strip() else None
        return None

    def _request_japan_ai_text(self, prompt_payload: dict[str, object]) -> str | None:
        if httpx is None or not self.settings.japan_ai_api_key:
            return None
        try:
            with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                response = client.post(
                    self._chat_url(),
                    headers=self._headers(),
                    json=prompt_payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            return None
        return self._extract_chat_message(data)

    def _request_chat_text(self, task: str, prompt_payload: dict[str, object]) -> str | None:
        content = None
        if self._gateway_enabled():
            content = self._request_gateway_text(task, prompt_payload)
        if content is None:
            content = self._request_japan_ai_text(prompt_payload)
        return content

    def _request_url_summary(self, url: str, context_text: str, explanation_level: int) -> UrlSummary | None:
        prompt = self._build_url_prompt(url=url, context_text=context_text, explanation_level=explanation_level)
        content = self._request_chat_text("times.url_summary", prompt)
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
        task = "times.digest.daily" if "daily" in period_label.lower() else "times.digest.weekly"
        content = self._request_chat_text(task, prompt)
        if not content:
            return None
        return DigestResult(
            period_label=period_label,
            summary=content,
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
                "\n"
                "各キーの要件:\n"
                "- title: 記事・ページの内容を表す簡潔なタイトル（元タイトルの直訳でなくてよい）\n"
                "- summary: 2文以内。何についての内容で、結論・要点は何かまで踏み込む\n"
                "- audience_label: エンジニア向け / ビジネス向け / 両方 のいずれか\n"
                "- bullets: 読みどころを最大3項目、1行1項目で先頭に '- '。"
                "「〜が書かれている」でなく中身そのもの（数字・結論・手法）を書く\n"
                "- value_line: 「どんな人が・何のために読むと得か」を1行で\n"
                "\n"
                "禁止: 「〜という記事です」等の冗長な前置き、URLから推測できない内容の創作\n"
                f"URL: {url}\n"
                f"共有文脈: {context_text}\n"
                f"説明レベル: {explanation_level}（1=平易 / 2=標準 / 3=専門的）"
            ),
            "systemPrompt": (
                "あなたは Slack times 投稿を整理するアシスタントです。"
                "日本語で簡潔に、Slack にそのまま貼れる出力だけを返してください。"
            ),
            "userId": self.settings.japan_ai_user_id,
            "artifactIds": self._artifact_ids(),
            "model": self.settings.japan_ai_model,
            "chatContextLimit": 10,
            "stream": False,
            "temperature": self.settings.japan_ai_temperature,
        }

    def _resolve_mentions(self, messages: list[MessageRecord]) -> list[str]:
        if not (SlackWebClient and self.settings.slack_bot_token):
            return [m.text for m in messages]
        client = SlackWebClient(token=self.settings.slack_bot_token)
        cache: dict[str, str] = {}

        def resolve(text: str) -> str:
            def replacer(match: re.Match) -> str:
                user_id = match.group(1)
                if user_id not in cache:
                    try:
                        resp = client.users_info(user=user_id)
                        profile = resp["user"]["profile"]
                        cache[user_id] = profile.get("display_name") or profile.get("real_name", user_id)
                    except Exception:
                        cache[user_id] = user_id
                return cache[user_id]
            return re.sub(r"<@([A-Z0-9]+)>", replacer, text)

        return [resolve(m.text) for m in messages]

    def _build_digest_prompt(self, period_label: str, messages: list[MessageRecord]) -> dict[str, object]:
        resolved_texts = self._resolve_mentions(messages)
        message_block = "\n".join(f"- {text}" for text in resolved_texts) or "- 投稿なし"
        channel_name = self.settings.source_channel_name or self.settings.source_channel
        date = period_label.split()[0] if period_label else period_label
        is_weekly = "weekly" in period_label.lower()

        common_rules = (
            "## チャンネルの前提\n"
            "このチャンネルは**個人の活動ログ（times チャンネル）**です。\n"
            "投稿の主語が省略されている場合は、チャンネルオーナー本人の行動・発言として読んでください。\n"
            "「本人が〜した」「〜に取り組んだ」のように自然な日本語で書いてください。\n"
            "\n"
            "---\n"
            f"{message_block}\n"
            "---\n"
            "\n"
            "## 共通ルール\n"
            "- 実際に起きた出来事・話題・気づきを自然な日本語でまとめる\n"
            "- 複数の投稿が同じ話題なら1つにまとめる\n"
            "- 全行「— 」始まりのフラットな箇条書き。セクション見出しは作らない\n"
            "- 行の種類をマーカーで区別する: 出来事・やったこと=マーカーなし / "
            "気づき・学び=「— 💡 」/ 問いかけ・未解決=「— ❓ 」\n"
            "- 投稿数・時間帯などの統計情報を出さない\n"
            "- 「〜について会話が展開」のような機械的な表現を使わない\n"
            "- テキストの断片をそのままテーマとして抜き出さない\n"
            "- ツールの動作説明（日記の主役でないもの）は除外する\n"
        )

        if is_weekly:
            body = (
                f"以下は、Slackチャンネル「{channel_name}」の {date} からの1週間のメッセージ一覧です。\n"
                "\n"
                f"{common_rules}"
                "\n"
                "## 週次の役割（日次との違い・重要）\n"
                "週次は「長い日次」ではなく**週の物語**です。\n"
                "- 複数日にまたがる流れは1つのテーマ行に統合する（例: 「◯◯の運用見直しが進行："
                "問題の自覚→ルール再設計の判断」のように週の中での進展まで含める）\n"
                "- 単発の細かい出来事は拾わない。週として意味のあるものだけ残す\n"
                "- 未解決・回答待ちのまま週を越えるものは「— ⏭️ 」で最後にまとめる\n"
                "\n"
                "## 出力形式（厳守）\n"
                "\n"
                f"*{date}週 weekly digest(#{channel_name})*\n"
                "— [今週の中心テーマとその進展を1〜2文で]\n"
                "— 💡 [今週の学び]\n"
                "— ⏭️ [持ち越し・未解決]\n"
                "...（テーマ2〜3件＋学び＋持ち越しで最大6件）\n"
                "\n"
                "活動がない場合は「今週は投稿がありませんでした」と記載する。"
            )
        else:
            body = (
                f"以下は、Slackチャンネル「{channel_name}」の {date} のメッセージ一覧です。\n"
                "\n"
                f"{common_rules}"
                "\n"
                "## 優先順位（高い順に採用）\n"
                "1. 実際にやったこと・作ったもの・解決したこと\n"
                "2. 決定・判断・気づき（次の行動につながるもの）\n"
                "3. 質問・疑問（具体的に誰かに投げかけたもの）\n"
                "\n"
                "## 除外ルール\n"
                "- 「〜を疑問に思った」だけで終わる内容（行動につながっていないもの）\n"
                "\n"
                "## 出力形式（厳守）\n"
                "\n"
                f"*{date} daily digest(#{channel_name})*\n"
                "— [出来事・やったことを1文で]\n"
                "— 💡 [気づき・学び（あれば）]\n"
                "— ❓ [問いかけ・未解決（あれば）]\n"
                "...（最大5件。💡・❓は該当がある場合のみ）\n"
                "\n"
                "活動がない場合は「本日は投稿がありませんでした」と記載する。"
            )

        return {
            "prompt": body,
            "systemPrompt": (
                "あなたは Slack times の digest 編集者です。"
                "日本語で簡潔に返してください。"
            ),
            "userId": self.settings.japan_ai_user_id,
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
        keywords = top_keywords(texts, limit=8)
        url_counter = Counter(url for message in messages for url in message.extracted_urls)
        user_counter = Counter(message.user_id for message in messages)
        tag_counter = Counter(tag for message in messages for tag in message.tags)
        hour_buckets = Counter(self._hour_bucket(message.created_at.hour) for message in messages)
        daily_counter = Counter(message.created_at.date().isoformat() for message in messages)

        themes = [f"{keyword} を中心に会話が展開" for keyword in keywords[:4]]
        learnings = [self._compact_text(message.text, 70) for message in messages if message.kidzuki_flag][:4]
        if not learnings and messages:
            learnings = [self._compact_text(messages[-1].text, 70)]
        activity_metrics = [
            f"投稿数 {len(messages)} 件",
            f"投稿者 {len(user_counter)} 人",
            f"URL共有 {sum(1 for message in messages if message.has_url)} 件",
            f"気づき判定 {sum(1 for message in messages if message.kidzuki_flag)} 件",
        ]
        if hour_buckets:
            bucket, count = hour_buckets.most_common(1)[0]
            activity_metrics.append(f"発話が多い時間帯 {bucket} ({count} 件)")
        theme_breakdown = [f"{tag} {count} 件" for tag, count in tag_counter.most_common(4)]
        if not theme_breakdown:
            theme_breakdown = [f"{keyword} 周辺の投稿が目立つ" for keyword in keywords[:3]]
        momentum_signals: list[str] = []
        if daily_counter:
            first_day, first_count = sorted(daily_counter.items())[0]
            last_day, last_count = sorted(daily_counter.items())[-1]
            momentum_signals.append(f"序盤 {first_day} は {first_count} 件、終盤 {last_day} は {last_count} 件")
        if len(keywords) >= 2:
            momentum_signals.append(f"{keywords[0]} から {keywords[1]} へ話題が接続")
        if hour_buckets:
            momentum_signals.append("主な稼働帯は " + " / ".join(f"{bucket}:{count}" for bucket, count in hour_buckets.most_common(3)))
        notable_points = [self._compact_text(message.text, 80) for message in messages[-3:]]
        action_candidates = [f"{keyword} に関するメモを整理する" for keyword in keywords[:3]]
        if tag_counter:
            action_candidates.append(f"{tag_counter.most_common(1)[0][0]} の内容を週次で棚卸しする")
        url_summaries = [f"{url} が {count} 回共有" for url, count in url_counter.most_common(3)]
        summary = f"{period_label} の投稿 {len(messages)} 件から主要トピックを整理しました。"
        return DigestResult(
            period_label=period_label,
            summary=summary,
            activity_metrics=activity_metrics,
            themes=themes,
            theme_breakdown=theme_breakdown,
            learnings=learnings,
            momentum_signals=momentum_signals[:4],
            notable_points=notable_points,
            action_candidates=action_candidates,
            url_summaries=url_summaries,
        )

    @staticmethod
    def _hour_bucket(hour: int) -> str:
        if 5 <= hour < 12:
            return "朝"
        if 12 <= hour < 18:
            return "昼"
        if 18 <= hour < 24:
            return "夜"
        return "深夜"

    @staticmethod
    def _compact_text(text: str, limit: int) -> str:
        normalized = " ".join(text.split())
        return normalized[:limit] + ("…" if len(normalized) > limit else "")
