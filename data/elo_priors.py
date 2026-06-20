"""Pre-tournament Elo priors from eloratings.net (World Football Elo Ratings).

Bootstrapping ratings from scratch (everyone at 1500) let teams with thin,
friendly-padded records drift too high. Instead we seed each team with a real,
published strength estimate from the END OF 2021 — just before our training
history begins — then update forward. Because the prior predates the history
window, re-walking 2022+ results neither double-counts nor leaks.

eloratings.net exposes two flat files we join on country code:
  en.teams.tsv : CODE -> full country name
  2021.tsv     : CODE -> end-of-2021 Elo (rating in column index 3)
"""
from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

from .aliases import canonical

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"
NAMES_URL = "https://www.eloratings.net/en.teams.tsv"
PRIOR_YEAR_URL = "https://www.eloratings.net/2021.tsv"  # end-2021 snapshot

BASE_RATING = 1500.0


def _fetch(url: str, cache_name: str, force: bool = False) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / cache_name
    if path.exists() and not force:
        return path.read_text()
    with urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    path.write_text(text)
    return text


def load_elo_priors(force: bool = False) -> dict[str, float]:
    """Return {canonical_team_name: end-2021 Elo rating}."""
    names_raw = _fetch(NAMES_URL, "eloratings_teams.tsv", force)
    ratings_raw = _fetch(PRIOR_YEAR_URL, "eloratings_2021.tsv", force)

    code_to_name: dict[str, str] = {}
    for line in names_raw.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0]:
            code_to_name[parts[0]] = parts[1]

    priors: dict[str, float] = {}
    for line in ratings_raw.splitlines():
        f = line.split("\t")
        if len(f) < 4:
            continue
        code, rating = f[2], f[3]
        name = code_to_name.get(code)
        if not name:
            continue
        try:
            priors[canonical(name)] = float(rating)
        except ValueError:
            continue
    return priors


if __name__ == "__main__":
    p = load_elo_priors()
    print(f"Loaded {len(p)} Elo priors (end-2021).")
    for t in ["brazil", "france", "argentina", "spain", "colombia", "japan",
              "germany", "england", "usa", "czechia"]:
        print(f"  {t:12} {p.get(t, BASE_RATING):.0f}")
