"""CLI script to extract player stats from Yahoo API and save to CSV."""
import argparse
import sys
import logging
import pandas as pd
from pathlib import Path

from .extract_player_stats import extract_player_stats_from_api
from .data_loader import DataLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Extract player stats from Yahoo API."""
    parser = argparse.ArgumentParser(
        description="Extract player fantasy points from Yahoo Fantasy API"
    )
    parser.add_argument(
        '--start',
        type=int,
        default=2014,
        help='First season to extract (default: 2014)'
    )
    parser.add_argument(
        '--end',
        type=int,
        default=2024,
        help='Last season to extract (default: 2024)'
    )
    parser.add_argument(
        '--out',
        type=str,
        default='data/cleaned_data/player_stats.csv',
        help='Output CSV file (default: data/cleaned_data/player_stats.csv)'
    )
    
    args = parser.parse_args()
    
    all_stats = []
    
    try:
        from yahoofantasy import Context
        import config
        
        ctx = Context(
            persist_key='yahoo_fantasy',
            client_id=config.YAHOO_CLIENT_ID,
            client_secret=config.YAHOO_CLIENT_SECRET,
            refresh_token=config.YAHOO_REFRESH_TOKEN
        )
        
        # Get league name for matching
        leagues = ctx.get_leagues('nfl', args.end)
        if leagues:
            ctx._league_name = getattr(leagues[0], 'name', '')
        
        for year in range(args.start, args.end + 1):
            logger.info(f"Extracting player stats for {year}...")
            stats_df = extract_player_stats_from_api(year, ctx=ctx)
            if not stats_df.empty:
                all_stats.append(stats_df)
        
        if not all_stats:
            logger.error("No player stats extracted")
            return 1
        
        # Combine all seasons
        combined = pd.concat(all_stats, ignore_index=True)
        
        # Save to CSV
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(output_path, index=False)
        
        total_players = len(combined)
        players_with_points = combined['fantasy_points_total'].notna().sum()
        
        logger.info(f"Extracted stats for {total_players} players")
        logger.info(f"Players with points: {players_with_points} ({100*players_with_points/total_players:.1f}%)")
        logger.info(f"Saved to {output_path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())


