"""Provider client for football-data.org with on-disk caching.

We do not auto-refresh. Every API response is cached to data/cache/ with a date
stamp so the project is reproducible offline and stays well within the free-tier
limit (10 req/min). Call with force=True to re-fetch.

Usage:
    from data.fetch import FootballDataClient
    client = FootballDataClient()
    matches = client.matches()      # cached → cache/WC_matches_2026_<date>.json
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = "https://api.football-data.org/v4"
COMPETITION = "WC"
DEFAULT_SEASON = 2026

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"


def _load_token() -> str:
    """Read FOOTBALL_DATA_TOKEN from the environment or the project .env file."""
    token = os.environ.get("FOOTBALL_DATA_TOKEN")
    if token:
        return token.strip()
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("FOOTBALL_DATA_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(
        "No football-data.org token found. Set FOOTBALL_DATA_TOKEN in the "
        "environment or in a .env file at the project root."
    )


class FootballDataClient:
    def __init__(self, season: int = DEFAULT_SEASON, token: str | None = None):
        self.season = season
        self.token = token or _load_token()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # -- low level ---------------------------------------------------------
    def _cache_path(self, name: str) -> Path:
        stamp = date.today().isoformat()
        return CACHE_DIR / f"{COMPETITION}_{name}_{self.season}_{stamp}.json"

    def _get(self, path: str, name: str, force: bool = False) -> dict:
        cache_path = self._cache_path(name)
        if cache_path.exists() and not force:
            return json.loads(cache_path.read_text())
        url = f"{BASE}{path}"
        req = Request(url, headers={"X-Auth-Token": self.token})
        try:
            with urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode())
        except HTTPError as e:
            body = e.read().decode(errors="replace")
            raise RuntimeError(f"football-data.org {e.code} for {url}: {body}") from e
        # stamp the payload with fetch time before caching
        payload["_fetched_at"] = datetime.now(timezone.utc).isoformat()
        cache_path.write_text(json.dumps(payload, indent=2))
        return payload

    # -- endpoints ---------------------------------------------------------
    def competition(self, force: bool = False) -> dict:
        return self._get(f"/competitions/{COMPETITION}", "competition", force)

    def matches(self, force: bool = False) -> dict:
        return self._get(
            f"/competitions/{COMPETITION}/matches?season={self.season}",
            "matches", force,
        )

    def standings(self, force: bool = False) -> dict:
        return self._get(
            f"/competitions/{COMPETITION}/standings?season={self.season}",
            "standings", force,
        )


if __name__ == "__main__":
    c = FootballDataClient()
    m = c.matches()
    print(f"Fetched {len(m.get('matches', []))} matches for season {c.season}")
    print(f"Cached under {CACHE_DIR}")
