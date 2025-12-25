# Auction + Keeper Value Analysis Summary

**Analysis Period:** 2020-2021
**Baseline Season:** 2020

## Overall Statistics

- Total Drafted Players: 420
- Players with VAR: 278 (66.2%)
- Players with Points: 325 (77.4%)

## Key Insights

### Top 10 Value Picks (VAR per Dollar)

| Player | Position | Price | VAR | VAR/$ |
|--------|----------|-------|-----|-------|
| Justin Jefferson | WR | $206.0 | 127.9 | 0.62 |
| Damien Harris | RB | $103.0 | 55.7 | 0.54 |
| Calvin Ridley | WR | $169.2 | 86.9 | 0.51 |
| Jaylen Waddle | WR | $103.0 | 43.3 | 0.42 |
| Patrick Mahomes | QB | $338.5 | 108.8 | 0.32 |
| Kirk Cousins | QB | $169.2 | 48.2 | 0.28 |
| Aaron Jones Sr. | RB | $338.5 | 94.7 | 0.28 |
| Kirk Cousins | QB | $206.0 | 54.4 | 0.26 |
| Joe Burrow | QB | $309.0 | 75.3 | 0.24 |
| Amon-Ra St. Brown | WR | $103.0 | 24.8 | 0.24 |

### Tier Hit Rates by Position

- **QB**: 100.0% average hit rate
- **RB**: 100.0% average hit rate
- **WR**: 100.0% average hit rate
- **TE**: 100.0% average hit rate

### Keeper Analysis

- Total Keepers Analyzed: 420
- Average Keeper Surplus: $1790.41
- Keeper Surplus vs VAR Correlation: 0.349

### Manager Strategy Profiles

Manager Archetype Distribution:
- PASSIVE: 28

## Output Files

- `analysis_ready_{season}.parquet`: Complete analysis-ready dataset per season
- `tier_summary.csv`: Tier hit rates and bust rates
- `position_efficiency.csv`: Dollar efficiency by position and tier
- `keeper_surplus_summary.csv`: Keeper value analysis
- `price_vs_var_by_position.png`: Scatter plots of price vs VAR
- `missing_players.csv`: Players in drafts but missing from results
- `lifecycle_table.parquet`: Complete player-season lifecycle
- `manager_strategy_profiles.csv`: Manager strategy archetypes

## Methodology

1. **Price Normalization**: Prices normalized to baseline season accounting for keeper inflation
2. **VAR Calculation**: Value Above Replacement = Player Points - Replacement Baseline Points
3. **Tier Assignment**: Tiers based on normalized price ranks within position
4. **Keeper Surplus**: Market Price Estimate - Keeper Cost
