"""AI insights generation module - separated to avoid unnecessary API calls."""
from openai_insights import OpenAIInsightsGenerator
from data_manager import DataManager
import config


def generate_all_insights(insights: dict, cleaned_data: dict):
    """Generate all AI-powered insights and save them.
    
    Args:
        insights: Dictionary of key insights from data cleaner
        cleaned_data: Dictionary of cleaned DataFrames
    """
    if not config.OPENAI_API_KEY:
        print("Skipping AI insights generation - OPENAI_API_KEY not configured")
        return
    
    print(f"\nGenerating AI-powered insights and narratives using {config.OPENAI_MODEL}...")
    data_manager = DataManager()
    generator = OpenAIInsightsGenerator(api_key=config.OPENAI_API_KEY, model=config.OPENAI_MODEL)
    
    # Generate league overview
    print("\nGenerating league overview...")
    overview = generator.generate_league_overview(insights, cleaned_data)
    data_manager.save_insight("league_overview", overview)
    print("\n" + "=" * 60)
    print("LEAGUE OVERVIEW")
    print("=" * 60)
    print(overview)
    
    # Generate storylines
    print("\n" + "=" * 60)
    print("KEY STORYLINES")
    print("=" * 60)
    storylines = generator.generate_storylines(insights, cleaned_data)
    data_manager.save_insight("key_storylines", storylines)
    print(storylines)
    
    # Generate manager profiles
    if 'managers' in cleaned_data and not cleaned_data['managers'].empty:
        print("\n" + "=" * 60)
        print("MANAGER PROFILES")
        print("=" * 60)
        managers_df = cleaned_data['managers']
        
        for idx, manager_row in managers_df.iterrows():
            manager_dict = manager_row.to_dict()
            print(f"\n{'-' * 60}")
            print(f"Profile: {manager_dict['manager_name']}")
            print(f"{'-' * 60}")
            profile = generator.generate_manager_profile(manager_dict, cleaned_data)
            filename = f"manager_profile_{manager_dict['manager_name'].replace(' ', '_').lower()}"
            data_manager.save_insight(filename, profile)
            print(profile)
    
    # Generate season reviews
    if 'season_summary' in cleaned_data and not cleaned_data['season_summary'].empty:
        print("\n" + "=" * 60)
        print("SEASON REVIEWS")
        print("=" * 60)
        season_df = cleaned_data['season_summary']
        
        for idx, season_row in season_df.iterrows():
            season_dict = season_row.to_dict()
            year = season_dict['season_year']
            print(f"\n{'-' * 60}")
            print(f"{year} Season Review")
            print(f"{'-' * 60}")
            review = generator.generate_season_review(year, season_dict)
            filename = f"season_review_{year}"
            data_manager.save_insight(filename, review)
            print(review)

