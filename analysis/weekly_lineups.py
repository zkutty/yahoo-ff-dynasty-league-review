"""Weekly lineup and matchup analysis."""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


def load_weekly_matchups_from_json(
    league_data_dir: Path,
    start_year: int,
    end_year: int
) -> pd.DataFrame:
    """Load weekly matchup data from raw JSON files.
    
    Tries to extract weekly points from matchup data if available.
    Falls back to season totals if weekly data unavailable.
    
    Args:
        league_data_dir: Directory containing season JSON files
        start_year: First season
        end_year: Last season
        
    Returns:
        DataFrame with weekly matchup data
    """
    weekly_matchups = []
    
    for year in range(start_year, end_year + 1):
        json_file = league_data_dir / f"season_{year}.json"
        if not json_file.exists():
            continue
        
        try:
            with open(json_file, 'r') as f:
                season_data = json.load(f)
            
            matchups = season_data.get('matchups', [])
            
            for matchup in matchups:
                week = matchup.get('week', 0)
                team1_key = matchup.get('team1_key', '')
                team2_key = matchup.get('team2_key', '')
                team1_points = matchup.get('team1_points', 0.0)
                team2_points = matchup.get('team2_points', 0.0)
                winner = matchup.get('winner', '')
                
                # Skip if no points (likely incomplete data)
                if team1_points == 0 and team2_points == 0:
                    continue
                
                # Team 1 perspective
                weekly_matchups.append({
                    'season_year': year,
                    'week': week,
                    'team_key': team1_key,
                    'opponent_team_key': team2_key,
                    'points_for': team1_points,
                    'points_against': team2_points,
                    'win_flag': 1 if team1_key == winner else 0,
                })
                
                # Team 2 perspective
                weekly_matchups.append({
                    'season_year': year,
                    'week': week,
                    'team_key': team2_key,
                    'opponent_team_key': team1_key,
                    'points_for': team2_points,
                    'points_against': team1_points,
                    'win_flag': 1 if team2_key == winner else 0,
                })
        
        except Exception as e:
            logger.warning(f"Error loading weekly matchups for {year}: {e}")
            continue
    
    result = pd.DataFrame(weekly_matchups)
    
    if not result.empty:
        logger.info(f"Loaded {len(result)} weekly matchup records")
    else:
        logger.warning("No weekly matchup data found")
    
    return result


def load_weekly_lineups_from_json(
    league_data_dir: Path,
    teams_df: pd.DataFrame,
    start_year: int,
    end_year: int
) -> pd.DataFrame:
    """Load weekly lineup data from raw JSON files.
    
    Currently, we only have end-of-season rosters in JSON.
    For weekly lineups, we would need to fetch from API or derive.
    
    This is a placeholder that will need to be extended when weekly roster data is available.
    
    Args:
        league_data_dir: Directory containing season JSON files
        teams_df: Teams DataFrame for manager mapping
        start_year: First season
        end_year: Last season
        
    Returns:
        DataFrame with weekly lineup data (empty if unavailable)
    """
    weekly_lineups = []
    
    # Build team_key -> manager mapping
    team_manager_map = {}
    if not teams_df.empty:
        for _, row in teams_df.iterrows():
            team_manager_map[row['team_key']] = row.get('manager', '')
    
    # Try to extract from teams data (if weekly roster snapshots exist)
    # Currently, we only have end-of-season rosters, so this will be empty
    # TODO: Extend to fetch weekly rosters from Yahoo API
    
    result = pd.DataFrame(weekly_lineups)
    
    if result.empty:
        logger.warning("Weekly lineup data not available - need to fetch from API or derive from transactions")
    
    return result


