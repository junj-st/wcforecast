"""Poisson goal model (Dixon-Coles style) for expected scorelines.

Fitted as a Poisson regression: each match contributes two observations —
(home goals | home attack, away defense, +home advantage) and
(away goals | away attack, home defense). The fitted coefficients are each team's
log attack and log defense strength. This is the real, citable technique behind
football analytics; we estimate it via sklearn's PoissonRegressor (log link, L2).

The classifier (gbm.py) owns win/draw/loss probabilities; this model owns expected
goals and scoreline sampling, which the Monte Carlo simulator needs for group
goal-difference tiebreakers.
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import PoissonRegressor

MAX_GOALS = 10  # truncate the scoreline distribution here


class PoissonModel:
    def __init__(self, alpha: float = 1e-3):
        self.alpha = alpha
        self.teams: list[str] = []
        self.idx: dict[str, int] = {}
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}
        self.intercept: float = 0.0
        self.home_coef: float = 0.0

    def fit(self, matches, weights=None) -> "PoissonModel":
        """Fit attack/defense coefficients. `weights` (parallel to matches) lets the
        caller apply time-decay so recent scorelines count more; defaults to each
        match's competition weight."""
        teams = sorted({m.home for m in matches} | {m.away for m in matches})
        self.teams = teams
        self.idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        if weights is None:
            weights = [m.weight for m in matches]

        # Design: [attack one-hot (n) | defense one-hot (n) | home flag]
        rows, goals, w = [], [], []
        for m, mw in zip(matches, weights):
            hi, ai = self.idx[m.home], self.idx[m.away]
            # home side attacking, at home
            r1 = np.zeros(2 * n + 1)
            r1[hi] = 1; r1[n + ai] = 1; r1[-1] = 1
            rows.append(r1); goals.append(m.home_goals); w.append(mw)
            # away side attacking, not at home
            r2 = np.zeros(2 * n + 1)
            r2[ai] = 1; r2[n + hi] = 1; r2[-1] = 0
            rows.append(r2); goals.append(m.away_goals); w.append(mw)
        weights = w

        X = np.array(rows)
        y = np.array(goals)
        w = np.array(weights)
        model = PoissonRegressor(alpha=self.alpha, max_iter=500)
        model.fit(X, y, sample_weight=w)

        coef = model.coef_
        self.intercept = float(model.intercept_)
        self.home_coef = float(coef[-1])
        self.attack = {t: float(coef[self.idx[t]]) for t in teams}
        self.defense = {t: float(coef[n + self.idx[t]]) for t in teams}
        return self

    def _lin(self, attacking: str, defending: str, at_home: bool) -> float:
        a = self.attack.get(attacking, 0.0)
        d = self.defense.get(defending, 0.0)
        return self.intercept + a + d + (self.home_coef if at_home else 0.0)

    def expected_goals(self, home: str, away: str, neutral: bool = False) -> tuple[float, float]:
        lam_home = np.exp(self._lin(home, away, at_home=not neutral))
        lam_away = np.exp(self._lin(away, home, at_home=False))
        return float(lam_home), float(lam_away)

    def score_matrix(self, home: str, away: str, neutral: bool = False) -> np.ndarray:
        """Joint probability of each scoreline up to MAX_GOALS (independent Poisson)."""
        lam_h, lam_a = self.expected_goals(home, away, neutral)
        ph = _poisson_pmf(lam_h)
        pa = _poisson_pmf(lam_a)
        return np.outer(ph, pa)

    def outcome_probs(self, home: str, away: str, neutral: bool = False) -> dict:
        """Win/draw/loss implied by the Poisson model (a baseline vs the GBM)."""
        M = self.score_matrix(home, away, neutral)
        home_win = float(np.tril(M, -1).sum())
        draw = float(np.trace(M))
        away_win = float(np.triu(M, 1).sum())
        return {"home_win": home_win, "draw": draw, "away_win": away_win}

    def sample_score(self, home: str, away: str, rng: np.random.Generator,
                     neutral: bool = False) -> tuple[int, int]:
        lam_h, lam_a = self.expected_goals(home, away, neutral)
        return int(rng.poisson(lam_h)), int(rng.poisson(lam_a))


def _poisson_pmf(lam: float) -> np.ndarray:
    k = np.arange(MAX_GOALS + 1)
    # pmf via log to stay stable, then renormalize over the truncated support
    logp = -lam + k * np.log(lam + 1e-12) - _log_factorial(k)
    p = np.exp(logp)
    return p / p.sum()


def _log_factorial(k: np.ndarray) -> np.ndarray:
    from scipy.special import gammaln
    return gammaln(k + 1)


if __name__ == "__main__":
    from data.history import load_history

    pm = PoissonModel().fit(load_history())
    for h, a in [("argentina", "france"), ("spain", "germany"), ("brazil", "england")]:
        lh, la = pm.expected_goals(h, a, neutral=True)
        probs = pm.outcome_probs(h, a, neutral=True)
        print(f"{h} vs {a} (neutral): xG {lh:.2f}-{la:.2f} | "
              f"W/D/L {probs['home_win']:.2f}/{probs['draw']:.2f}/{probs['away_win']:.2f}")
