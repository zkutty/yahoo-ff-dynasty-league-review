"""Script to rerun data pulls for seasons 2014-2025 in reverse order."""
import sys
import argparse
import time
from datetime import datetime
from yahoo_client import YahooFantasyClient
from data_manager import DataManager
import config

def is_rate_limit_error(error):
    """Check if an error is a rate limit error."""
    error_str = str(error).lower()
    rate_limit_indicators = [
        'rate limit',
        'rate_limit',
        '429',
        'too many requests',
        'quota exceeded',
        'quota limit',
        'throttle',
        'throttled',
        'limit exceeded',
        'daily limit',
        'hourly limit'
    ]
    return any(indicator in error_str for indicator in rate_limit_indicators)

def wait_with_backoff(attempt, base_delay=60, max_delay=3600):
    """Wait with exponential backoff for rate limit errors.
    
    Args:
        attempt: Current retry attempt (0-indexed)
        base_delay: Base delay in seconds (default: 60 seconds = 1 minute)
        max_delay: Maximum delay in seconds (default: 3600 seconds = 1 hour)
    
    Returns:
        Delay time in seconds
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    return delay

def fetch_season_with_retry(client, data_manager, year, fetch_weekly_points=False, max_retries=3):
    """Fetch season data with retry logic for rate limit errors.

    Args:
        client: YahooFantasyClient instance
        data_manager: DataManager instance
        year: Season year to fetch
        fetch_weekly_points: Whether to fetch weekly player points data
        max_retries: Maximum number of retry attempts

    Returns:
        Tuple of (success: bool, was_rate_limited: bool)
    """
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                wait_time = wait_with_backoff(attempt - 1)
                print(f"  Retry attempt {attempt}/{max_retries} after {wait_time} seconds...")
                print(f"  Waiting until {datetime.now().strftime('%H:%M:%S')}...")
                time.sleep(wait_time)
            
            season_data = client.fetch_season_data(
                year,
                fetch_weekly_points=fetch_weekly_points,
                start_week=1,
                end_week=17
            )
            data_manager.save_season_data(year, season_data)
            return (True, False)
            
        except (ValueError, Exception) as e:
            error_str = str(e)
            
            if is_rate_limit_error(e):
                if attempt < max_retries:
                    print(f"  ⚠ Rate limit error detected: {error_str[:200]}")
                    print(f"  This is attempt {attempt + 1}/{max_retries + 1}")
                    # Will retry with backoff
                    continue
                else:
                    print(f"  ✗ Rate limit error after {max_retries + 1} attempts")
                    print(f"  ⚠ You've hit the daily API limit. Please wait 24 hours and resume.")
                    print(f"  ⚠ You can resume by running this script again - it will skip already-fetched seasons.")
                    return (False, True)  # Failed due to rate limit
            else:
                # Non-rate-limit error - don't retry
                print(f"  ✗ Failed to fetch {year}: {error_str[:200]}")
                return (False, False)  # Failed for other reason
    
    return (False, False)

def main():
    """Rerun data pulls for 2014-2025, working backwards."""
    parser = argparse.ArgumentParser(
        description="Rerun data pulls for seasons 2014-2025 in reverse order"
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force refetch even if data already exists (default: skip existing data)'
    )
    parser.add_argument(
        '--weekly-points',
        action='store_true',
        help='Fetch weekly player points data (default: False)'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=2014,
        help='Start year for data fetch (default: 2014)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        default=2025,
        help='End year for data fetch (default: 2025)'
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"Rerunning Data Pulls for Seasons {args.start_year}-{args.end_year} (Reverse Order)")
    if args.force:
        print("⚠ FORCE MODE: Will refetch all seasons even if data exists")
    if args.weekly_points:
        print("📊 WEEKLY POINTS MODE: Will fetch weekly player points data")
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
    
    # Authenticate once
    print("\nAuthenticating with Yahoo API...")
    try:
        client.authenticate()
        client.get_league()
        print("Authentication successful!")
    except Exception as e:
        print(f"ERROR: Authentication failed: {e}")
        sys.exit(1)
    
    # Years to fetch: from command-line args, in reverse order
    start_year = args.start_year
    end_year = args.end_year

    print(f"\nFetching data for seasons {end_year} down to {start_year}...")
    print(f"Total seasons: {end_year - start_year + 1}\n")
    
    successful = []
    failed = []
    skipped = []
    rate_limited = False
    
    total_seasons = end_year - start_year + 1
    start_time = time.time()
    
    # Iterate backwards from 2025 to 2014
    for idx, year in enumerate(range(end_year, start_year - 1, -1), 1):
        # Check if data already exists (skip unless --force is used)
        if not args.force:
            existing_data = data_manager.load_season_data(year)
            if existing_data:
                print(f"\n{'='*60}")
                print(f"[{idx}/{total_seasons}] {year} season data already exists - skipping")
                print(f"{'='*60}")
                print(f"  (Use --force flag to refetch)")
                skipped.append(year)
                continue
        
        print(f"\n{'='*60}")
        print(f"[{idx}/{total_seasons}] Fetching {year} season data...")
        print(f"{'='*60}")
        
        # Fetch with retry logic
        success, was_rate_limited = fetch_season_with_retry(
            client, data_manager, year,
            fetch_weekly_points=args.weekly_points,
            max_retries=3
        )
        
        if success:
            successful.append(year)
            print(f"✓ Successfully fetched and saved {year} season data")
            
            # Calculate progress
            elapsed = time.time() - start_time
            avg_time_per_season = elapsed / len(successful) if successful else 0
            remaining = total_seasons - idx
            estimated_remaining = avg_time_per_season * remaining if remaining > 0 else 0
            
            print(f"  Progress: {idx}/{total_seasons} seasons")
            if estimated_remaining > 0:
                print(f"  Estimated time remaining: {estimated_remaining/60:.1f} minutes")
        else:
            # Check if it was a rate limit
            if was_rate_limited:
                rate_limited = True
                print(f"\n⚠ RATE LIMIT HIT - Stopping to avoid further errors")
                print(f"  Successfully fetched: {len(successful)} seasons")
                print(f"  Failed due to rate limit: {year}")
                print(f"  Remaining seasons: {list(range(year - 1, start_year - 1, -1))}")
                print(f"\n  You can resume this script later - it will skip already-fetched seasons.")
                break
            else:
                failed.append(year)
        
        # Delay between seasons to avoid hitting rate limits
        # Longer delay for more recent seasons (they tend to have more data)
        if year >= 2020:
            delay = 10  # 10 seconds for recent seasons
        else:
            delay = 5   # 5 seconds for older seasons
        
        if idx < total_seasons and not rate_limited:
            print(f"\n  Waiting {delay} seconds before next season...")
            time.sleep(delay)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    if successful:
        print(f"✓ Successfully fetched: {len(successful)} seasons")
        print(f"  Years: {sorted(successful)}")
    
    if skipped:
        print(f"\n⊘ Skipped (already exists): {len(skipped)} seasons")
        print(f"  Years: {sorted(skipped)}")
    
    if failed:
        print(f"\n✗ Failed to fetch: {len(failed)} seasons")
        print(f"  Years: {sorted(failed)}")
    
    if rate_limited:
        print(f"\n⚠ RATE LIMIT REACHED")
        print(f"  The script stopped due to API rate limits.")
        print(f"  Please wait 24 hours and run this script again.")
        print(f"  It will automatically skip already-fetched seasons.")
    
    total_time = time.time() - start_time
    print(f"\n⏱ Total time: {total_time/60:.1f} minutes")
    print(f"\nData files saved to: {config.LEAGUE_DATA_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()

