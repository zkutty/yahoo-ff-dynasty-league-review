"""Schedule luck and points-against analysis."""
import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def build_weekly_matchups_table(
    matchups_df: pd.DataFrame,
    teams_df: pd.DataFrame,
    standings_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """Build comprehensive weekly matchups table from matchup data.
    
    Creates one row per team-week with:
    - season_year, week, team_id, team_key, manager
    - opponent_team_id, opponent_team_key, opponent_manager
    - points_for, points_against, win_flag
    
    Args:
        matchups_df: DataFrame with matchup data
        teams_df: DataFrame with team info (for manager mapping)
        
    Returns:
        DataFrame with weekly matchup details
    """
    if matchups_df.empty:
        logger.warning("No matchup data available")
        return pd.DataFrame()
    
    weekly_data = []
    
    # Build team lookup
    team_lookup = {}
    if not teams_df.empty:
        for _, team in teams_df.iterrows():
            team_key = team.get('team_key', '')
            team_lookup[team_key] = {
                'team_id': team.get('team_id', ''),
                'manager': team.get('manager', ''),
                'manager_id': team.get('manager_id', '')
            }
    
    # Build weekly points lookup from standings if matchups don't have points
    # For now, use points from matchups; if missing, we'll need to derive or skip
    
    # Process matchups
    for _, matchup in matchups_df.iterrows():
        season = matchup.get('season_year')
        week = matchup.get('week')
        
        team1_key = matchup.get('team1_key', '')
        team2_key = matchup.get('team2_key', '')
        team1_points = matchup.get('team1_points', 0.0)
        team2_points = matchup.get('team2_points', 0.0)
        winner = matchup.get('winner', '')
        
        # If points are 0, try to skip or log warning
        if team1_points == 0 and team2_points == 0:
            # Skip weeks with no points (likely bye weeks or incomplete data)
            continue
        
        # Team 1 perspective
        weekly_data.append({
            'season_year': season,
            'week': week,
            'team_key': team1_key,
            'team_id': team_lookup.get(team1_key, {}).get('team_id', ''),
            'manager': team_lookup.get(team1_key, {}).get('manager', ''),
            'manager_id': team_lookup.get(team1_key, {}).get('manager_id', ''),
            'opponent_team_key': team2_key,
            'opponent_team_id': team_lookup.get(team2_key, {}).get('team_id', ''),
            'opponent_manager': team_lookup.get(team2_key, {}).get('manager', ''),
            'points_for': team1_points,
            'points_against': team2_points,
            'win_flag': 1 if team1_key == winner else 0,
        })
        
        # Team 2 perspective
        weekly_data.append({
            'season_year': season,
            'week': week,
            'team_key': team2_key,
            'team_id': team_lookup.get(team2_key, {}).get('team_id', ''),
            'manager': team_lookup.get(team2_key, {}).get('manager', ''),
            'manager_id': team_lookup.get(team2_key, {}).get('manager_id', ''),
            'opponent_team_key': team1_key,
            'opponent_team_id': team_lookup.get(team1_key, {}).get('team_id', ''),
            'opponent_manager': team_lookup.get(team1_key, {}).get('manager', ''),
            'points_for': team2_points,
            'points_against': team1_points,
            'win_flag': 1 if team2_key == winner else 0,
        })
    
    result = pd.DataFrame(weekly_data)
    
    if not result.empty:
        logger.info(f"Built weekly matchups table with {len(result)} team-weeks")
    
    return result


def calculate_expected_wins_from_season_totals(
    standings_df: pd.DataFrame,
    teams_df: pd.DataFrame,
    matchups_df: pd.DataFrame
) -> pd.DataFrame:
    """Calculate expected wins using season totals when weekly data unavailable.
    
    Uses a simplified model: assumes weekly performance proportional to season totals.
    This is an approximation but useful when weekly breakdown isn't available.
    
    Args:
        standings_df: Standings DataFrame with season totals
        teams_df: Teams DataFrame with manager mapping
        matchups_df: Matchups DataFrame to determine number of weeks
        
    Returns:
        DataFrame with expected wins per manager-season
    """
    if standings_df.empty or teams_df.empty:
        return pd.DataFrame()
    
    expected_wins_list = []
    
    # Determine weeks per season from matchups
    weeks_per_season = {}
    if not matchups_df.empty:
        for season in matchups_df['season_year'].unique():
            season_matchups = matchups_df[matchups_df['season_year'] == season]
            weeks_per_season[season] = season_matchups['week'].max()
    
    # For each season
    for season in standings_df['season_year'].unique():
        season_standings = standings_df[standings_df['season_year'] == season].copy()
        season_teams = teams_df[teams_df['season_year'] == season]
        
        if season_standings.empty:
            continue
        
        # Merge to get manager info
        season_data = season_standings.merge(
            season_teams[['team_key', 'manager']],
            on='team_key',
            how='left'
        )
        
        # Rank teams by points_for
        season_data = season_data.sort_values('points_for', ascending=False)
        season_data['rank'] = range(1, len(season_data) + 1)
        
        num_teams = len(season_data)
        num_weeks = weeks_per_season.get(season, 13)  # Default to 13 weeks
        
        # Expected wins formula: (num_teams - rank) / (num_teams - 1) per week * num_weeks
        season_data['expected_wins'] = ((num_teams - season_data['rank']) / (num_teams - 1)) * num_weeks
        
        # Aggregate by manager
        for manager in season_data['manager'].unique():
            if pd.isna(manager):
                continue
            mgr_data = season_data[season_data['manager'] == manager]
            expected_wins_list.append({
                'season_year': season,
                'manager': manager,
                'expected_wins': mgr_data['expected_wins'].sum(),
            })
    
    result = pd.DataFrame(expected_wins_list)
    logger.info(f"Calculated expected wins from season totals for {len(result)} manager-seasons")
    return result


def calculate_expected_wins(
    weekly_matchups_df: pd.DataFrame,
    standings_df: Optional[pd.DataFrame] = None,
    teams_df: Optional[pd.DataFrame] = None,
    matchups_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """Calculate expected wins using all-play model.
    
    For each week:
    - Rank all teams by points_for
    - Team earns (num_teams - rank) / (num_teams - 1) expected wins
    
    If weekly data unavailable, falls back to season totals approximation.
    
    Args:
        weekly_matchups_df: Weekly matchups DataFrame
        standings_df: Optional standings DataFrame (fallback)
        teams_df: Optional teams DataFrame (fallback)
        matchups_df: Optional matchups DataFrame (for week counts)
        
    Returns:
        DataFrame with expected wins per manager-season
    """
    # Check if we have valid weekly points
    if not weekly_matchups_df.empty:
        has_points = (weekly_matchups_df['points_for'] > 0).any()
        if has_points:
            expected_wins_list = []
            
            # Group by season and week
            for (season, week), week_data in weekly_matchups_df.groupby(['season_year', 'week']):
                # Rank teams by points_for (descending)
                week_data = week_data.copy()
                week_data['rank'] = week_data['points_for'].rank(ascending=False, method='min')
                
                num_teams = len(week_data)
                if num_teams < 2:
                    continue
                
                # Expected wins formula: (num_teams - rank) / (num_teams - 1)
                week_data['expected_wins_this_week'] = (num_teams - week_data['rank']) / (num_teams - 1)
                
                # Aggregate by manager (in case same manager has multiple teams, sum)
                for manager in week_data['manager'].unique():
                    if pd.isna(manager):
                        continue
                    mgr_week_data = week_data[week_data['manager'] == manager]
                    expected_wins_list.append({
                        'season_year': season,
                        'week': week,
                        'manager': manager,
                        'expected_wins_this_week': mgr_week_data['expected_wins_this_week'].sum()
                    })
            
            expected_wins_weekly = pd.DataFrame(expected_wins_list)
            
            # Aggregate to season level
            if not expected_wins_weekly.empty:
                expected_wins_season = expected_wins_weekly.groupby(['season_year', 'manager']).agg({
                    'expected_wins_this_week': 'sum'
                }).reset_index()
                expected_wins_season.columns = ['season_year', 'manager', 'expected_wins']
                
                logger.info(f"Calculated expected wins from weekly data for {len(expected_wins_season)} manager-seasons")
                return expected_wins_season
    
    # Fallback: use season totals
    if standings_df is not None and teams_df is not None:
        logger.info("Weekly points unavailable, using season totals approximation")
        return calculate_expected_wins_from_season_totals(standings_df, teams_df, matchups_df if matchups_df is not None else pd.DataFrame())
    
    logger.warning("Cannot calculate expected wins - insufficient data")
    return pd.DataFrame()


def build_manager_season_schedule(
    weekly_matchups_df: pd.DataFrame,
    standings_df: pd.DataFrame,
    teams_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """Build manager-season schedule analysis.
    
    One row per (season, manager) with:
    - games_played, wins, losses
    - points_for, points_against
    - avg_points_for, avg_points_against
    - std_points_against
    - league_avg_PA
    - PA_diff
    
    Args:
        weekly_matchups_df: Weekly matchups DataFrame (may be empty if weekly unavailable)
        standings_df: Standings DataFrame
        teams_df: Optional teams DataFrame for manager mapping
        
    Returns:
        DataFrame with schedule metrics
    """
    schedule_list = []
    
    # Try weekly data first
    if not weekly_matchups_df.empty and (weekly_matchups_df['points_for'] > 0).any():
        for (season, manager), mgr_data in weekly_matchups_df.groupby(['season_year', 'manager']):
            games_played = len(mgr_data)
            wins = mgr_data['win_flag'].sum()
            losses = games_played - wins
            points_for = mgr_data['points_for'].sum()
            points_against = mgr_data['points_against'].sum()
            avg_points_for = mgr_data['points_for'].mean()
            avg_points_against = mgr_data['points_against'].mean()
            std_points_against = mgr_data['points_against'].std()
            
            # League average PA for this season
            season_all = weekly_matchups_df[weekly_matchups_df['season_year'] == season]
            league_avg_PA = season_all['points_against'].mean()
            PA_diff = avg_points_against - league_avg_PA
            
            schedule_list.append({
                'season_year': season,
                'manager': manager,
                'games_played': games_played,
                'wins': wins,
                'losses': losses,
                'points_for': points_for,
                'points_against': points_against,
                'avg_points_for': avg_points_for,
                'avg_points_against': avg_points_against,
                'std_points_against': std_points_against,
                'league_avg_PA': league_avg_PA,
                'PA_diff': PA_diff,
            })
    
    # Fallback: use standings/teams data
    elif not standings_df.empty and teams_df is not None and not teams_df.empty:
        # Merge standings with teams to get manager
        merged = standings_df.merge(
            teams_df[['season_year', 'team_key', 'manager']],
            on=['season_year', 'team_key'],
            how='left'
        )
        
        for (season, manager), mgr_data in merged.groupby(['season_year', 'manager']):
            if pd.isna(manager):
                continue
            
            wins = mgr_data['wins'].sum() if 'wins' in mgr_data.columns else 0
            losses = mgr_data['losses'].sum() if 'losses' in mgr_data.columns else 0
            games_played = wins + losses
            
            points_for = mgr_data['points_for'].sum() if 'points_for' in mgr_data.columns else 0
            points_against = mgr_data['points_against'].sum() if 'points_against' in mgr_data.columns else 0
            
            avg_points_for = points_for / games_played if games_played > 0 else 0
            avg_points_against = points_against / games_played if games_played > 0 else 0
            
            # League average PA for this season
            season_all = merged[merged['season_year'] == season]
            league_avg_PA = season_all['points_against'].mean() if 'points_against' in season_all.columns else 0
            PA_diff = avg_points_against - league_avg_PA
            
            schedule_list.append({
                'season_year': season,
                'manager': manager,
                'games_played': games_played,
                'wins': wins,
                'losses': losses,
                'points_for': points_for,
                'points_against': points_against,
                'avg_points_for': avg_points_for,
                'avg_points_against': avg_points_against,
                'std_points_against': np.nan,  # Can't calculate without weekly data
                'league_avg_PA': league_avg_PA,
                'PA_diff': PA_diff,
            })
    
    result = pd.DataFrame(schedule_list)
    
    if not result.empty:
        logger.info(f"Built schedule analysis for {len(result)} manager-seasons")
    else:
        logger.warning("No schedule data available")
    
    return result


def calculate_schedule_difficulty(
    weekly_matchups_df: pd.DataFrame
) -> pd.DataFrame:
    """Calculate schedule difficulty index.
    
    For each manager-season:
    - Avg opponent strength (avg opponent points_for)
    - Opponent percentile (avg percentile of opponents' weekly scores)
    
    Normalized to league mean = 0.
    
    Args:
        weekly_matchups_df: Weekly matchups DataFrame
        
    Returns:
        DataFrame with schedule difficulty metrics
    """
    if weekly_matchups_df.empty:
        return pd.DataFrame()
    
    difficulty_list = []
    
    for (season, manager), mgr_data in weekly_matchups_df.groupby(['season_year', 'manager']):
        # Average opponent strength (points scored by opponents)
        avg_opponent_points = mgr_data['points_against'].mean()
        
        # Opponent percentile calculation
        # For each week, calculate percentile of opponent's score
        opponent_percentiles = []
        for week in mgr_data['week'].unique():
            week_all = weekly_matchups_df[
                (weekly_matchups_df['season_year'] == season) &
                (weekly_matchups_df['week'] == week)
            ]
            if len(week_all) < 2:
                continue
            
            mgr_week = mgr_data[mgr_data['week'] == week]
            if mgr_week.empty:
                continue
            
            opponent_pf = mgr_week['points_against'].iloc[0]  # Points opponent scored = PA for this team
            percentile = (week_all['points_for'] <= opponent_pf).sum() / len(week_all)
            opponent_percentiles.append(percentile)
        
        avg_opponent_percentile = np.mean(opponent_percentiles) if opponent_percentiles else np.nan
        
        difficulty_list.append({
            'season_year': season,
            'manager': manager,
            'avg_opponent_points_for': avg_opponent_points,
            'avg_opponent_percentile': avg_opponent_percentile,
        })
    
    result = pd.DataFrame(difficulty_list)
    
    # Normalize to league mean = 0
    if not result.empty:
        # Calculate league means per season
        for season in result['season_year'].unique():
            season_mask = result['season_year'] == season
            league_mean_opp_points = result.loc[season_mask, 'avg_opponent_points_for'].mean()
            result.loc[season_mask, 'schedule_difficulty_score'] = (
                result.loc[season_mask, 'avg_opponent_points_for'] - league_mean_opp_points
            )
            
            # For percentile, center around 0.5
            league_mean_percentile = result.loc[season_mask, 'avg_opponent_percentile'].mean()
            result.loc[season_mask, 'schedule_difficulty_percentile'] = (
                result.loc[season_mask, 'avg_opponent_percentile'] - 0.5
            ) * 100  # Scale to percentage points
    
    logger.info(f"Calculated schedule difficulty for {len(result)} manager-seasons")
    return result


def build_manager_luck_profile(
    schedule_df: pd.DataFrame,
    expected_wins_df: pd.DataFrame,
    manager_season_value_df: pd.DataFrame
) -> pd.DataFrame:
    """Build long-run luck vs skill profile per manager.
    
    Aggregate across seasons:
    - mean_PA_diff
    - std_PA_diff
    - mean_win_luck
    - std_win_luck
    - % seasons unlucky (win_luck < -1)
    - % seasons lucky (win_luck > +1)
    
    Args:
        schedule_df: Manager-season schedule DataFrame
        expected_wins_df: Expected wins DataFrame
        manager_season_value_df: Manager-season value DataFrame
        
    Returns:
        DataFrame with manager luck profiles
    """
    if schedule_df.empty or expected_wins_df.empty:
        return pd.DataFrame()
    
    # Merge data
    merged = schedule_df.merge(
        expected_wins_df,
        on=['season_year', 'manager'],
        how='left'
    )
    
    if merged.empty:
        return pd.DataFrame()
    
    # Calculate win_luck
    merged['win_luck'] = merged['wins'] - merged['expected_wins'].fillna(merged['wins'])
    
    # Aggregate by manager
    luck_profiles = []
    
    for manager in merged['manager'].unique():
        mgr_data = merged[merged['manager'] == manager].copy()
        
        seasons_count = len(mgr_data)
        
        mean_PA_diff = mgr_data['PA_diff'].mean()
        std_PA_diff = mgr_data['PA_diff'].std()
        mean_win_luck = mgr_data['win_luck'].mean()
        std_win_luck = mgr_data['win_luck'].std()
        
        # Unlucky/lucky seasons
        unlucky_seasons = (mgr_data['win_luck'] < -1).sum()
        lucky_seasons = (mgr_data['win_luck'] > 1).sum()
        pct_unlucky = (unlucky_seasons / seasons_count * 100) if seasons_count > 0 else 0
        pct_lucky = (lucky_seasons / seasons_count * 100) if seasons_count > 0 else 0
        
        # Add points_for rank info if available
        avg_PF_rank = np.nan
        if manager_season_value_df is not None and not manager_season_value_df.empty:
            mgr_value = manager_season_value_df[manager_season_value_df['manager'] == manager]
            # Calculate PF rank per season (would need to merge with all teams)
            # For now, skip this detail
        
        luck_profiles.append({
            'manager': manager,
            'seasons_played': seasons_count,
            'mean_PA_diff': mean_PA_diff,
            'std_PA_diff': std_PA_diff,
            'mean_win_luck': mean_win_luck,
            'std_win_luck': std_win_luck,
            'total_unlucky_seasons': unlucky_seasons,
            'total_lucky_seasons': lucky_seasons,
            'pct_seasons_unlucky': pct_unlucky,
            'pct_seasons_lucky': pct_lucky,
        })
    
    result = pd.DataFrame(luck_profiles)
    logger.info(f"Built luck profiles for {len(result)} managers")
    return result


def analyze_championship_luck(
    schedule_df: pd.DataFrame,
    expected_wins_df: pd.DataFrame,
    standings_df: pd.DataFrame,
    teams_df: pd.DataFrame
) -> pd.DataFrame:
    """Analyze luck component of championships.
    
    For championship seasons:
    - wins_over_expected
    - PA_diff
    - PF_rank
    
    Args:
        schedule_df: Manager-season schedule DataFrame
        expected_wins_df: Expected wins DataFrame
        standings_df: Standings DataFrame
        teams_df: Teams DataFrame
        
    Returns:
        DataFrame with championship luck analysis
    """
    if schedule_df.empty or expected_wins_df.empty or standings_df.empty:
        return pd.DataFrame()
    
    # Find champions (rank == 1)
    champions = standings_df[standings_df['final_rank'] == 1].copy()
    
    if champions.empty:
        return pd.DataFrame()
    
    # Merge schedule and expected wins
    champ_analysis = []
    
    for _, champ in champions.iterrows():
        season = champ['season_year']
        team_key = champ['team_key']
        
        # Get manager from teams
        team_info = teams_df[
            (teams_df['season_year'] == season) &
            (teams_df['team_key'] == team_key)
        ]
        
        if team_info.empty:
            continue
        
        manager = team_info['manager'].iloc[0]
        points_for_actual = champ.get('points_for', 0)
        
        # Get schedule data
        mgr_schedule = schedule_df[
            (schedule_df['season_year'] == season) &
            (schedule_df['manager'] == manager)
        ]
        
        # Get expected wins
        mgr_expected = expected_wins_df[
            (expected_wins_df['season_year'] == season) &
            (expected_wins_df['manager'] == manager)
        ]
        
        wins_over_expected = np.nan
        if not mgr_schedule.empty and not mgr_expected.empty:
            wins_over_expected = mgr_schedule['wins'].iloc[0] - mgr_expected['expected_wins'].iloc[0]
        
        PA_diff = mgr_schedule['PA_diff'].iloc[0] if not mgr_schedule.empty else np.nan
        
        # Calculate PF rank (percentile in league)
        season_standings = standings_df[standings_df['season_year'] == season]
        pf_rank = (season_standings['points_for'] <= points_for_actual).sum() / len(season_standings) * 100
        pf_rank_percentile = 100 - pf_rank  # Higher is better
        
        champ_analysis.append({
            'season_year': season,
            'manager': manager,
            'wins': champ.get('wins', 0),
            'expected_wins': mgr_expected['expected_wins'].iloc[0] if not mgr_expected.empty else np.nan,
            'wins_over_expected': wins_over_expected,
            'points_for': points_for_actual,
            'points_for_percentile': pf_rank_percentile,
            'PA_diff': PA_diff,
            'championship_type': 'DOMINANT' if wins_over_expected >= 1 else ('LUCKY' if wins_over_expected <= -1 else 'BALANCED')
        })
    
    result = pd.DataFrame(champ_analysis)
    
    if not result.empty:
        logger.info(f"Analyzed {len(result)} championship seasons")
    
    return result

