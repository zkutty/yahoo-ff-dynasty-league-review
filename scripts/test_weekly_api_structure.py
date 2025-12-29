"""Enhanced test script to thoroughly explore Yahoo Fantasy API weekly data structure.

This script will help us understand:
1. How to get weekly matchup points (team totals)
2. How to get weekly player points
3. What attributes/methods are available on roster and player objects
"""
import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print('=' * 80)

def explore_object(obj, name, max_depth=2, current_depth=0):
    """Recursively explore an object's attributes."""
    if current_depth >= max_depth:
        return

    indent = "  " * current_depth
    print(f"{indent}{name} (type: {type(obj).__name__})")

    # Get non-private attributes
    attrs = [a for a in dir(obj) if not a.startswith('_')]

    if attrs and current_depth < max_depth - 1:
        for attr in attrs[:15]:  # Limit to first 15 to avoid spam
            try:
                value = getattr(obj, attr)
                if callable(value):
                    print(f"{indent}  - {attr}() [method]")
                elif isinstance(value, (str, int, float, bool)):
                    print(f"{indent}  - {attr}: {value}")
                elif isinstance(value, (list, tuple)) and len(value) > 0:
                    print(f"{indent}  - {attr}: [{type(value[0]).__name__} x {len(value)}]")
                else:
                    print(f"{indent}  - {attr}: {type(value).__name__}")
            except Exception as e:
                print(f"{indent}  - {attr}: Error accessing - {e}")

