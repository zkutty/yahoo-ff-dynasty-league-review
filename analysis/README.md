# Auction + Keeper Value Analysis

This module provides a comprehensive analysis pipeline for evaluating auction draft performance, keeper value, and draft efficiency.

## Overview

The analysis pipeline answers three key questions:
1. How well does auction price predict end-of-season value (by position and tier)?
2. Where does the league systematically over/underpay (keeper + inflation aware)?
3. Which positions/tiers produce the best dollar efficiency and hit rates?

## Data Requirements

### Input Data Structure

The pipeline expects data in the following format:

**Drafts (`draft_picks.csv` or `season_{year}.json`):**
- `season_year`: Season year
- `player_id`: Unique player identifier
- `player_name`: Player name
- `position`: Player position (QB, RB, WR, TE)
- `cost`: Auction price paid
- `is_keeper`: Boolean indicating if player was kept
- `keeper_cost`: Cost of keeping the player (optional, defaults to `cost`)

**Results (`player_results.csv` or extracted from `season_{year}.json`):**
- `season_year`: Season year
- `player_id`: Unique player identifier (must match draft data)
- `player_name`: Player name
- `position`: Player position
- `fantasy_points_total`: Total fantasy points for the season
- `games_played`: Number of games played (optional)

**League Metadata (`season_{year}.json`):**
- `num_teams`: Number of teams in league
- `auction_budget`: Auction budget per team (default: $200)
- `starting_slots_by_position`: Dict with starter counts (e.g., {'QB': 1, 'RB': 2, 'WR': 2, 'TE': 1})
- `bench_slots`: Number of bench slots per team
- `num_keepers`: Number of keepers per team (default: 2)

## Usage

### CLI Entrypoint

```bash
python -m analysis --start 2014 --end 2024 --out ./out
```

**Arguments:**
- `--start`: First season to analyze (default: 2014)
- `--end`: Last season to analyze (default: 2024)
- `--out`: Output directory (default: ./out)
- `--baseline`: Baseline season for normalization (default: 2014)

### Programmatic Usage

```python
from analysis.pipeline import run_analysis

results = run_analysis(
    start_year=2014,
    end_year=2024,
    output_dir='./out',
    baseline_season=2014
)
```

## Output Files

The pipeline generates the following outputs in the specified output directory:

1. **`analysis_ready_{season}.parquet`**: Complete analysis-ready dataset per season with:
   - `normalized_price`: Inflation-adjusted price (normalized to baseline)
   - `position_tier`: Tier based on price rank (e.g., WR1, WR2)
   - `replacement_baseline_points`: Replacement level points for position
   - `VAR`: Value Above Replacement
   - `dollar_per_VAR`: Price divided by VAR
   - `VAR_per_dollar`: VAR divided by price
   - `keeper_surplus`: Market price estimate - keeper cost

2. **`tier_summary.csv`**: Tier hit rates and bust rates by position and tier
   - Hit rate: % of players finishing at or above expected tier
   - Bust rate: % of players finishing below replacement level

3. **`position_efficiency.csv`**: Dollar efficiency metrics by position and tier
   - Average and median VAR per dollar
   - Average and median dollar per VAR

4. **`keeper_surplus_summary.csv`**: Keeper value analysis
   - Average keeper surplus by position
   - Correlation between keeper surplus and realized VAR

5. **`price_vs_var_by_position.png`**: Scatter plots showing price vs VAR for each position with trend lines

6. **`missing_players.csv`**: List of players in drafts but missing from results (data quality check)

7. **`ANALYSIS_SUMMARY.md`**: Human-readable summary report with key insights

## Methodology

### Price Normalization

Prices are normalized to account for keeper inflation:
1. Calculate total budget for season: `num_teams * auction_budget`
2. Calculate keeper spend: Sum of all keeper costs
3. Calculate remaining budget: Total budget - keeper spend
4. Calculate effective budget per open roster spot
5. Normalize prices relative to baseline season's effective budget per spot

This allows comparing prices across years despite inflation from keeper values.

### VAR Calculation

