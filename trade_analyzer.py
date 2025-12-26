"""Trade analysis module for analyzing trades between teams/managers."""
import pandas as pd
from typing import Dict, List
from collections import defaultdict
import config


class TradeAnalyzer:
    """Analyzes trade data including trade frequency, partners, and player movement."""
    
    def __init__(self, all_seasons_data: Dict[int, Dict]):
        """Initialize with all seasons data.
        
        Args:
            all_seasons_data: Dictionary mapping years to season data
        """
        self.all_seasons_data = all_seasons_data
        self.trades_df = None
        self.analysis_results = {}
    
    def analyze_all_trades(self) -> Dict:
        """Analyze all trade data.
        
        Returns:
            Dictionary containing trade analyses
        """
        # Create trades DataFrame
        self.trades_df = self._create_trades_dataframe()
        
        if self.trades_df.empty:
            print("No trade data found")
            return {}
        
        # Perform analyses
        self.analysis_results = {
            'trade_frequency': self._analyze_trade_frequency(),
            'trade_partners': self._analyze_trade_partners(),
            'manager_trade_stats': self._analyze_manager_trade_stats(),
        }
        
        return self.analysis_results
    
    def _create_trades_dataframe(self) -> pd.DataFrame:
        """Create a trades DataFrame from transaction data."""
        trades_list = []
        
        for year, season_data in self.all_seasons_data.items():
            transactions = season_data.get('transactions', [])
            for transaction in transactions:
                # Filter for trade transactions
                trans_type = transaction.get('type', '').lower()
                if 'trade' in trans_type:
                    trades_list.append({
                        'season_year': year,
                        'transaction_id': transaction.get('transaction_id', ''),
                        'type': transaction.get('type', ''),
                        'timestamp': transaction.get('timestamp', ''),
                        'status': transaction.get('status', ''),
                    })
        
        return pd.DataFrame(trades_list)
    
    def _analyze_trade_frequency(self) -> pd.DataFrame:
        """Analyze trade frequency by season."""
        if self.trades_df.empty:
            return pd.DataFrame()
        
        return self.trades_df.groupby('season_year').size().reset_index(name='num_trades')
    
    def _analyze_trade_partners(self) -> pd.DataFrame:
        """Analyze most frequent trade partners."""
        # This would require parsing trade transaction details
        # For now, return empty - needs enhancement with transaction details
        return pd.DataFrame()
    
    def _analyze_manager_trade_stats(self) -> pd.DataFrame:
        """Analyze trade statistics by manager."""
        # This would require parsing which managers are involved in trades
        # For now, return empty - needs enhancement
        return pd.DataFrame()
    
    def save_analyses(self, data_manager):
        """Save all trade analyses to CSV files."""
        if not self.trades_df.empty:
            data_manager.save_cleaned_data('trades', self.trades_df)
        
        for analysis_name, analysis_df in self.analysis_results.items():
            if not analysis_df.empty:
                data_manager.save_cleaned_data(f'trade_{analysis_name}', analysis_df)


