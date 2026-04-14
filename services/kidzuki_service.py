from __future__ import annotations


class KidzukiService:
    HINTS = ("気づき", "学び", "初めて", "なるほど", "発見", "改善", "知った")

    def is_kidzuki(self, text: str) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in self.HINTS)
