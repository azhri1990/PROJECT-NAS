"""Advisory recommendations that never grant execution authority."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Recommendation:
    title: str
    explanation: str
    benefit: str
    risk: str
    alternatives: tuple[str, ...] = ()
    requires_approval: bool = False
    authorizes_execution: bool = False


class RecommendationEngine:
    """Build deterministic advisory objects for future JARVIS planners."""

    def build(
        self,
        *,
        title: str,
        explanation: str,
        benefit: str,
        risk: str,
        alternatives: tuple[str, ...] = (),
    ) -> Recommendation:
        for field_name, value in (
            ("title", title),
            ("explanation", explanation),
            ("benefit", benefit),
            ("risk", risk),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must not be empty")
        if not isinstance(alternatives, tuple):
            raise ValueError("alternatives must be a tuple")
        return Recommendation(
            title=title.strip(),
            explanation=explanation.strip(),
            benefit=benefit.strip(),
            risk=risk.strip(),
            alternatives=tuple(item.strip() for item in alternatives if item.strip()),
        )
