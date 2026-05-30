from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SocialFact:
    subject_names: tuple[str, ...]
    related_names: tuple[str, ...]
    action: str
    evidence_urls: tuple[str, ...]
    confidence: float = 1.0
    channel_name: str | None = None


def render_catchup_bullets(facts: list[SocialFact], viewer_name: str) -> list[str]:
    lines = [f"Catch-up for @{viewer_name}"]
    for fact in facts:
        sentence = _fact_sentence(fact)
        if fact.confidence < 0.6:
            sentence = f"Looks like {sentence}"
        source = fact.evidence_urls[0] if fact.evidence_urls else "no source"
        lines.append(f"- {sentence}. Source: {source}")
    return lines


def _fact_sentence(fact: SocialFact) -> str:
    subject = _join_names(fact.subject_names)
    related = _join_names(fact.related_names)
    if fact.action == "would_hang_out_later":
        return f"{subject} said he would hang out with {related} later"
    if fact.action == "can_vc_now":
        return f"{subject} said he can VC right now"
    if fact.action == "asked_question":
        return f"{subject} asked a question"
    if fact.action == "made_plan":
        if related:
            return f"{subject} made plans with {related}"
        return f"{subject} made plans"
    return f"{subject} said something worth catching up on"


def _join_names(names: tuple[str, ...]) -> str:
    if not names:
        return "Someone"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f" and {names[-1]}"