def compute_optimal_lineup(
    players: pd.DataFrame,
    league_settings: Dict
) -> Tuple[float, List[str]]:
    """Compute optimal lineup given roster and constraints.
    
    Constraints (default if not provided):
    - QB: 1
    - RB: 2
    - WR: 2
    - TE: 1
    - FLEX: 1 (can be RB/WR/TE)
    
    Uses greedy selection (sort by points, fill positions).
    
    Args:
        players: DataFrame with columns: player_id, position, points, roster_slot
        league_settings: Dict with lineup constraints
        
    Returns:
        Tuple of (optimal_points, list of player_ids in optimal lineup)
    """
    if players.empty:
        return 0.0, []
    
    # Default lineup constraints
    constraints = {
        'QB': league_settings.get('QB', 1),
        'RB': league_settings.get('RB', 2),
        'WR': league_settings.get('WR', 2),
        'TE': league_settings.get('TE', 1),
        'FLEX': league_settings.get('FLEX', 1),
    }
    
    # Filter to players with valid points
    valid_players = players[players['points'].notna() & (players['points'] > 0)].copy()
    
    if valid_players.empty:
        return 0.0, []
    
    # Sort by points descending
    valid_players = valid_players.sort_values('points', ascending=False).reset_index(drop=True)
    
    # Fill positions
    lineup = []
    remaining_flex_slots = constraints['FLEX']
    flex_positions = ['RB', 'WR', 'TE']
    
    # First fill required positions
    for position, count in constraints.items():
        if position == 'FLEX':
            continue
        
        pos_players = valid_players[
            (valid_players['position'] == position) &
            (~valid_players['player_id'].isin(lineup))
        ].head(count)
        
        lineup.extend(pos_players['player_id'].tolist())
    
    # Then fill FLEX slots with best remaining RB/WR/TE
    flex_candidates = valid_players[
        (valid_players['position'].isin(flex_positions)) &
        (~valid_players['player_id'].isin(lineup))
    ]
    
    for i in range(min(remaining_flex_slots, len(flex_candidates))):
        lineup.append(flex_candidates.iloc[i]['player_id'])
    
    # Calculate total points
    lineup_players = valid_players[valid_players['player_id'].isin(lineup)]
    optimal_points = lineup_players['points'].sum()
    
    return optimal_points, lineup


def build_weekly_lineups_table(
    weekly_lineups_df: pd.DataFrame,
    teams_df: pd.DataFrame,
    league_meta: Dict
) -> pd.DataFrame:
    """Build comprehensive weekly lineup analysis.
    
    For each team-week:
    - actual_points (sum of started players)
    - optimal_points (best possible lineup)
    - lineup_efficiency (actual / optimal)
    - points_left_on_bench
    
    Args:
        weekly_lineups_df: Weekly lineup DataFrame
        teams_df: Teams DataFrame for manager mapping
        league_meta: League settings/metadata
        
    Returns:
        DataFrame with team-week lineup analysis
    """
    if weekly_lineups_df.empty:
        logger.warning("No weekly lineup data available")
        return pd.DataFrame()
    
    team_week_analysis = []
    
    # Get lineup constraints from league_meta
    lineup_constraints = {}
    for season, meta in league_meta.items():
        # Extract from settings if available
        # Default constraints
        lineup_constraints[season] = {
            'QB': 1,
            'RB': 2,
            'WR': 2,
            'TE': 1,
            'FLEX': 1,
        }
    
    for (season, week, team_key), week_data in weekly_lineups_df.groupby(['season_year', 'week', 'team_key']):
        # Calculate actual points (started players)
        started = week_data[week_data['started'] == True]
        actual_points = started['points'].sum() if not started.empty else 0.0
        
        # Calculate optimal lineup
        constraints = lineup_constraints.get(season, lineup_constraints.get(list(lineup_constraints.keys())[0], {}))
        optimal_points, optimal_lineup = compute_optimal_lineup(week_data, constraints)
        
        lineup_efficiency = actual_points / optimal_points if optimal_points > 0 else np.nan
        points_left_on_bench = optimal_points - actual_points
        
        # Get manager
        manager = ''
        team_info = teams_df[
            (teams_df['season_year'] == season) &
            (teams_df['team_key'] == team_key)
        ]
        if not team_info.empty:
            manager = team_info['manager'].iloc[0]
        
        team_week_analysis.append({
            'season_year': season,
            'week': week,
            'team_key': team_key,
            'manager': manager,
            'actual_points': actual_points,
            'optimal_points': optimal_points,
            'lineup_efficiency': lineup_efficiency,
            'points_left_on_bench': points_left_on_bench,
        })
    
    result = pd.DataFrame(team_week_analysis)
    logger.info(f"Built weekly lineup analysis for {len(result)} team-weeks")
    return result


