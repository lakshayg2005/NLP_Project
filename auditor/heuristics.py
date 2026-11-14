
"""Phase 1: high-recall filter that decides whether text needs the transformer tier."""

from dataclasses import dataclass, field

from auditor.config import get_settings
from auditor.lexicon import regex_hits


@dataclass
class HeuristicResult:
    suspicious: bool
    regex_hits: dict[str, list[tuple[int, int, str]]] = field(default_factory=dict)
    semantic: dict[str, dict] = field(default_factory=dict)
    reason: str = ""


def screen(text: str, use_semantic: bool = True) -> HeuristicResult:
    """Return whether the supplied text contains a potential dark pattern."""
    hits = regex_hits(text)

    if hits:
        return HeuristicResult(
            suspicious=True,
            regex_hits=hits,
            reason="regex:" + ",".join(sorted(hits)),
        )

    if use_semantic:
        from auditor.embeddings import semantic_scores

        threshold = get_settings().semantic_threshold
        semantic = semantic_scores(text)
        triggered = sorted(
            category
            for category, result in semantic.items()
            if result["score"] >= threshold
        )

        if triggered:
            return HeuristicResult(
                suspicious=True,
                regex_hits=hits,
                semantic=semantic,
                reason="semantic:" + ",".join(triggered),
            )

        return HeuristicResult(
            suspicious=False,
            regex_hits=hits,
            semantic=semantic,
            reason="clean",
        )

    return HeuristicResult(
        suspicious=False,
        regex_hits=hits,
        reason="clean",
    )
