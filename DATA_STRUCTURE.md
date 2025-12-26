# Data File Structures

This document describes the structure of all data files in the project.

## Directory Structure

```
data/
├── cleaned_data/          # Processed CSV files
├── league_data/           # Raw JSON files from Yahoo API (season_YYYY.json)
└── insights/              # Generated analysis summaries

out/                       # Analysis outputs (Parquet, CSV, plots, reports)
```

---

## Raw League Data (JSON)

**Location:** `data/league_data/season_YYYY.json`

One JSON file per season containing raw data from Yahoo Fantasy API.

### Structure:

```json
{
  "year": 2024,
  "teams": [
    {
      "team_id": "...",
      "team_key": "...",
      "name": "...",
      "manager": "...",
      "manager_id": "...",
      "wins": 10,
      "losses": 4,
      "ties": 0,
      "points_for": 1850.5,
      "points_against": 1700.2,
      "roster": [
        {
          "player_id": 12345,
          "name": "Player Name",
          "position": "QB",
          "status": "",
          "selected_position": "QB",
          "fantasy_points_total": 250.5
        }
      ],
      "season_year": 2024
    }
  ],
  "standings": [
    {
      "team_key": "...",
      "rank": 1,
      "wins": 10,
      "losses": 4,
      "ties": 0,
      "points_for": 1850.5,
      "points_against": 1700.2
    }
  ],
  "transactions": [
    {
      "transaction_id": 472,
      "transaction_key": "449.l.666007.tr.472",
      "type": "add/drop",
      "timestamp": "1735504856",
      "status": "successful",
      "involved_players": [
        {
          "player_id": 41010,
          "player_key": "449.p.41010",
          "transaction_type": "ADD",
          "player_name": "Jaylen Wright",
          "from_team_key": "freeagents",
          "to_team_key": "449.l.666007.t.14",
          "faab_bid": null,
          "waiver_priority": null
        }
      ],
      "num_players_involved": 2
    }
  ],
  "settings": {
    "num_teams": 14,
    "draft_budget": 200,
    ...
  },
  "matchups": [...],
  "draft_results": [...]
}
```

---

## Cleaned Data (CSV files)

**Location:** `data/cleaned_data/*.csv`

### `draft_picks.csv`

Draft pick information including auction prices and keeper status.

**Columns:**
- `season_year`: Season year (int)
- `round`: Draft round (int)
- `pick`: Pick number (int)
- `team_key`: Team identifier (str)
- `player_key`: Yahoo player key (str)
- `player_id`: Yahoo player ID (int)
- `player_name`: Player name (str)
- `position`: Player position (QB, RB, WR, TE, etc.)
- `cost`: Auction draft price (float)
- `is_keeper`: Boolean indicating if player was kept (bool)
- `team_name`: Team name (str)
- `manager`: Manager name (str)
- `manager_id`: Manager ID (str)
- `potential_keeper`: Whether player could be kept next year (bool)
- `keeper_cost`: Keeper cost if applicable (float, nullable)

**Note:** For snake draft years, `cost` may be 0.

---

### `teams.csv`

Team-level statistics and information.

**Columns:**
- `team_id`: Team ID (str)
- `team_key`: Team key (str)
- `name`: Team name (str)
- `manager`: Manager name (str)
- `manager_id`: Manager ID (str)
- `season_year`: Season year (int)
- `wins`: Number of wins (int)
- `losses`: Number of losses (int)
- `ties`: Number of ties (int)
- `points_for`: Total points scored (float)
- `points_against`: Total points allowed (float)

---

### `standings.csv`

League standings data.

**Columns:**
- `team_key`: Team key (str)
- `rank`: Final rank (int)
- `wins`: Number of wins (int)
- `losses`: Number of losses (int)
- `ties`: Number of ties (int)
- `points_for`: Total points scored (float)
- `points_against`: Total points allowed (float)

---

### `managers.csv`

Aggregated manager statistics across all seasons.

**Columns:**
- `manager_id`: Manager ID (str)
- `manager_name`: Manager name (str)
- `seasons`: List of seasons participated (str)
- `total_wins`: Total wins across all seasons (int)
- `total_losses`: Total losses across all seasons (int)
- `total_ties`: Total ties across all seasons (int)
- `total_points_for`: Total points scored (float)
- `total_points_against`: Total points allowed (float)

---

### `matchups.csv`

Weekly matchup results.

