"""Group-stage standings: compute final tables from real + simulated results.

Already-played matches are fixed; unplayed ones get a sampled scoreline. Tables
follow the FIFA 2026 tiebreakers we can compute from results: points, then goal
difference, then goals for, then the head-to-head mini-table among the still-tied
teams, then a random draw (standing in for fair-play / drawing of lots).
"""
from __future__ import annotations

import numpy as np


class GroupResult:
    __slots__ = ("team", "points", "gd", "gf")

    def __init__(self, team, points, gd, gf):
        self.team, self.points, self.gd, self.gf = team, points, gd, gf


def _tally(teams, results):
    """results: list of (home, away, hg, ag). Returns {team: [pts, gd, gf]}."""
    table = {t: [0, 0, 0] for t in teams}
    for home, away, hg, ag in results:
        table[home][2] += hg
        table[away][2] += ag
        table[home][1] += hg - ag
        table[away][1] += ag - hg
        if hg > ag:
            table[home][0] += 3
        elif hg < ag:
            table[away][0] += 3
        else:
            table[home][0] += 1
            table[away][0] += 1
    return table


def rank_group(teams, results, rng: np.random.Generator):
    """Return teams ordered 1st..4th applying tiebreakers."""
    table = _tally(teams, results)

    def overall_key(t):
        pts, gd, gf = table[t]
        return (pts, gd, gf)

    # group by identical (pts, gd, gf); break those ties by head-to-head then random
    order = sorted(teams, key=overall_key, reverse=True)
    resolved = []
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and overall_key(order[j + 1]) == overall_key(order[i]):
            j += 1
        tied = order[i:j + 1]
        if len(tied) == 1:
            resolved.append(tied[0])
        else:
            resolved.extend(_break_tie(tied, results, rng))
        i = j + 1
    return [GroupResult(t, *table[t]) for t in resolved]


def _break_tie(tied, results, rng):
    """Head-to-head mini-table among tied teams, then random."""
    tied_set = set(tied)
    h2h = _tally(tied, [(h, a, hg, ag) for (h, a, hg, ag) in results
                        if h in tied_set and a in tied_set])
    return sorted(
        tied,
        key=lambda t: (h2h[t][0], h2h[t][1], h2h[t][2], rng.random()),
        reverse=True,
    )


def rank_thirds(third_results, rng: np.random.Generator):
    """third_results: list of (group_letter, GroupResult). Best 8 qualify.

    Returns the ordered list; caller takes the first 8 as qualified.
    """
    return sorted(
        third_results,
        key=lambda gr: (gr[1].points, gr[1].gd, gr[1].gf, rng.random()),
        reverse=True,
    )
