"""Pydantic response models for the API."""
from __future__ import annotations

from pydantic import BaseModel


class MatchPrediction(BaseModel):
    home: str
    away: str
    home_win: float
    draw: float
    away_win: float
    expected_home_goals: float
    expected_away_goals: float


class StandingRow(BaseModel):
    position: int
    team: str
    canonical: str
    played: int
    points: int
    goal_difference: int
    goals_for: int


class TeamInfo(BaseModel):
    name: str
    canonical: str
    tla: str | None
    group: str | None


class StageProbabilities(BaseModel):
    name: str
    canonical: str
    R32: float
    R16: float
    QF: float
    SF: float
    FINAL: float
    WINNER: float


class SimulationResponse(BaseModel):
    n_simulations: int
    stages: list[str]
    teams: list[StageProbabilities]
