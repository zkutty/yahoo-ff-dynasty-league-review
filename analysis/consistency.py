"""Consistency, volatility, and distribution analysis for managers."""
import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


def calculate_manager_outcome_distributions(
    manager_season_value_df: pd.DataFrame
) -> pd.DataFrame:
    """Calculate distribution statistics for manager outcomes.
    
    For each manager across all seasons:
    - wins: mean, median, std, CV, percentiles, min, max
    - VAR: mean, median, std, CV, percentiles
    - VAR/$: mean, median, std, CV, percentiles
    - championships and championship rate
    
    Args:
        manager_season_value_df: Manager-season value DataFrame
        
    Returns:
        DataFrame with one row per manager and distribution stats
    """
    if manager_season_value_df.empty:
        logger.warning("No manager-season data for distribution analysis")
        return pd.DataFrame()
    
    distributions = []
    
    for manager in manager_season_value_df['manager'].unique():
        mgr_data = manager_season_value_df[
            manager_season_value_df['manager'] == manager
        ].copy()
        
        seasons_played = len(mgr_data)
        
        # Wins distribution
        wins = mgr_data['wins'].fillna(0)
        mean_wins = wins.mean()
        median_wins = wins.median()
        std_wins = wins.std()
        cv_wins = std_wins / mean_wins if mean_wins > 0 else np.nan
        p25_wins = wins.quantile(0.25)
        p50_wins = wins.quantile(0.50)
        p75_wins = wins.quantile(0.75)
        min_wins = wins.min()
        max_wins = wins.max()
        
        # Championships
        championships = mgr_data['champion_flag'].sum()
        championship_rate = championships / seasons_played if seasons_played > 0 else 0
        
        # VAR distribution
        total_var = mgr_data['total_VAR'].fillna(0)
        mean_var = total_var.mean()
        median_var = total_var.median()
        std_var = total_var.std()
        cv_var = std_var / mean_var if mean_var != 0 else np.nan
        p25_var = total_var.quantile(0.25)
        p50_var = total_var.quantile(0.50)
        p75_var = total_var.quantile(0.75)
        
        # VAR/$ distribution
        var_per_dollar = mgr_data['VAR_per_dollar'].fillna(0)
        mean_var_per_dollar = var_per_dollar.mean()
        median_var_per_dollar = var_per_dollar.median()
        std_var_per_dollar = var_per_dollar.std()
        cv_var_per_dollar = std_var_per_dollar / mean_var_per_dollar if mean_var_per_dollar != 0 else np.nan
        p25_var_per_dollar = var_per_dollar.quantile(0.25)
        p50_var_per_dollar = var_per_dollar.quantile(0.50)
        p75_var_per_dollar = var_per_dollar.quantile(0.75)
        
        distributions.append({
            'manager': manager,
            'seasons_played': seasons_played,
            # Wins stats
            'mean_wins': mean_wins,
            'median_wins': median_wins,
            'std_wins': std_wins,
            'coefficient_of_variation_wins': cv_wins,
            'win_percentile_25': p25_wins,
            'win_percentile_50': p50_wins,
            'win_percentile_75': p75_wins,
            'min_wins': min_wins,
            'max_wins': max_wins,
            # Championships
            'championships': championships,
            'championship_rate': championship_rate,
            # VAR stats
            'mean_VAR_per_season': mean_var,
            'median_VAR_per_season': median_var,
            'std_VAR_per_season': std_var,
            'coefficient_of_variation_VAR': cv_var,
            'VAR_percentile_25': p25_var,
            'VAR_percentile_50': p50_var,
            'VAR_percentile_75': p75_var,
            # VAR/$ stats
            'mean_VAR_per_dollar_per_season': mean_var_per_dollar,
            'median_VAR_per_dollar_per_season': median_var_per_dollar,
            'std_VAR_per_dollar_per_season': std_var_per_dollar,
            'coefficient_of_variation_VAR_per_dollar': cv_var_per_dollar,
            'VAR_per_dollar_percentile_25': p25_var_per_dollar,
            'VAR_per_dollar_percentile_50': p50_var_per_dollar,
            'VAR_per_dollar_percentile_75': p75_var_per_dollar,
        })
    
    result = pd.DataFrame(distributions)
    logger.info(f"Calculated outcome distributions for {len(result)} managers")
    return result


