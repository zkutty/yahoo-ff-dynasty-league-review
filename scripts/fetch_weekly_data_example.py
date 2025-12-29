"""Example script to fetch weekly matchup and roster data from Yahoo API.

This script demonstrates how to extract weekly points and rosters.
Run this to test and understand the API structure before implementing in yahoo_client.py.
"""
import os
from dotenv import load_dotenv
from yahoofantasy import Context
import json

load_dotenv()

def fetch_weekly_data_example(year=2023, week_num=1):
    """Fetch weekly matchup and roster data for testing."""
    
    ctx = Context(
        persist_key='yahoo_fantasy',
        client_id=os.getenv('YAHOO_CLIENT_ID'),
        client_secret=os.getenv('YAHOO_CLIENT_SECRET'),
        refresh_token=os.getenv('YAHOO_REFRESH_TOKEN')
    )
    
    # Get league
    leagues = ctx.get_leagues('nfl', year)
    if not leagues:
        print(f"No leagues found for {year}")
        return
    
    league = leagues[0]
    print(f"League: {league.name}")
    
    # Get week
    weeks = league.weeks()
    week = [w for w in weeks if getattr(w, 'week_num', 0) == week_num]
    
    if not week:
        print(f"Week {week_num} not found")
        return
    
    week = week[0]
    print(f"Week {week_num}")
    
    # Get matchups
    matchups = week.matchups
    print(f"Found {len(matchups)} matchups")
    
    # Process first matchup as example
    if matchups:
        matchup = matchups[0]
        print(f"\n=== Matchup Example ===")
        print(f"Team1: {matchup.team1.name}")
        print(f"Team2: {matchup.team2.name}")
        
        # Try to get team points
        team1 = matchup.team1
        team2 = matchup.team2
        
        # Method 1: Try to get roster and sum points
        print(f"\n--- Team1 Roster ---")
        try:
            roster = team1.roster()
            print(f"Roster has {len(roster.players)} players")
            
            total_points = 0.0
            started_players = []
            
            for player in roster.players:
                player_id = getattr(player, 'player_id', '')
                player_name = getattr(getattr(player, 'name', None), 'full', '') if hasattr(player, 'name') else ''
                position = getattr(player, 'primary_position', '')
                
                # Get roster slot
                selected_pos = getattr(player, 'selected_position', None)
                if selected_pos:
                    if isinstance(selected_pos, dict):
                        roster_slot = selected_pos.get('position', '')
                    else:
                        roster_slot = getattr(selected_pos, 'position', '')
                else:
                    roster_slot = ''
                
                started = roster_slot not in ['BN', 'IR', '']
                
                # Try to get weekly points
                weekly_points = 0.0
                try:
                    # NOTE: This is the key - need to find how to get weekly points
                    # Options:
                    # 1. player.get_points() - but this might be season total
                    # 2. player.get_stats() with week parameter
                    # 3. Points might be in roster object itself
                    
                    # Check if player has points attribute
                    if hasattr(player, 'points'):
                        pts = getattr(player, 'points')
                        print(f"  Player {player_name} has points attribute: {pts}")
                    
                    # Try get_stats method
                    if hasattr(player, 'get_stats'):
                        try:
                            stats = player.get_stats()
                            print(f"  Player {player_name} get_stats(): {type(stats)}")
                            print(f"    Stats: {str(stats)[:200]}")
                        except Exception as e:
                            print(f"  Player {player_name} get_stats() error: {e}")
                    
                except Exception as e:
                    print(f"  Error getting points for {player_name}: {e}")
                
                if started:
                    started_players.append({
                        'name': player_name,
                        'position': position,
                        'roster_slot': roster_slot,
                        'points': weekly_points
                    })
            
            print(f"\nStarted players ({len(started_players)}):")
            for p in started_players[:5]:  # Show first 5
                print(f"  {p['name']} ({p['position']}) - {p['roster_slot']}: {p['points']} pts")
            
            print(f"\nTotal team points (sum of started): {total_points}")
            
        except Exception as e:
            print(f"Error getting roster: {e}")
            import traceback
            traceback.print_exc()
        
        # Method 2: Try alternative ways to get team points
        print(f"\n--- Alternative Methods ---")
        print("Note: team1_stats requires additional API calls and may raise error")
        print("Need to find the correct method to get weekly team totals")


if __name__ == '__main__':
    import sys
    
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2023
    week = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    print(f"Fetching weekly data for {year}, week {week}")
    print("=" * 60)
    
    fetch_weekly_data_example(year, week)
    
    print("\n" + "=" * 60)
    print("\nNext Steps:")
    print("1. Identify how to get weekly player points (key blocker)")
    print("2. Once identified, update yahoo_client.py to fetch weekly data")
    print("3. Re-run: python main.py --refresh")
    print("4. Run analysis: python -m analysis --start <year> --end <year>")


