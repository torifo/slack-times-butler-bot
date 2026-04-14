from dataclasses import dataclass, field


@dataclass(slots=True)
class DigestResult:
    period_label: str
    summary: str
    themes: list[str] = field(default_factory=list)
    learnings: list[str] = field(default_factory=list)
    action_candidates: list[str] = field(default_factory=list)
    url_summaries: list[str] = field(default_factory=list)