def test_weekly_data(year=2023, week_num=1):
    """Test weekly data extraction from Yahoo API."""

    # Check for required env variables
    client_id = os.getenv('YAHOO_CLIENT_ID')
    client_secret = os.getenv('YAHOO_CLIENT_SECRET')
    refresh_token = os.getenv('YAHOO_REFRESH_TOKEN')

    if not client_id or not client_secret:
        print("\n❌ ERROR: Missing Yahoo API credentials in .env file")
        print("\nPlease create a .env file with:")
        print("  YAHOO_CLIENT_ID=your_client_id")
        print("  YAHOO_CLIENT_SECRET=your_client_secret")
        print("  YAHOO_REFRESH_TOKEN=your_refresh_token (optional - will prompt for OAuth)")
        print("  YAHOO_LEAGUE_ID=your_league_id")
        return

    try:
        from yahoofantasy import Context
    except ImportError:
        print("\n❌ ERROR: yahoofantasy library not installed")
        print("Run: pip install yahoofantasy")
        return

    print_section(f"Testing Yahoo Fantasy API - {year} Week {week_num}")

    # Create context
    print("\n📡 Authenticating with Yahoo API...")
    try:
        ctx = Context(
            persist_key='yahoo_fantasy',
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("\nIf refresh token is invalid, you may need to re-authenticate:")
        print("Run: yahoofantasy login")
        return

    # Get league
    print(f"\n📋 Fetching leagues for {year}...")
    try:
        leagues = ctx.get_leagues('nfl', year)
        if not leagues:
            print(f"❌ No leagues found for {year}")
            return

        league = leagues[0]
        print(f"✅ Found league: {league.name}")
        print(f"   League ID: {getattr(league, 'league_id', 'N/A')}")
        print(f"   League Key: {getattr(league, 'league_key', 'N/A')}")
    except Exception as e:
        print(f"❌ Error fetching leagues: {e}")
        import traceback
        traceback.print_exc()
        return

    # Get weeks
    print_section("Exploring Week Structure")
    try:
        weeks = league.weeks()
        print(f"✅ Found {len(weeks)} weeks")

        # Find the requested week
        target_week = None
        for w in weeks:
            wnum = getattr(w, 'week_num', getattr(w, 'week', 0))
            if wnum == week_num:
                target_week = w
                break

        if not target_week:
            print(f"❌ Week {week_num} not found")
            return

        print(f"✅ Found week {week_num}")
        explore_object(target_week, "Week object", max_depth=2)

    except Exception as e:
        print(f"❌ Error fetching weeks: {e}")
        import traceback
        traceback.print_exc()
        return

    # Get matchups
    print_section("Exploring Matchup Structure")
    try:
        matchups = target_week.matchups
        print(f"✅ Found {len(matchups)} matchups for week {week_num}")

        if not matchups:
            print("❌ No matchups found")
            return

        # Analyze first matchup in detail
        matchup = matchups[0]
        print(f"\n🔍 Analyzing first matchup...")
        explore_object(matchup, "Matchup object", max_depth=2)

        # Try to get teams
        team1 = getattr(matchup, 'team1', None)
        team2 = getattr(matchup, 'team2', None)

        if team1 and team2:
            print(f"\n✅ Teams found:")
            print(f"   Team 1: {getattr(team1, 'name', 'N/A')}")
            print(f"   Team 2: {getattr(team2, 'name', 'N/A')}")

        # Try to extract weekly team points (from WEEKLY_DATA_FIXED.md approach)
        print_section("Testing Weekly Team Points Extraction")

        # Method 1: Check matchup.teams.team structure (from Yahoo API docs)
        if hasattr(matchup, 'teams'):
            print("✅ matchup.teams exists")
            teams_obj = getattr(matchup, 'teams')
            explore_object(teams_obj, "matchup.teams", max_depth=2)

            if hasattr(teams_obj, 'team'):
                team_list = getattr(teams_obj, 'team')
                if not isinstance(team_list, list):
                    team_list = [team_list]

                print(f"\n✅ Found {len(team_list)} teams in matchup.teams.team")

                for i, team_obj in enumerate(team_list[:2]):
                    print(f"\n   Team {i+1}:")
                    if hasattr(team_obj, 'team_points'):
                        team_points = getattr(team_obj, 'team_points')
                        print(f"      ✅ team_points exists")
                        explore_object(team_points, f"Team {i+1} team_points", max_depth=2)

                        # Try to get total
                        if hasattr(team_points, 'total'):
                            total = getattr(team_points, 'total')
                            print(f"      🎯 WEEKLY POINTS: {total}")
                    else:
                        print(f"      ❌ No team_points attribute")
        else:
            print("❌ matchup.teams does not exist")

    except Exception as e:
        print(f"❌ Error exploring matchups: {e}")
        import traceback
        traceback.print_exc()

    # Test roster and player data
    print_section("Exploring Weekly Roster & Player Data")
    try:
        # Get roster from team in matchup
        if team1:
            print(f"\n🔍 Getting roster for {getattr(team1, 'name', 'Team 1')}...")
            roster = team1.roster()

            print(f"✅ Roster retrieved")
            explore_object(roster, "Roster object", max_depth=2)

            if hasattr(roster, 'players'):
                players = roster.players
                print(f"\n✅ Found {len(players)} players in roster")

                if players:
                    # Analyze first player in detail
                    player = players[0]
                    player_name = getattr(getattr(player, 'name', None), 'full', 'Unknown') if hasattr(player, 'name') else 'Unknown'
                    print(f"\n🔍 Analyzing player: {player_name}")
                    explore_object(player, "Player object", max_depth=2)

                    # Test different methods to get player points
                    print_section("Testing Methods to Get Player Weekly Points")

                    # Method 1: Check for points attribute
                    if hasattr(player, 'points'):
                        points = getattr(player, 'points')
                        print(f"✅ player.points: {points}")
                    else:
                        print("❌ player.points does not exist")

                    # Method 2: Check for player_points attribute
                    if hasattr(player, 'player_points'):
                        player_points = getattr(player, 'player_points')
                        print(f"✅ player.player_points exists")
                        explore_object(player_points, "player.player_points", max_depth=2)
                    else:
                        print("❌ player.player_points does not exist")

                    # Method 3: Try get_points() method
                    if hasattr(player, 'get_points'):
                        try:
                            points = player.get_points()
                            print(f"✅ player.get_points(): {points}")
                            print(f"   Type: {type(points)}")
                            if hasattr(points, '__dict__'):
                                print(f"   Attributes: {points.__dict__}")
                        except Exception as e:
                            print(f"❌ player.get_points() error: {e}")
                    else:
                        print("❌ player.get_points() method does not exist")

                    # Method 4: Try get_stats() method
                    if hasattr(player, 'get_stats'):
                        try:
                            stats = player.get_stats()
                            print(f"✅ player.get_stats(): {type(stats)}")
                            explore_object(stats, "player.get_stats() result", max_depth=2)
                        except Exception as e:
                            print(f"❌ player.get_stats() error: {e}")
                    else:
                        print("❌ player.get_stats() method does not exist")

                    # Method 5: Check selected_position (roster slot)
                    if hasattr(player, 'selected_position'):
                        selected_pos = getattr(player, 'selected_position')
                        print(f"✅ player.selected_position: {selected_pos}")
                        if hasattr(selected_pos, 'position'):
                            roster_slot = getattr(selected_pos, 'position')
                            print(f"   Roster slot: {roster_slot}")
                            started = roster_slot not in ['BN', 'IR']
                            print(f"   Started: {started}")

                    # Check if roster has week context
                    print(f"\n📅 Roster context:")
                    if hasattr(roster, 'week'):
                        print(f"   ✅ roster.week: {getattr(roster, 'week')}")
                    if hasattr(roster, 'week_num'):
                        print(f"   ✅ roster.week_num: {getattr(roster, 'week_num')}")
                    if hasattr(roster, 'coverage_type'):
                        print(f"   ✅ roster.coverage_type: {getattr(roster, 'coverage_type')}")

    except Exception as e:
        print(f"❌ Error exploring roster/player data: {e}")
        import traceback
        traceback.print_exc()

    print_section("Summary & Recommendations")
    print("""
Based on the test results above:

1. ✅ If matchup.teams.team[].team_points.total exists:
   → Weekly team totals ARE available!
   → Your yahoo_client.py code should already work

2. For weekly player points, check above:
   → If player.get_points() showed different values from season totals:
      ✓ Use player.get_points() in weekly roster context

   → If player.player_points exists with weekly context:
      ✓ Extract from player.player_points.total

   → If both return season totals:
      ✗ May need direct API calls or cumulative calculation

3. Next steps:
   - Review the output above
   - Identify which method provides weekly player points
   - Update yahoo_client.py accordingly
    """)

if __name__ == '__main__':
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2023
    week = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    test_weekly_data(year, week)
