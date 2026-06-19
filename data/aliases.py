"""Canonical team-name normalization.

The two providers spell national teams differently (football-data.org says
"Czechia", api-football says "Czech Republic"). Everything that joins data across
providers — Elo ratings, training features, predictions — keys on canonical(name)
so the same team lines up regardless of source.
"""
from __future__ import annotations

import unicodedata


def _slug(name: str) -> str:
    """Lowercase, strip accents/punctuation, collapse whitespace."""
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    out = []
    for ch in no_accents.lower():
        if ch.isalnum() or ch == " ":
            out.append(ch)
        elif ch in "-_/&.'":
            out.append(" ")
    return " ".join("".join(out).split())


# Canonical team name -> every alternative spelling (slugged) that means it.
# Add a spelling here and all providers using it collapse to the one canonical key.
_ALIAS_GROUPS = {
    "czechia": ["czech republic"],
    "south korea": ["korea republic"],
    "iran": ["ir iran", "iran islamic republic of"],
    "usa": ["united states", "united states of america"],
    "cape verde islands": ["cape verde", "cabo verde"],
    "congo dr": ["dr congo", "democratic republic of congo", "congo democratic republic"],
    "bosnia and herzegovina": ["bosnia herzegovina", "bosnia"],
    "ivory coast": ["cote d ivoire"],
    "turkey": ["turkiye"],
    "china": ["china pr"],
    "netherlands": ["the netherlands", "holland"],
}

# Flatten to {alias_slug: canonical_slug} for O(1) lookup.
_ALIASES = {
    _slug(alias): canonical_name
    for canonical_name, aliases in _ALIAS_GROUPS.items()
    for alias in aliases
}


def canonical(name: str) -> str:
    """Return the canonical key for a team name from any provider."""
    s = _slug(name)
    return _ALIASES.get(s, s)
