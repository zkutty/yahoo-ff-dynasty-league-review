# How to Get Weekly Data - Summary

## Quick Answer

To get weekly data, you need to:

1. **Get rosters from matchup context** (this works - roster has week info)
2. **Extract weekly player points** (the blocker - `player.get_points()` returns season totals)
3. **Sum started players' weekly points** to get team weekly totals

## What Works Now

✅ **Rosters accessible**: Can get roster for each team in each matchup
✅ **Started players identifiable**: Can determine who started (roster_slot not BN/IR)  
✅ **Player points accessible**: `player.get_points()` returns points

## The Problem

❌ **Weekly vs Season totals**: `player.get_points()` in matchup context returns **season totals**, not weekly stats

From testing:
- Tua Tagovailoa: 284.36 pts (season total, not week 1)
- Started 8 players summing to 1653.8 pts (likely season totals, too high for one week)

## Solutions to Try

### Option 1: Use Roster Week Context (Recommended First Try)

The roster object has `week` and `week_num` attributes. Try fetching roster with explicit week:

```python
# In matchup context, try:
roster = team.roster(week=week_num)  # Explicit week parameter
# Then check if player.get_points() returns weekly points
```

### Option 2: Use `roster.fetch_player_stats`

The roster has a `fetch_player_stats` method. This might fetch weekly stats:

```python
roster.fetch_player_stats()  # May populate weekly stats
# Then check player.get_points() again
```

### Option 3: Calculate from Cumulative Stats

Fetch rosters for consecutive weeks and calculate difference:

```python
week_1_roster = team.roster(week=1)
week_2_roster = team.roster(week=2)

player_week1_points = week_1_player.get_points()  # Cumulative to week 1
player_week2_points = week_2_player.get_points()  # Cumulative to week 2
weekly_points = week_2_points - week_1_points
```

### Option 4: Use Yahoo API Directly (If yahoofantasy doesn't support weekly)

The raw Yahoo Fantasy API has endpoints for weekly stats. You might need to:
1. Check yahoofantasy library documentation for weekly stats methods
2. Or make direct API calls bypassing the library
3. Or check if there's a different method/parameter for weekly stats

## Quick Test Commands

Test if roster week parameter works:

```bash
python -c "
from yahoofantasy import Context
from dotenv import load_dotenv
import os
load_dotenv()

ctx = Context(
    persist_key='yahoo_fantasy',
    client_id=os.getenv('YAHOO_CLIENT_ID'),
    client_secret=os.getenv('YAHOO_CLIENT_SECRET'),
    refresh_token=os.getenv('YAHOO_REFRESH_TOKEN')
)

leagues = ctx.get_leagues('nfl', 2023)
league = leagues[0]
teams = league.teams()
team = teams[0]

# Try with explicit week
try:
    roster_w1 = team.roster(week=1)
    print(f'Roster week 1 - week_num: {roster_w1.week_num}')
    if roster_w1.players:
        player = roster_w1.players[0]
        points = player.get_points()
        print(f'Player points week 1: {points}')
except Exception as e:
    print(f'Error: {e}')

# Compare with week 2
try:
    roster_w2 = team.roster(week=2)
    if roster_w2.players and len(roster_w2.players) > 0:
        player = roster_w2.players[0]
        points = player.get_points()
        print(f'Player points week 2: {points}')
except Exception as e:
    print(f'Error: {e}')
"
```

If points differ between weeks, they're cumulative and you can calculate weekly.
If points are the same, they're season totals and you need a different approach.

## Once Weekly Points Are Working

1. Update `_fetch_matchup_data` in `yahoo_client.py`:
   - Get roster for each team
   - Filter to started players
   - Sum `player.get_points()` for started players
   - Set `team1_points` and `team2_points`

2. Update `_fetch_weekly_rosters_from_matchup`:
   - Get roster for each team
   - For each player, extract weekly points using `player.get_points()`
   - Include in weekly_rosters list

3. Re-fetch data:
   ```bash
   python main.py --refresh --start-year 2023 --end-year 2023
   ```

4. Run analysis:
   ```bash
   python -m analysis --start 2023 --end 2023 --out ./out
   ```

## Resources

- Test script: `fetch_weekly_data_example.py` - Explore API structure
- Documentation: `FETCH_WEEKLY_DATA.md` - Detailed implementation guide
- Yahoo Fantasy API docs: Check yahoofantasy library GitHub/docs for weekly stats methods


