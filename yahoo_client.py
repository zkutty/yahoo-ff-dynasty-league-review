"""Yahoo Fantasy Football API client for fetching league data."""
import os
import json
import time
from typing import Dict, List, Optional
from yahoofantasy import Context
from yahoofantasy.api.games import get_game_id
import config
from yahoo_oauth import get_refresh_token


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
        except ValueError as e:
            if "refresh token" in str(e).lower():
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
        leagues = self.ctx.get_leagues(game_id, year)
        
        # Find the specific league
        # Try matching by league_id or league_key
        for league in leagues:
            league_id_match = hasattr(league, 'league_id') and str(league.league_id) == str(self.league_id)
            league_key_match = hasattr(league, 'league_key') and str(self.league_id) in str(league.league_key)
            
            if league_id_match or league_key_match:
                self.league = league
                return league
                
        raise ValueError(
            f"League {self.league_id} not found. "
            f"Available leagues: {[getattr(l, 'league_id', getattr(l, 'league_key', 'unknown')) for l in leagues]}. "
            f"Make sure the league ID is correct."
        )
    
    def fetch_season_data(self, year: int) -> Dict:
        """Fetch all data for a specific season.
        
        Note: For historical seasons, you may need to specify the league_key
        with the year. Adjust this method based on your league structure.
        
        Args:
            year: The season year to fetch
            
        Returns:
            Dictionary containing all season data
        """
        # Try to get league for this specific year
        # Note: Yahoo API structure may require different approach for historical data
        try:
            self.get_league(year=year)
        except:
            # Fall back to current league if year-specific lookup fails
            if not self.league:
                self.get_league()
            
        season_data = {
            'year': year,
            'teams': [],
            'standings': [],
            'matchups': [],
            'transactions': [],
            'settings': None,
            'draft_results': [],
        }
        
        try:
            # Get league settings (access attributes directly)
            season_data['settings'] = self._serialize_settings(self.league)
            
            # Get standings first (we need this to get team stats)
            standings = self.league.standings()
            season_data['standings'] = [self._serialize_standings(s) for s in standings]
            
            # Create a lookup dict for team stats from standings
            standings_lookup = {s['team_key']: s for s in season_data['standings']}
            
            # Get teams (call as method)
            teams = self.league.teams()
            for team in teams:
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
            
            # Get matchups/weeks (call as method)
            weeks = self.league.weeks()
            for week in weeks:
                if hasattr(week, 'start') and hasattr(week.start, 'year'):
                    week_year = week.start.year
                elif hasattr(week, 'end') and hasattr(week.end, 'year'):
                    week_year = week.end.year
                else:
                    week_year = year  # Default to requested year
                    
                if week_year == year or not hasattr(week, 'start'):
                    week_matchups = week.matchups  # Access as attribute (it's a list)
                    for matchup in week_matchups:
                        matchup_data = self._fetch_matchup_data(matchup)
                        matchup_data['week'] = getattr(week, 'week_num', getattr(week, 'week', 0))
                        matchup_data['season_year'] = year
                        season_data['matchups'].append(matchup_data)
            
            # Get transactions (call as method)
            transactions = self.league.transactions()
            season_data['transactions'] = [
                self._serialize_transaction(t) for t in transactions
                if hasattr(t, 'timestamp') and hasattr(t.timestamp, 'year') and t.timestamp.year == year
            ]
            
        except Exception as e:
            print(f"Error fetching data for {year}: {e}")
            import traceback
            traceback.print_exc()
            season_data['error'] = str(e)
            
        return season_data
    
    def _fetch_team_data(self, team, year: int) -> Dict:
        """Fetch detailed data for a team."""
        try:
            roster = team.roster()
            players = []
            # Roster.players is a list
            for player in roster.players:
                player_data = {
                    'player_id': getattr(player, 'player_id', ''),
                    'name': getattr(player.name, 'full', '') if hasattr(player, 'name') else '',
                    'position': getattr(player, 'primary_position', ''),
                    'status': getattr(player, 'status', ''),
                    'selected_position': getattr(getattr(player, 'selected_position', {}), 'position', '') if hasattr(player, 'selected_position') else ''
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
    
    def _fetch_matchup_data(self, matchup) -> Dict:
        """Fetch data for a matchup."""
        try:
            # Matchup objects have team1 and team2 attributes directly
            team1 = getattr(matchup, 'team1', None)
            team2 = getattr(matchup, 'team2', None)
            
            # Helper to get team points from team_stats
            def get_team_points(team):
                if not team:
                    return 0.0
                try:
                    # Try to get from team_stats (if available in matchup)
                    # For matchups, we may need to look at stats differently
                    # For now, return 0.0 - matchup points may need different approach
                    return 0.0
                except:
                    return 0.0
            
            matchup_data = {
                'matchup_id': getattr(matchup, 'matchup_id', ''),
                'team1_key': getattr(team1, 'team_key', None) if team1 else None,
                'team1_name': getattr(team1, 'name', None) if team1 else None,
                'team1_points': get_team_points(team1),
                'team2_key': getattr(team2, 'team_key', None) if team2 else None,
                'team2_name': getattr(team2, 'name', None) if team2 else None,
                'team2_points': get_team_points(team2),
                'winner': getattr(matchup, 'winner_team_key', None) if hasattr(matchup, 'winner_team_key') else None,
            }
            return matchup_data
        except Exception as e:
            print(f"Error fetching matchup data: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
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
        """Serialize transaction to dictionary."""
        return {
            'transaction_id': getattr(transaction, 'transaction_id', ''),
            'type': getattr(transaction, 'type', ''),
            'timestamp': str(getattr(transaction, 'timestamp', '')),
            'status': getattr(transaction, 'status', ''),
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
