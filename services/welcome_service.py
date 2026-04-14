from __future__ import annotations


class WelcomeService:
    def build_public_message(self, user_id: str) -> str:
        return f"<@{user_id}> さん、ようこそ。times-Butler が補助に入ります。"

    def build_private_message(self) -> str:
        return (
            "この Bot は times の振り返り、URL 補助、検索を担当します。\n"
            "まずは URL 投稿と digest を中心に動作確認してください。"
        )
