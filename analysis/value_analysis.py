"""VAR-based value analysis for managers and players."""
import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


def build_analysis_ready_player_season(
    analysis_df: pd.DataFrame,
    trades_df: pd.DataFrame = None,
    standings_df: pd.DataFrame = None
) -> pd.DataFrame:
    """Build comprehensive analysis-ready player-season dataset.
    
    One row per (season, player_id) with:
    - position, points_total, games_played
    - replacement_points, VAR, VAR_per_game
    - drafted_flag, draft_price, draft_price_norm, draft_manager
    - keeper_flag, keeper_cost, keeper_surplus
    - acquired_via_trade_flag, trade_week
    - champion_team_flag (if player was on champion team at end)
    
    Args:
        analysis_df: Complete analysis DataFrame with VAR, tiers, etc.
        trades_df: Optional DataFrame with trade transactions
        standings_df: Optional DataFrame with standings (for champion flag)
        
    Returns:
        DataFrame with one row per player-season
    """
    df = analysis_df.copy()
    
    # Ensure we have all required columns
    required_cols = {
        'season_year', 'player_id', 'player_name', 'position',
        'fantasy_points_total', 'replacement_baseline_points', 'VAR',
        'cost', 'normalized_price', 'is_keeper', 'keeper_cost',
        'keeper_surplus', 'manager', 'team_key_draft'
    }
    
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        logger.warning(f"Missing columns in analysis_df: {missing_cols}")
        for col in missing_cols:
            df[col] = np.nan
    
    # Build player-season table
    player_season = df[[
        'season_year', 'player_id', 'player_name', 'position',
        'fantasy_points_total', 'games_played', 'replacement_baseline_points',
        'VAR', 'cost', 'normalized_price', 'is_keeper', 'keeper_cost',
        'keeper_surplus', 'manager', 'team_key_draft'
    ]].copy()
    
    # Rename and add flags
    player_season = player_season.rename(columns={
        'cost': 'draft_price',
        'normalized_price': 'draft_price_norm',
        'manager': 'draft_manager',
        'team_key_draft': 'draft_team_key'
    })
    
    # Flags
    player_season['drafted_flag'] = player_season['draft_price'].notna()
    player_season['keeper_flag'] = player_season['is_keeper'].fillna(False)
    
    # VAR per game
    player_season['VAR_per_game'] = np.nan
    if 'games_played' in player_season.columns:
        has_games = player_season['games_played'].notna() & (player_season['games_played'] > 0)
        player_season.loc[has_games, 'VAR_per_game'] = (
            player_season.loc[has_games, 'VAR'] / player_season.loc[has_games, 'games_played']
        )
    
    # Trade flags (if trades_df available)
    player_season['acquired_via_trade_flag'] = False
    player_season['trade_week'] = np.nan
    
    if trades_df is not None and not trades_df.empty:
        # Extract trade acquisitions from transactions
        trade_acquisitions = trades_df[
            (trades_df['transaction_type'] == 'TRADE') &
            (trades_df['player_id'].notna())
        ].copy()
        
        if not trade_acquisitions.empty:
            # Convert timestamp to week (simplified - use isocalendar week)
            trade_acquisitions['trade_week'] = pd.to_datetime(
                pd.to_numeric(trade_acquisitions['timestamp'], errors='coerce'),
                unit='s',
                errors='coerce'
            ).dt.isocalendar().week
            
            # Merge with player_season
            trade_info = trade_acquisitions.groupby(['season_year', 'player_id']).agg({
                'trade_week': 'first'
            }).reset_index()
            
            player_season = player_season.merge(
                trade_info,
                on=['season_year', 'player_id'],
                how='left',
                suffixes=('', '_trade')
            )
            
            player_season['acquired_via_trade_flag'] = player_season['trade_week'].notna()
            player_season['trade_week'] = player_season['trade_week'].fillna(
                player_season.get('trade_week_trade', pd.Series(dtype=float))
            )
    
    # Champion flag (if standings available)
    player_season['champion_team_flag'] = False
    
    if standings_df is not None and not standings_df.empty:
        # Find champions (rank == 1)
        champions = standings_df[standings_df['final_rank'] == 1][
            ['season_year', 'team_key']
        ].copy()
        
        # Merge with player_season using team_key
        # We need to know which team the player ended the season on
        # For now, use draft_team_key as proxy (TODO: improve with final roster data)
        player_season = player_season.merge(
            champions,
            left_on=['season_year', 'draft_team_key'],
            right_on=['season_year', 'team_key'],
            how='left',
            suffixes=('', '_champ')
        )
        player_season['champion_team_flag'] = player_season['team_key'].notna()
        player_season = player_season.drop(columns=['team_key'], errors='ignore')
    
    # Select final columns
    output_cols = [
        'season_year', 'player_id', 'player_name', 'position',
        'fantasy_points_total', 'games_played',
        'replacement_baseline_points', 'VAR', 'VAR_per_game',
        'drafted_flag', 'draft_price', 'draft_price_norm', 'draft_manager',
        'keeper_flag', 'keeper_cost', 'keeper_surplus',
        'acquired_via_trade_flag', 'trade_week',
        'champion_team_flag'
    ]
    
    result = player_season[[c for c in output_cols if c in player_season.columns]].copy()
    
    logger.info(f"Built analysis-ready player-season table with {len(result)} rows")
    return result


