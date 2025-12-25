"""Extract player fantasy points from Yahoo Fantasy API."""
import pandas as pd
from typing import Dict, List
from pathlib import Path
import logging
from yahoofantasy import Context
import config

logger = logging.getLogger(__name__)


def extract_player_stats_from_api(
    season: int,
    league_id: str = None,
    ctx: Context = None
) -> pd.DataFrame:
    """Extract player fantasy points from Yahoo Fantasy API.
    
    Args:
        season: Season year
        league_id: League ID (uses config if None)
        ctx: Yahoo Context object (creates new if None)
        
    Returns:
        DataFrame with player_id, fantasy_points_total, games_played
    """
    if ctx is None:
        ctx = Context(
            persist_key='yahoo_fantasy',
            client_id=config.YAHOO_CLIENT_ID,
            client_secret=config.YAHOO_CLIENT_SECRET,
            refresh_token=config.YAHOO_REFRESH_TOKEN
        )
    
    if league_id is None:
        league_id = config.YAHOO_LEAGUE_ID
    
    try:
        # Get league for this season
        leagues = ctx.get_leagues('nfl', season)
        league = None
        
        # Find league by ID or name
        for l in leagues:
            if str(getattr(l, 'league_id', '')) == str(league_id):
                league = l
                break
            # Try matching by name if we have cached name
            if hasattr(ctx, '_league_name'):
                if getattr(l, 'name', '') == ctx._league_name:
                    league = l
                    break
        
        if not league:
            logger.warning(f"League not found for season {season}")
            return pd.DataFrame()
        
        # Get all teams
        teams = league.teams()
        
        player_stats_list = []
        
        for team in teams:
            try:
                roster = team.roster()
                
                for player in roster.players:
                    player_id = getattr(player, 'player_id', None)
                    if not player_id:
                        continue
                    
                    # Try to get points for the season
                    total_points = None
                    games_played = None
                    
                    # Method 1: Try get_points() if available
                    if hasattr(player, 'get_points'):
                        try:
                            points_obj = player.get_points()
                            # Points might be a dict, APIAttr, or number
                            if isinstance(points_obj, dict):
                                total_points = points_obj.get('total', points_obj.get('points', None))
                            elif hasattr(points_obj, 'total'):
                                total_points = getattr(points_obj, 'total', None)
                            else:
                                total_points = float(points_obj) if points_obj else None
                        except Exception as e:
                            logger.debug(f"Error getting points for player {player_id}: {e}")
                    
                    # Method 2: Try to get from player stats
                    if total_points is None and hasattr(player, 'get_stats'):
                        try:
                            stats = player.get_stats()
                            if stats:
                                # Stats structure varies - try different access patterns
                                if isinstance(stats, dict):
                                    total_points = stats.get('points', stats.get('total', None))
                                elif hasattr(stats, 'points'):
                                    total_points = getattr(stats, 'points', None)
                        except Exception as e:
                            logger.debug(f"Error getting stats for player {player_id}: {e}")
                    
                    # Get player name and position
                    player_name = ''
                    if hasattr(player, 'name'):
                        name_obj = getattr(player, 'name', None)
                        if hasattr(name_obj, 'full'):
                            player_name = getattr(name_obj, 'full', '')
                        elif isinstance(name_obj, str):
                            player_name = name_obj
                    
                    position = getattr(player, 'primary_position', '')
                    
                    if player_id:
                        player_stats_list.append({
                            'season_year': season,
                            'player_id': player_id,
                            'player_name': player_name,
                            'position': position,
                            'fantasy_points_total': total_points,
                            'games_played': games_played,  # Will need separate extraction
                            'team_key': getattr(team, 'team_key', ''),
                        })
            
            except Exception as e:
                logger.warning(f"Error processing team {getattr(team, 'name', 'unknown')}: {e}")
                continue
        
        df = pd.DataFrame(player_stats_list)
        logger.info(f"Extracted stats for {len(df)} players from season {season}")
        return df
        
    except Exception as e:
        logger.error(f"Error extracting player stats for season {season}: {e}")
        return pd.DataFrame()


def extract_player_stats_from_matchups(
    season_data: Dict,
    season: int
) -> pd.DataFrame:
    """Alternative: Extract player points from matchup/roster data.
    
    This is a fallback if direct player stats aren't available.
    Note: This would require weekly lineup data which may not be available.
    
    Args:
        season_data: Season data dictionary
        season: Season year
        
    Returns:
        DataFrame with player stats (likely incomplete)
    """
    # This would require parsing weekly lineup contributions
    # For now, return empty - would need weekly lineup data
    logger.warning("Extraction from matchups not yet implemented - requires weekly lineup data")
    return pd.DataFrame()

