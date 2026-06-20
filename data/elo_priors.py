"""Team strength from eloratings.net (World Football Elo Ratings).

We anchor every team to its CURRENT published Elo — the live 2026 table, which
already folds in the 2025 qualifiers, recent form, and the ongoing tournament, and
naturally weights recent results more as it evolves. This keeps the forecast
current (a rising squad climbs, a fading one drops) without letting thin friendly
records float, because the rating is professionally maintained.

We do NOT re-walk our 2022-2024 history on top of this rating — that would
double-count, since the current table already includes those results. The history
is used only for the Poisson scoreline model and the GBM (both time-decayed).

eloratings.net exposes two flat files we join on country code:
  en.teams.tsv : CODE -> full country name
  <year>.tsv   : CODE -> Elo for that year (rating in column index 3)
"""
from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

from .aliases import canonical

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"
NAMES_URL = "https://www.eloratings.net/en.teams.tsv"
CURRENT_YEAR = 2026
RATINGS_URL = f"https://www.eloratings.net/{CURRENT_YEAR}.tsv"  # live current table

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
    """Return {canonical_team_name: current (2026) Elo rating}.

    Pass force=True to re-fetch the live table as the tournament progresses.
    """
    names_raw = _fetch(NAMES_URL, "eloratings_teams.tsv", force)
    ratings_raw = _fetch(RATINGS_URL, f"eloratings_{CURRENT_YEAR}.tsv", force)

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
    print(f"Loaded {len(p)} current Elo ratings ({CURRENT_YEAR}).")
    for t in ["brazil", "france", "argentina", "spain", "colombia", "japan",
              "germany", "england", "usa", "czechia"]:
        print(f"  {t:12} {p.get(t, BASE_RATING):.0f}")