def calculate_weekly_expected_wins(
    weekly_matchups_df: pd.DataFrame
) -> pd.DataFrame:
    """Calculate expected wins using all-play model on weekly basis.
    
    For each week:
    - Rank all teams by points_for
    - expected_wins_week = (num_teams - rank) / (num_teams - 1)
    
    Args:
        weekly_matchups_df: Weekly matchups DataFrame
        
    Returns:
        DataFrame with expected wins per team-week
    """
    if weekly_matchups_df.empty:
        return pd.DataFrame()
    
    expected_wins_weekly = []
    
    for (season, week), week_data in weekly_matchups_df.groupby(['season_year', 'week']):
        # Rank teams by points_for
        week_data = week_data.copy()
        week_data['rank'] = week_data['points_for'].rank(ascending=False, method='min')
        
        num_teams = len(week_data)
        if num_teams < 2:
            continue
        
        # Expected wins formula
        week_data['expected_wins_this_week'] = (num_teams - week_data['rank']) / (num_teams - 1)
        
        for _, row in week_data.iterrows():
            expected_wins_weekly.append({
                'season_year': season,
                'week': week,
                'team_key': row['team_key'],
                'points_for': row['points_for'],
                'expected_wins_this_week': row['expected_wins_this_week'],
            })
    
    result = pd.DataFrame(expected_wins_weekly)
    
    # Aggregate to season level per manager
    if not result.empty and 'manager' in weekly_matchups_df.columns:
        result = result.merge(
            weekly_matchups_df[['season_year', 'week', 'team_key', 'manager']].drop_duplicates(),
            on=['season_year', 'week', 'team_key'],
            how='left'
        )
    
    logger.info(f"Calculated weekly expected wins for {len(result)} team-weeks")
    return result


def classify_losses(
    team_week_perf_df: pd.DataFrame,
    weekly_matchups_df: pd.DataFrame
) -> pd.DataFrame:
    """Classify losses by type: UNLUCKY, LINEUP, DEPTH, SKILL.
    
    For each team-week loss:
    - UNLUCKY_LOSS: actual_points >= league_week_75th_pct
    - LINEUP_LOSS: lineup_efficiency < 0.9
    - DEPTH_LOSS: optimal_points < league_avg
    - SKILL_LOSS: otherwise
    
    Args:
        team_week_perf_df: Team-week performance DataFrame
        weekly_matchups_df: Weekly matchups DataFrame
        
    Returns:
        DataFrame with loss classifications
    """
    if team_week_perf_df.empty or weekly_matchups_df.empty:
        return pd.DataFrame()
    
    # Merge to get wins/losses
    merged = team_week_perf_df.merge(
        weekly_matchups_df[['season_year', 'week', 'team_key', 'win_flag', 'points_for']],
        on=['season_year', 'week', 'team_key'],
        how='inner'
    )
    
    # Only classify losses
    losses = merged[merged['win_flag'] == 0].copy()
    
    if losses.empty:
        return pd.DataFrame()
    
    # Calculate league-wide stats per week
    loss_classifications = []
    
    for (season, week), week_data in losses.groupby(['season_year', 'week']):
        # Get league-wide stats for this week
        week_all = merged[(merged['season_year'] == season) & (merged['week'] == week)]
        
        league_75th_pct = week_all['points_for'].quantile(0.75)
        league_avg_points = week_all['optimal_points'].mean() if 'optimal_points' in week_all.columns else week_all['points_for'].mean()
        
        for _, row in week_data.iterrows():
            actual_points = row['points_for']
            lineup_eff = row.get('lineup_efficiency', np.nan)
            optimal_pts = row.get('optimal_points', np.nan)
            
            loss_type = 'SKILL_LOSS'
            
            if pd.notna(actual_points) and actual_points >= league_75th_pct:
                loss_type = 'UNLUCKY_LOSS'
            elif pd.notna(lineup_eff) and lineup_eff < 0.9:
                loss_type = 'LINEUP_LOSS'
            elif pd.notna(optimal_pts) and optimal_pts < league_avg_points:
                loss_type = 'DEPTH_LOSS'
            
            loss_classifications.append({
                'season_year': season,
                'week': week,
                'team_key': row['team_key'],
                'manager': row.get('manager', ''),
                'points_for': actual_points,
                'optimal_points': optimal_pts,
                'lineup_efficiency': lineup_eff,
                'league_75th_pct': league_75th_pct,
                'league_avg_points': league_avg_points,
                'loss_type': loss_type,
            })
    
    result = pd.DataFrame(loss_classifications)
    logger.info(f"Classified {len(result)} losses")
    return result


