"""Validate weekly player points data to ensure accuracy.

This script checks:
1. Are all players on a roster getting the same points? (BUG: team total instead of individual)
2. Do individual player points sum to team total?
3. Are cumulative points increasing week-over-week?
"""
import json
from pathlib import Path
from collections import defaultdict

data_path = Path("data/league_data/season_2024.json")
with open(data_path) as f:
    data = json.load(f)

wpp = data.get('weekly_player_points', [])
matchups = data.get('matchups', [])

print("="*80)
print("WEEKLY PLAYER POINTS VALIDATION")
print("="*80)

# Check 1: Do all players on a team have the same weekly points?
print("\n1. CHECKING FOR DUPLICATE POINTS (all players having same value)...")
print("-"*80)

issues_found = []

# Group by team and week
team_week_players = defaultdict(list)
for record in wpp:
    key = (record['team_key'], record['week'])
    team_week_players[key].append(record)

# Check if all players have the same points
duplicate_issues = []
for (team_key, week), players in team_week_players.items():
    # Get unique weekly_points values (ignoring 0)
    points_values = set(p['weekly_points'] for p in players if p['weekly_points'] > 0)

    # If all non-zero players have the exact same points, that's suspicious
    if len(points_values) == 1 and len([p for p in players if p['weekly_points'] > 0]) > 1:
        duplicate_issues.append({
            'team_key': team_key,
            'week': week,
            'num_players': len([p for p in players if p['weekly_points'] > 0]),
            'all_have_points': list(points_values)[0]
        })

if duplicate_issues:
    print(f"\n⚠️  FOUND {len(duplicate_issues)} ISSUES - Players on same team have identical points!")
    print("\nSample issues:")
    for issue in duplicate_issues[:5]:
        print(f"  Week {issue['week']}, Team {issue['team_key']}")
        print(f"    {issue['num_players']} players all have {issue['all_have_points']:.1f} points")

        # Show the actual players
        players = team_week_players[(issue['team_key'], issue['week'])]
        non_zero = [p for p in players if p['weekly_points'] > 0][:3]
        for p in non_zero:
            print(f"      - {p['player_name']}: {p['weekly_points']:.1f} pts")
else:
    print("✓ No duplicate point issues found")

# Check 2: Compare individual points to team totals from matchups
print("\n2. COMPARING PLAYER POINTS SUM TO TEAM TOTALS...")
print("-"*80)

# Create matchup lookup
matchup_totals = {}
for m in matchups:
    matchup_totals[(m['team1_key'], m['week'])] = m['team1_points']
    matchup_totals[(m['team2_key'], m['week'])] = m['team2_points']

sum_vs_total_issues = []
for (team_key, week), players in team_week_players.items():
    # Sum weekly points for started players only
    started_sum = sum(p['weekly_points'] for p in players if p['started'])

    # Get team total from matchup
    team_total = matchup_totals.get((team_key, week))

    if team_total:
        diff = abs(started_sum - team_total)
        if diff > 0.1:  # Allow for small rounding errors
            sum_vs_total_issues.append({
                'team_key': team_key,
                'week': week,
                'started_sum': started_sum,
                'team_total': team_total,
                'diff': diff
            })

if sum_vs_total_issues:
    print(f"\n⚠️  FOUND {len(sum_vs_total_issues)} MISMATCHES between player sum and team total")
    print("\nSample mismatches:")
    for issue in sum_vs_total_issues[:5]:
        print(f"  Week {issue['week']}, Team {issue['team_key']}")
        print(f"    Started players sum: {issue['started_sum']:.2f}")
        print(f"    Team total (matchup): {issue['team_total']:.2f}")
        print(f"    Difference: {issue['diff']:.2f}")
else:
    print("✓ Player point sums match team totals")

# Check 3: Verify cumulative points are increasing (or staying same for inactive players)
print("\n3. CHECKING CUMULATIVE POINTS PROGRESSION...")
print("-"*80)

cumulative_issues = []
player_weeks = defaultdict(list)
for record in wpp:
    player_weeks[record['player_id']].append(record)

for player_id, weeks in player_weeks.items():
    sorted_weeks = sorted(weeks, key=lambda x: x['week'])

    for i in range(1, len(sorted_weeks)):
        prev = sorted_weeks[i-1]
        curr = sorted_weeks[i]

        # Cumulative should never decrease
        if curr['cumulative_points'] < prev['cumulative_points']:
            cumulative_issues.append({
                'player_name': curr['player_name'],
                'week': curr['week'],
                'prev_cumulative': prev['cumulative_points'],
                'curr_cumulative': curr['cumulative_points']
            })

if cumulative_issues:
    print(f"\n⚠️  FOUND {len(cumulative_issues)} ISSUES - Cumulative points decreased!")
    print("\nSample issues:")
    for issue in cumulative_issues[:5]:
        print(f"  {issue['player_name']} - Week {issue['week']}")
        print(f"    Previous week cumulative: {issue['prev_cumulative']:.1f}")
        print(f"    Current week cumulative: {issue['curr_cumulative']:.1f}")
else:
    print("✓ Cumulative points are monotonically increasing")

# Check 4: Look at actual weekly point values - are they realistic?
print("\n4. CHECKING FOR UNREALISTIC WEEKLY POINT VALUES...")
print("-"*80)

high_scorers = sorted([r for r in wpp if r['weekly_points'] > 0],
                      key=lambda x: x['weekly_points'], reverse=True)[:10]

print("\nTop 10 highest weekly scores:")
for r in high_scorers:
    print(f"  Week {r['week']}: {r['player_name']:20} {r['weekly_points']:7.1f} pts ({r['position']})")

if high_scorers[0]['weekly_points'] > 100:
    print("\n⚠️  WARNING: Top weekly score is unrealistically high!")
    print("    This suggests players may be getting season totals instead of weekly points")
else:
    print("\n✓ Weekly point values appear realistic")

# Summary
print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)

total_issues = len(duplicate_issues) + len(sum_vs_total_issues) + len(cumulative_issues)

if total_issues == 0 and high_scorers[0]['weekly_points'] <= 100:
    print("✓ All validation checks passed!")
    print("  Weekly player points data appears to be correct.")
else:
    print(f"⚠️  Found {total_issues} data quality issues")
    if duplicate_issues:
        print(f"  - {len(duplicate_issues)} teams where all players have identical points")
    if sum_vs_total_issues:
        print(f"  - {len(sum_vs_total_issues)} mismatches between player sum and team total")
    if cumulative_issues:
        print(f"  - {len(cumulative_issues)} cases where cumulative points decreased")
    if high_scorers[0]['weekly_points'] > 100:
        print(f"  - Unrealistically high weekly scores (max: {high_scorers[0]['weekly_points']:.1f})")

    print("\n💡 LIKELY ROOT CAUSE:")
    print("  The _get_player_cumulative_points() method may be returning season totals")
    print("  instead of cumulative-through-week totals, causing incorrect weekly calculations.")