Value Above Replacement (VAR) is calculated as:
```
VAR = Player Fantasy Points - Replacement Baseline Points
```

Replacement baseline is determined as:
- `replacement_rank = num_teams * starters_at_position`
- `replacement_points = points of player at replacement_rank`

For example, in a 12-team league with 2 starting RBs per team:
- Replacement rank = 12 * 2 = 24
- Replacement baseline = points of 24th-ranked RB

### Tier Assignment

Tiers are assigned based on normalized price ranks within position:
- Sort players by normalized price (descending)
- Tier size = `num_teams * starters_at_position`
- Tier 1 = ranks 1 to tier_size (e.g., WR1)
- Tier 2 = ranks tier_size+1 to 2*tier_size (e.g., WR2)
- etc.

### Keeper Surplus

Keeper surplus measures value gained from keeping players:
```
keeper_surplus = market_price_estimate - keeper_cost
```

Where `market_price_estimate` is the normalized price (what the player would cost in auction).

## Getting Player Fantasy Points

Player fantasy points are automatically extracted from roster data when you refresh data using `python main.py --refresh`. The `yahoo_client.py` now includes player points in the roster data.

**To populate player points for existing cached data:**

1. **Option 1: Refresh all data** (will update existing JSON files with player points):
   ```bash
   python main.py --refresh
   ```

2. **Option 2: Extract points from API** (if you want to extract just player stats without refreshing everything):
   ```bash
   python -m analysis.extract_stats --start 2014 --end 2024
   ```

The analysis pipeline will automatically load player points from the cached JSON files if available. If player points are missing, the analysis will still run but VAR calculations will be skipped.

## Extended Analysis Features

The pipeline now includes extended analysis for waivers, trades, and roster churn:

### Player Lifecycle Tracking

- **Acquisition Timeline**: Tracks how each player was acquired (draft, keeper, waiver, free agent, trade)
- **Lifecycle Table**: One row per (player, season) with acquisition details and metrics
- **Roster Movements**: Tracks teams played for and retention status

### Waiver Pickup Analysis

- **Pickup Classification**: Automatically classifies pickups into:
  - `LEAGUE_WINNER`: Top VAR at position, multiple starts
  - `SOLID_STARTER`: Positive VAR, multiple starts
  - `STREAMER`: Short tenure, matchup-based
  - `DEAD_PICKUP`: Negative VAR or never started
- **FAAB Efficiency**: VAR per FAAB dollar spent
- **Keeper Conversion**: Tracks which waiver pickups became keepers

### Trade Impact Analysis

- **VAR Impact**: Measures VAR gained/lost per team in each trade
- **Trade Outcomes**: Classifies trades as WIN/LOSS/NEUTRAL
- **Net VAR Swing**: Calculates net value change per team

### Manager Strategy Profiles

- **VAR Breakdown**: % of total VAR from draft, keeper, waiver, trade
- **Strategy Archetypes**:
  - `DRAFT_AND_HOLD`: >60% from draft, <10% from waiver
  - `WAIVER_HAWK`: >30% from waivers
  - `TRADER`: >20% from trades
  - `PASSIVE`: <10% from waiver and trade
  - `BALANCED`: Mixed approach
- **FAAB Efficiency**: VAR per FAAB dollar
- **Roster Churn**: Unique players per season

## Future Enhancements

1. **Weekly Roster Data**: Extract weekly lineup data to calculate weeks_started and weeks_rostered
2. **Weekly VAR**: Calculate VAR on a weekly basis for more granular analysis
3. **Inflation Trends**: Track inflation by position over time
4. **Draft Value Models**: Build predictive models for draft value based on historical data
5. **Keeper Optimization**: Analyze optimal keeper strategies based on surplus and risk

## Testing

The pipeline includes schema validation and data quality checks:
- Validates required columns in draft and results data
- Reports missing players (drafted but no results)
- Warns about missing data (points, tiers, etc.)

## Dependencies

- pandas >= 2.0.0
- numpy
- pyarrow >= 10.0.0 (for Parquet output)
- matplotlib >= 3.7.0 (for plots)
- seaborn >= 0.12.0 (for plots)

