"""World-Football-style Elo ratings, learned online from historical results.

Each match nudges both teams' ratings toward whatever better explains the result
(margin-aware, weighted by competition importance). The trained ratings serve two
purposes: a strength prior for every team, and the single most important feature
for the gradient-boosted classifier.

We also keep, per team, a short rolling buffer of recent (goals_for, goals_against)
so the feature builder and the predictor can read "current form" from the same
state — computed strictly from matches already processed (no leakage).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

BASE_RATING = 1500.0
HOME_ADVANTAGE = 55.0   # rating points; applied to the listed home side
FORM_WINDOW = 5


def _goal_multiplier(margin: int) -> float:
    """World Football Elo margin-of-victory factor."""
    if margin <= 1:
        return 1.0
    if margin == 2:
        return 1.5
    return (11 + margin) / 8.0


@dataclass
class TeamState:
    rating: float = BASE_RATING
    recent: deque = field(default_factory=lambda: deque(maxlen=FORM_WINDOW))  # (gf, ga)
    games: int = 0

    def form_gf(self) -> float:
        return sum(gf for gf, _ in self.recent) / len(self.recent) if self.recent else 1.0

    def form_ga(self) -> float:
        return sum(ga for _, ga in self.recent) / len(self.recent) if self.recent else 1.0

    def form_diff(self) -> float:
        return sum(gf - ga for gf, ga in self.recent) / len(self.recent) if self.recent else 0.0


class EloModel:
    def __init__(self, k: float = 32.0, priors: dict[str, float] | None = None,
                 freeze_ratings: bool = False):
        """If freeze_ratings, seeded ratings stay fixed (we trust the published
        eloratings table); updates then only populate recent-form buffers."""
        self.k = k
        self.priors = priors or {}
        self.freeze_ratings = freeze_ratings
        self.teams: dict[str, TeamState] = {}

    def state(self, team: str) -> TeamState:
        if team not in self.teams:
            self.teams[team] = TeamState(rating=self.priors.get(team, BASE_RATING))
        return self.teams[team]

    def rating(self, team: str) -> float:
        return self.state(team).rating

    def expected_home(self, home: str, away: str, neutral: bool = False) -> float:
        """Win-expectancy of the home side (draw counts as half), in [0, 1]."""
        ha = 0.0 if neutral else HOME_ADVANTAGE
        diff = (self.rating(home) + ha) - self.rating(away)
        return 1.0 / (1.0 + 10 ** (-diff / 400.0))

    def update(self, home: str, away: str, hg: int, ag: int,
               weight: float = 1.0, neutral: bool = False) -> None:
        """Process one result: update ratings, then push into form buffers."""
        h, a = self.state(home), self.state(away)
        if not self.freeze_ratings:
            exp_h = self.expected_home(home, away, neutral=neutral)
            score_h = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
            k_eff = self.k * weight * _goal_multiplier(abs(hg - ag))
            delta = k_eff * (score_h - exp_h)
            h.rating += delta
            a.rating -= delta
        for st, gf, ga in ((h, hg, ag), (a, ag, hg)):
            st.recent.append((gf, ga))
            st.games += 1

    def fit(self, matches) -> "EloModel":
        """Process an iterable of HistMatch in chronological order."""
        for m in matches:
            self.update(m.home, m.away, m.home_goals, m.away_goals, weight=m.weight)
        return self

    def rankings(self, top: int = 20):
        return sorted(self.teams.items(), key=lambda kv: -kv[1].rating)[:top]


if __name__ == "__main__":
    from data.history import load_history
    from data.elo_priors import load_elo_priors

    elo = EloModel(priors=load_elo_priors()).fit(load_history())
    print("Top 20 by trained Elo:")
    for i, (team, st) in enumerate(elo.rankings(20), 1):
        print(f"  {i:2}. {team:24} {st.rating:7.1f}  ({st.games} games)")
