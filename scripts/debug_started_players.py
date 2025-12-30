"""Debug script to check all started players for a team"""
import sys
sys.path.insert(0, '/Users/zbkutlow/yahoo-ff-dynasty-league-review')

from yahoo_client import YahooFantasyClient
import config

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
team_key_to_check = '449.l.666007.t.1'  # The team with the biggest mismatch

league = client.get_league(year=year)

print(f"Checking team {team_key_to_check} - Week {week_num}")
print("="*80)

weeks = league.weeks()
week_obj = next((w for w in weeks if w.week_num == week_num), None)

if week_obj:
    matchups = week_obj.matchups if hasattr(week_obj, 'matchups') and not callable(week_obj.matchups) else week_obj.matchups()

    # Find the team
    target_team = None
    for matchup in matchups:
        for team in [matchup.team1, matchup.team2]:
            if team.team_key == team_key_to_check:
                target_team = team
                break
        if target_team:
            break

    if target_team:
        roster = target_team.roster()

        # Call fetch_player_stats
        roster.fetch_player_stats()

        print(f"Team: {target_team.name}")
        print(f"Total players: {len(roster.players)}\n")

        started_sum = 0
        print("STARTED PLAYERS:")
        print("-"*80)

        for player in roster.players:
            # Check if started
            selected_pos = getattr(player, 'selected_position', None)
            roster_slot = ''
            if selected_pos:
                if isinstance(selected_pos, dict):
                    roster_slot = selected_pos.get('position', '')
                else:
                    roster_slot = getattr(selected_pos, 'position', '')

            started = roster_slot not in ['BN', 'IR', ''] if roster_slot else False

            if started:
                player_name = player.name.full if hasattr(player.name, 'full') else 'Unknown'
                position = getattr(player, 'primary_position', '???')

                # Get points using the method in our code
                try:
                    points = player.get_points(week_num)
                    if points is None:
                        points = 0.0
                    else:
                        points = float(points)
                except Exception as e:
                    points = 0.0

                started_sum += points
                print(f"  {player_name:30} {position:3} {roster_slot:4} {points:7.2f}")

        print("-"*80)
        print(f"Started players sum: {started_sum:.2f}")

        # Get team total from matchup
        for matchup in matchups:
            if matchup.team1.team_key == team_key_to_check:
                team_total = matchup.team1_points
                break
            elif matchup.team2.team_key == team_key_to_check:
                team_total = matchup.team2_points
                break

        print(f"Team total (matchup): {team_total:.2f}")
        print(f"Difference: {team_total - started_sum:.2f}")
