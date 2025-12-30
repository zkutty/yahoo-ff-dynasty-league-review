"""Debug script to check ALL players for a team to see if we're missing started players"""
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
team_key_to_check = '449.l.666007.t.1'  # The team with the biggest mismatch

# Also load our saved data to see what we recorded
with open('data/league_data/season_2024.json') as f:
    saved_data = json.load(f)

our_players = [p for p in saved_data['weekly_player_points']
               if p['team_key'] == team_key_to_check and p['week'] == week_num]

print(f"Checking team {team_key_to_check} - Week {week_num}")
print("="*80)

league = client.get_league(year=year)
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
        roster.fetch_player_stats()

        print(f"Team: {target_team.name}")
        print(f"Total players in roster: {len(roster.players)}\n")

        print("ALL PLAYERS WITH ROSTER POSITIONS:")
        print("-"*100)
        print(f"{'Player Name':30} {'Pos':3} {'Slot':10} {'Started?':8} {'Points':7} {'In Our Data?':12}")
        print("-"*100)

        total_started_sum = 0
        for player in roster.players:
            player_name = player.name.full if hasattr(player.name, 'full') else 'Unknown'
            player_id = player.player_id
            position = getattr(player, 'primary_position', '???')

            # Get roster slot
            selected_pos = getattr(player, 'selected_position', None)
            roster_slot = ''
            if selected_pos:
                if isinstance(selected_pos, dict):
                    roster_slot = selected_pos.get('position', 'NONE')
                elif hasattr(selected_pos, 'position'):
                    roster_slot = getattr(selected_pos, 'position', 'NONE')
                else:
                    roster_slot = str(selected_pos)

            # Check if we consider it started
            started = roster_slot not in ['BN', 'IR', ''] if roster_slot else False

            # Get points
            try:
                points = float(player.get_points(week_num) or 0.0)
            except:
                points = 0.0

            if started:
                total_started_sum += points

            # Check if in our saved data
            in_our_data = any(p['player_id'] == player_id for p in our_players)
            our_started = next((p['started'] for p in our_players if p['player_id'] == player_id), None)
            our_points = next((p['weekly_points'] for p in our_players if p['player_id'] == player_id), None)

            print(f"{player_name:30} {position:3} {roster_slot:10} {str(started):8} {points:7.2f} " +
                  f"{'YES' if in_our_data else 'NO':12} " +
                  (f"(start={our_started}, pts={our_points:.1f})" if in_our_data else ""))

        print("-"*100)
        print(f"Total started sum (API): {total_started_sum:.2f}")
        print(f"Total started sum (our data): {sum(p['weekly_points'] for p in our_players if p['started']):.2f}")

        # Check matchup team total
        matchup_data = saved_data['matchups']
        matchup_record = next((m for m in matchup_data
                              if (m['team1_key'] == team_key_to_check or m['team2_key'] == team_key_to_check)
                              and m['week'] == week_num), None)
        if matchup_record:
            team_total = matchup_record['team1_points'] if matchup_record['team1_key'] == team_key_to_check else matchup_record['team2_points']
            print(f"Team total (from matchup data): {team_total:.2f}")
            print(f"Difference: {team_total - total_started_sum:.2f}")
