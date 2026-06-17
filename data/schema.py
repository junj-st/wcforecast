"""Internal normalized schema for the World Cup forecast engine.

Everything downstream (model, sim, backend) consumes these dataclasses, NOT raw
provider JSON. This is the contract: swapping data providers means rewriting only
data/fetch.py + data/normalize.py, nothing else.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


# Stage identifiers, ordered from earliest to latest. Mirrors football-data.org's
# `stage` field but kept as our own constants so we don't leak the provider's vocab.
GROUP_STAGE = "GROUP_STAGE"
LAST_32 = "LAST_32"
LAST_16 = "LAST_16"
QUARTER_FINALS = "QUARTER_FINALS"
SEMI_FINALS = "SEMI_FINALS"
THIRD_PLACE = "THIRD_PLACE"
FINAL = "FINAL"

KNOCKOUT_STAGES = [LAST_32, LAST_16, QUARTER_FINALS, SEMI_FINALS, FINAL]
STAGE_ORDER = [GROUP_STAGE] + KNOCKOUT_STAGES


@dataclass
class Team:
    id: int
    name: str
    tla: Optional[str]            # three-letter abbreviation, e.g. "ARG"
    group: Optional[str] = None   # "GROUP_A" .. "GROUP_L"; None for placeholders

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Match:
    id: int
    stage: str
    group: Optional[str]          # set only for group-stage matches
    matchday: Optional[int]
    utc_date: str
    status: str                   # "FINISHED" | "TIMED" | "IN_PLAY" | ...
    home_id: Optional[int]
    home_name: Optional[str]
    away_id: Optional[int]
    away_name: Optional[str]
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    winner: Optional[str] = None  # "HOME_TEAM" | "AWAY_TEAM" | "DRAW" | None
    duration: Optional[str] = None  # "REGULAR" | "EXTRA_TIME" | "PENALTY_SHOOTOUT"

    @property
    def played(self) -> bool:
        return self.status == "FINISHED" and self.home_goals is not None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Tournament:
    """A full normalized snapshot: teams, matches, and the source timestamp."""
    season: int
    fetched_at: str
    teams: list[Team] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)

    def teams_by_id(self) -> dict[int, Team]:
        return {t.id: t for t in self.teams}

    def groups(self) -> dict[str, list[Team]]:
        out: dict[str, list[Team]] = {}
        for t in self.teams:
            if t.group:
                out.setdefault(t.group, []).append(t)
        return out

    def to_dict(self) -> dict:
        return {
            "season": self.season,
            "fetched_at": self.fetched_at,
            "teams": [t.to_dict() for t in self.teams],
            "matches": [m.to_dict() for m in self.matches],
        }
