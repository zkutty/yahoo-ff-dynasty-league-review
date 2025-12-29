"""Check what weekly player points data was fetched."""
import json
from pathlib import Path

data_path = Path("data/league_data/season_2024.json")
with open(data_path) as f:
    data = json.load(f)

print("="*60)
print("2024 DATA CHECK")
print("="*60)

print(f"\nData keys: {list(data.keys())}")

wpp = data.get('weekly_player_points', [])
print(f"\nWeekly player points records: {len(wpp)}")

if wpp:
    weeks = sorted(set(w['week'] for w in wpp))
    print(f"Weeks covered: {weeks}")
    print(f"Number of weeks: {len(weeks)}")

    # Count records per week
    from collections import Counter
    week_counts = Counter(w['week'] for w in wpp)
    print(f"\nRecords per week:")
    for week in sorted(week_counts.keys()):
        print(f"  Week {week}: {week_counts[week]} player-records")

    # Show sample record
    print(f"\nSample record (first with points > 0):")
    sample = next((w for w in wpp if w.get('weekly_points', 0) > 0), wpp[0])
    for k, v in sample.items():
        print(f"  {k}: {v}")
else:
    print("No weekly player points data found!")

# Check weekly rosters
wr = data.get('weekly_rosters', [])
print(f"\nWeekly rosters records: {len(wr)}")
if wr:
    non_zero = [w for w in wr if w.get('points', 0) > 0]
    print(f"Records with non-zero points: {len(non_zero)}")
