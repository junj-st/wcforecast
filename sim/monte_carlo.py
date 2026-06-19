"""Monte Carlo tournament simulation.

Builds a context once (group fixtures with cached Poisson rates, an advance-
probability matrix over all 48 teams), then replays the whole tournament N times
with fresh random draws for every unplayed match. Aggregating the runs gives each
team's probability of reaching every stage — the FiveThirtyEight-style output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

from data.aliases import canonical
from data.normalize import load_tournament
from model.predictor import Predictor
from .bracket import STAGES
from .group_stage import rank_group, rank_thirds
from .knockout import assign_third_slots, play_bracket

HOSTS = {"usa", "mexico", "canada"}


@dataclass
class GroupFixtures:
    teams: list[str]
    played: list[tuple]                 # (home, away, hg, ag) fixed results
    unplayed: list[tuple]               # (home, away)
    lam_home: np.ndarray = field(default=None)
    lam_away: np.ndarray = field(default=None)


class SimContext:
    """Everything needed to replay the tournament, precomputed once."""

    def __init__(self, predictor: Predictor | None = None):
        self.pred = predictor or Predictor()
        t = load_tournament()
        self.team_names = {canonical(tm.name): tm.name for tm in t.teams}  # display
        self.groups: dict[str, GroupFixtures] = {}
        self._build_groups(t)
        self._build_adv_matrix()

    def _build_groups(self, t):
        by_group: dict[str, list] = {}
        teams_by_group: dict[str, list] = {}
        for tm in t.teams:
            if tm.group:
                teams_by_group.setdefault(tm.group[-1], []).append(canonical(tm.name))
        for m in t.matches:
            if m.stage != "GROUP_STAGE" or not m.group:
                continue
            by_group.setdefault(m.group[-1], []).append(m)

        for letter, matches in by_group.items():
            played, unplayed = [], []
            lam_h, lam_a = [], []
            for m in matches:
                h, a = canonical(m.home_name), canonical(m.away_name)
                if m.played:
                    played.append((h, a, m.home_goals, m.away_goals))
                else:
                    neutral = h not in HOSTS
                    lh, la = self.pred.poisson.expected_goals(h, a, neutral=neutral)
                    unplayed.append((h, a))
                    lam_h.append(lh)
                    lam_a.append(la)
            gf = GroupFixtures(teams_by_group[letter], played, unplayed)
            gf.lam_home = np.array(lam_h)
            gf.lam_away = np.array(lam_a)
            self.groups[letter] = gf

    def _build_adv_matrix(self):
        """P(a advances past b) for all ordered pairs, vectorized in one GBM call."""
        from model.features import feature_row
        from model.gbm import elo_baseline_proba, BLEND_WEIGHT
        from model.predictor import WC_WEIGHT

        teams = sorted(self.team_names)
        pairs = [(a, b) for a in teams for b in teams if a != b]
        X = np.array([
            feature_row(self.pred.elo, self.pred.poisson, a, b,
                        neutral=True, weight=WC_WEIGHT)
            for a, b in pairs
        ])
        exp_home = np.array([
            self.pred.elo.expected_home(a, b, neutral=True) for a, b in pairs
        ])
        p_gbm = self.pred.gbm.proba(X)
        p_elo = elo_baseline_proba(exp_home)
        p = BLEND_WEIGHT * p_gbm + (1 - BLEND_WEIGHT) * p_elo
        p /= p.sum(axis=1, keepdims=True)
        # advance = win + share of the draw decided on penalties (Elo-tilted)
        adv_vec = p[:, 0] + p[:, 1] * exp_home
        self.adv = {pair: float(v) for pair, v in zip(pairs, adv_vec)}

    def _adv(self, a, b):
        return self.adv[(a, b)]

    def simulate_once(self, rng: np.random.Generator) -> dict[str, str]:
        """One full tournament. Returns {team: furthest stage reached}."""
        slot_team: dict[str, str] = {}
        thirds = []
        third_team_by_group = {}

        for letter, gf in self.groups.items():
            results = list(gf.played)
            if gf.unplayed:
                hg = rng.poisson(gf.lam_home)
                ag = rng.poisson(gf.lam_away)
                for (h, a), x, y in zip(gf.unplayed, hg, ag):
                    results.append((h, a, int(x), int(y)))
            ranked = rank_group(gf.teams, results, rng)
            slot_team[f"W_{letter}"] = ranked[0].team
            slot_team[f"RU_{letter}"] = ranked[1].team
            thirds.append((letter, ranked[2]))
            third_team_by_group[letter] = ranked[2].team

        ranked_thirds = rank_thirds(thirds, rng)
        qualified = {letter for letter, _ in ranked_thirds[:8]}
        slot_assignment = assign_third_slots(qualified)
        for slot, group in slot_assignment.items():
            slot_team[slot] = third_team_by_group[group]

        _, reach = play_bracket(slot_team, self._adv, rng)
        return reach


def run_monte_carlo(n_simulations: int = 10000, seed: int = 0,
                    context: SimContext | None = None) -> dict:
    ctx = context or SimContext()
    rng = np.random.default_rng(seed)
    stage_index = {s: i for i, s in enumerate(STAGES)}
    counts: dict[str, np.ndarray] = {
        c: np.zeros(len(STAGES)) for c in ctx.team_names
    }

    for _ in range(n_simulations):
        reach = ctx.simulate_once(rng)
        for team, stage in reach.items():
            counts[team][: stage_index[stage] + 1] += 1

    from .aggregate import aggregate
    return aggregate(counts, n_simulations, ctx.team_names)


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
    print(f"Running {n} simulations...")
    out = run_monte_carlo(n)
    rows = sorted(out["teams"], key=lambda r: -r["WINNER"])
    print(f"\n{'Team':22}{'R16':>7}{'QF':>7}{'SF':>7}{'FINAL':>8}{'WIN':>7}")
    for r in rows[:16]:
        print(f"{r['name']:22}{r['R16']*100:6.1f}%{r['QF']*100:6.1f}%"
              f"{r['SF']*100:6.1f}%{r['FINAL']*100:7.1f}%{r['WINNER']*100:6.1f}%")
