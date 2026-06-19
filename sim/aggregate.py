"""Turn raw simulation tallies into per-team stage probabilities."""
from __future__ import annotations

import numpy as np

from .bracket import STAGES


def aggregate(counts: dict[str, np.ndarray], n: int, names: dict[str, str]) -> dict:
    """counts[team] = cumulative reach tally per stage. Returns JSON-ready dict."""
    teams = []
    for canon, tally in counts.items():
        probs = (tally / n).tolist()
        row = {"name": names.get(canon, canon), "canonical": canon}
        row.update({stage: probs[i] for i, stage in enumerate(STAGES)})
        teams.append(row)
    teams.sort(key=lambda r: (-r["WINNER"], -r["FINAL"], -r["SF"]))
    return {"n_simulations": n, "stages": STAGES, "teams": teams}
