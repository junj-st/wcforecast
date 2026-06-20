"""Historical international matches from api-football, for training the model.

api-football's free plan blocks the live 2026 season but gives full 2022-2024
data. We pull a curated set of international competitions, normalize each fixture
to (date, home, away, goals, weight) with canonical team names, and cache to disk.

`weight` reflects how informative a result is: a World Cup match says more about
team strength than a friendly. Elo and the Poisson fit use it; it is NOT a model
feature (no leakage).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from .aliases import canonical

BASE = "https://v3.football.api-sports.io"
ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"

# (league_id, season, competition_weight). Higher weight = more informative.
# Tournament finals weigh most, qualifiers/Nations League mid, friendlies least.
TRAINING_SOURCES = [
    (1, 2022, 3.0),   # World Cup 2022
    (4, 2024, 2.5),   # Euro 2024
    (9, 2024, 2.5),   # Copa America 2024
    (6, 2023, 2.5),   # Africa Cup of Nations 2023
    (5, 2024, 1.8),   # UEFA Nations League 2024-25
    (5, 2022, 1.8),   # UEFA Nations League 2022-23
    (10, 2024, 0.35),  # Friendlies 2024 — heavily discounted (weak/rotated sides)
    (10, 2023, 0.35),  # Friendlies 2023
]


@dataclass
class HistMatch:
    date: str        # ISO date (sortable)
    home: str        # canonical name
    away: str        # canonical name
    home_goals: int
    away_goals: int
    weight: float


def _load_key() -> str:
    key = os.environ.get("API_FOOTBALL_KEY")
    if key:
        return key.strip()
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip().startswith("API_FOOTBALL_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("No API_FOOTBALL_KEY found in environment or .env")


def _fetch_fixtures(league: int, season: int, key: str, force: bool = False) -> dict:
    cache_path = CACHE_DIR / f"apifootball_fixtures_{league}_{season}.json"
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text())
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    qs = urlencode({"league": league, "season": season})
    req = Request(f"{BASE}/fixtures?{qs}", headers={"x-apisports-key": key})
    try:
        with urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except HTTPError as e:
        raise RuntimeError(f"api-football {e.code}: {e.read().decode(errors='replace')}") from e
    if payload.get("errors"):
        raise RuntimeError(f"api-football errors for {league}/{season}: {payload['errors']}")
    cache_path.write_text(json.dumps(payload))
    return payload


def load_history(force: bool = False) -> list[HistMatch]:
    """Fetch (cached) and normalize all training sources, sorted by date."""
    key = _load_key()
    matches: list[HistMatch] = []
    for league, season, weight in TRAINING_SOURCES:
        payload = _fetch_fixtures(league, season, key, force=force)
        for f in payload.get("response", []):
            if f["fixture"]["status"]["short"] != "FT":
                continue  # only finished matches
            g = f["goals"]
            if g["home"] is None or g["away"] is None:
                continue
            matches.append(HistMatch(
                date=f["fixture"]["date"][:10],
                home=canonical(f["teams"]["home"]["name"]),
                away=canonical(f["teams"]["away"]["name"]),
                home_goals=int(g["home"]),
                away_goals=int(g["away"]),
                weight=weight,
            ))
    matches.sort(key=lambda m: m.date)
    return matches


if __name__ == "__main__":
    hist = load_history()
    teams = {m.home for m in hist} | {m.away for m in hist}
    print(f"Loaded {len(hist)} historical matches, {len(teams)} distinct teams")
    print(f"Date range: {hist[0].date} .. {hist[-1].date}")
