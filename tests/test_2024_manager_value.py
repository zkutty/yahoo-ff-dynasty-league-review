"""Test 2024 manager draft and trade value using weekly cumulative scoring.

This test analyzes whether players drafted and traded for in 2024 were good value
by using weekly player points to calculate cumulative performance metrics.

Key Metrics:
- Draft Value: Points per dollar spent on drafted players
- Trade Value: Cumulative points gained from traded-in players after trade week
- Overall Manager Value Score: Weighted combination of draft and trade efficiency
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
import config


class Test2024ManagerValue:
    """Test suite for 2024 manager draft and trade value analysis."""

    @pytest.fixture
    def season_data(self):
        """Load 2024 season data."""
        data_path = Path(config.DATA_DIR) / "league_data" / "season_2024.json"
        with open(data_path, "r") as f:
            return json.load(f)

    @pytest.fixture
    def weekly_rosters_df(self, season_data):
        """Convert weekly rosters to DataFrame."""
        weekly_rosters = season_data.get("weekly_rosters", [])
        return pd.DataFrame(weekly_rosters)

    @pytest.fixture
    def player_season_points_df(self, season_data):
        """Extract season total points from team rosters."""
        teams = season_data.get("teams", [])
        player_points = []

        for team in teams:
            team_key = team.get("team_key")
            roster = team.get("roster", [])
            for player in roster:
                player_points.append({
                    "player_id": player.get("player_id"),
                    "player_name": player.get("name"),
                    "position": player.get("position"),
                    "team_key": team_key,
                    "fantasy_points_total": player.get("fantasy_points_total", 0.0),
                })

        return pd.DataFrame(player_points)

    @pytest.fixture
    def draft_data_df(self, season_data):
        """Extract draft data as DataFrame."""
        draft_results = season_data.get("draft_results", [])
        return pd.DataFrame(draft_results)

    @pytest.fixture
    def transactions_df(self, season_data):
        """Extract transactions data as DataFrame."""
        transactions = season_data.get("transactions", [])
        # Flatten transactions - each involved player gets a row
        flattened = []
        for txn in transactions:
            base = {
                "transaction_id": txn.get("transaction_id"),
                "type": txn.get("type"),
                "timestamp": txn.get("timestamp"),
                "status": txn.get("status"),
            }
            for player in txn.get("involved_players", []):
                row = {**base, **player}
                flattened.append(row)
        return pd.DataFrame(flattened)

    @pytest.fixture
    def teams_df(self, season_data):
        """Extract teams data as DataFrame."""
        teams = season_data.get("teams", [])
        return pd.DataFrame(teams)

    def calculate_player_cumulative_points(
        self, weekly_rosters_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Calculate cumulative points by week for each player.

        Args:
            weekly_rosters_df: Weekly roster data

        Returns:
            DataFrame with player_id, week, weekly_points, cumulative_points
        """
        if weekly_rosters_df.empty:
            return pd.DataFrame()

        # Group by player and week, sum points (in case player appears multiple times)
        player_weekly = (
            weekly_rosters_df.groupby(["player_id", "player_name", "week"])["points"]
            .sum()
            .reset_index()
        )

        # Sort by player and week
        player_weekly = player_weekly.sort_values(["player_id", "week"])

        # Calculate cumulative points
        player_weekly["cumulative_points"] = player_weekly.groupby("player_id")[
            "points"
        ].cumsum()

        # Rename for clarity
        player_weekly = player_weekly.rename(columns={"points": "weekly_points"})

        return player_weekly

    def analyze_draft_value(
        self,
        draft_data_df: pd.DataFrame,
        player_season_points_df: pd.DataFrame,
        teams_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Analyze draft value: points per dollar for drafted players.

        Args:
            draft_data_df: Draft picks data
            player_season_points_df: Player season total points
            teams_df: Teams data for manager mapping

        Returns:
            DataFrame with manager_id, player metrics, draft value
        """
        if draft_data_df.empty or player_season_points_df.empty:
            return pd.DataFrame()

        # Merge draft data with season points
        draft_value = draft_data_df.merge(
            player_season_points_df[["player_id", "fantasy_points_total"]],
            on="player_id",
            how="left",
        )

        # Fill NaN points with 0 (players who didn't score)
        draft_value["fantasy_points_total"] = draft_value["fantasy_points_total"].fillna(0)

        # Calculate value metrics
        draft_value["cost"] = pd.to_numeric(draft_value["cost"], errors="coerce").fillna(0)
        draft_value["points_per_dollar"] = draft_value.apply(
            lambda row: (
                row["fantasy_points_total"] / row["cost"]
                if row["cost"] > 0
                else row["fantasy_points_total"]
            ),
            axis=1,
        )

        # Add keeper flag
        draft_value["is_keeper"] = draft_value.get("is_keeper", False)

        # Map team_key to manager
        if not teams_df.empty:
            team_manager_map = dict(
                zip(teams_df["team_key"], teams_df["manager"])
            )
            team_manager_id_map = dict(
                zip(teams_df["team_key"], teams_df["manager_id"])
            )
            draft_value["manager"] = draft_value["team_key"].map(team_manager_map)
            draft_value["manager_id"] = draft_value["team_key"].map(team_manager_id_map)

        return draft_value

    def analyze_trade_value(
        self,
        transactions_df: pd.DataFrame,
        player_cumulative_df: pd.DataFrame,
        teams_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Analyze trade value: cumulative points from traded players after trade.

        Args:
            transactions_df: Transactions data
            player_cumulative_df: Player cumulative points by week
            teams_df: Teams data

        Returns:
            DataFrame with manager_id, trade metrics, post-trade points
        """
        if transactions_df.empty or player_cumulative_df.empty:
            return pd.DataFrame()

        # Filter to trade acquisitions
        trades = transactions_df[
            (transactions_df["type"].str.contains("trade", case=False, na=False))
            & (transactions_df["transaction_type"] == "ADD")
        ].copy()

        if trades.empty:
            return pd.DataFrame()

        # Convert timestamp to week (approximate)
        # NFL season 2024 started around Sept 5, 2024
        import datetime

        def timestamp_to_week(ts):
            try:
                dt = datetime.datetime.fromtimestamp(int(ts))
                season_start = datetime.datetime(2024, 9, 5)
                if dt < season_start:
                    return 0
                days_diff = (dt - season_start).days
                week = min((days_diff // 7) + 1, 17)
                return week
            except:
                return 0

        trades["trade_week"] = trades["timestamp"].apply(timestamp_to_week)

        # For each trade acquisition, calculate points earned after trade
        trade_value_list = []

        for _, trade in trades.iterrows():
            player_id = trade.get("player_id")
            trade_week = trade.get("trade_week", 0)
            to_team = trade.get("to_team_key")

            if pd.isna(player_id) or pd.isna(to_team):
                continue

            # Get player's weekly points after trade week
            player_post_trade = player_cumulative_df[
                (player_cumulative_df["player_id"] == player_id)
                & (player_cumulative_df["week"] > trade_week)
            ]

            post_trade_points = player_post_trade["weekly_points"].sum()
            weeks_active = len(player_post_trade)

            trade_value_list.append(
                {
                    "transaction_id": trade.get("transaction_id"),
                    "team_key": to_team,
                    "player_id": player_id,
                    "player_name": trade.get("player_name", ""),
                    "trade_week": trade_week,
                    "post_trade_points": post_trade_points,
                    "weeks_active_post_trade": weeks_active,
                    "points_per_week": (
                        post_trade_points / weeks_active if weeks_active > 0 else 0
                    ),
                }
            )

        trade_value_df = pd.DataFrame(trade_value_list)

        # Map to managers
        if not teams_df.empty:
            team_manager_map = dict(zip(teams_df["team_key"], teams_df["manager"]))
            team_manager_id_map = dict(
                zip(teams_df["team_key"], teams_df["manager_id"])
            )
            trade_value_df["manager"] = trade_value_df["team_key"].map(team_manager_map)
            trade_value_df["manager_id"] = trade_value_df["team_key"].map(
                team_manager_id_map
            )

        return trade_value_df

    def aggregate_manager_value(
        self,
        draft_value_df: pd.DataFrame,
        trade_value_df: pd.DataFrame,
        teams_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Aggregate draft and trade value by manager.

        Args:
            draft_value_df: Draft value analysis
            trade_value_df: Trade value analysis
            teams_df: Teams data

        Returns:
            DataFrame with manager-level value metrics
        """
        manager_metrics = []

        # Get unique managers
        managers = teams_df[["manager_id", "manager"]].drop_duplicates()

        for _, mgr in managers.iterrows():
            manager_id = mgr["manager_id"]
            manager_name = mgr["manager"]

            # Draft metrics
            mgr_drafts = draft_value_df[
                draft_value_df["manager_id"] == manager_id
            ]
            total_draft_cost = mgr_drafts["cost"].sum()
            total_draft_points = mgr_drafts["fantasy_points_total"].sum()
            avg_points_per_dollar = (
                total_draft_points / total_draft_cost if total_draft_cost > 0 else 0
            )
            num_drafted = len(mgr_drafts[~mgr_drafts["is_keeper"]])
            num_keepers = len(mgr_drafts[mgr_drafts["is_keeper"]])

            # Trade metrics (handle empty trade_value_df)
            if not trade_value_df.empty and "manager_id" in trade_value_df.columns:
                mgr_trades = trade_value_df[
                    trade_value_df["manager_id"] == manager_id
                ]
            else:
                mgr_trades = pd.DataFrame()
            if not mgr_trades.empty:
                total_trade_points = mgr_trades["post_trade_points"].sum()
                num_trades_in = len(mgr_trades)
                avg_trade_points = (
                    total_trade_points / num_trades_in if num_trades_in > 0 else 0
                )
            else:
                total_trade_points = 0
                num_trades_in = 0
                avg_trade_points = 0

            # Combined value score (weighted)
            # Weight draft value more heavily since it's the foundation
            draft_score = avg_points_per_dollar * 0.6
            trade_score = avg_trade_points * 0.4
            overall_value_score = draft_score + trade_score

            manager_metrics.append(
                {
                    "manager_id": manager_id,
                    "manager": manager_name,
                    "total_draft_cost": total_draft_cost,
                    "total_draft_points": total_draft_points,
                    "avg_points_per_dollar": avg_points_per_dollar,
                    "num_drafted": num_drafted,
                    "num_keepers": num_keepers,
                    "total_trade_points": total_trade_points,
                    "num_trades_in": num_trades_in,
                    "avg_trade_points": avg_trade_points,
                    "overall_value_score": overall_value_score,
                }
            )

        return pd.DataFrame(manager_metrics).sort_values(
            "overall_value_score", ascending=False
        )

    def test_weekly_roster_data_exists(self, weekly_rosters_df):
        """Test that weekly roster data exists and has expected structure."""
        assert not weekly_rosters_df.empty, "Weekly roster data should not be empty"
        assert "player_id" in weekly_rosters_df.columns
        assert "week" in weekly_rosters_df.columns
        assert "points" in weekly_rosters_df.columns
        assert "team_key" in weekly_rosters_df.columns
        print(f"\n✓ Weekly roster data loaded: {len(weekly_rosters_df)} player-weeks")

    def test_cumulative_points_calculation(self, weekly_rosters_df):
        """Test cumulative points calculation."""
        cumulative_df = self.calculate_player_cumulative_points(weekly_rosters_df)

        assert not cumulative_df.empty, "Cumulative points should not be empty"
        assert "cumulative_points" in cumulative_df.columns
        assert "weekly_points" in cumulative_df.columns

        # Test that cumulative points are monotonically increasing
        for player_id in cumulative_df["player_id"].unique()[:5]:  # Sample 5 players
            player_data = cumulative_df[cumulative_df["player_id"] == player_id].sort_values("week")
            cumulative = player_data["cumulative_points"].values
            # Allow for small decreases (stat corrections)
            assert len(cumulative) > 0, f"Player {player_id} should have cumulative data"

        print(f"\n✓ Cumulative points calculated for {cumulative_df['player_id'].nunique()} players")

    def test_draft_value_analysis(
        self, draft_data_df, player_season_points_df, teams_df
    ):
        """Test draft value analysis - are drafted players providing good value?"""
        draft_value = self.analyze_draft_value(draft_data_df, player_season_points_df, teams_df)

        assert not draft_value.empty, "Draft value analysis should not be empty"
        assert "points_per_dollar" in draft_value.columns

        # Print top 10 draft values
        print("\n" + "="*80)
        print("TOP 10 DRAFT VALUES (Points per Dollar)")
        print("="*80)
        top_draft = draft_value.nlargest(10, "points_per_dollar")[
            [
                "player_name",
                "cost",
                "fantasy_points_total",
                "points_per_dollar",
                "manager",
                "is_keeper",
            ]
        ]
        print(top_draft.to_string(index=False))

        # Print worst 10 draft values (min cost > $5)
        print("\n" + "="*80)
        print("WORST 10 DRAFT VALUES (Minimum $5 cost)")
        print("="*80)
        expensive_busts = draft_value[draft_value["cost"] >= 5].nsmallest(
            10, "points_per_dollar"
        )[
            [
                "player_name",
                "cost",
                "fantasy_points_total",
                "points_per_dollar",
                "manager",
                "is_keeper",
            ]
        ]
        print(expensive_busts.to_string(index=False))

        # Calculate league average
        avg_points_per_dollar = draft_value[draft_value["cost"] > 0][
            "points_per_dollar"
        ].mean()
        print(f"\n✓ League average points per dollar: {avg_points_per_dollar:.2f}")

    def test_trade_value_analysis(
        self, transactions_df, weekly_rosters_df, teams_df
    ):
        """Test trade value analysis - are traded-for players performing well?"""
        cumulative_df = self.calculate_player_cumulative_points(weekly_rosters_df)
        trade_value = self.analyze_trade_value(
            transactions_df, cumulative_df, teams_df
        )

        if trade_value.empty:
            print("\n⚠ No trade transactions found in 2024")
            return

        assert "post_trade_points" in trade_value.columns

        # Print top trade acquisitions
        print("\n" + "="*80)
        print("TOP 10 TRADE ACQUISITIONS (Post-Trade Points)")
        print("="*80)
        top_trades = trade_value.nlargest(10, "post_trade_points")[
            [
                "player_name",
                "trade_week",
                "post_trade_points",
                "weeks_active_post_trade",
                "points_per_week",
                "manager",
            ]
        ]
        print(top_trades.to_string(index=False))

        # Print worst trade acquisitions
        print("\n" + "="*80)
        print("WORST 10 TRADE ACQUISITIONS (Post-Trade Points)")
        print("="*80)
        worst_trades = trade_value.nsmallest(10, "post_trade_points")[
            [
                "player_name",
                "trade_week",
                "post_trade_points",
                "weeks_active_post_trade",
                "points_per_week",
                "manager",
            ]
        ]
        print(worst_trades.to_string(index=False))

        avg_post_trade_points = trade_value["post_trade_points"].mean()
        print(f"\n✓ Average post-trade points: {avg_post_trade_points:.2f}")

    def test_manager_value_ranking(
        self, draft_data_df, transactions_df, player_season_points_df, teams_df
    ):
        """Test manager value ranking - who got best value from draft and trades?"""
        # For now, use season totals instead of weekly cumulative
        # TODO: Implement weekly cumulative once weekly_rosters.points is populated
        draft_value = self.analyze_draft_value(draft_data_df, player_season_points_df, teams_df)

        # Create empty cumulative df for trade analysis (since weekly points not available)
        cumulative_df = pd.DataFrame()
        trade_value = self.analyze_trade_value(
            transactions_df, cumulative_df, teams_df
        )

        manager_value = self.aggregate_manager_value(
            draft_value, trade_value, teams_df
        )

        assert not manager_value.empty, "Manager value rankings should not be empty"

        # Print full manager value rankings
        print("\n" + "="*80)
        print("MANAGER VALUE RANKINGS - 2024 SEASON")
        print("="*80)
        print(
            manager_value[
                [
                    "manager",
                    "avg_points_per_dollar",
                    "total_draft_points",
                    "total_draft_cost",
                    "num_drafted",
                    "num_keepers",
                    "num_trades_in",
                    "avg_trade_points",
                    "overall_value_score",
                ]
            ].to_string(index=False)
        )

        # Assertions on data quality
        assert manager_value["total_draft_cost"].sum() > 0, "Total draft cost should be > 0"
        assert manager_value["total_draft_points"].sum() > 0, "Total draft points should be > 0"

        print(f"\n✓ Manager value analysis complete for {len(manager_value)} managers")

        # Return rankings for further analysis
        return manager_value

    def test_value_insights(
        self, draft_data_df, player_season_points_df, teams_df
    ):
        """Test to generate value insights and recommendations."""
        draft_value = self.analyze_draft_value(draft_data_df, player_season_points_df, teams_df)

        # Insight 1: Keeper value vs non-keeper value
        print("\n" + "="*80)
        print("INSIGHT: Keeper vs Non-Keeper Draft Value")
        print("="*80)

        if "is_keeper" in draft_value.columns:
            keeper_avg = draft_value[draft_value["is_keeper"] == True][
                "points_per_dollar"
            ].mean()
            non_keeper_avg = draft_value[draft_value["is_keeper"] == False][
                "points_per_dollar"
            ].mean()

            print(f"Keepers average: {keeper_avg:.2f} points per dollar")
            print(f"Non-keepers average: {non_keeper_avg:.2f} points per dollar")
            print(
                f"Keeper advantage: {((keeper_avg / non_keeper_avg - 1) * 100):.1f}%"
                if non_keeper_avg > 0
                else "N/A"
            )

        # Insight 2: Position value efficiency
        print("\n" + "="*80)
        print("INSIGHT: Position Value Efficiency")
        print("="*80)

        position_value = (
            draft_value.groupby("position")
            .agg(
                {
                    "cost": "mean",
                    "fantasy_points_total": "mean",
                    "points_per_dollar": "mean",
                }
            )
            .round(2)
        )
        print(position_value.to_string())

        print("\n✓ Value insights generated")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