def calculate_consistency_scores(
    distribution_df: pd.DataFrame
) -> pd.DataFrame:
    """Calculate normalized consistency scores.
    
    Consistency Score = (1 / (1 + std)) * median
    Normalized to 0-100 across all managers.
    
    Args:
        distribution_df: Manager outcome distributions DataFrame
        
    Returns:
        DataFrame with consistency scores
    """
    if distribution_df.empty:
        return pd.DataFrame()
    
    df = distribution_df.copy()
    
    # Wins consistency
    # For managers with 1 season, std is NaN - handle by setting consistency to median directly
    std_wins_filled = df['std_wins'].fillna(0)
    df['consistency_score_wins'] = (1 / (1 + std_wins_filled)) * df['median_wins']
    # If only 1 season, just use median (high consistency by default)
    df.loc[df['seasons_played'] == 1, 'consistency_score_wins'] = df.loc[df['seasons_played'] == 1, 'median_wins']
    
    # VAR consistency
    std_var_filled = df['std_VAR_per_season'].fillna(0)
    df['consistency_score_VAR'] = (1 / (1 + std_var_filled)) * df['median_VAR_per_season']
    df.loc[df['seasons_played'] == 1, 'consistency_score_VAR'] = df.loc[df['seasons_played'] == 1, 'median_VAR_per_season']
    
    # Normalize to 0-100
    for col in ['consistency_score_wins', 'consistency_score_VAR']:
        if df[col].notna().any():
            min_val = df[col].min()
            max_val = df[col].max()
            if max_val > min_val:
                df[col] = ((df[col] - min_val) / (max_val - min_val)) * 100
            else:
                df[col] = 50  # All same value, set to middle
    
    result = df[[
        'manager', 'seasons_played',
        'consistency_score_wins', 'consistency_score_VAR',
        'median_wins', 'std_wins',
        'median_VAR_per_season', 'std_VAR_per_season'
    ]].copy()
    
    # Sort by consistency score (descending)
    result = result.sort_values('consistency_score_wins', ascending=False)
    
    logger.info(f"Calculated consistency scores for {len(result)} managers")
    return result


def classify_manager_archetypes(
    distribution_df: pd.DataFrame
) -> pd.DataFrame:
    """Classify managers into consistency/volatility archetypes.
    
    Definitions:
    - CONSISTENT_CONTENDER: median_wins >= league_median AND std_wins <= league_median_std
    - BOOM_BUST: std_wins >= league_75th_percentile_std
    - LOTTERY: championships >= 1 AND median_wins < league_median
    - STEADY_BUT_UNLUCKY: median_wins >= league_60th_percentile AND championships == 0
    
    Args:
        distribution_df: Manager outcome distributions DataFrame
        
    Returns:
        DataFrame with archetype classifications
    """
    if distribution_df.empty:
        return pd.DataFrame()
    
    df = distribution_df.copy()
    
    # Calculate league benchmarks
    league_median_wins = df['median_wins'].median()
    league_median_std_wins = df['std_wins'].median()
    league_75th_std_wins = df['std_wins'].quantile(0.75)
    league_60th_median_wins = df['median_wins'].quantile(0.60)
    
    # Initialize archetype
    df['archetype'] = 'UNCLASSIFIED'
    
    # CONSISTENT_CONTENDER
    contender_mask = (
        (df['median_wins'] >= league_median_wins) &
        (df['std_wins'] <= league_median_std_wins)
    )
    df.loc[contender_mask, 'archetype'] = 'CONSISTENT_CONTENDER'
    
    # BOOM_BUST (overrides contender if applicable)
    boom_bust_mask = df['std_wins'] >= league_75th_std_wins
    df.loc[boom_bust_mask, 'archetype'] = 'BOOM_BUST'
    
    # LOTTERY
    lottery_mask = (
        (df['championships'] >= 1) &
        (df['median_wins'] < league_median_wins)
    )
    df.loc[lottery_mask, 'archetype'] = 'LOTTERY'
    
    # STEADY_BUT_UNLUCKY (only if not already classified)
    unlucky_mask = (
        (df['archetype'] == 'UNCLASSIFIED') &
        (df['median_wins'] >= league_60th_median_wins) &
        (df['championships'] == 0)
    )
    df.loc[unlucky_mask, 'archetype'] = 'STEADY_BUT_UNLUCKY'
    
    # Keep remaining as UNCLASSIFIED or add more categories
    # For managers with few seasons, mark as LOW_SAMPLE
    low_sample_mask = df['seasons_played'] < 3
    df.loc[low_sample_mask & (df['archetype'] == 'UNCLASSIFIED'), 'archetype'] = 'LOW_SAMPLE'
    
    result = df[[
        'manager', 'seasons_played', 'archetype',
        'median_wins', 'std_wins', 'championships', 'championship_rate'
    ]].copy()
    
    logger.info(f"Classified {len(result)} managers into archetypes")
    logger.info(f"Archetype distribution: {result['archetype'].value_counts().to_dict()}")
    
    return result


