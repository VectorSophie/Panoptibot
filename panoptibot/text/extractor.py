from __future__ import annotations

import re

_QUESTION_STARTERS = frozenset({
    "what", "who", "why", "how", "when", "where", "is", "are", "does", "can", "did",
})

_STOP_WORDS = frozenset({
    "the", "and", "for", "that", "with", "this", "are", "was", "not", "but",
    "you", "all", "from", "they", "will", "have", "been", "has", "its", "our",
    "his", "her", "their", "your", "had", "him", "she", "one", "can", "get",
    "got", "just", "like", "also", "more", "into", "over", "then", "than",
    "out", "about", "which", "some", "very", "any", "would", "could", "should",
    "when", "what", "where", "who", "how", "why", "did", "does", "dont", "isnt",
    "wasnt", "werent", "didnt", "doesnt", "wont", "well", "yes", "yeah", "nope",
    "okay", "lol", "omg", "there", "here", "now", "still", "even", "only",
    "being", "doing", "going", "said", "says", "say", "went", "going", "too",
    "really", "actually", "though", "thought",
})

_DISCORD_MARKUP = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+")
_TOKEN = re.compile(r"[a-z]{3,20}")


def classify_archetype(content: str, has_attachment: bool) -> str:
    stripped = content.strip()
    text_len = len(stripped)
    if has_attachment:
        return "art_post" if text_len <= 60 else "art_commentary"
    if text_len > 200:
        return "discussion"
    if stripped.endswith("?"):
        return "question"
    words = stripped.lower().split()
    if words and words[0] in _QUESTION_STARTERS:
        return "question"
    return "reaction"


def caps_ratio(content: str) -> float:
    alpha = [c for c in content if c.isalpha()]
    if not alpha:
        return 0.0
    return round(sum(1 for c in alpha if c.isupper()) / len(alpha), 6)


def punctuation_density(content: str) -> float:
    if not content:
        return 0.0
    return round((content.count("!") + content.count("?")) / len(content), 6)


def extract_terms(content: str) -> list[str]:
    text = _DISCORD_MARKUP.sub(" ", content)
    text = _URL.sub(" ", text)
    text = text.lower()
    tokens = [tok for tok in _TOKEN.findall(text) if tok not in _STOP_WORDS]
    bigrams = [f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1)]
    return tokens + bigrams
