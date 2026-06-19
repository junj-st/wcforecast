"""Gradient-boosted outcome classifier (home win / draw / away win).

sklearn's HistGradientBoostingClassifier — genuine gradient boosting, no extra
deps — wrapped with sigmoid probability calibration (a time-ordered tail of the
training data is held out to fit the calibrator). Raw boosted probabilities are
overconfident; calibration is what makes them usable for simulation.

`evaluate_pipeline` runs an honest, leak-free assessment: it splits history in
time, fits the Poisson feature-generator on the TRAIN slice only, then compares
the Elo baseline, the GBM, and their blend on the held-out tail.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import log_loss, accuracy_score

CLASSES = ["home_win", "draw", "away_win"]
BLEND_WEIGHT = 0.5   # weight on the GBM in the GBM/Elo blend; rest goes to Elo

_GBM_PARAMS = dict(
    max_depth=2,
    learning_rate=0.03,
    max_iter=250,
    l2_regularization=8.0,
    min_samples_leaf=50,
    random_state=42,
)


class GBMOutcomeModel:
    def __init__(self, **kwargs):
        self.params = {**_GBM_PARAMS, **kwargs}
        self.cal = None
        self._classes = None

    def train(self, X, y, sample_weight=None, calib_fraction: float = 0.15):
        """Fit on the head of (X, y); calibrate on the time-ordered tail."""
        n = len(y)
        cut = int(n * (1 - calib_fraction))
        base = HistGradientBoostingClassifier(**self.params)
        sw = None if sample_weight is None else sample_weight[:cut]
        base.fit(X[:cut], y[:cut], sample_weight=sw)
        self.cal = CalibratedClassifierCV(FrozenEstimator(base), method="sigmoid")
        self.cal.fit(X[cut:], y[cut:])
        self._classes = list(self.cal.classes_)
        return self

    def proba(self, X) -> np.ndarray:
        """Return an (n, 3) array aligned to [home_win, draw, away_win]."""
        p = self.cal.predict_proba(np.atleast_2d(X))
        out = np.zeros((p.shape[0], 3))
        for i, c in enumerate(self._classes):
            out[:, c] = p[:, i]
        return out

    def proba_row(self, features: list[float]) -> dict:
        p = self.proba(np.array([features]))[0]
        return {CLASSES[i]: float(p[i]) for i in range(3)}


def elo_baseline_proba(elo_expectancy: np.ndarray, draw_p: float = 0.26) -> np.ndarray:
    """Map Elo home win-expectancy to [home_win, draw, away_win]."""
    e = np.asarray(elo_expectancy, dtype=float)
    b = np.zeros((len(e), 3))
    b[:, 0] = e * (1 - draw_p)
    b[:, 2] = (1 - e) * (1 - draw_p)
    b[:, 1] = draw_p
    return b / b.sum(axis=1, keepdims=True)


def evaluate_pipeline(history, test_fraction: float = 0.2) -> dict:
    """Honest, leak-free comparison of Elo baseline vs GBM vs blend."""
    from .poisson_model import PoissonModel
    from .features import build_features

    n = len(history)
    cut = int(n * (1 - test_fraction))
    poisson = PoissonModel().fit(history[:cut])      # train-only: no test leakage
    X, y, w, _ = build_features(history, poisson)
    Xtr, Xte, ytr, yte, wtr = X[:cut], X[cut:], y[:cut], y[cut:], w[:cut]

    gbm = GBMOutcomeModel().train(Xtr, ytr, sample_weight=wtr)
    P_gbm = gbm.proba(Xte)
    P_base = elo_baseline_proba(Xte[:, 1])           # elo_expectancy is column 1
    P_blend = BLEND_WEIGHT * P_gbm + (1 - BLEND_WEIGHT) * P_base
    P_blend /= P_blend.sum(axis=1, keepdims=True)

    def metrics(P):
        return (log_loss(yte, P, labels=[0, 1, 2]),
                accuracy_score(yte, P.argmax(axis=1)))

    ll_b, acc_b = metrics(P_base)
    ll_g, acc_g = metrics(P_gbm)
    ll_x, acc_x = metrics(P_blend)
    return {
        "n_train": cut, "n_test": n - cut,
        "elo_log_loss": ll_b, "elo_acc": acc_b,
        "gbm_log_loss": ll_g, "gbm_acc": acc_g,
        "blend_log_loss": ll_x, "blend_acc": acc_x,
    }


if __name__ == "__main__":
    from data.history import load_history

    r = evaluate_pipeline(load_history())
    print(f"Holdout: train {r['n_train']} / test {r['n_test']}  (time-ordered)\n")
    print(f"{'model':12} {'log_loss':>9} {'accuracy':>9}")
    print(f"{'Elo only':12} {r['elo_log_loss']:9.4f} {r['elo_acc']:9.3f}")
    print(f"{'GBM':12} {r['gbm_log_loss']:9.4f} {r['gbm_acc']:9.3f}")
    print(f"{'Blend':12} {r['blend_log_loss']:9.4f} {r['blend_acc']:9.3f}  <- served")
    edge = r["elo_log_loss"] - r["blend_log_loss"]
    print(f"\nBlend vs Elo baseline: {edge:+.4f} log loss "
          f"({'better' if edge > 0 else 'worse'})")
