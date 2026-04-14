from __future__ import annotations

import re

from models.tag import TagOperation


class TagService:
    DEFAULT_RULES = {
        "技術": ("python", "api", "sql", "slack", "fastapi", "llm", "ai"),
        "業務改善": ("改善", "運用", "フロー", "効率", "自動化"),
        "法務": ("契約", "法務", "規約", "コンプラ"),
        "思考法": ("振り返り", "学び", "気づき", "考え方"),
        "ビジネス": ("稟議", "売上", "事業", "営業", "顧客"),
    }

    def infer_tags(self, text: str) -> list[str]:
        lowered = text.lower()
        inferred = [tag for tag, keywords in self.DEFAULT_RULES.items() if any(keyword in lowered for keyword in keywords)]
        return sorted(set(inferred))

    def parse_tag_instruction(self, text: str) -> TagOperation | None:
        if not text.lower().startswith("tag:"):
            return None
        payload = text.split(":", 1)[1]
        add: list[str] = []
        remove: list[str] = []
        for chunk in re.split(r"[,\s]+", payload.strip()):
            if not chunk:
                continue
            if chunk.startswith("-"):
                remove.append(chunk[1:])
            elif chunk.startswith("+"):
                add.append(chunk[1:])
            else:
                add.append(chunk)
        return TagOperation(add=sorted(set(add)), remove=sorted(set(remove)))
