from dataclasses import dataclass, field


@dataclass(slots=True)
class DigestResult:
    period_label: str
    summary: str
    activity_metrics: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    theme_breakdown: list[str] = field(default_factory=list)
    learnings: list[str] = field(default_factory=list)
    momentum_signals: list[str] = field(default_factory=list)
    notable_points: list[str] = field(default_factory=list)
    action_candidates: list[str] = field(default_factory=list)
    url_summaries: list[str] = field(default_factory=list)
