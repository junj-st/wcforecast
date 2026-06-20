<p align="center">
  <img src="assets/forecast-logo.png" alt="World Cup 2026 Forecast" width="200" />
</p>

<h1 align="center">World Cup 2026 Forecast Engine</h1>

An end-to-end sports-analytics pipeline for the **2026 FIFA World Cup**. A match-outcome model feeds a Monte
Carlo tournament simulator (10,000 runs) that estimates every team's probability
of reaching each stage, served through a FastAPI backend and an interactive
bracket/dashboard frontend.

```
 football-data.org (live 2026) ─┐
                                ├─► data/  ─► model/ ─► sim/ ─► backend/ ─► frontend/
 api-football (2022-24 history) ─┤        (normalize) (predict) (10k sims) (FastAPI)  (bracket+dashboard)
 eloratings.net (current Elo)  ─┘
```

## Data sources

Three providers, each with a distinct role:

| Source | Role | Notes |
|--------|------|-------|
| **football-data.org** | The tournament we forecast | Live 2026: 48 teams, 12 groups, 104 matches. |
| **api-football** | Historical training data | ~1,270 international matches, 2022–2024 (free tier is capped at 2024). |
| **eloratings.net** | Team strength | Live 2026 World Football Elo table — already reflects current form. |


## The model

**Strength anchor — current Elo (eloratings.net).** Each team's rating comes from
the *live* 2026 eloratings table, which already folds in the 2025 qualifiers,
recent form, and the ongoing tournament. Anchoring to a maintained current rating
keeps the forecast current (rising squads climb, fading ones drop) without letting
thin friendly records inflate weak teams.

**Poisson goal model (Dixon-Coles style).** A `PoissonRegressor` estimates each
team's attack/defense coefficients from historical scorelines, giving expected
goals and a sampled scoreline for any matchup. The simulator needs these for group
goal-difference tiebreakers.

**Gradient-boosted classifier.** A calibrated `HistGradientBoostingClassifier`
predicts win/draw/loss from Elo, recent form, competition importance, and the
Poisson xG signal (model stacking). Served as a **blend** with the Elo baseline at
the cross-validated optimum weight.

**Time-decay.** Historical matches feeding the Poisson and GBM are exponentially
down-weighted by age (1.5-year half-life, tuned on a holdout) so recent results
dominate. Friendlies are additionally discounted (weight 0.35).

## Simulation

Each run fixes already-played results, samples Poisson scorelines for the rest,
computes group tables (FIFA tiebreakers), allocates the 8 best third-placed teams
to the official Round-of-32 slots via constrained matching, then plays out the
exact 2026 bracket (extra time/penalties modeled as an Elo-tilted coin flip).
Aggregating 10,000 runs yields per-team stage probabilities.

## Setup

```bash
pip install -r requirements.txt          # numpy, scipy, pandas, scikit-learn, fastapi, uvicorn

# tokens (free signups) — kept in .env, git-ignored
echo 'FOOTBALL_DATA_TOKEN=your_token' >> .env   # football-data.org/client/register
echo 'API_FOOTBALL_KEY=your_key'      >> .env   # api-football.com (RapidAPI/direct)
```

## Usage

```bash
python -m data.normalize        # fetch (cached) + print the live tournament state
python -m model.elo             # current Elo top 20
python -m model.predictor       # sample match predictions
python -m model.gbm             # honest model evaluation
python -m sim.monte_carlo 10000 # run the full simulation

uvicorn backend.main:app --reload      # API at :8000, frontend at /app
```

Then open **http://localhost:8000/app/** for the dashboard and bracket.
API responses cache to `data/cache/`; re-fetch live data with `force=True`.


 **No squad/player data.** "Current form" is inferred from recent results, not
injuries or lineups.

