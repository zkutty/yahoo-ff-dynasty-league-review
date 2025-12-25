"""Configuration settings for the Yahoo Fantasy Football League Review App."""
import os
from dotenv import load_dotenv

load_dotenv()

# Yahoo Fantasy API Configuration
YAHOO_CLIENT_ID = os.getenv("YAHOO_CLIENT_ID")
YAHOO_CLIENT_SECRET = os.getenv("YAHOO_CLIENT_SECRET")
YAHOO_LEAGUE_ID = os.getenv("YAHOO_LEAGUE_ID")
YAHOO_GAME_ID = os.getenv("YAHOO_GAME_ID", "nfl")
YAHOO_REFRESH_TOKEN = os.getenv("YAHOO_REFRESH_TOKEN")  # Optional, will prompt for OAuth if not set

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Default to gpt-4o-mini for cost efficiency

# Data storage paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LEAGUE_DATA_DIR = os.path.join(DATA_DIR, "league_data")
CLEANED_DATA_DIR = os.path.join(DATA_DIR, "cleaned_data")
INSIGHTS_DIR = os.path.join(DATA_DIR, "insights")

# League history (adjust based on your league's start year)
LEAGUE_START_YEAR = 2012
CURRENT_YEAR = 2024

def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LEAGUE_DATA_DIR, exist_ok=True)
    os.makedirs(CLEANED_DATA_DIR, exist_ok=True)
    os.makedirs(INSIGHTS_DIR, exist_ok=True)

