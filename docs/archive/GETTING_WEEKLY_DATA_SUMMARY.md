# Getting Weekly Data - Current Status

## Summary

**What you need**: Weekly matchup points and weekly roster lineups with player points

**Current status**: Framework is ready, but need to extract weekly player points from Yahoo API

## What Works

✅ Can get rosters from matchup context  
✅ Can identify which players started (vs benched)  
✅ Can call `player.get_points()` - but it returns **season totals**, not weekly

## The Challenge

`player.get_points()` returns season totals (e.g., 284.36 for Tua) even when roster is from a specific week matchup context.

## Next Steps to Get Weekly Data

### Option 1: Check yahoofantasy Library Documentation

The library might have a method for weekly stats that we're not using:
- Check GitHub: https://github.com/spilchen/yahoofantasy
- Look for weekly stats methods or parameters
- Check if there's a way to pass week to `get_points()` or `get_stats()`

### Option 2: Use Cumulative Stats Difference (Works but Requires All Weeks)

1. Fetch roster for week N
2. Fetch roster for week N-1  
3. Calculate: `weekly_points = week_N_total - week_N_minus_1_total`

This works but requires fetching all previous weeks to get any week's data.

### Option 3: Use Yahoo API Directly (Most Reliable)

Bypass yahoofantasy library and call Yahoo Fantasy API directly:
- API endpoint: `https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster;week={week}`
- This should return weekly roster with weekly stats
- Requires OAuth token (you already have this)

### Option 4: Manual Data Entry (Fallback)

For key seasons, manually enter weekly matchup scores from league history.

## Recommended Action Plan

1. **First**: Check yahoofantasy docs/Issues for weekly stats support
2. **If not available**: Implement Option 3 (direct API calls) for weekly rosters
3. **Alternative**: Use Option 2 (cumulative difference) - slower but works
4. **Once working**: Update `yahoo_client.py` and re-fetch data

## Test Scripts Available

- `fetch_weekly_data_example.py` - Explore API structure
- `HOW_TO_GET_WEEKLY_DATA.md` - Detailed guide
- `FETCH_WEEKLY_DATA.md` - Implementation notes

## Current Code Status

✅ Framework complete in `analysis/weekly_lineups.py`  
✅ Integration ready in `analysis/pipeline.py`  
✅ Report section ready in `analysis/insight_report.py`  
⏳ Waiting on: Weekly player points extraction method

Once you identify how to get weekly player points, the rest will work automatically!


