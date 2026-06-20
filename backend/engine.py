"""Lazily-built, cached engine shared by all API routes.

Training the model + building the simulation context takes a few seconds, so we do
it once on first use and reuse it. Simulation results are cached per request size.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from data.aliases import canonical
from data.normalize import load_tournament
from model.predictor import Predictor
from sim.group_stage import rank_group
from sim.monte_carlo import SimContext, run_monte_carlo

_sim_cache: dict[int, dict] = {}


@lru_cache(maxsize=1)
def get_predictor() -> Predictor:
    return Predictor()


@lru_cache(maxsize=1)
def get_context() -> SimContext:
    return SimContext(predictor=get_predictor())


@lru_cache(maxsize=1)
def get_tournament():
    return load_tournament()


def simulate(n: int) -> dict:
    if n not in _sim_cache:
        _sim_cache[n] = run_monte_carlo(n, context=get_context())
    return _sim_cache[n]


def current_standings() -> dict[str, list[dict]]:
    """Group tables from played matches only (deterministic display order)."""
    t = get_tournament()
    rng = np.random.default_rng(0)
    teams_by_group: dict[str, list[str]] = {}
    display: dict[str, str] = {}
    for tm in t.teams:
        if tm.group:
            teams_by_group.setdefault(tm.group[-1], []).append(canonical(tm.name))
            display[canonical(tm.name)] = tm.name

    results_by_group: dict[str, list[tuple]] = {}
    for m in t.matches:
        if m.stage == "GROUP_STAGE" and m.group and m.played:
            results_by_group.setdefault(m.group[-1], []).append(
                (canonical(m.home_name), canonical(m.away_name),
                 m.home_goals, m.away_goals))

    out: dict[str, list[dict]] = {}
    for letter, teams in sorted(teams_by_group.items()):
        played = results_by_group.get(letter, [])
        ranked = rank_group(teams, played, rng)
        games = {t: 0 for t in teams}
        for h, a, _, _ in played:
            games[h] += 1
            games[a] += 1
        out[letter] = [
            {"position": i + 1, "team": display[r.team], "canonical": r.team,
             "played": games[r.team], "points": r.points,
             "goal_difference": r.gd, "goals_for": r.gf}
            for i, r in enumerate(ranked)
        ]
    return out


def projected_bracket() -> dict:
    """Seed the R32 slots from current standings ('if the groups ended now')."""
    from sim.knockout import assign_third_slots
    from sim.bracket import R32_MATCHES, KO_TREE

    standings = current_standings()
    slot_team: dict[str, str] = {}
    thirds = []
    for letter, rows in standings.items():
        slot_team[f"W_{letter}"] = rows[0]["team"]
        slot_team[f"RU_{letter}"] = rows[1]["team"]
        thirds.append((letter, rows[2]))
    thirds.sort(key=lambda x: (x[1]["points"], x[1]["goal_difference"],
                               x[1]["goals_for"]), reverse=True)
    qualified = {letter for letter, _ in thirds[:8]}
    third_team_by_group = {letter: row["team"] for letter, row in thirds}
    for slot, group in assign_third_slots(qualified).items():
        slot_team[slot] = third_team_by_group[group]

    r32 = [{"match": m, "home_slot": sa, "away_slot": sb,
            "home": slot_team.get(sa), "away": slot_team.get(sb)}
           for m, (sa, sb) in sorted(R32_MATCHES.items())]
    tree = [{"match": m, "feeds_from": list(KO_TREE[m])} for m in sorted(KO_TREE)]
    return {"round_of_32": r32, "later_rounds": tree, "note":
            "Slots seeded from current group standings; updates as results arrive."}
