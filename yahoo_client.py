"""Yahoo Fantasy Football API client for fetching league data."""
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from yahoofantasy import Context
from yahoofantasy.api.games import get_game_id
import config
from yahoo_oauth import get_refresh_token

logger = logging.getLogger(__name__)


class YahooFantasyClient:
    """Client for interacting with Yahoo Fantasy Football API."""
    
    def __init__(self, client_id: str, client_secret: str, league_id: str, refresh_token: str = None):
        """Initialize the Yahoo Fantasy client.
        
        Args:
            client_id: Yahoo API client ID
            client_secret: Yahoo API client secret
            league_id: Yahoo Fantasy League ID
            refresh_token: Optional refresh token (will prompt for OAuth if not provided)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.league_id = league_id
        self.refresh_token = refresh_token
        self.ctx = None
        self.league = None
        
    def authenticate(self, force_oauth: bool = False):
        """Authenticate with Yahoo Fantasy API.
        
        Args:
            force_oauth: If True, force new OAuth flow even if refresh token exists
        """
        # If no refresh token, get one through OAuth
        if not self.refresh_token or force_oauth:
            print("No refresh token found. Starting OAuth flow...")
            self.refresh_token = get_refresh_token(self.client_id, self.client_secret)
            # Save refresh token to config for future use
            # You might want to save this to a secure location
        
        # Create context with credentials
        try:
            self.ctx = Context(
                persist_key="yahoo_fantasy",
                client_id=self.client_id,
                client_secret=self.client_secret,
                refresh_token=self.refresh_token
            )
        except (UnicodeDecodeError, ValueError, EOFError, OSError) as e:
            # Handle corrupted cache file or invalid refresh token
            if isinstance(e, (UnicodeDecodeError, EOFError)) or "utf-8" in str(e).lower():
                # Corrupted cache file
                logger.warning(f"Authentication cache appears corrupted: {e}")
                logger.info("Attempting to clear cache and re-authenticate...")
                
                # Try to find and remove the corrupted cache file
                cache_locations = [
                    Path('.') / 'yahoo_fantasy.yahoofantasy',
                    Path('.') / f'{self.persist_key}.yahoofantasy',
                    Path.home() / '.cache' / 'yahoofantasy',
                    Path.home() / '.yahoofantasy',
                ]
                
                cache_cleared = False
                for cache_path in cache_locations:
                    if cache_path.exists():
                        try:
                            if cache_path.is_file():
                                cache_path.unlink()
                                logger.info(f"Removed corrupted cache file: {cache_path}")
                                cache_cleared = True
                            elif cache_path.is_dir():
                                import shutil
                                shutil.rmtree(cache_path)
                                logger.info(f"Removed corrupted cache directory: {cache_path}")
                                cache_cleared = True
                        except Exception as cleanup_error:
                            logger.warning(f"Could not remove cache at {cache_path}: {cleanup_error}")
                
                # Retry authentication after clearing cache
                if cache_cleared:
                    try:
                        self.ctx = Context(
                            persist_key="yahoo_fantasy",
                            client_id=self.client_id,
                            client_secret=self.client_secret,
                            refresh_token=self.refresh_token
                        )
                        logger.info("Successfully re-authenticated after clearing cache")
                    except Exception as retry_error:
                        logger.error(f"Failed to authenticate after clearing cache: {retry_error}")
                        raise
                else:
                    logger.error("Could not clear corrupted cache - authentication failed")
                    raise
            elif isinstance(e, ValueError) and "refresh token" in str(e).lower():
                # Invalid refresh token
                print("Refresh token invalid or expired. Getting new token...")
                self.refresh_token = get_refresh_token(self.client_id, self.client_secret)
                self.ctx = Context(
                    persist_key="yahoo_fantasy",
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    refresh_token=self.refresh_token
                )
            else:
                raise
        
    def get_league(self, game_id: str = config.YAHOO_GAME_ID, year: int = None):
        """Get the league object.
        
        Args:
            game_id: Yahoo game ID (default: 'nfl')
            year: Optional year to get league for (for historical seasons)
            
        Returns:
            League object
        """
        if not self.ctx:
            self.authenticate()
        
        # Use current year if not specified
        if year is None:
            year = config.CURRENT_YEAR
            
        # Get all leagues for the current game and season
        # yahoofantasy requires: get_leagues(game, season)
        try:
            leagues = self.ctx.get_leagues(game_id, year)
        except (TypeError, KeyError, AttributeError) as e:
            # Handle cases where the API doesn't have data for this year
            # This can happen for very old years or if the league didn't exist yet
            raise ValueError(
                f"Cannot access leagues for year {year}. The league may not exist for this year, "
                f"or Yahoo API data is unavailable. Original error: {e}"
            )
        
        # Find the specific league
        # First try matching by league_id or league_key (works for current year)
        for league in leagues:
            league_id_match = hasattr(league, 'league_id') and str(league.league_id) == str(self.league_id)
            league_key_match = hasattr(league, 'league_key') and str(self.league_id) in str(league.league_key)
            
            if league_id_match or league_key_match:
                # Store as current league only if it's the current year
                if year == config.CURRENT_YEAR:
                    self.league = league
                return league
        
        # If not found by ID, try matching by league name
        # First, get the league name from current year if we don't have it cached
        if not hasattr(self, '_league_name') or not self._league_name:
            try:
                current_leagues = self.ctx.get_leagues(game_id, config.CURRENT_YEAR)
                if current_leagues:
                    for league in current_leagues:
                        league_id_match = hasattr(league, 'league_id') and str(league.league_id) == str(self.league_id)
                        league_key_match = hasattr(league, 'league_key') and str(self.league_id) in str(league.league_key)
                        if league_id_match or league_key_match:
                            self._league_name = getattr(league, 'name', '')
                            if year == config.CURRENT_YEAR:
                                self.league = league
                            break
            except Exception as e:
                # If we can't get current year leagues, that's ok - we'll try other methods
                pass
        
        # Try matching by name (league IDs change year-to-year, but names usually stay the same)
        if hasattr(self, '_league_name') and self._league_name:
            for league in leagues:
                if hasattr(league, 'name') and getattr(league, 'name', '') == self._league_name:
                    # Only cache as self.league if it's the current year
                    if year == config.CURRENT_YEAR:
                        self.league = league
                    return league
        
        # If still not found and only one league available, use it
        if len(leagues) == 1:
            if year == config.CURRENT_YEAR:
                self.league = leagues[0]
            return leagues[0]
                
        raise ValueError(
            f"League {self.league_id} not found for year {year}. "
            f"Available leagues: {[(getattr(l, 'name', 'unknown'), getattr(l, 'league_id', getattr(l, 'league_key', 'unknown'))) for l in leagues]}. "
            f"Make sure the league ID is correct."
        )
    
    def fetch_season_data(self, year: int, retry_on_auth_error: bool = True,
                          fetch_weekly_points: bool = False, num_weeks: int = 17) -> Dict:
        """Fetch all data for a specific season.

        Note: For historical seasons, you may need to specify the league_key
        with the year. Adjust this method based on your league structure.

        Args:
            year: The season year to fetch
            retry_on_auth_error: If True, attempt to re-authenticate and retry on 401 errors
            fetch_weekly_points: If True, also fetch weekly player points using cumulative
                difference method (slower but provides weekly granularity)
            num_weeks: Number of weeks in the season (default: 17)

        Returns:
            Dictionary containing all season data
        """
        # Get league for this specific year - important for getting correct draft data
        # Do NOT fall back to current league - this would give wrong data for historical seasons
        try:
            league_for_year = self.get_league(year=year)
        except Exception as e:
            print(f"Error: Could not get league for year {year}: {e}")
            # Don't fall back - raise the error so we know data is missing
            raise ValueError(f"Cannot fetch data for year {year}: {e}")
            
        season_data = {
            'year': year,
            'teams': [],
            'standings': [],
            'matchups': [],
            'transactions': [],
            'settings': None,
            'draft_results': [],
            'weekly_player_points': [],  # Populated if fetch_weekly_points=True
        }
        
        try:
            # Use the league for this specific year
            league = league_for_year
            
            # Get league settings (access attributes directly)
            season_data['settings'] = self._serialize_settings(league)
            
            # Get standings first (we need this to get team stats)
            standings = league.standings()
            season_data['standings'] = [self._serialize_standings(s) for s in standings]
            
            # Create a lookup dict for team stats from standings
            standings_lookup = {s['team_key']: s for s in season_data['standings']}
            
            # Get teams (call as method)
            teams = league.teams()
            for team in teams:
                try:
                    team_data = self._fetch_team_data(team, year)
                    # Update team data with stats from standings
                    team_key = team_data.get('team_key', '')
                    if team_key in standings_lookup:
                        stats = standings_lookup[team_key]
                        team_data['wins'] = stats['wins']
                        team_data['losses'] = stats['losses']
                        team_data['ties'] = stats['ties']
                        team_data['points_for'] = stats['points_for']
                        team_data['points_against'] = stats['points_against']
                    season_data['teams'].append(team_data)
                except Exception as team_error:
                    # Handle errors fetching individual team data (e.g., 500 errors on player stats)
                    error_str = str(team_error)
                    if '500' in error_str or 'Server Error' in error_str:
                        logger.warning(f"Server error fetching team {getattr(team, 'name', 'unknown')} for {year}: {team_error}")
                        # Continue with other teams
                        continue
                    else:
                        # For other errors, log and continue
                        logger.warning(f"Error fetching team {getattr(team, 'name', 'unknown')} for {year}: {team_error}")
                        continue
            
            # Get matchups/weeks (call as method)
            weeks = league.weeks()
            for week in weeks:
                if hasattr(week, 'start') and hasattr(week.start, 'year'):
                    week_year = week.start.year
                elif hasattr(week, 'end') and hasattr(week.end, 'year'):
                    week_year = week.end.year
                else:
                    week_year = year  # Default to requested year
                    
                if week_year == year or not hasattr(week, 'start'):
                    week_num = getattr(week, 'week_num', getattr(week, 'week', 0))
                    week_matchups = week.matchups  # Access as attribute (it's a list)
                    for matchup in week_matchups:
                        matchup_data = self._fetch_matchup_data(matchup, week_num)
                        matchup_data['week'] = week_num
                        matchup_data['season_year'] = year
                        season_data['matchups'].append(matchup_data)
                        
                        # Also fetch weekly rosters for lineup analysis
                        try:
                            weekly_rosters = self._fetch_weekly_rosters_from_matchup(matchup, year, week_num)
                            if 'weekly_rosters' not in season_data:
                                season_data['weekly_rosters'] = []
                            season_data['weekly_rosters'].extend(weekly_rosters)
                        except Exception as roster_error:
                            logger.debug(f"Could not fetch weekly rosters for week {week_num}: {roster_error}")
                            # Continue - weekly rosters are optional
                            pass
            
            # Get transactions (call as method)
            transactions = league.transactions()
            serialized_transactions = []
            for t in transactions:
                # Filter by year if timestamp has year attribute, otherwise include all
                include = True
                if hasattr(t, 'timestamp') and t.timestamp:
                    try:
                        if hasattr(t.timestamp, 'year'):
                            include = t.timestamp.year == year
                        elif isinstance(t.timestamp, (int, float)):
                            # Unix timestamp - convert to year
                            from datetime import datetime
                            dt = datetime.fromtimestamp(int(t.timestamp))
                            include = dt.year == year
                    except:
                        # If we can't determine year, include it
                        pass
                
                if include:
                    serialized_transactions.append(self._serialize_transaction(t))
            
            season_data['transactions'] = serialized_transactions
            
            # Get draft results - use league for this specific year to get correct draft data
            try:
                draft_results = league.draft_results()
                season_data['draft_results'] = [self._serialize_draft_pick(pick, year) for pick in draft_results]
                if draft_results:
                    print(f"  Fetched {len(draft_results)} draft picks for {year}")
            except Exception as e:
                print(f"Error fetching draft results for {year}: {e}")
                season_data['draft_results'] = []

            # Fetch weekly player points if requested (uses cumulative difference method)
            if fetch_weekly_points:
                try:
                    print(f"  Fetching weekly player points for {year}...")
                    weekly_points = self.fetch_weekly_player_points(year, num_weeks=num_weeks)
                    season_data['weekly_player_points'] = weekly_points
                    print(f"  Fetched {len(weekly_points)} weekly player point records for {year}")
                except Exception as e:
                    logger.warning(f"Error fetching weekly player points for {year}: {e}")
                    season_data['weekly_player_points'] = []

        except Exception as e:
            error_str = str(e)
            import traceback
            
            error_type = str(type(e).__name__)
            
            # Check if this is an authentication error (401)
            is_401 = '401' in error_str or 'Unauthorized' in error_str
            is_500 = '500' in error_str or 'Server Error' in error_str or 'INKApi Error' in error_str
            is_http_error = 'HTTPError' in error_type
            
            if is_401:
                logger.warning(f"Authentication error (401) fetching season {year}: {e}")
                season_data['error'] = f"Authentication error: Token may have expired. {str(e)}"
                
                # Try to re-authenticate and retry once
                if retry_on_auth_error:
                    try:
                        logger.info(f"Attempting to re-authenticate and retry season {year}...")
                        # Clear context and re-authenticate
                        self.ctx = None
                        self.authenticate()
                        # Retry the fetch (but don't retry again to avoid infinite loop)
                        logger.info(f"Retrying fetch for season {year} after re-authentication...")
                        return self.fetch_season_data(year, retry_on_auth_error=False,
                                                      fetch_weekly_points=fetch_weekly_points,
                                                      num_weeks=num_weeks)
                    except Exception as retry_error:
                        logger.error(f"Failed to re-authenticate: {retry_error}")
                        season_data['error'] = f"Authentication failed after retry: {str(retry_error)}"
                else:
                    logger.error(f"Authentication error occurred, but retry disabled or already attempted")
            elif is_500:
                # Yahoo server errors (500) - often happen for historical data
                # Log warning but don't fail completely - some data may have been fetched
                logger.warning(f"Yahoo server error (500) while fetching season {year}: {e}")
                logger.warning(f"This is often caused by incomplete player stats for historical seasons.")
                logger.warning(f"Continuing with partial data...")
                season_data['error'] = f"Partial data: Yahoo server error for some players. {str(e)[:200]}"
                # Don't raise - continue with whatever data we got
            else:
                # Other errors - log and continue
                logger.error(f"Error fetching season {year}: {e}")
                traceback.print_exc()
                season_data['error'] = str(e)
            
        return season_data
    
    def _fetch_team_data(self, team, year: int) -> Dict:
        """Fetch detailed data for a team."""
        try:
            roster = team.roster()
            players = []
            # Roster.players is a list
            # Track if we hit too many server errors to avoid spamming
            server_error_count = 0
            max_server_errors = 5  # Log first 5, then stop logging to avoid spam
            
            for player in roster.players:
                # Try to get player points for the season
                fantasy_points = None
                if hasattr(player, 'get_points'):
                    try:
                        points_obj = player.get_points()
                        # Points might be a number or dict/object
                        if isinstance(points_obj, (int, float)):
                            fantasy_points = float(points_obj)
                        elif hasattr(points_obj, 'total'):
                            fantasy_points = float(getattr(points_obj, 'total', 0))
                        elif isinstance(points_obj, dict):
                            fantasy_points = float(points_obj.get('total', points_obj.get('points', 0)))
                    except Exception as e:
                        # Handle various API errors gracefully
                        error_str = str(e)
                        error_type = str(type(e).__name__)
                        
                        # Check for HTTP errors
                        is_401 = '401' in error_str or 'Unauthorized' in error_str
                        is_500 = '500' in error_str or 'Server Error' in error_str or 'INKApi Error' in error_str
                        is_http_error = 'HTTPError' in error_type or 'HTTP' in error_str
                        
                        if is_401:
                            # Raise 401 errors - they should be handled at season level for token refresh
                            raise
                        elif is_500:
                            server_error_count += 1
                            if server_error_count <= max_server_errors:
                                logger.debug(f"Server error (500) fetching points for player {getattr(player, 'player_id', 'unknown')}: {e}")
                            elif server_error_count == max_server_errors + 1:
                                logger.debug(f"Additional server errors occurred but not logging to avoid spam...")
                            # Yahoo server error - likely incomplete data for this player
                            # Just skip this player's points and continue
                        elif is_http_error:
                            logger.debug(f"HTTP error fetching points for player {getattr(player, 'player_id', 'unknown')}: {e}")
                            # Other HTTP errors (404, 403, etc.) - skip this player
                        else:
                            logger.debug(f"Error fetching points for player {getattr(player, 'player_id', 'unknown')}: {e}")
                        # Silently fail - points may not be available for all players, especially in historical seasons
                        pass
                
                player_data = {
                    'player_id': getattr(player, 'player_id', ''),
                    'name': getattr(player.name, 'full', '') if hasattr(player, 'name') else '',
                    'position': getattr(player, 'primary_position', ''),
                    'status': getattr(player, 'status', ''),
                    'selected_position': getattr(getattr(player, 'selected_position', {}), 'position', '') if hasattr(player, 'selected_position') else '',
                    'fantasy_points_total': fantasy_points,
                }
                players.append(player_data)
            
            # Get manager info - APIAttr uses getattr, not subscript notation
            manager_name = ''
            manager_id = ''
            if hasattr(team, 'managers'):
                try:
                    # APIAttr objects use getattr to access nested attributes
                    managers_data = team.managers
                    if hasattr(managers_data, 'manager'):
                        mgr = getattr(managers_data, 'manager')
                        # Manager is an APIAttr - use getattr to access fields
                        # APIAttr supports both getattr() and .get() method
                        if hasattr(mgr, 'nickname'):
                            manager_name = getattr(mgr, 'nickname', '')
                        elif hasattr(mgr, 'get') and callable(mgr.get):
                            manager_name = mgr.get('nickname', '')
                        
                        if hasattr(mgr, 'guid'):
                            manager_id = getattr(mgr, 'guid', '')
                        elif hasattr(mgr, 'get') and callable(mgr.get):
                            manager_id = mgr.get('guid', '')
                except (TypeError, AttributeError) as e:
                    # Silently fail - manager info might not be available for all seasons
                    pass
            
            # Team stats aren't directly on team object - they come from standings
            # We'll get them from standings later
            return {
                'team_id': getattr(team, 'team_id', ''),
                'team_key': getattr(team, 'team_key', ''),
                'name': getattr(team, 'name', ''),
                'manager': manager_name,
                'manager_id': manager_id,
                'wins': 0,  # Will be filled from standings
                'losses': 0,  # Will be filled from standings
                'ties': 0,  # Will be filled from standings
                'points_for': 0.0,  # Will be filled from standings
                'points_against': 0.0,  # Will be filled from standings
                'roster': players,
                'season_year': year
            }
        except Exception as e:
            print(f"Error fetching team data for {getattr(team, 'name', 'Unknown')}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'team_id': getattr(team, 'team_id', ''),
                'name': getattr(team, 'name', ''),
                'error': str(e),
                'season_year': year
            }
    
    def _fetch_matchup_data(self, matchup, week_num: int = 0) -> Dict:
        """Fetch data for a matchup, including weekly points.
        
        According to Yahoo API docs, matchups from scoreboard contain teams with
        team_points that have coverage_type='week' and total field for weekly points.
        Access via matchup.teams.team[0] and matchup.teams.team[1].
        """
        try:
            # Matchup objects have team1 and team2 attributes directly (for convenience)
            team1 = getattr(matchup, 'team1', None)
            team2 = getattr(matchup, 'team2', None)
            
            # Helper to extract weekly points from team in matchup.teams
            def get_team_points_from_matchup_teams(team_obj):
                """Extract weekly points from team object in matchup.teams structure."""
                if not team_obj:
                    return 0.0
                try:
                    # Teams in matchup.teams have team_points with total field
                    if hasattr(team_obj, 'team_points'):
                        team_points = getattr(team_obj, 'team_points')
                        if hasattr(team_points, 'total'):
                            total = getattr(team_points, 'total')
                            if total is not None:
                                return float(total)
                    return 0.0
                except (ValueError, TypeError, AttributeError) as e:
                    logger.debug(f"Error extracting points from team_points: {e}")
                    return 0.0
            
            # Extract weekly points from matchup.teams structure
            # This is where the weekly points are stored according to Yahoo API
            team1_points = 0.0
            team2_points = 0.0
            team1_key = None
            team1_name = None
            team2_key = None
            team2_name = None
            
            try:
                if hasattr(matchup, 'teams'):
                    teams_obj = getattr(matchup, 'teams')
                    if hasattr(teams_obj, 'team'):
                        team_list = getattr(teams_obj, 'team')
                        # team might be a single object or a list
                        if not isinstance(team_list, list):
                            team_list = [team_list]
                        
                        if len(team_list) >= 1:
                            team1_obj = team_list[0]
                            team1_points = get_team_points_from_matchup_teams(team1_obj)
                            if hasattr(team1_obj, 'team_key'):
                                team1_key = getattr(team1_obj, 'team_key')
                            if hasattr(team1_obj, 'name'):
                                team1_name = getattr(team1_obj, 'name')
                        
                        if len(team_list) >= 2:
                            team2_obj = team_list[1]
                            team2_points = get_team_points_from_matchup_teams(team2_obj)
                            if hasattr(team2_obj, 'team_key'):
                                team2_key = getattr(team2_obj, 'team_key')
                            if hasattr(team2_obj, 'name'):
                                team2_name = getattr(team2_obj, 'name')
            except Exception as e:
                logger.debug(f"Error accessing matchup.teams: {e}")
                # Fallback to team1/team2 attributes if teams structure fails
                pass
            
            # Fallback: Use team1/team2 attributes if we didn't get points from teams structure
            if team1_points == 0.0 and team1:
                team1_key = getattr(team1, 'team_key', team1_key)
                team1_name = getattr(team1, 'name', team1_name)
            if team2_points == 0.0 and team2:
                team2_key = getattr(team2, 'team_key', team2_key)
                team2_name = getattr(team2, 'name', team2_name)
            
            matchup_data = {
                'matchup_id': getattr(matchup, 'matchup_id', ''),
                'team1_key': team1_key,
                'team1_name': team1_name,
                'team1_points': team1_points,
                'team2_key': team2_key,
                'team2_name': team2_name,
                'team2_points': team2_points,
                'winner': getattr(matchup, 'winner_team_key', None) if hasattr(matchup, 'winner_team_key') else None,
            }
            return matchup_data
        except Exception as e:
            logger.warning(f"Error fetching matchup data: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    def _fetch_weekly_rosters_from_matchup(self, matchup, year: int, week: int) -> List[Dict]:
        """Fetch weekly rosters for teams in a matchup.
        
        Args:
            matchup: Matchup object from Yahoo API
            year: Season year
            week: Week number
            
        Returns:
            List of roster dictionaries with player info for the week
        """
        weekly_rosters = []
        
        try:
            team1 = getattr(matchup, 'team1', None)
            team2 = getattr(matchup, 'team2', None)
            
            for team in [team1, team2]:
                if not team:
                    continue
                
                try:
                    # Get roster for this team (this should return the roster for the week of the matchup)
                    roster = team.roster()
                    team_key = getattr(team, 'team_key', '')
                    team_name = getattr(team, 'name', '')
                    
                    if hasattr(roster, 'players'):
                        players_list = roster.players
                    else:
                        continue
                    
                    for player in players_list:
                        try:
                            # Get player position and roster slot
                            player_id = getattr(player, 'player_id', '')
                            player_name = getattr(getattr(player, 'name', None), 'full', '') if hasattr(player, 'name') else ''
                            position = getattr(player, 'primary_position', '')
                            
                            # Get selected position (roster slot)
                            selected_pos = getattr(player, 'selected_position', None)
                            if selected_pos:
                                if isinstance(selected_pos, dict):
                                    roster_slot = selected_pos.get('position', '')
                                else:
                                    roster_slot = getattr(selected_pos, 'position', '')
                            else:
                                roster_slot = ''
                            
                            # Determine if started (not BN/IR)
                            started = roster_slot not in ['BN', 'IR', ''] if roster_slot else False
                            
                            # Try to get weekly points for this player
                            weekly_points = 0.0
                            try:
                                # For weekly rosters, we need to get stats for the specific week
                                # This may require calling player.get_stats() with week parameter
                                # For now, we'll leave it as 0 and can enhance later
                                # The roster structure may have weekly stats embedded
                                pass
                            except:
                                pass
                            
                            weekly_rosters.append({
                                'season_year': year,
                                'week': week,
                                'team_key': team_key,
                                'team_name': team_name,
                                'player_id': player_id,
                                'player_name': player_name,
                                'position': position,
                                'roster_slot': roster_slot,
                                'started': started,
                                'points': weekly_points,  # Will need to populate from player stats
                            })
                        except Exception as player_error:
                            logger.debug(f"Error processing player in weekly roster: {player_error}")
                            continue
                
                except Exception as team_error:
                    logger.debug(f"Error fetching weekly roster for team: {team_error}")
                    continue
        
        except Exception as e:
            logger.debug(f"Error fetching weekly rosters from matchup: {e}")
        
        return weekly_rosters
    
    def _serialize_settings(self, league) -> Dict:
        """Serialize league settings to dictionary."""
        return {
            'name': getattr(league, 'name', ''),
            'num_teams': getattr(league, 'num_teams', 0),
            'scoring_type': getattr(league, 'scoring_type', ''),
            'league_type': getattr(league, 'league_type', ''),
        }
    
    def _serialize_standings(self, standing) -> Dict:
        """Serialize standings to dictionary."""
        # Get team_key
        team_key = getattr(standing, 'team_key', '')
        
        # Get stats from team_standings
        rank = 0
        wins = 0
        losses = 0
        ties = 0
        points_for = 0.0
        points_against = 0.0
        
        if hasattr(standing, 'team_standings'):
            ts = standing.team_standings
            if ts:
                # team_standings has rank, points_for, points_against directly
                rank = ts.get('rank', 0) if isinstance(ts, dict) else getattr(ts, 'rank', 0)
                points_for = float(ts.get('points_for', 0)) if isinstance(ts, dict) else float(getattr(ts, 'points_for', 0))
                points_against = float(ts.get('points_against', 0)) if isinstance(ts, dict) else float(getattr(ts, 'points_against', 0))
                
                # Wins/losses/ties are in outcome_totals
                if isinstance(ts, dict):
                    outcome_totals = ts.get('outcome_totals', {})
                else:
                    outcome_totals = getattr(ts, 'outcome_totals', {})
                
                if outcome_totals:
                    wins = outcome_totals.get('wins', 0) if isinstance(outcome_totals, dict) else getattr(outcome_totals, 'wins', 0)
                    losses = outcome_totals.get('losses', 0) if isinstance(outcome_totals, dict) else getattr(outcome_totals, 'losses', 0)
                    ties = outcome_totals.get('ties', 0) if isinstance(outcome_totals, dict) else getattr(outcome_totals, 'ties', 0)
        
        return {
            'team_key': team_key,
            'rank': rank,
            'wins': wins,
            'losses': losses,
            'ties': ties,
            'points_for': points_for,
            'points_against': points_against,
        }
    
    def _serialize_transaction(self, transaction) -> Dict:
        """Serialize transaction to dictionary with detailed player and team info."""
        transaction_data = {
            'transaction_id': getattr(transaction, 'transaction_id', ''),
            'transaction_key': getattr(transaction, 'transaction_key', ''),
            'type': getattr(transaction, 'type', ''),
            'timestamp': str(getattr(transaction, 'timestamp', '')),
            'status': getattr(transaction, 'status', ''),
        }
        
        # Extract involved players and teams
        involved_players_list = []
        faab_spent = None
        waiver_priority = None
        
        try:
            # Try involved_players first (for add/drop)
            if hasattr(transaction, 'involved_players'):
                involved_players = getattr(transaction, 'involved_players', [])
                if involved_players:
                    # involved_players might be iterable
                    for player_obj in involved_players:
                        player_info = self._extract_player_from_transaction(player_obj)
                        if player_info:
                            involved_players_list.append(player_info)
            
            # Also try players attribute (for trades)
            if hasattr(transaction, 'players'):
                players = getattr(transaction, 'players', [])
                if players and not involved_players_list:
                    for player_obj in players:
                        player_info = self._extract_player_from_transaction(player_obj)
                        if player_info:
                            involved_players_list.append(player_info)
            
            # Extract FAAB and waiver priority if available
            # These might be in the transaction object or player objects
            # Yahoo API structure may vary
            
        except Exception as e:
            logger.debug(f"Error extracting transaction details: {e}")
        
        transaction_data['involved_players'] = involved_players_list
        transaction_data['num_players_involved'] = len(involved_players_list)
        transaction_data['faab_spent'] = faab_spent
        transaction_data['waiver_priority'] = waiver_priority
        
        return transaction_data
    
    def _extract_player_from_transaction(self, player_obj) -> Dict:
        """Extract player info from transaction player object.
        
        Args:
            player_obj: Player object from transaction
            
        Returns:
            Dictionary with player info or None
        """
        try:
            player_info = {
                'player_id': getattr(player_obj, 'player_id', None),
                'player_key': getattr(player_obj, 'player_key', None),
                'transaction_type': None,  # ADD, DROP, TRADE_IN, TRADE_OUT
            }
            
            if not player_info['player_id']:
                return None
            
            # Get player name
            if hasattr(player_obj, 'name'):
                name_obj = getattr(player_obj, 'name', None)
                if hasattr(name_obj, 'full'):
                    player_info['player_name'] = getattr(name_obj, 'full', '')
                elif isinstance(name_obj, str):
                    player_info['player_name'] = name_obj
                else:
                    player_info['player_name'] = ''
            else:
                player_info['player_name'] = ''
            
            # Get source/destination team (from_team, to_team in Yahoo API)
            # Also check transaction_data for destination_team_key
            from_team = None
            to_team = None
            
            if hasattr(player_obj, 'from_team'):
                from_team = getattr(player_obj, 'from_team', None)
            
            if hasattr(player_obj, 'to_team'):
                to_team = getattr(player_obj, 'to_team', None)
            
            # Also check transaction_data for team keys
            if hasattr(player_obj, 'transaction_data'):
                txn_data = getattr(player_obj, 'transaction_data', None)
                if txn_data:
                    try:
                        # Handle both dict and APIAttr
                        if isinstance(txn_data, dict):
                            if not to_team:
                                to_team = txn_data.get('destination_team_key')
                            if not from_team:
                                from_team = txn_data.get('source_team_key')
                        else:
                            # APIAttr - use getattr
                            if not to_team and hasattr(txn_data, 'destination_team_key'):
                                to_team = getattr(txn_data, 'destination_team_key', None)
                            if not from_team and hasattr(txn_data, 'source_team_key'):
                                from_team = getattr(txn_data, 'source_team_key', None)
                    except:
                        pass
            
            player_info['from_team_key'] = from_team if isinstance(from_team, str) else None
            player_info['to_team_key'] = to_team if isinstance(to_team, str) else None
            
            # Determine transaction type
            # Check transaction_data first (most reliable source)
            txn_type_from_data = None
            if hasattr(player_obj, 'transaction_data'):
                txn_data = getattr(player_obj, 'transaction_data', None)
                # APIAttr objects can be accessed like dicts
                if txn_data:
                    try:
                        if isinstance(txn_data, dict):
                            txn_type_from_data = txn_data.get('type', None)
                        elif hasattr(txn_data, 'type'):
                            txn_type_from_data = getattr(txn_data, 'type', None)
                        elif hasattr(txn_data, 'get'):
                            txn_type_from_data = txn_data.get('type', None)
                    except:
                        pass
            
            # Use transaction_data type if available
            if txn_type_from_data:
                player_info['transaction_type'] = str(txn_type_from_data).upper()
            else:
                # Fallback: infer from team movements
                from_team = player_info.get('from_team_key')
                to_team = player_info.get('to_team_key')
                
                # Check if from/to are strings with 'freeagent'
                from_is_fa = (
                    isinstance(from_team, str) and 
                    ('freeagent' in from_team.lower() or from_team.lower() == 'freeagents')
                )
                to_is_fa = (
                    isinstance(to_team, str) and 
                    ('freeagent' in to_team.lower() or to_team.lower() == 'freeagents')
                )
                
                if from_team and to_team:
                    if from_is_fa and not to_is_fa:
                        player_info['transaction_type'] = 'ADD'  # From free agents to team = ADD
                    elif not from_is_fa and to_is_fa:
                        player_info['transaction_type'] = 'DROP'  # From team to free agents = DROP
                    elif not from_is_fa and not to_is_fa:
                        player_info['transaction_type'] = 'TRADE'  # Between teams = TRADE
                    else:
                        player_info['transaction_type'] = 'UNKNOWN'
                elif to_team and not from_team:
                    # Has destination but no source = ADD
                    player_info['transaction_type'] = 'ADD'
                elif from_team and not to_team:
                    # Has source but no destination = DROP
                    player_info['transaction_type'] = 'DROP'
                else:
                    player_info['transaction_type'] = 'UNKNOWN'
            
            # Get transaction details (FAAB, waiver priority)
            faab_bid = None
            waiver_priority = None
            
            if hasattr(player_obj, 'transaction_data'):
                txn_data = getattr(player_obj, 'transaction_data', None)
                if txn_data:
                    try:
                        # Handle both dict and APIAttr
                        if isinstance(txn_data, dict):
                            faab_bid = (
                                txn_data.get('faab_bid') or 
                                txn_data.get('amount') or 
                                txn_data.get('faab_amount') or
                                txn_data.get('bid_amount')
                            )
                            waiver_priority = (
                                txn_data.get('priority') or
                                txn_data.get('waiver_priority')
                            )
                        else:
                            # APIAttr - try getattr
                            faab_bid = (
                                getattr(txn_data, 'faab_bid', None) or
                                getattr(txn_data, 'amount', None) or
                                getattr(txn_data, 'faab_amount', None)
                            )
                            waiver_priority = (
                                getattr(txn_data, 'priority', None) or
                                getattr(txn_data, 'waiver_priority', None)
                            )
                    except:
                        pass
            
            player_info['faab_bid'] = faab_bid
            player_info['waiver_priority'] = waiver_priority
            
            return player_info
            
        except Exception as e:
            logger.debug(f"Error extracting player from transaction: {e}")
            return None
    
    def _serialize_draft_pick(self, pick, year: int) -> Dict:
        """Serialize draft pick to dictionary."""
        try:
            player = getattr(pick, 'player', None)
            player_name = ''
            player_id = ''
            position = ''
            is_keeper = False
            
            if player:
                if hasattr(player, 'name'):
                    name_obj = getattr(player, 'name', None)
                    if hasattr(name_obj, 'full'):
                        player_name = getattr(name_obj, 'full', '')
                    elif isinstance(name_obj, str):
                        player_name = name_obj
                
                player_id = getattr(player, 'player_id', '')
                position = getattr(player, 'primary_position', '')
                
                # is_keeper can be an object or boolean
                # For dynasty leagues, we need to check if this player was kept from previous year
                is_keeper_obj = getattr(player, 'is_keeper', False)
                is_keeper = False
                if isinstance(is_keeper_obj, bool):
                    is_keeper = is_keeper_obj
                elif hasattr(is_keeper_obj, 'kept'):
                    # APIAttr object with kept attribute - check if it has a truthy value
                    kept_val = getattr(is_keeper_obj, 'kept', {})
                    # If kept is a dict/object, check if it has content
                    if kept_val:
                        if isinstance(kept_val, dict):
                            # If dict has any keys, it's a keeper
                            is_keeper = len(kept_val) > 0
                        else:
                            is_keeper = bool(kept_val)
                elif isinstance(is_keeper_obj, dict):
                    kept_val = is_keeper_obj.get('kept', {})
                    if kept_val:
                        is_keeper = len(kept_val) > 0 if isinstance(kept_val, dict) else bool(kept_val)
            
            # Get team info
            team_key = getattr(pick, 'team_key', '')
            
            return {
                'season_year': year,
                'round': getattr(pick, 'round', 0),
                'pick': getattr(pick, 'pick', 0),
                'team_key': team_key,
                'player_key': getattr(pick, 'player_key', ''),
                'player_id': player_id,
                'player_name': player_name,
                'position': position,
                'cost': getattr(pick, 'cost', 0),  # Auction price
                'is_keeper': is_keeper,
            }
        except Exception as e:
            print(f"Error serializing draft pick: {e}")
            return {
                'season_year': year,
                'error': str(e)
            }
    
    def fetch_all_seasons(self, start_year: int, end_year: int) -> Dict[int, Dict]:
        """Fetch data for all seasons from start_year to end_year.

        Args:
            start_year: First year to fetch
            end_year: Last year to fetch (inclusive)

        Returns:
            Dictionary mapping years to season data
        """
        all_data = {}

        for year in range(start_year, end_year + 1):
            print(f"Fetching data for {year}...")
            season_data = self.fetch_season_data(year)
            all_data[year] = season_data
            time.sleep(1)  # Rate limiting

        return all_data

    def fetch_weekly_player_points(self, year: int, num_weeks: int = 17) -> List[Dict]:
        """Fetch weekly player points using cumulative difference method.

        This method is more efficient than fetching individual player stats:
        - One API call per team per week (gets all ~16 players)
        - Calculates weekly points as: cumulative[week] - cumulative[week-1]
        - ~15x faster than individual player API calls
        - 99.9%+ accuracy (see WEEKLY_PLAYER_POINTS_ANALYSIS.md)

        Args:
            year: Season year to fetch
            num_weeks: Number of weeks in the season (default: 17)

        Returns:
            List of dicts with weekly player point records:
            [{season_year, week, team_key, player_id, player_name, position,
              roster_slot, started, weekly_points, cumulative_points}, ...]
        """
        weekly_records = []

        try:
            league = self.get_league(year=year)
            teams = league.teams()
        except Exception as e:
            logger.error(f"Failed to get league/teams for {year}: {e}")
            return weekly_records

        # Cache cumulative points per player from previous week
        # Key: (team_key, player_id) -> cumulative_points
        prev_week_cumulative = {}

        for week in range(1, num_weeks + 1):
            print(f"  Fetching week {week}/{num_weeks} rosters...")
            current_week_cumulative = {}

            for team in teams:
                team_key = getattr(team, 'team_key', '')
                team_name = getattr(team, 'name', '')

                try:
                    # Fetch roster for this specific week
                    # The roster should include cumulative stats through this week
                    roster = team.roster(week=week)

                    if not hasattr(roster, 'players'):
                        continue

                    for player in roster.players:
                        player_id = getattr(player, 'player_id', '')
                        if not player_id:
                            continue

                        # Get player info
                        player_name = ''
                        if hasattr(player, 'name'):
                            name_obj = getattr(player, 'name', None)
                            if hasattr(name_obj, 'full'):
                                player_name = getattr(name_obj, 'full', '')
                            elif isinstance(name_obj, str):
                                player_name = name_obj

                        position = getattr(player, 'primary_position', '')

                        # Get roster slot (selected_position)
                        roster_slot = ''
                        selected_pos = getattr(player, 'selected_position', None)
                        if selected_pos:
                            if isinstance(selected_pos, dict):
                                roster_slot = selected_pos.get('position', '')
                            else:
                                roster_slot = getattr(selected_pos, 'position', '')

                        started = roster_slot not in ['BN', 'IR', ''] if roster_slot else False

                        # Get cumulative points for this player through this week
                        cumulative_points = self._get_player_cumulative_points(player, week)

                        # Cache for next week's calculation
                        cache_key = (team_key, player_id)
                        current_week_cumulative[cache_key] = cumulative_points

                        # Calculate weekly points using cumulative difference
                        if week == 1:
                            # Week 1: cumulative IS the weekly points
                            weekly_points = cumulative_points if cumulative_points else 0.0
                        else:
                            # Week N: weekly = cumulative[N] - cumulative[N-1]
                            prev_cumulative = prev_week_cumulative.get(cache_key, 0.0)
                            if cumulative_points is not None:
                                weekly_points = cumulative_points - prev_cumulative
                            else:
                                weekly_points = 0.0

                        weekly_records.append({
                            'season_year': year,
                            'week': week,
                            'team_key': team_key,
                            'team_name': team_name,
                            'player_id': player_id,
                            'player_name': player_name,
                            'position': position,
                            'roster_slot': roster_slot,
                            'started': started,
                            'weekly_points': weekly_points,
                            'cumulative_points': cumulative_points,
                        })

                except Exception as team_error:
                    error_str = str(team_error)
                    if '500' in error_str or 'Server Error' in error_str:
                        logger.debug(f"Server error fetching week {week} roster for {team_name}: {team_error}")
                    else:
                        logger.warning(f"Error fetching week {week} roster for {team_name}: {team_error}")
                    continue

                # Small delay between teams to avoid rate limiting
                time.sleep(0.1)

            # Update previous week cache for next iteration
            prev_week_cumulative = current_week_cumulative.copy()

            # Delay between weeks
            time.sleep(0.5)

        logger.info(f"Fetched {len(weekly_records)} weekly player records for {year}")
        return weekly_records

    def _get_player_cumulative_points(self, player, week: int) -> Optional[float]:
        """Get cumulative fantasy points for a player through the specified week.

        Args:
            player: Player object from roster
            week: Week number

        Returns:
            Cumulative fantasy points or None if not available
        """
        try:
            # Try to get points from player object
            # The roster for week N should have cumulative stats through week N

            # Method 1: Try player_points attribute (from roster context)
            if hasattr(player, 'player_points'):
                points_obj = getattr(player, 'player_points', None)
                if points_obj:
                    if isinstance(points_obj, (int, float)):
                        return float(points_obj)
                    elif hasattr(points_obj, 'total'):
                        total = getattr(points_obj, 'total', None)
                        if total is not None:
                            return float(total)
                    elif isinstance(points_obj, dict):
                        total = points_obj.get('total', points_obj.get('points'))
                        if total is not None:
                            return float(total)

            # Method 2: Try player_stats
            if hasattr(player, 'player_stats'):
                stats_obj = getattr(player, 'player_stats', None)
                if stats_obj:
                    # Stats might have coverage_type indicating if it's weekly or cumulative
                    if hasattr(stats_obj, 'stats'):
                        # Look for total/points in stats
                        stats = getattr(stats_obj, 'stats', None)
                        if stats and hasattr(stats, 'total'):
                            return float(getattr(stats, 'total', 0))

            # Method 3: Try get_points method (may trigger additional API call)
            if hasattr(player, 'get_points'):
                try:
                    points_obj = player.get_points()
                    if isinstance(points_obj, (int, float)):
                        return float(points_obj)
                    elif hasattr(points_obj, 'total'):
                        return float(getattr(points_obj, 'total', 0))
                    elif isinstance(points_obj, dict):
                        return float(points_obj.get('total', points_obj.get('points', 0)))
                except Exception as e:
                    # Don't log - this is expected to fail sometimes
                    pass

            return None

        except Exception as e:
            logger.debug(f"Error getting cumulative points for player: {e}")
            return None
