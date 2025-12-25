"""Data cleaning and organization module."""
import pandas as pd
from typing import Dict, List
from collections import defaultdict
import config


class DataCleaner:
    """Cleans and organizes league data for analysis."""
    
    def __init__(self, all_seasons_data: Dict[int, Dict]):
        """Initialize with all seasons data.
        
        Args:
            all_seasons_data: Dictionary mapping years to season data
        """
        self.all_seasons_data = all_seasons_data
        self.cleaned_data = {}
    
    def clean_all_data(self) -> Dict[str, pd.DataFrame]:
        """Clean and organize all data into DataFrames.
        
        Returns:
            Dictionary of cleaned DataFrames
        """
        teams_df = self._create_teams_dataframe()
        matchups_df = self._create_matchups_dataframe()
        standings_df = self._create_standings_dataframe()
        managers_df = self._create_managers_dataframe()
        season_summary_df = self._create_season_summary_dataframe()
        
        self.cleaned_data = {
            'teams': teams_df,
            'matchups': matchups_df,
            'standings': standings_df,
            'managers': managers_df,
            'season_summary': season_summary_df,
        }
        
        return self.cleaned_data
    
    def _create_teams_dataframe(self) -> pd.DataFrame:
        """Create a comprehensive teams DataFrame."""
        teams_list = []
        
        for year, season_data in self.all_seasons_data.items():
            for team in season_data.get('teams', []):
                if 'error' not in team:
                    teams_list.append({
                        'season_year': year,
                        'team_id': team.get('team_id', ''),
                        'team_key': team.get('team_key', ''),
                        'team_name': team.get('name', ''),
                        'manager': team.get('manager', ''),
                        'manager_id': team.get('manager_id', ''),
                        'wins': team.get('wins', 0),
                        'losses': team.get('losses', 0),
                        'ties': team.get('ties', 0),
                        'points_for': team.get('points_for', 0.0),
                        'points_against': team.get('points_against', 0.0),
                        'win_percentage': self._calculate_win_percentage(
                            team.get('wins', 0),
                            team.get('losses', 0),
                            team.get('ties', 0)
                        ),
                        'roster_size': len(team.get('roster', [])),
                    })
        
        return pd.DataFrame(teams_list)
    
    def _create_matchups_dataframe(self) -> pd.DataFrame:
        """Create a matchups DataFrame."""
        matchups_list = []
        
        for year, season_data in self.all_seasons_data.items():
            for matchup in season_data.get('matchups', []):
                if 'error' not in matchup:
                    matchups_list.append({
                        'season_year': year,
                        'week': matchup.get('week', 0),
                        'team1_key': matchup.get('team1_key', ''),
                        'team1_name': matchup.get('team1_name', ''),
                        'team1_points': matchup.get('team1_points', 0.0),
                        'team2_key': matchup.get('team2_key', ''),
                        'team2_name': matchup.get('team2_name', ''),
                        'team2_points': matchup.get('team2_points', 0.0),
                        'winner': matchup.get('winner', ''),
                        'point_differential': abs(
                            matchup.get('team1_points', 0.0) - 
                            matchup.get('team2_points', 0.0)
                        ),
                    })
        
        return pd.DataFrame(matchups_list)
    
    def _create_standings_dataframe(self) -> pd.DataFrame:
        """Create a standings DataFrame."""
        standings_list = []
        
        for year, season_data in self.all_seasons_data.items():
            for standing in season_data.get('standings', []):
                standings_list.append({
                    'season_year': year,
                    'team_key': standing.get('team_key', ''),
                    'final_rank': standing.get('rank', 0),
                    'wins': standing.get('wins', 0),
                    'losses': standing.get('losses', 0),
                    'ties': standing.get('ties', 0),
                    'points_for': standing.get('points_for', 0.0),
                    'points_against': standing.get('points_against', 0.0),
                })
        
        return pd.DataFrame(standings_list)
    
    def _create_managers_dataframe(self) -> pd.DataFrame:
        """Create a managers/owners DataFrame with aggregated stats."""
        manager_stats = defaultdict(lambda: {
            'manager_id': '',
            'manager_name': '',
            'seasons': [],
            'total_wins': 0,
            'total_losses': 0,
            'total_ties': 0,
            'total_points_for': 0.0,
            'total_points_against': 0.0,
            'championships': 0,
            'playoff_appearances': 0,
            'best_finish': float('inf'),
            'worst_finish': 0,
        })
        
        # Aggregate stats by manager
        for year, season_data in self.all_seasons_data.items():
            # Process standings to find champions and playoff teams
            standings = sorted(
                season_data.get('standings', []),
                key=lambda x: x.get('rank', 999)
            )
            
            for idx, standing in enumerate(standings):
                # Find corresponding team data
                team_key = standing.get('team_key', '')
                team_data = next(
                    (t for t in season_data.get('teams', []) if t.get('team_key') == team_key),
                    None
                )
                
                if team_data:
                    manager_id = team_data.get('manager_id', '')
                    manager_name = team_data.get('manager', '')
                    
                    # Use manager_id if available, otherwise use manager_name as key
                    # This handles cases where manager_id might be empty
                    manager_key = manager_id if manager_id else manager_name
                    
                    if manager_key:  # Use manager_key instead of just manager_id
                        manager_stats[manager_key]['manager_id'] = manager_id
                        manager_stats[manager_key]['manager_name'] = manager_name if manager_name else f'Manager_{manager_key}'
                        manager_stats[manager_key]['seasons'].append(year)
                        manager_stats[manager_key]['total_wins'] += team_data.get('wins', 0)
                        manager_stats[manager_key]['total_losses'] += team_data.get('losses', 0)
                        manager_stats[manager_key]['total_ties'] += team_data.get('ties', 0)
                        manager_stats[manager_key]['total_points_for'] += team_data.get('points_for', 0.0)
                        manager_stats[manager_key]['total_points_against'] += team_data.get('points_against', 0.0)
                        
                        rank = standing.get('rank', 999)
                        if rank == 1:
                            manager_stats[manager_key]['championships'] += 1
                        if rank <= 4:  # Assuming top 4 make playoffs (adjust as needed)
                            manager_stats[manager_key]['playoff_appearances'] += 1
                        
                        manager_stats[manager_key]['best_finish'] = min(
                            manager_stats[manager_key]['best_finish'],
                            rank
                        )
                        manager_stats[manager_key]['worst_finish'] = max(
                            manager_stats[manager_key]['worst_finish'],
                            rank
                        )
        
        # Convert to DataFrame
        managers_list = []
        for manager_key, stats in manager_stats.items():
            num_seasons = len(stats['seasons'])
            managers_list.append({
                'manager_id': stats['manager_id'],
                'manager_name': stats['manager_name'],
                'num_seasons': num_seasons,
                'total_wins': stats['total_wins'],
                'total_losses': stats['total_losses'],
                'total_ties': stats['total_ties'],
                'total_points_for': stats['total_points_for'],
                'total_points_against': stats['total_points_against'],
                'avg_points_for': stats['total_points_for'] / num_seasons if num_seasons > 0 else 0,
                'avg_points_against': stats['total_points_against'] / num_seasons if num_seasons > 0 else 0,
                'win_percentage': self._calculate_win_percentage(
                    stats['total_wins'],
                    stats['total_losses'],
                    stats['total_ties']
                ),
                'championships': stats['championships'],
                'playoff_appearances': stats['playoff_appearances'],
                'best_finish': stats['best_finish'] if stats['best_finish'] != float('inf') else None,
                'worst_finish': stats['worst_finish'],
                'seasons': ','.join(map(str, stats['seasons'])),
            })
        
        return pd.DataFrame(managers_list)
    
    def _create_season_summary_dataframe(self) -> pd.DataFrame:
        """Create a season-level summary DataFrame."""
        season_summaries = []
        
        for year, season_data in self.all_seasons_data.items():
            teams = season_data.get('teams', [])
            matchups = season_data.get('matchups', [])
            standings = season_data.get('standings', [])
            
            if teams:
                total_points = sum(t.get('points_for', 0.0) for t in teams)
                avg_points = total_points / len(teams) if teams else 0
                
                # Find champion
                champion = next(
                    (s for s in sorted(standings, key=lambda x: x.get('rank', 999)) if s.get('rank') == 1),
                    None
                )
                champion_team = next(
                    (t for t in teams if t.get('team_key') == champion.get('team_key')),
                    None
                ) if champion else None
                
                season_summaries.append({
                    'season_year': year,
                    'num_teams': len(teams),
                    'total_games': len(matchups),
                    'total_points_scored': total_points,
                    'avg_points_per_team': avg_points,
                    'champion_team_key': champion.get('team_key') if champion else '',
                    'champion_manager': champion_team.get('manager', '') if champion_team else '',
                    'champion_points': champion.get('points_for', 0.0) if champion else 0.0,
                })
        
        return pd.DataFrame(season_summaries)
    
    def _calculate_win_percentage(self, wins: int, losses: int, ties: int) -> float:
        """Calculate win percentage."""
        total_games = wins + losses + ties
        if total_games == 0:
            return 0.0
        return (wins + (ties * 0.5)) / total_games
    
    def get_key_insights(self) -> Dict:
        """Extract key insights from cleaned data.
        
        Returns:
            Dictionary of key insights and statistics
        """
        insights = {}
        
        if 'teams' in self.cleaned_data:
            teams_df = self.cleaned_data['teams']
            
            # Most successful managers
            if 'managers' in self.cleaned_data:
                managers_df = self.cleaned_data['managers']
                if not managers_df.empty and 'total_wins' in managers_df.columns:
                    insights['top_managers_by_wins'] = managers_df.nlargest(5, 'total_wins')[
                        ['manager_name', 'total_wins', 'win_percentage', 'championships']
                    ].to_dict('records')
                if not managers_df.empty and 'championships' in managers_df.columns:
                    insights['championship_leaders'] = managers_df.nlargest(5, 'championships')[
                        ['manager_name', 'championships', 'total_wins', 'win_percentage']
                    ].to_dict('records')
            
            # Season champions
            if 'season_summary' in self.cleaned_data:
                season_df = self.cleaned_data['season_summary']
                if not season_df.empty and 'champion_manager' in season_df.columns:
                    insights['all_champions'] = season_df[
                        ['season_year', 'champion_manager', 'champion_points']
                    ].to_dict('records')
        
        return insights

