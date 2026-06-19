"""Unified match predictor: the single interface the simulator and API call.

Wiring:
  - PoissonModel  -> expected scorelines + goal sampling (group tiebreakers)
  - EloModel      -> strength prior, baseline W/D/L, and GBM features
  - GBMOutcomeModel (calibrated) -> nonlinear W/D/L on stacked features
  - served W/D/L  = blend(GBM, Elo baseline)

On construction it trains everything on historical internationals, then folds the
already-played 2026 World Cup results into the Elo/form state so "current form"
reflects the live tournament. Training is a few seconds, so the simulator just
builds one Predictor and reuses it across all 10,000 runs.
"""
from __future__ import annotations

import numpy as np

from data.aliases import canonical
from data.history import load_history
from data.normalize import load_tournament
from .elo import EloModel
from .poisson_model import PoissonModel
from .gbm import GBMOutcomeModel, elo_baseline_proba, BLEND_WEIGHT, CLASSES
from .features import build_features, feature_row

WC_WEIGHT = 3.0  # World Cup matches are maximally competitive


class Predictor:
    def __init__(self, ingest_live: bool = True):
        history = load_history()
        # Fit on ALL history for deployment (the train-only split in gbm.evaluate
        # exists purely to measure generalization honestly).
        self.poisson = PoissonModel().fit(history)
        X, y, w, elo = build_features(history, self.poisson)
        self.elo = elo
        self.gbm = GBMOutcomeModel().train(X, y, sample_weight=w)
        if ingest_live:
            self._ingest_live_results()

    def _ingest_live_results(self) -> None:
        """Update Elo/form with finished 2026 matches so form is current."""
        t = load_tournament()
        for m in sorted((m for m in t.matches if m.played),
                        key=lambda m: m.utc_date or ""):
            self.elo.update(canonical(m.home_name), canonical(m.away_name),
                            m.home_goals, m.away_goals, weight=WC_WEIGHT)

    # -- core interface ----------------------------------------------------
    def predict_match(self, home: str, away: str, neutral: bool = True) -> dict:
        """W/D/L probabilities (blended) + Poisson expected score."""
        h, a = canonical(home), canonical(away)
        feats = feature_row(self.elo, self.poisson, h, a,
                            neutral=neutral, weight=WC_WEIGHT)
        p_gbm = self.gbm.proba(np.array([feats]))[0]
        p_elo = elo_baseline_proba([self.elo.expected_home(h, a, neutral=neutral)])[0]
        p = BLEND_WEIGHT * p_gbm + (1 - BLEND_WEIGHT) * p_elo
        p = p / p.sum()
        lam_h, lam_a = self.poisson.expected_goals(h, a, neutral=neutral)
        return {
            "home_win": float(p[0]),
            "draw": float(p[1]),
            "away_win": float(p[2]),
            "expected_score": (round(lam_h, 2), round(lam_a, 2)),
        }

    def sample_score(self, home: str, away: str, rng: np.random.Generator,
                     neutral: bool = True) -> tuple[int, int]:
        """A random scoreline for one match — used by the Monte Carlo sim."""
        return self.poisson.sample_score(canonical(home), canonical(away),
                                         rng, neutral=neutral)

    def advance_probability(self, home: str, away: str, neutral: bool = True) -> float:
        """P(home advances) for a knockout tie: win + share of the draw (penalties).

        Penalty shootouts are close to a coin flip, nudged slightly toward the
        stronger side via Elo expectancy.
        """
        p = self.predict_match(home, away, neutral=neutral)
        h, a = canonical(home), canonical(away)
        shootout_edge = self.elo.expected_home(h, a, neutral=True)  # ~0.5 if even
        return p["home_win"] + p["draw"] * shootout_edge


if __name__ == "__main__":
    pred = Predictor()
    print("Sample predictions (neutral venue):\n")
    for h, a in [("Argentina", "France"), ("Spain", "Germany"),
                 ("Brazil", "England"), ("USA", "Argentina"),
                 ("Cape Verde Islands", "Spain")]:
        r = pred.predict_match(h, a)
        print(f"{h:20} vs {a:20}  "
              f"W {r['home_win']:.2f} / D {r['draw']:.2f} / L {r['away_win']:.2f}"
              f"  xG {r['expected_score'][0]}-{r['expected_score'][1]}")
