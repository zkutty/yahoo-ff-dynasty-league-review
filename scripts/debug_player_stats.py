"""Debug script to investigate player stats after roster.fetch_player_stats()"""
import sys
sys.path.insert(0, '/Users/zbkutlow/yahoo-ff-dynasty-league-review')

from yahoo_client import YahooFantasyClient
import config
import json

# Initialize client
client = YahooFantasyClient(
    client_id=config.YAHOO_CLIENT_ID,
    client_secret=config.YAHOO_CLIENT_SECRET,
    league_id=config.YAHOO_LEAGUE_ID,
    refresh_token=config.YAHOO_REFRESH_TOKEN
)

# Get league and fetch week 1
year = 2024
week_num = 1
league = client.get_league(year=year)

print(f"Fetching week {week_num} rosters...")
weeks = league.weeks()
week_obj = next((w for w in weeks if w.week_num == week_num), None)

if week_obj:
    matchups = week_obj.matchups if hasattr(week_obj, 'matchups') and not callable(week_obj.matchups) else week_obj.matchups()

    # Get first matchup, first team
    if matchups:
        matchup = matchups[0]
        team = matchup.team1
        team_key = team.team_key

        print(f"\nTeam: {team.name} ({team_key})")

        # Get roster
        roster = team.roster()
        print(f"Roster has {len(roster.players)} players")

        # Call fetch_player_stats()
        print(f"\nCalling roster.fetch_player_stats()...")
        try:
            roster.fetch_player_stats()
            print("✓ fetch_player_stats() succeeded")
        except Exception as e:
            print(f"✗ fetch_player_stats() failed: {e}")

        # Inspect first 3 players
        for i, player in enumerate(roster.players[:3]):
            print(f"\n{'='*60}")
            print(f"Player {i+1}: {player.name.full if hasattr(player.name, 'full') else 'Unknown'}")
            print(f"Player ID: {player.player_id}")
            print(f"Position: {getattr(player, 'primary_position', 'Unknown')}")

            # Check what attributes the player has
            print(f"\nPlayer attributes:")
            attrs = [a for a in dir(player) if not a.startswith('_')]
            for attr in ['player_points', 'player_stats', 'get_points', 'selected_position']:
                if attr in attrs:
                    print(f"  ✓ has {attr}")

            # Try to get points various ways
            print(f"\nTrying to extract points:")

            # Method 1: player_points
            if hasattr(player, 'player_points'):
                pp = player.player_points
                print(f"  player.player_points type: {type(pp)}")
                print(f"  player.player_points: {pp}")
                if hasattr(pp, 'total'):
                    print(f"  player.player_points.total: {pp.total}")
                if hasattr(pp, 'coverage_type'):
                    print(f"  player.player_points.coverage_type: {pp.coverage_type}")
                if hasattr(pp, 'week'):
                    print(f"  player.player_points.week: {pp.week}")

            # Method 2: get_points() without week
            try:
                points_no_week = player.get_points()
                print(f"  player.get_points(): {points_no_week}")
            except Exception as e:
                print(f"  player.get_points() failed: {e}")

            # Method 3: get_points(week_num)
            try:
                points_with_week = player.get_points(week_num)
                print(f"  player.get_points({week_num}): {points_with_week}")
            except Exception as e:
                print(f"  player.get_points({week_num}) failed: {e}")

            # Check _stats_cache
            if hasattr(player, '_stats_cache'):
                print(f"  player._stats_cache keys: {list(player._stats_cache.keys())}")
                if week_num in player._stats_cache:
                    cached = player._stats_cache[week_num]
                    print(f"  player._stats_cache[{week_num}] exists!")
                    if 'player_points' in cached:
                        print(f"  cached player_points: {cached['player_points']}")

print("\nDone!")