def calculate_season_volatility(
    manager_season_value_df: pd.DataFrame
) -> pd.DataFrame:
    """Calculate season-level volatility metrics.
    
    For each season:
    - mean_wins, std_wins
    - win_distribution_skew
    - VAR_distribution_std
    - Gini coefficient of VAR (concentration measure)
    
    Args:
        manager_season_value_df: Manager-season value DataFrame
        
    Returns:
        DataFrame with season volatility metrics
    """
    if manager_season_value_df.empty:
        return pd.DataFrame()
    
    season_volatility = []
    
    for season in sorted(manager_season_value_df['season_year'].unique()):
        season_data = manager_season_value_df[
            manager_season_value_df['season_year'] == season
        ].copy()
        
        # Wins distribution
        wins = season_data['wins'].fillna(0)
        mean_wins = wins.mean()
        std_wins = wins.std()
        win_skew = wins.skew() if len(wins) > 2 else np.nan
        
        # VAR distribution
        var_data = season_data['total_VAR'].fillna(0)
        var_std = var_data.std()
        
        # Gini coefficient for VAR (measure of concentration)
        # Gini = (2 * sum(i * x_i)) / (n * sum(x_i)) - (n + 1) / n
        # where x_i are sorted values
        var_sorted = var_data.sort_values().values
        if len(var_sorted) > 0 and var_sorted.sum() > 0:
            n = len(var_sorted)
            gini_var = (2 * sum((i + 1) * val for i, val in enumerate(var_sorted))) / (n * var_sorted.sum()) - (n + 1) / n
        else:
            gini_var = np.nan
        
        season_volatility.append({
            'season_year': season,
            'num_managers': len(season_data),
            'mean_wins': mean_wins,
            'std_wins': std_wins,
            'win_distribution_skew': win_skew,
            'VAR_distribution_std': var_std,
            'Gini_coefficient_VAR': gini_var,
        })
    
    result = pd.DataFrame(season_volatility)
    logger.info(f"Calculated volatility for {len(result)} seasons")
    return result


