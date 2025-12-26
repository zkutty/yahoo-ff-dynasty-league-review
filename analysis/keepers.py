"""Keeper surplus analysis."""
import pandas as pd
from typing import Dict
import numpy as np
import logging

logger = logging.getLogger(__name__)


def calculate_keeper_surplus(
    df: pd.DataFrame
) -> pd.DataFrame:
    """Calculate keeper surplus (market value - keeper cost).
    
    For keepers:
    - market_price_estimate = normalized_price (if available)
    - keeper_cost = actual cost paid at draft (or keeper_cost column if exists)
    - keeper_surplus = market_price_estimate - keeper_cost
    
    Args:
        df: DataFrame with draft picks, normalized_price, and is_keeper
        
    Returns:
        DataFrame with 'keeper_surplus' column added
    """
    df = df.copy()
    
    # Ensure keeper_cost exists (use cost for keepers, NaN for non-keepers)
    if 'keeper_cost' not in df.columns:
        df['keeper_cost'] = df['cost'].where(df['is_keeper'], np.nan)
    
    # Market price estimate is normalized_price
    df['market_price_estimate'] = df['normalized_price']
    
    # Calculate surplus
    df['keeper_surplus'] = np.nan
    keeper_mask = df['is_keeper'] == True
    df.loc[keeper_mask, 'keeper_surplus'] = (
        df.loc[keeper_mask, 'market_price_estimate'] - df.loc[keeper_mask, 'keeper_cost']
    )
    
    logger.info(f"Calculated keeper surplus for {keeper_mask.sum()} keepers")
    return df


def analyze_keeper_value(
    df: pd.DataFrame
) -> pd.DataFrame:
    """Analyze correlation between keeper surplus and realized VAR.
    
    Args:
        df: DataFrame with keeper_surplus, VAR, and related columns
        
    Returns:
        DataFrame with keeper analysis summary
    """
    # Filter to keepers with both surplus and VAR
    keepers = df[(df['is_keeper'] == True) & 
                 (df['keeper_surplus'].notna()) & 
                 (df['VAR'].notna())].copy()
    
    if keepers.empty:
        logger.warning("No keepers with both surplus and VAR data")
        return pd.DataFrame()
    
    # Calculate correlation
    correlation = keepers['keeper_surplus'].corr(keepers['VAR'])
    
    # Group by position and calculate statistics
    keeper_summary = keepers.groupby('position').agg({
        'player_id': 'count',
        'keeper_surplus': ['mean', 'median', 'std'],
        'VAR': ['mean', 'median'],
        'normalized_price': 'mean',
        'keeper_cost': 'mean',
        'VAR_per_dollar': 'mean',
    }).reset_index()
    
    keeper_summary.columns = [
        'position', 'count',
        'avg_surplus', 'median_surplus', 'std_surplus',
        'avg_VAR', 'median_VAR',
        'avg_market_price', 'avg_keeper_cost',
        'avg_VAR_per_dollar'
    ]
    
    # Add overall correlation
    keeper_summary['surplus_VAR_correlation'] = correlation
    
    logger.info(f"Analyzed {len(keepers)} keepers, correlation: {correlation:.3f}")
    return keeper_summary