**Columns:**
- `season_year`: Season year (int)
- `week`: Week number (int)
- `team1_key`: Team 1 key (str)
- `team1_name`: Team 1 name (str)
- `team1_points`: Team 1 weekly points (float)
- `team2_key`: Team 2 key (str)
- `team2_name`: Team 2 name (str)
- `team2_points`: Team 2 weekly points (float)
- `winner`: Winning team key (str)

---

### `season_summary.csv`

Season-level summary statistics.

**Columns:**
- `season_year`: Season year (int)
- `num_teams`: Number of teams (int)
- `total_games`: Total games played (int)
- `avg_points_per_game`: Average points per game (float)

---

### Draft Analysis CSVs

**`draft_position_spending.csv`**
- Position spending analysis by manager

**`draft_manager_draft_strategies.csv`**
- Manager draft strategy summaries

**`draft_keeper_analysis.csv`**
- Keeper usage analysis

**`draft_draft_value.csv`**
- Draft value metrics

**`draft_year_over_year_trends.csv`**
- Year-over-year position pricing trends

---

## Analysis Outputs

**Location:** `out/*`

### `analysis_ready_{season}.parquet`

Complete analysis-ready dataset per season with all computed metrics.

**Columns:**
- `season_year`: Season year (int)
- `player_id`: Player ID (int)
- `player_name`: Player name (str)
- `position`: Player position (str)
- `cost`: Original auction price (float)
- `is_keeper`: Whether player was a keeper (bool)
- `keeper_cost`: Keeper cost if applicable (float)
- `normalized_price`: Inflation-adjusted price (float)
- `fantasy_points_total`: Total fantasy points (float, nullable)
- `games_played`: Games played (int, nullable)
- `replacement_baseline_points`: Replacement baseline for position (float)
- `VAR`: Value Above Replacement (float, nullable)
- `VAR_per_dollar`: VAR divided by normalized price (float, nullable)
- `dollar_per_VAR`: Normalized price divided by VAR (float, nullable)
- `expected_tier`: Draft tier based on price rank (int, nullable)
- `price_rank_within_position`: Price rank within position (int, nullable)
- `actual_finish_tier`: Actual finish tier based on points (int, nullable)
- `points_rank_within_position`: Points rank within position (int, nullable)
- `market_price_estimate`: Estimated market price (float)
- `keeper_surplus`: Market price - keeper cost (float, nullable)

---

### `lifecycle_table.parquet`

Player-season lifecycle tracking with acquisition information.

**Columns:**
- `season_year`: Season year (int)
- `player_id`: Player ID (int)
- `player_name`: Player name (str)
- `position`: Player position (str)
- `team_key`: Team that acquired player (str)
- `acquisition_type`: draft, keeper, waiver, free_agent, or trade (str)
- `acquisition_week`: Week of acquisition (0 = draft/keeper) (int)
- `acquisition_cost`: Cost of acquisition (draft price, FAAB, or 0) (float)
- `teams_played_for`: Number of teams player was on (int)
- `total_points`: Total fantasy points (float, nullable)
- `VAR_total`: Total VAR (float, nullable)
- `became_keeper`: Whether player became keeper next year (bool)
- `weeks_rostered`: Weeks on roster (int, nullable) - TODO: requires weekly data
- `weeks_started`: Weeks started (int, nullable) - TODO: requires weekly data
- `retained_to_end`: Whether retained to end of season (bool, nullable) - TODO

---

### `waiver_pickups.csv`

Waiver and free agent pickup analysis.

**Columns:**
- `season_year`: Season year (int)
- `player_id`: Player ID (int)
- `player_name`: Player name (str)
- `position`: Player position (str)
- `team_key`: Team that acquired player (str)
- `acquisition_type`: waiver or free_agent (str)
- `acquisition_week`: Week of pickup (int)
- `acquisition_cost`: FAAB spent (float)
- `var_after_pickup`: VAR accumulated after pickup (float)
- `weeks_rostered`: Weeks on roster (int, nullable)
- `weeks_started`: Weeks started (int, nullable)
- `pickup_type`: LEAGUE_WINNER, SOLID_STARTER, STREAMER, or DEAD_PICKUP (str)
- `cost_efficiency`: VAR per FAAB dollar (float, nullable)
- `var_percentile`: VAR percentile at position (float, nullable)
- `became_keeper`: Whether became keeper next year (bool)

---

### `pickup_archetypes.csv`

Summary of pickup classifications.

**Columns:**
- `pickup_type`: Archetype classification (str)
- `position`: Player position (str)
- `count`: Number of pickups (int)
- `avg_VAR`: Average VAR (float)
- `avg_cost_efficiency`: Average cost efficiency (float)

---

### `trade_impact.csv`

Trade impact analysis.

