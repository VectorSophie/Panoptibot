from __future__ import annotations

from panoptibot.bot.config import Settings
from panoptibot.copycat.core import (
    CopycatProfile,
    CopycatSession,
    build_labeled_reply,
    is_allowed_copycat_text,
)
from panoptibot.copycat.lm_studio import generate_lm_studio_reply


def build_copycat_prompts(
    *,
    profile: CopycatProfile,
    session: CopycatSession,
    incoming_text: str,
    style_examples: list[str],
) -> tuple[str, str]:
    system_prompt = (
        "You are Panoptibot producing a short away-proxy quote. "
        "Return only the text Jack would say, without attribution or quotation marks. "
        "Do not invent unsupported facts, secrets, commitments, or private data."
    )
    user_prompt = "\n".join(
        [
            f"Display name: {profile.display_name}",
            f"Status note: {session.status_note or 'away'}",
            f"Tone notes: {', '.join(profile.tone_notes) or 'casual, concise'}",
            f"Catchphrases: {', '.join(profile.catchphrases) or 'none configured'}",
            f"Spelling quirks: {', '.join(profile.spelling_quirks) or 'none configured'}",
            f"Hard facts: {', '.join(profile.hard_facts) or 'none configured'}",
            "Recent examples:",
            *[f"- {example}" for example in style_examples[-6:]],
            f"Incoming message: {incoming_text}",
        ]
    )
    return system_prompt, user_prompt


def fallback_copycat_text(profile: CopycatProfile, incoming_text: str) -> str:
    if "vc" in incoming_text.lower():
        return "i can prob vc when im back"
    if profile.catchphrases:
        return profile.catchphrases[0]
    return "not sure tbh, ask me when im back"


def generate_copycat_text(
    *,
    settings: Settings,
    profile: CopycatProfile,
    session: CopycatSession,
    incoming_text: str,
    style_examples: list[str],
) -> tuple[str, str, str]:
    system_prompt, user_prompt = build_copycat_prompts(
        profile=profile,
        session=session,
        incoming_text=incoming_text,
        style_examples=style_examples,
    )
    if not is_allowed_copycat_text(incoming_text, profile.never_say):
        return (
            "Panoptibot will not answer that for him.",
            "refused",
            system_prompt + "\n" + user_prompt,
        )
    try:
        generated = generate_lm_studio_reply(
            base_url=settings.lm_studio_base_url,
            model=settings.lm_studio_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=settings.lm_studio_max_tokens,
            temperature=settings.lm_studio_temperature,
            timeout_seconds=settings.lm_studio_timeout_seconds,
        )
        if is_allowed_copycat_text(generated, profile.never_say):
            return generated, "generated", system_prompt + "\n" + user_prompt
    except Exception:
        pass
    return (
        fallback_copycat_text(profile, incoming_text),
        "fallback",
        system_prompt + "\n" + user_prompt,
    )


def format_copycat_response(profile: CopycatProfile, generated_text: str, decision: str) -> str:
    if decision == "refused":
        return f"@{profile.display_name} is away, but {generated_text}"
    return build_labeled_reply(profile, generated_text)
