# How to Fetch Weekly Data

## Current Status

The weekly lineup analysis framework is implemented but needs weekly roster and matchup point data. The current code structure will automatically process this data once it's available.

## What's Needed

1. **Weekly Matchup Points**: Points scored by each team in each weekly matchup
2. **Weekly Rosters**: Which players were started (vs benched) each week, and their weekly points

## How to Get Weekly Data

### Option 1: Fix Matchup Points Extraction (Currently Returns 0.0)

The `_fetch_matchup_data` method in `yahoo_client.py` has been updated to extract points from `team1_stats` and `team2_stats`, but the exact structure may need adjustment based on the Yahoo API response format.

**To debug and fix:**
1. Run a test script to inspect the `team_stats` structure (see test command below)
2. Adjust the `get_team_points_from_stats` function based on the actual API structure
3. Re-run data fetch: `python main.py --refresh`

### Option 2: Fetch Weekly Rosters (New Feature)

A new method `_fetch_weekly_rosters_from_matchup` has been added to fetch weekly rosters. However, weekly player points need to be extracted from player stats.

**To complete this:**
1. For each player in the weekly roster, call `player.get_stats()` or similar to get weekly points
2. This may require API calls per player per week (slow but accurate)
3. Alternative: Sum player stats from the roster if they're embedded

### Option 3: Use Yahoo API Directly (Recommended for Testing)

Create a test script to inspect the API structure:

```python
from yahoofantasy import Context
import os
from dotenv import load_dotenv

load_dotenv()

ctx = Context(
    persist_key='yahoo_fantasy',
    client_id=os.getenv('YAHOO_CLIENT_ID'),
    client_secret=os.getenv('YAHOO_CLIENT_SECRET'),
    refresh_token=os.getenv('YAHOO_REFRESH_TOKEN')
)

leagues = ctx.get_leagues('nfl', 2023)
league = leagues[0]
weeks = league.weeks()

# Inspect a specific week
week = [w for w in weeks if getattr(w, 'week_num', 0) == 1][0]
matchups = week.matchups

for matchup in matchups[:1]:  # Just first matchup
    # Inspect team stats structure
    team1_stats = matchup.team1_stats
    print(f"team1_stats type: {type(team1_stats)}")
    print(f"team1_stats dir: {[a for a in dir(team1_stats) if not a.startswith('_')]}")
    
    # Try to access points
    if hasattr(team1_stats, 'stat'):
        stat = team1_stats.stat
        print(f"stat type: {type(stat)}")
        print(f"stat: {stat}")
    
    # Get roster for team
    team1 = matchup.team1
    roster = team1.roster()
    print(f"\nRoster players: {len(roster.players)}")
    
    # Inspect first player
    if roster.players:
        player = roster.players[0]
        print(f"Player attributes: {[a for a in dir(player) if not a.startswith('_')][:20]}")
        
        # Try to get weekly stats
        try:
            stats = player.get_stats()
            print(f"Player stats: {stats}")
        except Exception as e:
            print(f"Error getting stats: {e}")
```

### Quick Test Script

Run the example script to explore the API:

```bash
python fetch_weekly_data_example.py 2023 1
```

This will show you the structure of roster data and help identify how to get weekly player points.

### Implementation Steps

1. **Fix matchup points extraction**:
   - Test the API structure with the script above
   - Update `_fetch_matchup_data` to correctly extract points
   - Verify points are non-zero after re-fetching

2. **Complete weekly roster extraction**:
   - Determine how to get weekly player points (from roster or separate API call)
   - Update `_fetch_weekly_rosters_from_matchup` to populate weekly points
   - Test with a single week first to avoid rate limits

3. **Re-fetch data**:
   ```bash
   python main.py --refresh --start-year 2023 --end-year 2023
   ```
   (Start with one year to test, then expand)

4. **Verify weekly data**:
   ```bash
   python -c "
   import json
   data = json.load(open('data/league_data/season_2023.json'))
   matchups = data.get('matchups', [])
   non_zero = [m for m in matchups if m.get('team1_points', 0) > 0]
   print(f'Matchups with points: {len(non_zero)}/{len(matchups)}')
   if non_zero:
       print('Sample:', non_zero[0])
   
   weekly_rosters = data.get('weekly_rosters', [])
   print(f'Weekly roster records: {len(weekly_rosters)}')
   if weekly_rosters:
       print('Sample:', weekly_rosters[0])
   "
   ```

5. **Run analysis**:
   ```bash
   python -m analysis --start 2023 --end 2023 --out ./out
   ```

## Notes

- Weekly roster fetching may be slow (requires API calls per team per week)
- Consider caching or batching API calls
- The `yahoofantasy` library may have rate limits - add delays if needed
- Historical weekly roster data may not be available for very old seasons

## Current Limitations

- Matchup points currently return 0.0 (needs API structure debugging)
- Weekly rosters structure is in place but weekly points need to be populated
- The analysis framework is ready and will work once data is available

