from dataclasses import dataclass, field


@dataclass(slots=True)
class UrlSummary:
    url: str
    title: str
    summary: str
    audience_label: str
    explanation_level: int
    bullets: list[str] = field(default_factory=list)
    value_line: str = ""
