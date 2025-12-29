"""Investigate 2024 data structure for points."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

# Load 2024 data
with open(Path(config.DATA_DIR) / "league_data" / "season_2024.json") as f:
    data = json.load(f)

print("=== 2024 DATA STRUCTURE ===\n")

# Check teams and rosters
teams = data.get("teams", [])
print(f"Number of teams: {len(teams)}")
if teams:
    print(f"\nSample team structure:")
    team = teams[0]
    print(f"  Team name: {team.get('name')}")
    print(f"  Manager: {team.get('manager')}")
    roster = team.get("roster", [])
    print(f"  Roster size: {len(roster)}")
    if roster:
        player = roster[0]
        print(f"\n  Sample player:")
        print(f"    Name: {player.get('name')}")
        print(f"    Position: {player.get('position')}")
        print(f"    Fantasy points: {player.get('fantasy_points_total')}")
        print(f"    Player keys: {list(player.keys())}")

# Check weekly rosters
weekly_rosters = data.get("weekly_rosters", [])
print(f"\n\nWeekly rosters entries: {len(weekly_rosters)}")
if weekly_rosters:
    # Find entry with non-zero points
    non_zero = [w for w in weekly_rosters if w.get('points', 0) > 0]
    print(f"Entries with non-zero points: {len(non_zero)}")

    print(f"\nSample weekly roster entry:")
    sample = weekly_rosters[0]
    for k, v in sample.items():
        print(f"  {k}: {v}")

    if non_zero:
        print(f"\nSample NON-ZERO weekly roster entry:")
        for k, v in non_zero[0].items():
            print(f"  {k}: {v}")

# Check matchups
matchups = data.get("matchups", [])
print(f"\n\nMatchups: {len(matchups)}")
if matchups:
    print(f"\nSample matchup keys: {list(matchups[0].keys())}")

# Check transactions for trades
transactions = data.get("transactions", [])
trades = [t for t in transactions if "trade" in t.get("type", "").lower()]
print(f"\n\nTotal transactions: {len(transactions)}")
print(f"Trade transactions: {len(trades)}")
if trades:
    print(f"\nSample trade structure:")
    trade = trades[0]
    print(f"  Transaction ID: {trade.get('transaction_id')}")
    print(f"  Type: {trade.get('type')}")
    print(f"  Players involved: {len(trade.get('involved_players', []))}")
    for player in trade.get('involved_players', []):
        print(f"    - {player.get('player_name')}: from={player.get('from_team_key')} to={player.get('to_team_key')}")
