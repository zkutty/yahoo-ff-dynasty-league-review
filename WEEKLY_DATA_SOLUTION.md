# Weekly Data Solution

## Key Findings from Yahoo API Documentation

1. **Matchup Team Points**: In matchups, teams have `team_points` with:
   - `coverage_type="week"`
   - `week=X`
   - `total` = weekly points scored

2. **Weekly Rosters**: Roster endpoint supports week parameter:
   - `https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster;week=10`

## Implementation Approach

Since the `yahoofantasy` library may not directly expose these fields, we have two options:

### Option 1: Use Raw API Calls (Recommended)

Make direct API calls to get:
1. Weekly matchup points from scoreboard/matchups endpoint
2. Weekly rosters using `;week=X` parameter

### Option 2: Try Library Methods First

1. Check if matchup teams expose `team_points` attribute
2. Check if roster method accepts `week` parameter
3. Fall back to raw API if library doesn't support

## Code Updates Needed

1. Update `_fetch_matchup_data` to extract `team_points.total` from matchup teams
2. Update `_fetch_weekly_rosters_from_matchup` to use `roster(week=X)` or direct API call
3. For player weekly points, fetch roster with week parameter and extract player stats

## Next Steps

1. Test accessing team_points from matchup teams in yahoofantasy
2. Test roster(week=X) parameter if library supports it
3. If not, implement direct API calls using existing OAuth tokens
4. Update yahoo_client.py with working solution