def calculate_manager_signal_strength(
    manager_season_value_df: pd.DataFrame
) -> pd.DataFrame:
    """Calculate correlations between VAR metrics and wins.
    
    For each manager:
    - corr_draft_VAR_wins
    - corr_total_VAR_wins
    - corr_keeper_VAR_wins
    - corr_trade_VAR_wins
    - corr_waiver_VAR_wins
    
    Args:
        manager_season_value_df: Manager-season value DataFrame
        
    Returns:
        DataFrame with correlation metrics per manager
    """
    if manager_season_value_df.empty:
        return pd.DataFrame()
    
    signal_strength = []
    
    for manager in manager_season_value_df['manager'].unique():
        mgr_data = manager_season_value_df[
            manager_season_value_df['manager'] == manager
        ].copy()
        
        if len(mgr_data) < 2:
            # Need at least 2 seasons for correlation
            continue
        
        wins = mgr_data['wins'].fillna(0)
        
        # Calculate correlations
        corr_total_var = wins.corr(mgr_data['total_VAR']) if 'total_VAR' in mgr_data.columns else np.nan
        corr_draft_var = wins.corr(mgr_data['draft_VAR']) if 'draft_VAR' in mgr_data.columns else np.nan
        corr_keeper_var = wins.corr(mgr_data['keeper_VAR']) if 'keeper_VAR' in mgr_data.columns else np.nan
        corr_trade_var = wins.corr(mgr_data['trade_VAR']) if 'trade_VAR' in mgr_data.columns else np.nan
        corr_waiver_var = wins.corr(mgr_data['waiver_VAR']) if 'waiver_VAR' in mgr_data.columns else np.nan
        
        signal_strength.append({
            'manager': manager,
            'seasons_played': len(mgr_data),
            'corr_total_VAR_wins': corr_total_var,
            'corr_draft_VAR_wins': corr_draft_var,
            'corr_keeper_VAR_wins': corr_keeper_var,
            'corr_trade_VAR_wins': corr_trade_var,
            'corr_waiver_VAR_wins': corr_waiver_var,
        })
    
    result = pd.DataFrame(signal_strength)
    logger.info(f"Calculated signal strength for {len(result)} managers")
    return result


def calculate_rolling_consistency(
    manager_season_value_df: pd.DataFrame,
    window_size: int = 3,
    min_seasons: int = 4
) -> pd.DataFrame:
    """Calculate rolling window consistency metrics.
    
    For managers with >= min_seasons:
    - Compute rolling window averages for wins and VAR
    - Calculate std of rolling averages
    - This separates sustained excellence from hot streaks
    
    Args:
        manager_season_value_df: Manager-season value DataFrame
        window_size: Size of rolling window (default 3)
        min_seasons: Minimum seasons required (default 4)
        
    Returns:
        DataFrame with rolling consistency metrics
    """
    if manager_season_value_df.empty:
        return pd.DataFrame()
    
    rolling_metrics = []
    
    for manager in manager_season_value_df['manager'].unique():
        mgr_data = manager_season_value_df[
            manager_season_value_df['manager'] == manager
        ].sort_values('season_year').copy()
        
        if len(mgr_data) < min_seasons:
            continue
        
        # Calculate rolling averages
        wins = mgr_data['wins'].fillna(0)
        total_var = mgr_data['total_VAR'].fillna(0)
        
        rolling_wins = wins.rolling(window=window_size, min_periods=window_size).mean()
        rolling_var = total_var.rolling(window=window_size, min_periods=window_size).mean()
        
        # Calculate std of rolling averages
        std_rolling_wins = rolling_wins.std()
        std_rolling_var = rolling_var.std()
        
        # Mean of rolling averages (sustained level)
        mean_rolling_wins = rolling_wins.mean()
        mean_rolling_var = rolling_var.mean()
        
        rolling_metrics.append({
            'manager': manager,
            'seasons_played': len(mgr_data),
            'mean_rolling_wins': mean_rolling_wins,
            'std_rolling_wins': std_rolling_wins,
            'mean_rolling_VAR': mean_rolling_var,
            'std_rolling_VAR': std_rolling_var,
            'rolling_consistency_score_wins': mean_rolling_wins / (1 + std_rolling_wins) if std_rolling_wins > 0 else mean_rolling_wins,
            'rolling_consistency_score_VAR': mean_rolling_var / (1 + std_rolling_var) if std_rolling_var > 0 else mean_rolling_var,
        })
    
    result = pd.DataFrame(rolling_metrics)
    if not result.empty:
        # Normalize consistency scores to 0-100
        for col in ['rolling_consistency_score_wins', 'rolling_consistency_score_VAR']:
            if result[col].notna().any():
                min_val = result[col].min()
                max_val = result[col].max()
                if max_val > min_val:
                    result[col] = ((result[col] - min_val) / (max_val - min_val)) * 100
        
        result = result.sort_values('rolling_consistency_score_wins', ascending=False)
    
    logger.info(f"Calculated rolling consistency for {len(result)} managers with {min_seasons}+ seasons")
    return result

