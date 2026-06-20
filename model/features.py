"""Feature construction for the gradient-boosted classifier.

One function — feature_row — builds the feature vector for a matchup from the
current EloModel state plus a fitted PoissonModel. It is the single source of truth
used BOTH when building the training set (called before each result updates the Elo
state, so no leakage) AND at prediction time (called on the trained state). That
guarantees train and inference features line up exactly.

The Poisson expected-goals terms are a *stacking* signal: the GBM gets to learn
nonlinear corrections on top of the Poisson model's view, which is what lets the
final blend beat a plain Elo baseline.

Label convention (home perspective): 0 = HOME_WIN, 1 = DRAW, 2 = AWAY_WIN.
"""
from __future__ import annotations

import numpy as np

from .elo import EloModel
from .poisson_model import PoissonModel

FEATURE_NAMES = [
    "elo_diff",        # home rating - away rating (neutral; no home bump)
    "elo_expectancy",  # home win-expectancy from Elo, in [0,1]
    "form_diff",       # home goal-diff form - away goal-diff form (last 5)
    "home_games",      # experience / data confidence
    "away_games",
    "comp_weight",     # competition importance (friendly=1 .. World Cup=3)
    "xg_diff",         # Poisson lambda_home - lambda_away  (stacking signal)
    "xg_total",        # Poisson lambda_home + lambda_away
]


def feature_row(elo: EloModel, poisson: PoissonModel, home: str, away: str,
                *, neutral: bool, weight: float) -> list[float]:
    h, a = elo.state(home), elo.state(away)
    lam_h, lam_a = poisson.expected_goals(home, away, neutral=neutral)
    return [
        h.rating - a.rating,
        elo.expected_home(home, away, neutral=neutral),
        h.form_diff() - a.form_diff(),
        float(h.games),
        float(a.games),
        weight,
        lam_h - lam_a,
        lam_h + lam_a,
    ]


def label(home_goals: int, away_goals: int) -> int:
    if home_goals > away_goals:
        return 0
    if home_goals == away_goals:
        return 1
    return 2


def build_features(matches, poisson: PoissonModel, elo: EloModel | None = None):
    """Walk matches chronologically; emit (X, y, w) with no Elo/form leakage.

    Training matches are treated as neutral-venue with their competition weight.
    Returns the fitted Elo model so the caller can reuse that exact state.
    """
    if elo is None:
        from data.elo_priors import load_elo_priors
        elo = EloModel(priors=load_elo_priors())
    X, y, w = [], [], []
    for m in matches:
        X.append(feature_row(elo, poisson, m.home, m.away,
                             neutral=True, weight=m.weight))
        y.append(label(m.home_goals, m.away_goals))
        w.append(m.weight)
        elo.update(m.home, m.away, m.home_goals, m.away_goals, weight=m.weight)
    return np.array(X), np.array(y), np.array(w), elo
