"""
Triage classification logic.

Checks user free-text for crisis keywords across all supported languages.
Returns 'urgent' if any keyword matches, otherwise 'normal'.
"""

URGENT_KEYWORDS: frozenset[str] = frozenset({
    # English
    "suicide", "kill myself", "end my life", "want to die", "no reason to live",
    "self-harm", "hurt myself", "overdose",
    # Russian
    "суицид", "убить себя", "не хочу жить", "покончить с жизнью", "умереть",
    "причинить себе вред", "самоповреждение",
    # Ukrainian
    "самогубство", "вбити себе", "не хочу жити", "покінчити з життям",
    "заподіяти собі шкоду",
    # Czech
    "sebevražda", "zabít se", "nechci žít", "ukončit život",
    "ublížit si",
    # Abbreviations / slang
    "нхж", "ня жить",
})


def classify_text(text: str) -> str:
    """Return 'urgent' if crisis keywords found, else 'normal'."""
    lower = text.lower()
    if any(kw in lower for kw in URGENT_KEYWORDS):
        return "urgent"
    return "normal"


# Category callback_data → triage level mapping
CATEGORY_TRIAGE: dict[str, str] = {
    "cat_crisis": "urgent",
    "cat_consult": "normal",
    "cat_ikp":    "normal",
}
