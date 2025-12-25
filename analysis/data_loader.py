"""Data loading and validation for auction analysis."""
import pandas as pd
import json
import os
from typing import Dict, Tuple, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    """Loads and validates draft and results data for analysis."""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize data loader.
        
        Args:
            data_dir: Base directory containing league_data and cleaned_data
        """
        self.data_dir = Path(data_dir)
        self.league_data_dir = self.data_dir / "league_data"
        self.cleaned_data_dir = self.data_dir / "cleaned_data"
    
    def load_data(self, start_year: int, end_year: int, include_transactions: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame, Dict, Optional[pd.DataFrame]]:
        """Load draft, results, league metadata, and optionally transactions.
        
        Args:
            start_year: First season to load
            end_year: Last season to load (inclusive)
            include_transactions: Whether to load transaction data
            
        Returns:
            Tuple of (drafts_df, results_df, league_meta_dict, transactions_df)
            transactions_df will be None if include_transactions=False
            
        Raises:
            FileNotFoundError: If required data files are missing
            ValueError: If data validation fails
        """
        logger.info(f"Loading data for seasons {start_year}-{end_year}")
        
        # Load draft data
        drafts_df = self._load_drafts(start_year, end_year)
        
        # Load results data (player fantasy points)
        results_df = self._load_results(start_year, end_year)
        
        # Load league metadata
        league_meta = self._load_league_meta(start_year, end_year)
        
        # Load transactions if requested
        transactions_df = None
        if include_transactions:
            transactions_df = self._load_transactions(start_year, end_year)
        
        # Validate schemas
        self._validate_drafts(drafts_df)
        self._validate_results(results_df)
        self._validate_league_meta(league_meta)
        
        return drafts_df, results_df, league_meta, transactions_df
    
    def _load_transactions(self, start_year: int, end_year: int) -> pd.DataFrame:
        """Load transaction data from raw JSON files.
        
        Args:
            start_year: First season
            end_year: Last season
            
        Returns:
            DataFrame with transactions
        """
        transactions_list = []
        
        for year in range(start_year, end_year + 1):
            json_file = self.league_data_dir / f"season_{year}.json"
            if not json_file.exists():
                continue
            
            with open(json_file, 'r') as f:
                season_data = json.load(f)
            
            transactions = season_data.get('transactions', [])
            for txn in transactions:
                if 'error' in txn:
                    continue
                
                # Flatten involved players into separate rows
                involved_players = txn.get('involved_players', [])
                
                if involved_players:
                    for player in involved_players:
                        transactions_list.append({
                            'season_year': year,
                            'transaction_id': txn.get('transaction_id', ''),
                            'transaction_key': txn.get('transaction_key', ''),
                            'transaction_type': txn.get('type', ''),
                            'timestamp': txn.get('timestamp', ''),
                            'status': txn.get('status', ''),
                            'player_id': player.get('player_id'),
                            'player_key': player.get('player_key'),
                            'player_name': player.get('player_name', ''),
                            'transaction_player_type': player.get('transaction_type'),  # ADD, DROP, TRADE
                            'from_team_key': player.get('from_team_key'),
                            'to_team_key': player.get('to_team_key'),
                            'faab_bid': player.get('faab_bid'),
                            'waiver_priority': player.get('waiver_priority'),
                        })
                else:
                    # Transaction without detailed player info - still record it
                    transactions_list.append({
                        'season_year': year,
                        'transaction_id': txn.get('transaction_id', ''),
                        'transaction_key': txn.get('transaction_key', ''),
                        'transaction_type': txn.get('type', ''),
                        'timestamp': txn.get('timestamp', ''),
                        'status': txn.get('status', ''),
                        'player_id': None,
                        'player_name': None,
                        'transaction_player_type': None,
                        'from_team_key': None,
                        'to_team_key': None,
                        'faab_bid': None,
                        'waiver_priority': None,
                    })
        
        df = pd.DataFrame(transactions_list)
        logger.info(f"Loaded {len(df)} transaction records")
        return df
    
    def _load_drafts(self, start_year: int, end_year: int) -> pd.DataFrame:
        """Load draft data from cleaned CSV or reconstruct from raw JSON.
        
        Args:
            start_year: First season
            end_year: Last season
            
        Returns:
            DataFrame with draft picks
        """
        # Try to load from cleaned CSV first
        draft_csv = self.cleaned_data_dir / "draft_picks.csv"
        if draft_csv.exists():
            try:
                df = pd.read_csv(draft_csv)
                # Filter to requested years
                if 'season_year' in df.columns:
                    df = df[(df['season_year'] >= start_year) & (df['season_year'] <= end_year)].copy()
                    if not df.empty:
                        logger.info(f"Loaded {len(df)} draft picks from CSV")
                        return df
            except Exception as e:
                logger.warning(f"Error loading draft CSV: {e}")
        
        # Otherwise reconstruct from raw JSON files
        logger.info("Reconstructing draft data from raw JSON files")
        picks_list = []
        
        for year in range(start_year, end_year + 1):
            json_file = self.league_data_dir / f"season_{year}.json"
            if not json_file.exists():
                logger.warning(f"Season {year} data file not found, skipping")
                continue
            
            with open(json_file, 'r') as f:
                season_data = json.load(f)
            
            draft_results = season_data.get('draft_results', [])
            for pick in draft_results:
                if 'error' not in pick:
                    picks_list.append(pick)
        
        if not picks_list:
            return pd.DataFrame()
        
        df = pd.DataFrame(picks_list)
        logger.info(f"Loaded {len(df)} draft picks from JSON files")
        return df
    
    def _load_results(self, start_year: int, end_year: int) -> pd.DataFrame:
        """Load player results (fantasy points) data.
        
        Attempts to extract player stats from:
        1. Cached player stats file (if exists)
        2. Raw JSON season data (if player stats were saved there)
        3. Yahoo API (via extract_player_stats module, if enabled)
        
        Args:
            start_year: First season
            end_year: Last season
            
        Returns:
            DataFrame with player results
        """
        # Try to load from a cached player stats file first
        player_stats_file = self.cleaned_data_dir / "player_stats.csv"
        if player_stats_file.exists():
            try:
                df = pd.read_csv(player_stats_file)
                df = df[(df['season_year'] >= start_year) & (df['season_year'] <= end_year)].copy()
                if not df.empty and df['fantasy_points_total'].notna().any():
                    logger.info(f"Loaded {len(df)} player stats from cached file")
                    return df
            except Exception as e:
                logger.warning(f"Error loading cached player stats: {e}")
        
        # Otherwise, extract from raw JSON files
        results_list = []
        
        for year in range(start_year, end_year + 1):
            json_file = self.league_data_dir / f"season_{year}.json"
            if not json_file.exists():
                continue
            
            with open(json_file, 'r') as f:
                season_data = json.load(f)
            
            # Extract player results from teams/rosters
            teams = season_data.get('teams', [])
            for team in teams:
                if 'error' in team:
                    continue
                
                roster = team.get('roster', [])
                # Collect player info - extract fantasy points if available
                for player in roster:
                    results_list.append({
                        'season_year': year,
                        'player_id': player.get('player_id', ''),
                        'player_name': player.get('name', ''),
                        'position': player.get('position', ''),
                        'fantasy_points_total': player.get('fantasy_points_total'),  # May be None
                        'games_played': None,  # Not available from roster
                        'team_key': team.get('team_key', ''),
                    })
        
        df = pd.DataFrame(results_list)
        
        if df.empty:
            logger.warning("No player results data found. Analysis will be limited.")
        else:
            has_points = df['fantasy_points_total'].notna().any()
            if not has_points:
                logger.warning(
                    f"Loaded {len(df)} player result records but no fantasy points found. "
                    "Run player stats extraction to populate points."
                )
            else:
                logger.info(f"Loaded {len(df)} player result records with points")
        
        return df
    
    def _load_league_meta(self, start_year: int, end_year: int) -> Dict:
        """Load league metadata (settings, roster requirements, etc.).
        
        Args:
            start_year: First season
            end_year: Last season
            
        Returns:
            Dictionary mapping year -> league metadata
        """
        league_meta = {}
        
        for year in range(start_year, end_year + 1):
            json_file = self.league_data_dir / f"season_{year}.json"
            if not json_file.exists():
                continue
            
            with open(json_file, 'r') as f:
                season_data = json.load(f)
            
            settings = season_data.get('settings', {})
            teams = season_data.get('teams', [])
            
            # Estimate league structure from data
            num_teams = len([t for t in teams if 'error' not in t])
            
            # Default values (can be overridden if settings have more info)
            meta = {
                'season': year,
                'num_teams': num_teams,
                'auction_budget': 200,  # Standard fantasy budget
                'starting_slots_by_position': {
                    'QB': 1,
                    'RB': 2,
                    'WR': 2,
                    'TE': 1,
                    'FLEX': 1,  # Assuming one FLEX spot
                },
                'bench_slots': 6,  # Estimate
                'num_keepers': 2,  # User specified 2 keepers per team
            }
            
            # Try to extract from settings if available
            if settings:
                # Yahoo settings may have roster requirements
                # This would need to be parsed from the settings dict structure
                pass
            
            league_meta[year] = meta
        
        logger.info(f"Loaded league metadata for {len(league_meta)} seasons")
        return league_meta
    
    def _validate_drafts(self, df: pd.DataFrame):
        """Validate draft data schema.
        
        Args:
            df: Draft DataFrame
            
        Raises:
            ValueError: If required columns are missing
        """
        required_cols = ['season_year', 'player_id', 'player_name', 'position', 'cost', 'is_keeper']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns in drafts: {missing}")
        
        if df.empty:
            logger.warning("Draft DataFrame is empty")
            return
        
        # Check for missing values in key fields
        null_counts = df[required_cols].isnull().sum()
        if null_counts.any():
            logger.warning(f"Null values in draft data:\n{null_counts[null_counts > 0]}")
    
    def _validate_results(self, df: pd.DataFrame):
        """Validate results data schema.
        
        Args:
            df: Results DataFrame
        """
        required_cols = ['season_year', 'player_id', 'player_name', 'position']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns in results: {missing}")
    
    def _validate_league_meta(self, meta: Dict):
        """Validate league metadata.
        
        Args:
            meta: League metadata dictionary
        """
        required_keys = ['num_teams', 'auction_budget', 'starting_slots_by_position']
        for year, year_meta in meta.items():
            missing = [key for key in required_keys if key not in year_meta]
            if missing:
                logger.warning(f"Season {year} missing metadata keys: {missing}")

