# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Yahoo Fantasy Football Dynasty League Review App - analyzes Yahoo Fantasy Football league history with auction draft value analysis, keeper metrics, VAR (Value Above Replacement) calculations, and optional AI-powered insights via OpenAI.

## Common Commands

```bash
# Fetch fresh data from Yahoo API (requires OAuth - will prompt for auth on first run)
python main.py --refresh

# Use cached data only (no API calls)
python main.py

# Fetch with AI-powered insights (costs OpenAI credits)
python main.py --refresh --generate-ai

# Run auction/keeper value analysis pipeline
python -m analysis --start 2014 --end 2024 --out ./out

# Fetch specific year range
python main.py --refresh --start-year 2020 --end-year 2024
```

## Architecture

### Two Main Entry Points

1. **`main.py`** - Data fetching and basic processing
   - Authenticates with Yahoo Fantasy API via `yahoo_client.py`
   - Fetches season data and saves to `data/league_data/season_YYYY.json`
   - Cleans data via `data_cleaner.py` → saves to `data/cleaned_data/*.csv`
   - Optionally generates AI insights via `ai_insights.py`/`openai_insights.py`

2. **`python -m analysis`** - Advanced analytics pipeline
   - Entry: `analysis/__main__.py` → `analysis/pipeline.py`
   - Loads data via `analysis/data_loader.py`
   - Runs ~15 analysis steps producing outputs in `out/`

### Analysis Pipeline Modules (`analysis/`)

| Module | Purpose |
|--------|---------|
| `normalize.py` | Price normalization accounting for keeper inflation |
| `var.py` | Value Above Replacement calculation |
| `tiers.py` | Draft tier assignment and hit rate analysis |
| `keepers.py` | Keeper surplus analysis |
| `lifecycle.py` | Player acquisition tracking (draft/waiver/trade) |
| `waivers.py` | Waiver pickup classification (LEAGUE_WINNER, SOLID_STARTER, etc.) |
| `trades.py` | Trade impact analysis |
| `strategies.py` | Manager archetype classification |
| `consistency.py` | Manager outcome distributions and volatility |
| `schedule_luck.py` | Expected wins vs actual, schedule difficulty |
| `weekly_lineups.py` | Weekly lineup optimization analysis |
| `plots.py` | Visualization generation |

### Key Data Flow

```
Yahoo API → data/league_data/season_YYYY.json
         → data/cleaned_data/*.csv (teams, matchups, standings, draft_picks, managers)
         → out/*.parquet, out/*.csv (analysis outputs)
         → out/*.png (plots)
```

### Configuration

- Environment: `.env` file with `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_LEAGUE_ID`, `OPENAI_API_KEY`
- Settings: `config.py` - year ranges, directory paths

## Key Concepts

- **VAR (Value Above Replacement)**: Player fantasy points minus replacement-level baseline for their position
- **Normalized Price**: Auction price adjusted for keeper inflation across seasons
- **Keeper Surplus**: Market price estimate minus keeper cost (value gained from keeping)
- **Manager Archetypes**: DRAFT_AND_HOLD, WAIVER_HAWK, TRADER, PASSIVE, BALANCED

## Data Files Reference

See `DATA_STRUCTURE.md` for complete schema documentation of all input/output files.
