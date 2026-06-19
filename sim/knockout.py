"""Seed and play the knockout bracket.

Two jobs:
  1. assign_third_slots — map the 8 qualifying third-place groups onto the 8
     third-place bracket slots, respecting each slot's eligibility. FIFA uses a
     precomputed 495-row table; we instead solve the same constraints directly
     with a most-constrained-first backtracking match, which always yields a valid
     assignment (occasionally a different-but-equivalent one than FIFA's table).
  2. play_bracket — resolve Round-of-32 slots to teams, then simulate every tie.
"""
from __future__ import annotations

import numpy as np

from .bracket import (
    R32_MATCHES, THIRD_SLOT_ELIGIBILITY, KO_TREE, STAGE_REACHED_BY_WINNING,
)


def assign_third_slots(qualified_groups: set[str]) -> dict[str, str]:
    """Return {slot: group_letter} covering all 8 slots.

    Solves the eligibility constraints with most-constrained-first backtracking.
    On the rare eligibility deadlock, fills any leftover slots greedily so the
    bracket always resolves.
    """
    slots = sorted(
        THIRD_SLOT_ELIGIBILITY,
        key=lambda s: len(THIRD_SLOT_ELIGIBILITY[s] & qualified_groups),
    )
    assignment: dict[str, str] = {}
    used: set[str] = set()

    def backtrack(i: int) -> bool:
        if i == len(slots):
            return True
        slot = slots[i]
        for g in sorted(THIRD_SLOT_ELIGIBILITY[slot] & qualified_groups):
            if g not in used:
                assignment[slot] = g
                used.add(g)
                if backtrack(i + 1):
                    return True
                used.discard(g)
                del assignment[slot]
        return False

    if not backtrack(0):
        leftover = sorted(qualified_groups - used)
        for slot in slots:
            if slot not in assignment and leftover:
                assignment[slot] = leftover.pop()
    return assignment


def play_bracket(slot_team: dict[str, str], adv, rng: np.random.Generator):
    """slot_team maps every R32 slot name -> team. `adv(a, b)` = P(a beats b).

    Returns (winner_by_match, reach) where reach[team] is the furthest stage.
    """
    # R32 matchups -> concrete teams
    matchup: dict[int, tuple[str, str]] = {}
    for m, (sa, sb) in R32_MATCHES.items():
        matchup[m] = (slot_team[sa], slot_team[sb])

    reach: dict[str, str] = {}
    for a, b in matchup.values():
        reach[a] = "R32"
        reach[b] = "R32"

    winner: dict[int, str] = {}

    def play(a: str, b: str) -> str:
        return a if rng.random() < adv(a, b) else b

    # Round of 32
    for m, (a, b) in matchup.items():
        w = play(a, b)
        winner[m] = w
        reach[w] = STAGE_REACHED_BY_WINNING[m]

    # Remaining rounds, in match-number order (feeders resolved first)
    for m in sorted(KO_TREE):
        fa, fb = KO_TREE[m]
        a, b = winner[fa], winner[fb]
        w = play(a, b)
        winner[m] = w
        reach[w] = STAGE_REACHED_BY_WINNING[m]

    return winner, reach
