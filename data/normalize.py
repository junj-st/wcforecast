"""Turn raw football-data.org JSON into our internal schema (data/schema.py).

The provider's match list is the source of truth: we derive the team roster and
each team's group from it, rather than trusting the (free-tier-limited) standings
endpoint. Group tables are computed from results elsewhere (sim layer), not here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .schema import Match, Team, Tournament


def _team_from_match_side(side: dict) -> Team | None:
    if not side or side.get("id") is None:
        return None
    return Team(id=side["id"], name=side.get("name"), tla=side.get("tla"))


def normalize_matches(raw: dict, season: int) -> Tournament:
    """Build a Tournament from a raw /matches response."""
    matches: list[Match] = []
    teams: dict[int, Team] = {}

    for m in raw.get("matches", []):
        stage = m.get("stage")
        group = m.get("group")  # e.g. "GROUP_A", None for knockouts
        home = m.get("homeTeam") or {}
        away = m.get("awayTeam") or {}
        score = m.get("score") or {}
        full = score.get("fullTime") or {}

        match = Match(
            id=m["id"],
            stage=stage,
            group=group,
            matchday=m.get("matchday"),
            utc_date=m.get("utcDate"),
            status=m.get("status"),
            home_id=home.get("id"),
            home_name=home.get("name"),
            away_id=away.get("id"),
            away_name=away.get("name"),
            home_goals=full.get("home"),
            away_goals=full.get("away"),
            winner=score.get("winner"),
            duration=score.get("duration"),
        )
        matches.append(match)

        # collect teams + infer their group from group-stage fixtures
        for side in (home, away):
            t = _team_from_match_side(side)
            if t is None:
                continue
            if t.id not in teams:
                teams[t.id] = t
            if group and teams[t.id].group is None:
                teams[t.id].group = group

    fetched_at = raw.get("_fetched_at") or datetime.now(timezone.utc).isoformat()
    return Tournament(
        season=season,
        fetched_at=fetched_at,
        teams=sorted(teams.values(), key=lambda t: (t.group or "ZZZ", t.name or "")),
        matches=matches,
    )


def load_tournament(season: int = 2026, force: bool = False) -> Tournament:
    """Convenience: fetch (cached) + normalize in one call."""
    from .fetch import FootballDataClient

    client = FootballDataClient(season=season)
    return normalize_matches(client.matches(force=force), season)


if __name__ == "__main__":
    t = load_tournament()
    groups = t.groups()
    print(f"Season {t.season} — {len(t.teams)} teams, {len(t.matches)} matches")
    print(f"Groups: {len(groups)}")
    played = [m for m in t.matches if m.played]
    print(f"Played: {len(played)} / {len(t.matches)}")
    for g in sorted(groups):
        names = ", ".join(sorted(tm.name for tm in groups[g]))
        print(f"  {g}: {names}")
