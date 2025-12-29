# Weekly Data Findings & Recommendations

## Summary

After reviewing the Yahoo Fantasy API documentation and testing the `yahoofantasy` library, here's what we found:

## What the Yahoo API Provides

According to the official documentation:

1. **Weekly Matchup Points**: In matchups/scoreboard, teams have `team_points` with:
   ```xml
   <team_points>
     <coverage_type>week</coverage_type>
     <week>16</week>
     <total>135.22</total>
   </team_points>
   ```

2. **Weekly Rosters**: Roster endpoint supports week parameter:
   ```
   GET /team/{team_key}/roster;week=10
   ```

## yahoofantasy Library Limitations

1. ❌ `team1_stats` and `team2_stats` raise `RuntimeError: "Matchup does not contain individual stats"`
2. ❌ `team_points` is not directly accessible on matchup team objects
3. ❌ `roster(week=X)` parameter is not supported (TypeError when called)
4. ✅ Rosters from matchup context have `coverage_type="week"` but `player.get_points()` returns season totals

## Solutions

### Option 1: Direct API Calls (Most Reliable)

Make authenticated requests directly to Yahoo API:
- Use scoreboard endpoint: `/league/{league_key}/scoreboard;week=X` to get weekly team points
- Use roster endpoint: `/team/{team_key}/roster;week=X` to get weekly rosters

**Challenge**: Requires OAuth signing which `yahoofantasy` handles internally.

### Option 2: Use Library's Internal Session (Advanced)

Access the library's authenticated session and make requests:
```python
# Would need to reverse-engineer how yahoofantasy handles auth
# or find exposed methods in the library
```

### Option 3: Calculate from Cumulative Stats (Workaround)

1. Fetch rosters for consecutive weeks
2. Player stats are cumulative - calculate weekly = week_N - week_N_minus_1
3. Sum started players to get team weekly totals

**Limitation**: Requires fetching all previous weeks to get any week's data.

### Option 4: Accept Limitation for Now

For the current analysis framework:
- Use season totals for player points (already available)
- Skip weekly lineup analysis until weekly data source is identified
- Focus on other analyses (draft value, keeper surplus, consistency, etc.)

## Recommendation

Given the complexity of implementing direct API calls with proper OAuth signing, I recommend:

1. **Short term**: Focus on analyses that don't require weekly data (most of the analysis framework already works!)
2. **Medium term**: 
   - Check yahoofantasy library GitHub for issues/PRs about weekly stats
   - Consider contributing a feature request or PR to the library
   - Or implement direct API calls with proper OAuth (more complex but most reliable)

3. **Current workaround**: The analysis framework is designed to work with weekly data when available, but gracefully handles its absence. The schedule luck analysis already has a fallback mechanism.

## Files Created

- `HOW_TO_GET_WEEKLY_DATA.md` - Quick start guide
- `FETCH_WEEKLY_DATA.md` - Detailed implementation notes  
- `WEEKLY_DATA_SOLUTION.md` - Implementation approach
- `fetch_weekly_data_example.py` - Test script

## Next Steps

If you want to pursue weekly data:

1. Check yahoofantasy GitHub: https://github.com/spilchen/yahoofantasy
   - Look for issues about weekly stats
   - Check if there's a way to access raw API responses

2. Test direct API calls:
   - Use the library's OAuth tokens
   - Make direct requests to scoreboard/roster endpoints
   - Parse XML/JSON responses

3. Consider alternative data sources:
   - Manual entry for key seasons
   - Third-party APIs (if available)
   - Web scraping (not recommended, fragile)

For now, the analysis pipeline works great with season-level data!