def build_manager_season_value(
    analysis_df: pd.DataFrame,
    teams_df: pd.DataFrame,
    standings_df: pd.DataFrame,
    trades_df: pd.DataFrame = None,
    waiver_pickups_df: pd.DataFrame = None,
    lifecycle_df: pd.DataFrame = None,
    league_meta: Dict = None
) -> pd.DataFrame:
    """Build manager-season value analysis.
    
    One row per (season, manager) with:
    - wins, champion_flag, points_for
    - draft_spend, keeper_spend, total_spend
    - draft_VAR, keeper_VAR, waiver_VAR, trade_VAR
    - total_VAR, VAR_per_$
    - reliance metrics (%VAR from each source)
    
    Args:
        analysis_df: Complete analysis DataFrame
        teams_df: Teams DataFrame with manager info
        standings_df: Standings DataFrame with final ranks
        trades_df: Optional trade transactions
        waiver_pickups_df: Optional waiver pickup analysis
        lifecycle_df: Optional lifecycle DataFrame
        league_meta: League metadata for budget info
        
    Returns:
        DataFrame with manager-season value metrics
    """
    manager_seasons = []
    
    # Get unique manager-seasons - try teams_df first, fall back to analysis_df
    manager_season_keys = pd.DataFrame()
    
    if not teams_df.empty and 'manager' in teams_df.columns:
        manager_season_keys = teams_df[['season_year', 'manager']].drop_duplicates()
        if 'manager_id' in teams_df.columns:
            # Merge manager_id
            mgr_ids = teams_df[['season_year', 'manager', 'manager_id']].drop_duplicates()
            manager_season_keys = manager_season_keys.merge(mgr_ids, on=['season_year', 'manager'], how='left')
        else:
            manager_season_keys['manager_id'] = ''
    
    # Fall back to analysis_df if teams_df doesn't work
    if manager_season_keys.empty and not analysis_df.empty and 'manager' in analysis_df.columns:
        manager_season_keys = analysis_df[['season_year', 'manager']].drop_duplicates()
        if 'manager_id' in analysis_df.columns:
            mgr_ids = analysis_df[['season_year', 'manager', 'manager_id']].drop_duplicates()
            manager_season_keys = manager_season_keys.merge(mgr_ids, on=['season_year', 'manager'], how='left')
        else:
            manager_season_keys['manager_id'] = ''
    
    if manager_season_keys.empty:
        logger.warning("No manager-season combinations found in teams_df or analysis_df")
        return pd.DataFrame()
    
    for idx, ms_key in manager_season_keys.iterrows():
        try:
            season = ms_key['season_year']
            manager = ms_key['manager']
            manager_id = ms_key.get('manager_id', '')
        except KeyError as e:
            logger.warning(f"Missing column in manager_season_keys at row {idx}: {e}. Columns: {manager_season_keys.columns.tolist()}")
            continue
        
        # Get season metadata
        meta = league_meta.get(int(season), {}) if league_meta else {}
        auction_budget = meta.get('auction_budget', 200)
        num_teams = meta.get('num_teams', 12)
        total_league_budget = num_teams * auction_budget
        
        # Get manager's team info
        if not teams_df.empty and 'manager' in teams_df.columns:
            manager_teams = teams_df[
                (teams_df['season_year'] == season) &
                (teams_df['manager'] == manager)
            ]
        else:
            manager_teams = pd.DataFrame()
        
        wins = manager_teams['wins'].sum() if not manager_teams.empty else 0
        points_for = manager_teams['points_for'].sum() if not manager_teams.empty else 0
        
        # Check if champion
        manager_standings = standings_df[
            (standings_df['season_year'] == season) &
            (standings_df['team_key'].isin(manager_teams['team_key'].unique()))
        ]
        champion_flag = (manager_standings['final_rank'] == 1).any() if not manager_standings.empty else False
        
        # Get draft spending and VAR
        manager_drafts = analysis_df[
            (analysis_df['season_year'] == season) &
            (analysis_df['manager'] == manager)
        ].copy()
        
        # Calculate spending
        draft_spend = manager_drafts['cost'].sum()
        keeper_spend = manager_drafts[manager_drafts['is_keeper'] == True]['cost'].sum()
        auction_spend = manager_drafts[manager_drafts['is_keeper'] == False]['cost'].sum()
        total_spend = draft_spend
        
        # Calculate VAR by source
        # Draft VAR (non-keepers)
        draft_var = manager_drafts[
            (manager_drafts['is_keeper'] == False) &
            (manager_drafts['VAR'].notna())
        ]['VAR'].sum()
        
        # Keeper VAR
        keeper_var = manager_drafts[
            (manager_drafts['is_keeper'] == True) &
            (manager_drafts['VAR'].notna())
        ]['VAR'].sum()
        
        # Waiver VAR (if available)
        waiver_var = 0
        if waiver_pickups_df is not None and not waiver_pickups_df.empty:
            # Try to match by manager name if available, otherwise by team_key
            if 'manager' in waiver_pickups_df.columns:
                manager_waivers = waiver_pickups_df[
                    (waiver_pickups_df['season_year'] == season) &
                    (waiver_pickups_df['manager'] == manager)
                ]
            elif 'team_key' in waiver_pickups_df.columns and not manager_teams.empty:
                # Match by team_key
                team_keys = manager_teams['team_key'].unique()
                manager_waivers = waiver_pickups_df[
                    (waiver_pickups_df['season_year'] == season) &
                    (waiver_pickups_df['team_key'].isin(team_keys))
                ]
            else:
                manager_waivers = pd.DataFrame()
            
            if not manager_waivers.empty and 'var_after_pickup' in manager_waivers.columns:
                waiver_var = manager_waivers['var_after_pickup'].fillna(0).sum()
        
        # Trade VAR (if lifecycle available)
        trade_var = 0
        if lifecycle_df is not None and not lifecycle_df.empty:
            # Try to match by manager name if available, otherwise by team_key
            if 'manager' in lifecycle_df.columns:
                manager_lifecycle = lifecycle_df[
                    (lifecycle_df['season_year'] == season) &
                    (lifecycle_df['manager'] == manager) &
                    (lifecycle_df['acquisition_type'] == 'trade')
                ]
            elif 'team_key' in lifecycle_df.columns and not manager_teams.empty:
                team_keys = manager_teams['team_key'].unique()
                manager_lifecycle = lifecycle_df[
                    (lifecycle_df['season_year'] == season) &
                    (lifecycle_df['team_key'].isin(team_keys)) &
                    (lifecycle_df['acquisition_type'] == 'trade')
                ]
            else:
                manager_lifecycle = pd.DataFrame()
            
            if not manager_lifecycle.empty:
                var_col = 'VAR_total' if 'VAR_total' in manager_lifecycle.columns else 'VAR'
                if var_col in manager_lifecycle.columns:
                    trade_var = manager_lifecycle[var_col].fillna(0).sum()
        
        total_var = draft_var + keeper_var + waiver_var + trade_var
        
        # Calculate percentages
        pct_draft = (draft_var / total_var * 100) if total_var > 0 else 0
        pct_keeper = (keeper_var / total_var * 100) if total_var > 0 else 0
        pct_waiver = (waiver_var / total_var * 100) if total_var > 0 else 0
        pct_trade = (trade_var / total_var * 100) if total_var > 0 else 0
        
        # VAR per dollar
        var_per_dollar = total_var / total_spend if total_spend > 0 else np.nan
        
        # Keeper spending percent (FIXED: should be keeper_spend / total_spend, not / total_auction_value)
        keeper_spending_pct = (keeper_spend / total_spend * 100) if total_spend > 0 else 0
        
        manager_seasons.append({
            'season_year': season,
            'manager': manager,
            'manager_id': manager_id,
            'wins': wins,
            'champion_flag': champion_flag,
            'points_for': points_for,
            'draft_spend': draft_spend,
            'keeper_spend': keeper_spend,
            'auction_spend': auction_spend,
            'total_spend': total_spend,
            'keeper_spending_pct': keeper_spending_pct,
            'draft_VAR': draft_var,
            'keeper_VAR': keeper_var,
            'waiver_VAR': waiver_var,
            'trade_VAR': trade_var,
            'total_VAR': total_var,
            'VAR_per_dollar': var_per_dollar,
            'pct_VAR_from_draft': pct_draft,
            'pct_VAR_from_keeper': pct_keeper,
            'pct_VAR_from_waiver': pct_waiver,
            'pct_VAR_from_trade': pct_trade,
        })
    
    result = pd.DataFrame(manager_seasons)
    logger.info(f"Built manager-season value table with {len(result)} rows")
    return result

