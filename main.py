"""Main application script for Yahoo Fantasy Football League Review."""
import sys
from yahoo_client import YahooFantasyClient
from data_manager import DataManager
from data_cleaner import DataCleaner
from draft_analyzer import DraftAnalyzer
from trade_analyzer import TradeAnalyzer
import config


def fetch_league_data(refresh: bool = False, generate_ai: bool = False, start_year: int = None,
                      end_year: int = None, fetch_weekly_points: bool = False):
    """Fetch league data from Yahoo Fantasy API.

    Args:
        refresh: If True, fetch fresh data even if cached data exists
        generate_ai: If True, generate AI-powered insights (requires OpenAI API key)
        start_year: First year to fetch (default: config.LEAGUE_START_YEAR)
        end_year: Last year to fetch (default: config.CURRENT_YEAR)
        fetch_weekly_points: If True, fetch weekly player points using cumulative difference method
    """
    print("=" * 60)
    print("Yahoo Fantasy Football League Review App")
    print("=" * 60)
    
    # Validate configuration
    if not all([config.YAHOO_CLIENT_ID, config.YAHOO_CLIENT_SECRET, config.YAHOO_LEAGUE_ID]):
        print("ERROR: Missing required configuration. Please check your .env file.")
        print("Required: YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET, YAHOO_LEAGUE_ID")
        sys.exit(1)
    
    
    data_manager = DataManager()
    client = YahooFantasyClient(
        client_id=config.YAHOO_CLIENT_ID,
        client_secret=config.YAHOO_CLIENT_SECRET,
        league_id=config.YAHOO_LEAGUE_ID,
        refresh_token=config.YAHOO_REFRESH_TOKEN
    )
    
    # Fetch data for all seasons
    all_data = {}
    
    # Use provided years or default to config values
    start = start_year if start_year is not None else config.LEAGUE_START_YEAR
    end = end_year if end_year is not None else config.CURRENT_YEAR
    
    if refresh:
        print(f"\nFetching fresh data from Yahoo API for years {start}-{end}...")
        
        try:
            client.authenticate()
            client.get_league()
            
            for year in range(start, end + 1):
                print(f"\nFetching {year} season data...")
                try:
                    season_data = client.fetch_season_data(
                        year,
                        fetch_weekly_points=fetch_weekly_points
                    )
                    all_data[year] = season_data
                    data_manager.save_season_data(year, season_data)
                except (ValueError, Exception) as e:
                    print(f"  Skipping {year}: {e}")
                    # Continue with other years even if one fails
                    continue
                
        except Exception as e:
            print(f"Error fetching data: {e}")
            if "UnicodeDecodeError" in str(type(e).__name__) or "utf-8" in str(e).lower():
                print("\nNote: Authentication cache may be corrupted. The code will attempt to clear it on next run.")
                print("You can also manually clear the cache by running: rm -rf ~/.cache/yahoofantasy* ~/.yahoofantasy*")
            print("\nTrying to use cached data if available...")
            all_data = data_manager.load_all_seasons(start, end)
    else:
        print(f"\nLoading cached data from {start}-{end}...")
        all_data = data_manager.load_all_seasons(start, end)
        
        if not all_data:
            print("No cached data found. Use --refresh flag to fetch from Yahoo API.")
            sys.exit(1)
    
    print(f"\nLoaded data for {len(all_data)} seasons: {list(all_data.keys())}")
    
    # Clean and organize data
    print("\nCleaning and organizing data...")
    cleaner = DataCleaner(all_data)
    cleaned_data = cleaner.clean_all_data()
    
    # Save cleaned data
    for name, df in cleaned_data.items():
        data_manager.save_cleaned_data(name, df)
    
    # Extract key insights
    print("\nExtracting key insights...")
    insights = cleaner.get_key_insights()
    
    # Analyze draft data
    print("\nAnalyzing draft data...")
    draft_analyzer = DraftAnalyzer(all_data)
    draft_analyses = draft_analyzer.analyze_all_drafts()
    
    # Save draft analyses
    draft_analyzer.save_analyses(data_manager)
    
    if draft_analyses:
        print("\nDraft Analysis Summary:")
        if 'position_spending' in draft_analyses and not draft_analyses['position_spending'].empty:
            print("\nTop Position Spending by Manager:")
            print(draft_analyses['position_spending'].head(10).to_string())
        
        if 'keeper_analysis' in draft_analyses and not draft_analyses['keeper_analysis'].empty:
            print("\nKeeper Analysis:")
            print(draft_analyses['keeper_analysis'].to_string())
        
        if 'manager_draft_strategies' in draft_analyses and not draft_analyses['manager_draft_strategies'].empty:
            print("\nDraft Strategies Summary:")
            strategies_df = draft_analyses['manager_draft_strategies']
            print(strategies_df[['manager', 'avg_spending_per_season', 'top_position_spent', 'top_position_pct', 'early_round_spending_pct', 'keeper_picks']].to_string())
        
        # Generate detailed draft summary
        try:
            from draft_analysis_summary import generate_draft_summary
            generate_draft_summary()
        except Exception as e:
            print(f"\nNote: Could not generate draft summary: {e}")
    
    # Analyze trades
    print("\nAnalyzing trade data...")
    trade_analyzer = TradeAnalyzer(all_data)
    trade_analyses = trade_analyzer.analyze_all_trades()
    trade_analyzer.save_analyses(data_manager)
    
    if trade_analyses and 'trade_frequency' in trade_analyses and not trade_analyses['trade_frequency'].empty:
        print("\nTrade Frequency by Season:")
        print(trade_analyses['trade_frequency'].to_string())
    
    # Show basic statistics
    print("\n" + "=" * 60)
    print("KEY STATISTICS")
    print("=" * 60)
    if 'managers' in cleaned_data and not cleaned_data['managers'].empty:
        managers_df = cleaned_data['managers']
        print("\nTop Managers by Wins:")
        print(managers_df.nlargest(5, 'total_wins')[['manager_name', 'total_wins', 'championships', 'win_percentage']].to_string())
        
        print("\nChampionship Leaders:")
        print(managers_df.nlargest(5, 'championships')[['manager_name', 'championships', 'total_wins', 'win_percentage']].to_string())
    
    # Generate OpenAI insights if requested (separate module to save API costs)
    if generate_ai:
        try:
            from ai_insights import generate_all_insights
            generate_all_insights(insights, cleaned_data)
        except ImportError:
            print("\nERROR: Could not import ai_insights module")
        except Exception as e:
            print(f"\nERROR generating AI insights: {e}")
    else:
        print("\n" + "=" * 60)
        print("AI INSIGHTS")
        print("=" * 60)
        print("Skipped. Use --generate-ai flag to generate AI-powered insights.")
        print("Note: This will use your OpenAI API and may incur costs.")
    
    print("\n" + "=" * 60)
    print("Data processing complete!")
    print(f"Check the '{config.INSIGHTS_DIR}' directory for generated insights.")
    print(f"Check the '{config.CLEANED_DATA_DIR}' directory for cleaned data files.")
    print("=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Yahoo Fantasy Football League Review App"
    )
    parser.add_argument(
        '--refresh',
        action='store_true',
        help='Fetch fresh data from Yahoo API (ignores cached data)'
    )
    parser.add_argument(
        '--generate-ai',
        action='store_true',
        help='Generate AI-powered insights (requires OpenAI API key and incurs costs)'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=None,
        help=f'First year to fetch/analyze (default: {config.LEAGUE_START_YEAR})'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        default=None,
        help=f'Last year to fetch/analyze (default: {config.CURRENT_YEAR})'
    )
    parser.add_argument(
        '--weekly-points',
        action='store_true',
        help='Fetch weekly player points using cumulative difference method (slower but provides weekly granularity)'
    )

    args = parser.parse_args()

    # Run the main function
    fetch_league_data(
        refresh=args.refresh,
        generate_ai=args.generate_ai,
        start_year=args.start_year,
        end_year=args.end_year,
        fetch_weekly_points=args.weekly_points
    )


if __name__ == "__main__":
    main()

