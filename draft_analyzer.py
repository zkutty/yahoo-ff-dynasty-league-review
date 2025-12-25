"""Draft analysis module for auction drafts, keepers, and draft strategies."""
import pandas as pd
from typing import Dict, List
from collections import defaultdict
import config


class DraftAnalyzer:
    """Analyzes draft data including auction prices, positions, keepers, and strategies."""
    
    def __init__(self, all_seasons_data: Dict[int, Dict]):
        """Initialize with all seasons data.
        
        Args:
            all_seasons_data: Dictionary mapping years to season data
        """
        self.all_seasons_data = all_seasons_data
        self.draft_df = None
        self.analysis_results = {}
    
    def analyze_all_drafts(self) -> Dict:
        """Analyze all draft data and return comprehensive analysis.
        
        Returns:
            Dictionary containing various draft analyses
        """
        # Create draft DataFrame
        self.draft_df = self._create_draft_dataframe()
        
        if self.draft_df.empty:
            print("No draft data found")
            return {}
        
        # Link draft picks with team/manager info
        self.draft_df = self._link_draft_with_teams()
        
        # Perform analyses
        self.analysis_results = {
            'position_spending': self._analyze_position_spending(),
            'manager_draft_strategies': self._analyze_manager_strategies(),
            'keeper_analysis': self._analyze_keepers(),
            'draft_value': self._analyze_draft_value(),
            'year_over_year_trends': self._analyze_yoy_trends(),
        }
        
        return self.analysis_results
    
    def _create_draft_dataframe(self) -> pd.DataFrame:
        """Create a comprehensive draft picks DataFrame."""
        picks_list = []
        
        for year, season_data in self.all_seasons_data.items():
            draft_results = season_data.get('draft_results', [])
            for pick in draft_results:
                if 'error' not in pick:
                    picks_list.append(pick)
        
        return pd.DataFrame(picks_list)
    
    def _link_draft_with_teams(self) -> pd.DataFrame:
        """Link draft picks with team and manager information."""
        # Create team lookup from all seasons
        team_lookup = {}
        for year, season_data in self.all_seasons_data.items():
            for team in season_data.get('teams', []):
                team_key = team.get('team_key', '')
                if team_key:
                    team_lookup[team_key] = {
                        'team_name': team.get('name', ''),
                        'manager': team.get('manager', ''),
                        'manager_id': team.get('manager_id', ''),
                        'season_year': year,
                    }
        
        # Merge team info with draft picks
        if not self.draft_df.empty:
            # Create team info columns
            self.draft_df['team_name'] = self.draft_df['team_key'].map(
                lambda x: team_lookup.get(x, {}).get('team_name', '')
            )
            self.draft_df['manager'] = self.draft_df['team_key'].map(
                lambda x: team_lookup.get(x, {}).get('manager', '')
            )
            self.draft_df['manager_id'] = self.draft_df['team_key'].map(
                lambda x: team_lookup.get(x, {}).get('manager_id', '')
            )
        
        return self.draft_df
    
    def _analyze_position_spending(self) -> pd.DataFrame:
        """Analyze spending by position for each manager."""
        if self.draft_df.empty:
            return pd.DataFrame()
        
        # Group by manager and position
        position_spending = self.draft_df.groupby(['manager', 'position', 'season_year']).agg({
            'cost': ['sum', 'mean', 'count']
        }).reset_index()
        
        position_spending.columns = ['manager', 'position', 'season_year', 'total_spent', 'avg_price', 'num_picks']
        
        # Overall by manager and position
        manager_position = self.draft_df.groupby(['manager', 'position']).agg({
            'cost': ['sum', 'mean', 'count']
        }).reset_index()
        
        manager_position.columns = ['manager', 'position', 'total_spent_all_years', 'avg_price_all_years', 'total_picks']
        
        # Calculate percentage of total spending on each position per manager
        manager_totals = self.draft_df.groupby('manager')['cost'].sum()
        manager_position['pct_of_total_spending'] = manager_position.apply(
            lambda row: (row['total_spent_all_years'] / manager_totals[row['manager']] * 100) 
            if row['manager'] in manager_totals else 0, axis=1
        )
        
        return manager_position.sort_values('total_spent_all_years', ascending=False)
    
    def _analyze_manager_strategies(self) -> pd.DataFrame:
        """Analyze draft strategies for each manager."""
        if self.draft_df.empty:
            return pd.DataFrame()
        
        strategies = []
        
        for manager in self.draft_df['manager'].unique():
            if not manager:  # Skip empty managers
                continue
                
            manager_drafts = self.draft_df[self.draft_df['manager'] == manager]
            
            # Calculate strategy metrics
            total_spent = manager_drafts['cost'].sum()
            avg_pick_price = manager_drafts['cost'].mean()
            num_picks = len(manager_drafts)
            
            # Position distribution
            position_dist = manager_drafts.groupby('position')['cost'].sum().to_dict()
            top_position = max(position_dist, key=position_dist.get) if position_dist else ''
            
            # Early vs late round spending
            early_rounds = manager_drafts[manager_drafts['round'] <= 5]
            late_rounds = manager_drafts[manager_drafts['round'] > 5]
            
            early_spending = early_rounds['cost'].sum()
            late_spending = late_rounds['cost'].sum()
            early_pct = (early_spending / total_spent * 100) if total_spent > 0 else 0
            
            # Most expensive pick
            most_expensive = manager_drafts.loc[manager_drafts['cost'].idxmax()] if not manager_drafts.empty else None
            
            # Position spending breakdown
            position_pct = {}
            for pos, pos_data in manager_drafts.groupby('position'):
                pos_total = pos_data['cost'].sum()
                position_pct[pos] = (pos_total / total_spent * 100) if total_spent > 0 else 0
            
            strategies.append({
                'manager': manager,
                'total_seasons': manager_drafts['season_year'].nunique(),
                'total_spent_all_time': total_spent,
                'avg_spending_per_season': total_spent / manager_drafts['season_year'].nunique() if manager_drafts['season_year'].nunique() > 0 else 0,
                'avg_pick_price': avg_pick_price,
                'total_picks': num_picks,
                'top_position_spent': top_position,
                'top_position_pct': position_pct.get(top_position, 0),
                'early_round_spending_pct': early_pct,
                'most_expensive_pick_cost': most_expensive['cost'] if most_expensive is not None else 0,
                'most_expensive_pick_player': most_expensive['player_name'] if most_expensive is not None else '',
                'most_expensive_pick_position': most_expensive['position'] if most_expensive is not None else '',
                'keeper_picks': len(manager_drafts[manager_drafts['is_keeper'] == True]),
                'qb_spending_pct': position_pct.get('QB', 0),
                'rb_spending_pct': position_pct.get('RB', 0),
                'wr_spending_pct': position_pct.get('WR', 0),
                'te_spending_pct': position_pct.get('TE', 0),
            })
        
        return pd.DataFrame(strategies)
    
    def _analyze_keepers(self) -> pd.DataFrame:
        """Analyze keeper picks and value."""
        if self.draft_df.empty:
            return pd.DataFrame()
        
        # Note: Keeper detection may be imperfect due to API limitations
        # For now, we'll identify potential keepers based on low cost in early rounds
        # This is a heuristic - true keeper detection would need year-over-year player tracking
        
        # Identify potential keepers (low cost in early rounds = likely kept from previous year)
        self.draft_df['potential_keeper'] = (
            (self.draft_df['round'] <= 3) & 
            (self.draft_df['cost'] < self.draft_df.groupby(['season_year', 'position'])['cost'].transform('median') * 0.7)
        ) | (self.draft_df['is_keeper'] == True)
        
        keepers = self.draft_df[self.draft_df['potential_keeper'] == True].copy()
        
        if keepers.empty:
            return pd.DataFrame(columns=['manager', 'season_year', 'player_name', 'position', 'keeper_cost'])
        
        # Keeper analysis by manager
        keeper_analysis = keepers.groupby(['manager', 'season_year']).agg({
            'cost': ['sum', 'mean', 'count'],
            'player_name': lambda x: ', '.join(x[:5])  # Limit to first 5 players
        }).reset_index()
        
        keeper_analysis.columns = ['manager', 'season_year', 'total_keeper_cost', 'avg_keeper_cost', 'num_keepers', 'keeper_players']
        
        # Overall keeper stats by manager
        manager_keepers = keepers.groupby('manager').agg({
            'cost': ['sum', 'mean', 'count'],
            'season_year': 'nunique',
            'position': lambda x: x.mode()[0] if len(x.mode()) > 0 else ''
        }).reset_index()
        
        manager_keepers.columns = ['manager', 'total_keeper_spending', 'avg_keeper_cost', 'total_keepers', 'seasons_with_keepers', 'top_kept_position']
        
        # Calculate keeper value (lower cost = better value for keepers)
        manager_keepers['total_auction_value'] = self.draft_df.groupby('manager')['cost'].sum().reindex(manager_keepers['manager'], fill_value=0).values
        manager_keepers['keeper_spending_pct'] = (manager_keepers['total_keeper_spending'] / manager_keepers['total_auction_value'] * 100).fillna(0)
        
        return manager_keepers.sort_values('total_keepers', ascending=False)
    
    def _analyze_draft_value(self) -> pd.DataFrame:
        """Analyze draft value (cost vs round)."""
        if self.draft_df.empty:
            return pd.DataFrame()
        
        # Calculate value metrics
        draft_value = self.draft_df.copy()
        
        # Average cost by round
        avg_cost_by_round = draft_value.groupby('round')['cost'].mean().to_dict()
        draft_value['expected_cost_for_round'] = draft_value['round'].map(avg_cost_by_round)
        draft_value['value_score'] = draft_value['expected_cost_for_round'] - draft_value['cost']  # Positive = good value
        
        # Best/worst values by manager
        value_by_manager = draft_value.groupby('manager').agg({
            'value_score': ['mean', 'sum'],
            'cost': 'count'
        }).reset_index()
        
        value_by_manager.columns = ['manager', 'avg_value_score', 'total_value_score', 'total_picks']
        
        return value_by_manager.sort_values('avg_value_score', ascending=False)
    
    def _analyze_yoy_trends(self) -> pd.DataFrame:
        """Analyze year-over-year trends in spending and positions."""
        if self.draft_df.empty:
            return pd.DataFrame()
        
        # Overall league trends
        league_trends = self.draft_df.groupby(['season_year', 'position']).agg({
            'cost': ['mean', 'sum', 'count']
        }).reset_index()
        
        league_trends.columns = ['season_year', 'position', 'avg_price', 'total_spent', 'num_picks']
        
        return league_trends.sort_values(['season_year', 'avg_price'], ascending=[True, False])
    
    def save_analyses(self, data_manager):
        """Save all draft analyses to CSV files.
        
        Args:
            data_manager: DataManager instance for saving files
        """
        if not self.draft_df.empty:
            data_manager.save_cleaned_data('draft_picks', self.draft_df)
        
        for analysis_name, analysis_df in self.analysis_results.items():
            if not analysis_df.empty:
                data_manager.save_cleaned_data(f'draft_{analysis_name}', analysis_df)

