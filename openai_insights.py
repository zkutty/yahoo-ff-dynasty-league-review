"""OpenAI integration for generating insights and narratives."""
import json
from typing import Dict, List
from openai import OpenAI
import config


class OpenAIInsightsGenerator:
    """Generates insights and narratives using OpenAI GPT models."""
    
    def __init__(self, api_key: str, model: str = None):
        """Initialize the OpenAI client.
        
        Args:
            api_key: OpenAI API key
            model: GPT model to use (default: from config, or gpt-4o-mini)
        """
        self.client = OpenAI(api_key=api_key)
        # Use model from config if not specified, default to gpt-4o-mini
        self.model = model or config.OPENAI_MODEL
    
    def generate_league_overview(self, insights: Dict, cleaned_data: Dict) -> str:
        """Generate a comprehensive league overview narrative.
        
        Args:
            insights: Dictionary of key insights
            cleaned_data: Dictionary of cleaned DataFrames
            
        Returns:
            Generated narrative text
        """
        # Prepare context for the prompt
        context = self._prepare_context(insights, cleaned_data)
        
        prompt = f"""You are a fantasy football analyst writing a comprehensive review of a dynasty fantasy football league that has been running since 2012.

Here is the league data and key insights:

{context}

Please write an engaging, comprehensive overview of this fantasy football league that includes:
1. A brief introduction to the league's history and longevity
2. Discussion of the most successful managers and their achievements
3. Notable trends and patterns over the years
4. Memorable seasons or championship runs
5. Overall league competitiveness and dynamics

Make it engaging, fun to read, and highlight interesting storylines. Write in a conversational yet professional tone."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert fantasy football analyst with a talent for writing engaging narratives about fantasy sports leagues."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    def generate_manager_profile(self, manager_data: Dict, all_data: Dict) -> str:
        """Generate a detailed profile for a specific manager.
        
        Args:
            manager_data: Dictionary with manager statistics
            all_data: All cleaned data for context
            
        Returns:
            Generated manager profile narrative
        """
        prompt = f"""You are a fantasy football analyst writing a detailed profile of a fantasy football manager.

Manager Statistics:
- Name: {manager_data.get('manager_name', 'Unknown')}
- Seasons in League: {manager_data.get('num_seasons', 0)}
- Total Wins: {manager_data.get('total_wins', 0)}
- Total Losses: {manager_data.get('total_losses', 0)}
- Total Ties: {manager_data.get('total_ties', 0)}
- Win Percentage: {manager_data.get('win_percentage', 0):.3f}
- Championships: {manager_data.get('championships', 0)}
- Playoff Appearances: {manager_data.get('playoff_appearances', 0)}
- Best Finish: {manager_data.get('best_finish', 'N/A')}
- Worst Finish: {manager_data.get('worst_finish', 'N/A')}
- Average Points For: {manager_data.get('avg_points_for', 0):.2f}
- Average Points Against: {manager_data.get('avg_points_against', 0):.2f}

Write an engaging, detailed profile of this manager that includes:
1. An assessment of their overall success and consistency
2. Their championship pedigree (if any)
3. Notable strengths (high scoring, consistency, playoff success, etc.)
4. Areas where they might have struggled
5. Their legacy and standing in the league
6. Fun anecdotes or storylines if applicable

Make it personalized, engaging, and provide a balanced view of their fantasy football career."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert fantasy football analyst writing engaging manager profiles."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
    
    def generate_season_review(self, season_year: int, season_data: Dict) -> str:
        """Generate a review for a specific season.
        
        Args:
            season_year: The year of the season
            season_data: Season data dictionary
            
        Returns:
            Generated season review narrative
        """
        # Extract key season information
        champion = season_data.get('champion_manager', 'Unknown')
        champion_points = season_data.get('champion_points', 0)
        num_teams = season_data.get('num_teams', 0)
        avg_points = season_data.get('avg_points_per_team', 0)
        
        prompt = f"""You are a fantasy football analyst writing a season review for the {season_year} fantasy football season.

Season Summary:
- Year: {season_year}
- Number of Teams: {num_teams}
- Champion: {champion}
- Champion Points: {champion_points:.2f}
- Average Points per Team: {avg_points:.2f}

Write an engaging season review that includes:
1. Overview of the season's competitiveness
2. The champion's journey and dominance
3. Notable storylines, upsets, or surprises
4. Statistical highlights
5. Memorable moments or narratives

Make it exciting and capture the drama of the fantasy football season."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert fantasy football analyst writing engaging season reviews."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
    
    def generate_storylines(self, insights: Dict, cleaned_data: Dict) -> str:
        """Generate interesting storylines and narratives from the data.
        
        Args:
            insights: Dictionary of key insights
            cleaned_data: Dictionary of cleaned DataFrames
            
        Returns:
            Generated storylines narrative
        """
        context = self._prepare_context(insights, cleaned_data)
        
        prompt = f"""You are a fantasy football analyst identifying the most interesting storylines from a dynasty fantasy football league.

League Data:
{context}

Identify and write about the most compelling storylines, including:
1. Rivalries and competitive dynamics
2. Managers who have dominated or struggled
3. Comeback stories or surprising turnarounds
4. Consistent performers vs. boom-or-bust teams
5. Any notable trends or patterns that tell a story
6. Fun facts and interesting statistics

Make each storyline engaging and provide context. Write in a way that brings the league's history to life."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert fantasy football analyst who identifies compelling storylines in fantasy sports."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    def _prepare_context(self, insights: Dict, cleaned_data: Dict) -> str:
        """Prepare context string from insights and data.
        
        Args:
            insights: Dictionary of key insights
            cleaned_data: Dictionary of cleaned DataFrames
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add key insights
        if 'top_managers_by_wins' in insights:
            context_parts.append("Top Managers by Wins:")
            for manager in insights['top_managers_by_wins'][:5]:
                context_parts.append(
                    f"  - {manager.get('manager_name')}: {manager.get('total_wins')} wins, "
                    f"{manager.get('championships')} championships, "
                    f"{manager.get('win_percentage', 0):.3f} win percentage"
                )
        
        if 'championship_leaders' in insights:
            context_parts.append("\nChampionship Leaders:")
            for manager in insights['championship_leaders'][:5]:
                context_parts.append(
                    f"  - {manager.get('manager_name')}: {manager.get('championships')} championships, "
                    f"{manager.get('total_wins')} total wins"
                )
        
        if 'all_champions' in insights:
            context_parts.append("\nAll Champions by Year:")
            for champ in insights['all_champions']:
                context_parts.append(
                    f"  - {champ.get('season_year')}: {champ.get('champion_manager')} "
                    f"({champ.get('champion_points', 0):.2f} points)"
                )
        
        # Add summary statistics if available
        if 'managers' in cleaned_data and not cleaned_data['managers'].empty:
            managers_df = cleaned_data['managers']
            context_parts.append(f"\nLeague Statistics:")
            context_parts.append(f"  - Total Managers: {len(managers_df)}")
            context_parts.append(f"  - Average Win Percentage: {managers_df['win_percentage'].mean():.3f}")
            context_parts.append(f"  - Total Championships Awarded: {managers_df['championships'].sum()}")
        
        return "\n".join(context_parts)

