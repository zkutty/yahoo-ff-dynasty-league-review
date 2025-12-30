"""Check if roster positions are historical or current"""
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

year = 2024
week_num = 1
team_key = '449.l.666007.t.10'

league = client.get_league(year=year)
weeks = league.weeks()
week_obj = next((w for w in weeks if w.week_num == week_num), None)

if week_obj:
    matchups = week_obj.matchups if hasattr(week_obj, 'matchups') and not callable(week_obj.matchups) else week_obj.matchups()

    # Find team
    target_team = None
    for matchup in matchups:
        for team in [matchup.team1, matchup.team2]:
            if team.team_key == team_key:
                target_team = team
                break
        if target_team:
            break

    if target_team:
        roster = target_team.roster()
        roster.fetch_player_stats()

        print(f"Team: {target_team.name} - Week {week_num}")
        print("="*100)
        print("Checking Allen Lazard and Alexander Mattison roster positions:")
        print("-"*100)

        for player in roster.players:
            name = player.name.full if hasattr(player.name, 'full') else 'Unknown'

            if 'Lazard' in name or 'Mattison' in name:
                # Get position
                selected_pos = getattr(player, 'selected_position', None)
                if selected_pos:
                    if hasattr(selected_pos, 'coverage_type'):
                        print(f"\n{name}:")
                        print(f"  selected_position type: {type(selected_pos)}")
                        print(f"  selected_position: {selected_pos}")

                        # Check if it has week info
                        if hasattr(selected_pos, 'week'):
                            print(f"  Week: {selected_pos.week}")
                        if hasattr(selected_pos, 'position'):
                            print(f"  Position: {selected_pos.position}")
                        if hasattr(selected_pos, 'date'):
                            print(f"  Date: {selected_pos.date}")

                        # Try to access as dict
                        if isinstance(selected_pos, dict):
                            print(f"  As dict: {selected_pos}")
                    else:
                        if isinstance(selected_pos, dict):
                            print(f"\n{name}:")
                            print(f"  selected_position (dict): {selected_pos}")
                        else:
                            print(f"\n{name}:")
                            print(f"  selected_position.position: {getattr(selected_pos, 'position', 'N/A')}")

                # Get points
                try:
                    points = player.get_points(week_num)
                    print(f"  Week {week_num} points: {points}")
                except Exception as e:
                    print(f"  Error getting points: {e}")

print("\nAlso checking our saved data to compare:")
with open('data/league_data/season_2024.json') as f:
    data = json.load(f)

players = [p for p in data['weekly_player_points']
           if p['team_key'] == team_key and p['week'] == week_num
           and ('Lazard' in p['player_name'] or 'Mattison' in p['player_name'])]

for p in players:
    print(f"\n{p['player_name']}:")
    print(f"  Roster slot: {p['roster_slot']}")
    print(f"  Started: {p['started']}")
    print(f"  Weekly points: {p['weekly_points']}")
