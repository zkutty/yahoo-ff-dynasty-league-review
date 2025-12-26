"""Season-level normalization for keepers and inflation."""
import pandas as pd
from typing import Dict
import numpy as np
import logging

logger = logging.getLogger(__name__)


def normalize_prices(
    drafts_df: pd.DataFrame,
    league_meta: Dict,
    baseline_season: int = 2014
) -> pd.DataFrame:
    """Normalize auction prices to account for keepers and inflation.
    
    For each season:
    - Calculate total budget (num_teams * auction_budget)
    - Calculate keeper spend (sum of keeper costs)
    - Calculate remaining budget and roster spots
    - Compute inflation factor vs baseline
    - Normalize prices to baseline $200 cap
    
    Args:
        drafts_df: DataFrame with draft picks (must have cost, is_keeper, season_year)
        league_meta: Dictionary mapping year -> league metadata
        baseline_season: Season to use as baseline for normalization
        
    Returns:
        DataFrame with added 'normalized_price' column
    """
    df = drafts_df.copy()
    
    # Ensure we have keeper_cost column (use cost if keeper_cost doesn't exist)
    if 'keeper_cost' not in df.columns:
        df['keeper_cost'] = df['cost'].where(df['is_keeper'], np.nan)
    
    # Calculate normalization factors per season
    normalization_factors = {}
    
    baseline_meta = league_meta.get(baseline_season, {})
    baseline_budget = baseline_meta.get('num_teams', 12) * baseline_meta.get('auction_budget', 200)
    
    for year in df['season_year'].unique():
        meta = league_meta.get(int(year), {})
        if not meta:
            logger.warning(f"No metadata for season {year}, using defaults")
            num_teams = 12
            auction_budget = 200
            num_keepers_per_team = 2
        else:
            num_teams = meta.get('num_teams', 12)
            auction_budget = meta.get('auction_budget', 200)
            num_keepers_per_team = meta.get('num_keepers', 2)
        
        # Total budget for season
        total_budget = num_teams * auction_budget
        
        # Calculate keeper spend (sum of keeper costs)
        season_drafts = df[df['season_year'] == year]
        keeper_spend = season_drafts[season_drafts['is_keeper'] == True]['cost'].sum()
        
        # Remaining budget for auction
        remaining_budget = total_budget - keeper_spend
        
        # Calculate roster spots
        # Estimate: starting lineup + bench (will refine from metadata if available)
        starting_slots = meta.get('starting_slots_by_position', {})
        total_starters = sum(starting_slots.values()) if starting_slots else 9  # QB+2RB+2WR+TE+FLEX+DEF+K
        bench_slots = meta.get('bench_slots', 6)
        total_roster_spots = num_teams * (total_starters + bench_slots)
        
        # Keepers take up roster spots
        total_keepers = num_teams * num_keepers_per_team
        remaining_roster_spots = total_roster_spots - total_keepers
        
        # Effective budget per open spot (this season)
        effective_budget_per_spot = remaining_budget / remaining_roster_spots if remaining_roster_spots > 0 else auction_budget
        
        # Baseline budget per spot (assuming no keepers for simplicity, or adjust)
        # We normalize to baseline_season's effective budget
        baseline_meta = league_meta.get(baseline_season, {})
        baseline_num_teams = baseline_meta.get('num_teams', 12)
        baseline_auction_budget = baseline_meta.get('auction_budget', 200)
        baseline_total_budget = baseline_num_teams * baseline_auction_budget
        
        # For baseline, assume same structure
        baseline_starting_slots = baseline_meta.get('starting_slots_by_position', {})
        baseline_total_starters = sum(baseline_starting_slots.values()) if baseline_starting_slots else 9
        baseline_bench_slots = baseline_meta.get('bench_slots', 6)
        baseline_total_spots = baseline_num_teams * (baseline_total_starters + baseline_bench_slots)
        
        # For baseline season, check if there were keepers
        baseline_season_drafts = df[df['season_year'] == baseline_season]
        baseline_keeper_spend = baseline_season_drafts[baseline_season_drafts['is_keeper'] == True]['cost'].sum()
        baseline_remaining_budget = baseline_total_budget - baseline_keeper_spend
        baseline_num_keepers = baseline_num_teams * baseline_meta.get('num_keepers', 2)
        baseline_remaining_spots = baseline_total_spots - baseline_num_keepers
        baseline_budget_per_spot = baseline_remaining_budget / baseline_remaining_spots if baseline_remaining_spots > 0 else baseline_auction_budget
        
        # Inflation factor
        inflation_factor = effective_budget_per_spot / baseline_budget_per_spot if baseline_budget_per_spot > 0 else 1.0
        
        # Normalize prices: divide by inflation factor to get baseline-equivalent prices
        normalization_factors[year] = {
            'inflation_factor': inflation_factor,
            'effective_budget_per_spot': effective_budget_per_spot,
            'baseline_budget_per_spot': baseline_budget_per_spot,
            'keeper_spend': keeper_spend,
            'remaining_budget': remaining_budget,
        }
    
    # Apply normalization
    def normalize_price(row):
        year = int(row['season_year'])
        factor = normalization_factors.get(year, {}).get('inflation_factor', 1.0)
        return row['cost'] / factor if factor > 0 else row['cost']
    
    df['normalized_price'] = df.apply(normalize_price, axis=1)
    
    # Store normalization metadata for later use
    df.attrs['normalization_factors'] = normalization_factors
    
    logger.info(f"Normalized prices using baseline season {baseline_season}")
    return df


