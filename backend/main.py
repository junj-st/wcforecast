"""FastAPI app serving the World Cup forecast.

Endpoints:
  GET /teams                          48 teams + current group standings
  GET /predictions/{team_a}/{team_b}  single-match win/draw/loss + expected score
  GET /simulate?n=10000               Monte Carlo stage probabilities (cached per n)
  GET /bracket                        current/projected knockout bracket

Run:  uvicorn backend.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from data.aliases import canonical
from . import engine
from .schemas import MatchPrediction, SimulationResponse

app = FastAPI(title="World Cup 2026 Forecast", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.get("/teams")
def teams():
    t = engine.get_tournament()
    standings = engine.current_standings()
    pos = {row["canonical"]: row["position"]
           for rows in standings.values() for row in rows}
    return {
        "season": t.season,
        "fetched_at": t.fetched_at,
        "teams": [
            {"name": tm.name, "canonical": canonical(tm.name), "tla": tm.tla,
             "group": tm.group, "group_position": pos.get(canonical(tm.name))}
            for tm in t.teams
        ],
    }


@app.get("/standings")
def standings():
    return engine.current_standings()


@app.get("/predictions/{team_a}/{team_b}", response_model=MatchPrediction)
def predictions(team_a: str, team_b: str, neutral: bool = True):
    pred = engine.get_predictor()
    known = {canonical(name) for name in
             [tm.name for tm in engine.get_tournament().teams]}
    for name in (team_a, team_b):
        if canonical(name) not in known:
            raise HTTPException(404, f"Unknown team: {name!r}")
    r = pred.predict_match(team_a, team_b, neutral=neutral)
    return MatchPrediction(
        home=team_a, away=team_b,
        home_win=r["home_win"], draw=r["draw"], away_win=r["away_win"],
        expected_home_goals=r["expected_score"][0],
        expected_away_goals=r["expected_score"][1],
    )


@app.get("/simulate", response_model=SimulationResponse)
def simulate(n: int = Query(10000, ge=100, le=50000)):
    return engine.simulate(n)


@app.get("/bracket")
def bracket():
    return engine.projected_bracket()


# Serve the static frontend (if present) at the root.
_frontend = Path(__file__).resolve().parent.parent / "frontend"
if _frontend.exists():
    app.mount("/app", StaticFiles(directory=str(_frontend), html=True), name="frontend")


@app.get("/")
def root():
    return {"service": "World Cup 2026 Forecast",
            "endpoints": ["/teams", "/standings", "/predictions/{a}/{b}",
                          "/simulate?n=10000", "/bracket", "/app"]}