def build_manager_season_lineup_stats(
    team_week_perf_df: pd.DataFrame,
    teams_df: pd.DataFrame
) -> pd.DataFrame:
    """Build manager-season lineup statistics.
    
    Computes:
    - avg_lineup_efficiency
    - median_lineup_efficiency
    - std_lineup_efficiency
    - avg_points_left_on_bench
    - total_bench_points
    - bench_waste_rate
    - % weeks with lineup_efficiency >= 0.95
    
    Args:
        team_week_perf_df: Team-week performance DataFrame
        teams_df: Teams DataFrame for manager mapping
        
    Returns:
        DataFrame with manager-season lineup stats
    """
    if team_week_perf_df.empty:
        return pd.DataFrame()
    
    # Ensure manager is populated
    if 'manager' not in team_week_perf_df.columns or team_week_perf_df['manager'].isna().any():
        team_week_perf_df = team_week_perf_df.merge(
            teams_df[['season_year', 'team_key', 'manager']].drop_duplicates(),
            on=['season_year', 'team_key'],
            how='left'
        )
    
    lineup_stats = []
    
    for (season, manager), mgr_data in team_week_perf_df.groupby(['season_year', 'manager']):
        if pd.isna(manager):
            continue
        
        # Filter out weeks with invalid efficiency
        valid_weeks = mgr_data[mgr_data['lineup_efficiency'].notna()]
        
        if valid_weeks.empty:
            continue
        
        avg_efficiency = valid_weeks['lineup_efficiency'].mean()
        median_efficiency = valid_weeks['lineup_efficiency'].median()
        std_efficiency = valid_weeks['lineup_efficiency'].std()
        
        avg_bench_points = valid_weeks['points_left_on_bench'].mean()
        total_bench_points = valid_weeks['points_left_on_bench'].sum()
        
        # Bench waste rate = total bench points / total optimal points
        total_optimal = valid_weeks['optimal_points'].sum()
        bench_waste_rate = total_bench_points / total_optimal if total_optimal > 0 else np.nan
        
        # % weeks with efficiency >= 0.95
        weeks_high_efficiency = (valid_weeks['lineup_efficiency'] >= 0.95).sum()
        pct_high_efficiency = (weeks_high_efficiency / len(valid_weeks)) * 100 if len(valid_weeks) > 0 else 0
        
        lineup_stats.append({
            'season_year': season,
            'manager': manager,
            'weeks_analyzed': len(valid_weeks),
            'avg_lineup_efficiency': avg_efficiency,
            'median_lineup_efficiency': median_efficiency,
            'std_lineup_efficiency': std_efficiency,
            'avg_points_left_on_bench': avg_bench_points,
            'total_bench_points': total_bench_points,
            'total_optimal_points': total_optimal,
            'bench_waste_rate': bench_waste_rate,
            'weeks_high_efficiency': weeks_high_efficiency,
            'pct_weeks_high_efficiency': pct_high_efficiency,
        })
    
    result = pd.DataFrame(lineup_stats)
    logger.info(f"Built lineup stats for {len(result)} manager-seasons")
    return result