**Columns:**
- `season_year`: Season year (int)
- `transaction_id`: Trade transaction ID (str)
- `trade_week`: Week of trade (int)
- `team_a`: Team A key (str)
- `team_b`: Team B key (str)
- `team_a_players_count`: Number of players team A received (int)
- `team_b_players_count`: Number of players team B received (int)
- `team_a_var_gained`: VAR gained by team A (float)
- `team_a_var_lost`: VAR lost by team A (float)
- `team_b_var_gained`: VAR gained by team B (float)
- `team_b_var_lost`: VAR lost by team B (float)
- `team_a_net_var`: Net VAR for team A (float)
- `team_b_net_var`: Net VAR for team B (float)
- `team_a_result`: WIN, LOSS, or NEUTRAL (str)
- `team_b_result`: WIN, LOSS, or NEUTRAL (str)

---

### `manager_strategy_profiles.csv`

Manager strategy analysis by team-season.

**Columns:**
- `season_year`: Season year (int)
- `team_key`: Team key (str)
- `total_var`: Total VAR (float)
- `draft_var`: VAR from draft picks (float)
- `keeper_var`: VAR from keepers (float)
- `waiver_var`: VAR from waivers/free agents (float)
- `trade_var`: VAR from trades (float)
- `pct_var_from_draft`: % of total VAR from draft (float)
- `pct_var_from_keeper`: % of total VAR from keepers (float)
- `pct_var_from_waiver`: % of total VAR from waivers (float)
- `pct_var_from_trade`: % of total VAR from trades (float)
- `faab_spent`: Total FAAB spent (float)
- `faab_efficiency`: VAR per FAAB dollar (float, nullable)
- `unique_players`: Number of unique players (int)
- `roster_churn_rate`: Roster churn rate (float, nullable) - TODO
- `manager_archetype`: DRAFT_AND_HOLD, WAIVER_HAWK, TRADER, PASSIVE, or BALANCED (str)

---

### `tier_summary.csv`

Tier hit rate analysis.

**Columns:**
- `season_year`: Season year (int)
- `position`: Player position (str)
- `expected_tier`: Expected tier based on draft price (int)
- `count`: Number of players (int)
- `hit_rate`: % meeting or exceeding expected tier (float)
- `bust_rate`: % below replacement level (float)
- `avg_VAR`: Average VAR (float)
- `median_VAR`: Median VAR (float)
- `avg_normalized_price`: Average normalized price (float)
- `avg_fantasy_points`: Average fantasy points (float)

---

### `position_efficiency.csv`

Dollar efficiency metrics by position and tier.

**Columns:**
- `position`: Player position (str)
- `expected_tier`: Expected tier (int)
- `count`: Number of players (int)
- `avg_VAR_per_dollar`: Average VAR per dollar (float)
- `median_VAR_per_dollar`: Median VAR per dollar (float)
- `avg_dollar_per_VAR`: Average dollars per VAR (float)
- `median_dollar_per_VAR`: Median dollars per VAR (float)
- `avg_price`: Average normalized price (float)
- `avg_VAR`: Average VAR (float)

---

### `keeper_surplus_summary.csv`

Keeper value analysis summary.

**Columns:**
- `position`: Player position (str)
- `total_keepers`: Total number of keepers (int)
- `avg_keeper_cost`: Average keeper cost (float)
- `avg_market_price_estimate`: Average market price (float)
- `avg_keeper_surplus`: Average keeper surplus (float)
- `avg_var`: Average VAR (float)
- `correlation_surplus_var`: Correlation between surplus and VAR (float, nullable)

---

### `missing_players.csv`

Report of players drafted but missing from results.

**Columns:**
- `season_year`: Season year (int)
- `player_id`: Player ID (int)
- `player_name`: Player name (str)
- `position`: Player position (str)
- `cost`: Draft price (float)

---

### `ANALYSIS_SUMMARY.md`

Markdown summary report with key insights and statistics.

---

### Plot Files

- `price_vs_var_by_position.png`: Scatter plot of normalized price vs VAR by position
- `faab_vs_var.png`: Scatter plot of FAAB spent vs VAR for waiver pickups
- `var_by_acquisition_source.png`: Stacked bar chart of VAR by acquisition source over time

---

## Notes

- **Nullable fields**: Fields marked as "nullable" may contain `None`/`NaN` values
- **TODO fields**: Fields marked with "TODO" require additional data extraction (e.g., weekly lineup data)
- **Historical data**: Some fields (especially player stats) may be missing for older seasons due to Yahoo API limitations
- **Transaction data**: Requires data refresh with `--refresh` flag to populate

