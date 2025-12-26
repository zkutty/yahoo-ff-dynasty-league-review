"""Data management and storage for league data."""
import json
import os
from typing import Dict, List, Optional
import pandas as pd
import config


class DataManager:
    """Manages storage and retrieval of league data."""
    
    def __init__(self):
        """Initialize the data manager."""
        config.ensure_directories()
    
    def save_season_data(self, year: int, data: Dict):
        """Save season data to a JSON file.
        
        Args:
            year: The season year
            data: The season data dictionary
        """
        file_path = os.path.join(config.LEAGUE_DATA_DIR, f"season_{year}.json")
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Saved data for {year} to {file_path}")
    
    def load_season_data(self, year: int) -> Optional[Dict]:
        """Load season data from a JSON file.
        
        Args:
            year: The season year
            
        Returns:
            Season data dictionary or None if not found
        """
        file_path = os.path.join(config.LEAGUE_DATA_DIR, f"season_{year}.json")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    
    def load_all_seasons(self, start_year: int, end_year: int) -> Dict[int, Dict]:
        """Load all season data files.
        
        Args:
            start_year: First year to load
            end_year: Last year to load (inclusive)
            
        Returns:
            Dictionary mapping years to season data
        """
        all_data = {}
        for year in range(start_year, end_year + 1):
            data = self.load_season_data(year)
            if data:
                all_data[year] = data
        return all_data
    
    def save_cleaned_data(self, filename: str, data: pd.DataFrame):
        """Save cleaned/processed data to CSV.
        
        Args:
            filename: Name of the file (without extension)
            data: DataFrame to save
        """
        file_path = os.path.join(config.CLEANED_DATA_DIR, f"{filename}.csv")
        data.to_csv(file_path, index=False)
        print(f"Saved cleaned data to {file_path}")
    
    def load_cleaned_data(self, filename: str) -> Optional[pd.DataFrame]:
        """Load cleaned data from CSV.
        
        Args:
            filename: Name of the file (without extension)
            
        Returns:
            DataFrame or None if not found
        """
        file_path = os.path.join(config.CLEANED_DATA_DIR, f"{filename}.csv")
        if os.path.exists(file_path):
            return pd.read_csv(file_path)
        return None
    
    def save_insight(self, filename: str, content: str):
        """Save generated insight to a text file.
        
        Args:
            filename: Name of the file (without extension)
            content: The insight content to save
        """
        file_path = os.path.join(config.INSIGHTS_DIR, f"{filename}.txt")
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Saved insight to {file_path}")


