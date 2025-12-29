# Yahoo Fantasy Football Dynasty League Review App

A comprehensive application for analyzing and reviewing your Yahoo Fantasy Football dynasty league history, featuring auction draft value analysis, keeper metrics, VAR (Value Above Replacement) calculations, trade impact analysis, and optional AI-powered insights.

## Features

- **Historical Data Retrieval**: Fetches all league data from Yahoo Fantasy Football API
- **Auction Draft Analysis**: Evaluates draft value, keeper efficiency, and price normalization
- **VAR Calculations**: Value Above Replacement metrics for all players and positions
- **Trade Impact Analysis**: Tracks trade outcomes and identifies winners/losers
- **Manager Profiling**: Classifies manager archetypes (DRAFT_AND_HOLD, WAIVER_HAWK, TRADER, etc.)
- **Weekly Lineup Analysis**: Optimal lineup calculations and points left on bench
- **AI-Powered Narratives**: Generates engaging storylines and season reviews using OpenAI (optional)
- **Comprehensive Testing**: Validate draft value and manager performance

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your Yahoo and OpenAI credentials

# Fetch fresh data from Yahoo API
python main.py --refresh

# Run comprehensive analysis pipeline
python -m analysis --start 2014 --end 2024 --out ./out

# Run 2024 manager value tests
python -m pytest tests/test_2024_manager_value.py -v -s
```

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Architecture](#architecture)
- [Common Commands](#common-commands)
- [Analysis Pipeline](#analysis-pipeline)
- [Testing](#testing)
- [Data Structure](#data-structure)
- [Configuration](#configuration)
- [Output](#output)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)

## Prerequisites

1. **Yahoo Developer Account**:
   - Sign up at [Yahoo Developer Network](https://developer.yahoo.com/)
   - Create a new app to get Client ID and Client Secret
   - Set redirect URI (use `oob` for desktop apps)

2. **OpenAI API Key** (Optional):
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Generate an API key from your account settings

3. **Python 3.8+**: Required for running the application

4. **League Information**:
   - Your Yahoo Fantasy League ID (found in the league URL)

**📖 For detailed setup instructions, see [setup_guide.md](setup_guide.md)**

## Installation

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
cp .env.example .env
```

4. Edit `.env` and fill in your credentials:
```env
YAHOO_CLIENT_ID=your_yahoo_client_id_here
YAHOO_CLIENT_SECRET=your_yahoo_client_secret_here
YAHOO_LEAGUE_ID=your_league_id_here
YAHOO_GAME_ID=nfl
OPENAI_API_KEY=your_openai_api_key_here  # Optional
```

5. Edit `config.py` to adjust:
   - `LEAGUE_START_YEAR`: First year of your league (default: 2012)
   - `CURRENT_YEAR`: Current year for fetching data (default: 2024)
   - Directory paths for data storage
   - League constants (`NUM_TEAMS`, `AUCTION_BUDGET`)

## Architecture

### Two Main Entry Points

#### 1. `main.py` - Data Fetching and Basic Processing

- Authenticates with Yahoo Fantasy API via `yahoo_client.py`
- Fetches season data and saves to `data/league_data/season_YYYY.json`
- Cleans data via `data_cleaner.py` → saves to `data/cleaned_data/*.csv`
- Optionally generates AI insights via `ai_insights.py`/`openai_insights.py`

#### 2. `python -m analysis` - Advanced Analytics Pipeline

- Entry: `analysis/__main__.py` → `analysis/pipeline.py`
- Loads data via `analysis/data_loader.py`
- Runs comprehensive analysis producing outputs in `out/`

### Analysis Pipeline Modules

| Module | Purpose |
|--------|---------|
| `normalize.py` | Price normalization accounting for keeper inflation |
| `var.py` | Value Above Replacement calculation |
| `tiers.py` | Draft tier assignment and hit rate analysis |
| `keepers.py` | Keeper surplus analysis |
| `lifecycle_extended.py` | Player acquisition tracking (draft/waiver/trade) |
| `waivers.py` | Waiver pickup classification (LEAGUE_WINNER, SOLID_STARTER, etc.) |
| `trades.py` | Trade impact analysis |
| `strategies.py` | Manager archetype classification |
| `consistency.py` | Manager outcome distributions and volatility |
| `schedule_luck.py` | Expected wins vs actual, schedule difficulty |
| `weekly_lineups.py` | Weekly lineup optimization analysis |
| `outputs.py` | CSV/Parquet saving and visualization generation |
| `extract_player_stats.py` | Player stats extraction from Yahoo API |

### Key Data Flow

```
Yahoo API → data/league_data/season_YYYY.json
         → data/cleaned_data/*.csv (teams, matchups, standings, draft_picks, managers)
         → out/*.parquet, out/*.csv (analysis outputs)
         → out/*.png (plots)
```

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/exchange_token.py` | OAuth token exchange utility |
| `scripts/test_weekly_api_structure.py` | API structure exploration tool |
| `scripts/fetch_weekly_data_example.py` | Example weekly data fetching |
| `scripts/investigate_2024_data.py` | 2024 data structure investigation |

## Common Commands

### Data Fetching

```bash
# Fetch fresh data from Yahoo API (requires OAuth)
python main.py --refresh

# Use cached data only (no API calls)
python main.py

# Fetch with AI-powered insights (costs OpenAI credits)
python main.py --refresh --generate-ai

# Fetch specific year range
python main.py --refresh --start-year 2020 --end-year 2024
```

### Analysis Pipeline

```bash
# Run full analysis pipeline (2014-2024)
python -m analysis --start 2014 --end 2024 --out ./out

# Analyze specific seasons
python -m analysis --start 2022 --end 2024 --out ./out
```

### Testing

```bash
# Run all 2024 manager value tests
python -m pytest tests/test_2024_manager_value.py -v -s

# Run specific test
python -m pytest tests/test_2024_manager_value.py::Test2024ManagerValue::test_manager_value_ranking -v -s

# Run draft value analysis only
python -m pytest tests/test_2024_manager_value.py::Test2024ManagerValue::test_draft_value_analysis -v -s
```

## Testing

### Manager Value Analysis Tests

The test suite (`tests/test_2024_manager_value.py`) analyzes manager performance using season-total scoring:

**Key Metrics:**
- **Points Per Dollar**: Fantasy points produced per auction dollar spent
- **Overall Value Score**: Weighted combination of draft and trade efficiency
- **Position Efficiency**: Cost-effectiveness by position (QB, RB, WR, TE, DEF)

**Sample Output:**
```
Manager Value Rankings - 2024 Season
====================================
1. Zach - 13.83 pts/$ (2,766 total points)
2. James - 13.51 pts/$ (2,701 total points)
3. Kyle - 13.45 pts/$ (2,650 total points)

League average: 40.52 points per dollar

Best Draft Values:
- Geno Smith ($1): 281.0 pts/$
- Garrett Wilson ($1): 251.9 pts/$
- Bucky Irving ($1): 244.4 pts/$
```

See [tests/README.md](tests/README.md) for complete findings and insights.

## Key Concepts

- **VAR (Value Above Replacement)**: Player fantasy points minus replacement-level baseline for their position
- **Normalized Price**: Auction price adjusted for keeper inflation across seasons
- **Keeper Surplus**: Market price estimate minus keeper cost (value gained from keeping)
- **Manager Archetypes**: DRAFT_AND_HOLD, WAIVER_HAWK, TRADER, PASSIVE, BALANCED
- **Draft Efficiency**: Points per dollar spent in auction draft
- **Trade Impact**: Net VAR gained/lost from trade transactions

## Data Structure

### Directory Structure

```
data/
├── cleaned_data/          # Processed CSV files
├── league_data/           # Raw JSON files from Yahoo API (season_YYYY.json)
└── insights/              # Generated analysis summaries

out/                       # Analysis outputs (Parquet, CSV, plots, reports)

tests/                     # Test suite for manager value analysis
```

### Key Data Files

**Raw League Data:**
- `data/league_data/season_YYYY.json` - One JSON file per season containing raw Yahoo API data

**Cleaned Data:**
- `teams.csv` - Team statistics by season
- `matchups.csv` - All matchup results
- `standings.csv` - Final standings by season
- `managers.csv` - Aggregated manager statistics
- `draft_picks.csv` - Draft pick information with auction prices and keeper status
- `season_summary.csv` - Season-level summaries

**Analysis Outputs:**
- `out/analysis_ready_{season}.parquet` - Complete analysis-ready dataset with VAR, tiers, etc.
- `out/lifecycle_table.parquet` - Player acquisition tracking
- `out/waiver_pickups.csv` - Waiver/FA pickup analysis
- `out/trade_impact.csv` - Trade impact analysis
- `out/manager_strategy_profiles.csv` - Manager archetypes and strategies
- `out/tier_summary.csv` - Tier hit rate analysis
- `out/*.png` - Visualization plots

**See [DATA_STRUCTURE.md](DATA_STRUCTURE.md) for complete schema documentation**

## Output

### Generated Insights (with OpenAI)

- **League Overview**: `data/insights/league_overview.txt` - Comprehensive league history
- **Key Storylines**: `data/insights/key_storylines.txt` - Interesting narratives and trends
- **Manager Profiles**: `data/insights/manager_profile_*.txt` - Individual manager profiles
- **Season Reviews**: `data/insights/season_review_YYYY.txt` - Detailed season-by-season reviews

### Analysis Outputs

- **VAR Analysis**: Player value above replacement by position
- **Draft Value**: Points per dollar efficiency for drafted players
- **Keeper Analysis**: Keeper surplus and retention rates
- **Trade Impact**: Trade winners and losers by VAR
- **Manager Strategies**: Archetype classification and efficiency metrics
- **Visualizations**: Price vs VAR, FAAB efficiency, VAR by acquisition source

## Configuration

### Environment Variables (`.env`)

```env
YAHOO_CLIENT_ID=your_yahoo_client_id_here
YAHOO_CLIENT_SECRET=your_yahoo_client_secret_here
YAHOO_LEAGUE_ID=your_league_id_here
YAHOO_GAME_ID=nfl
OPENAI_API_KEY=your_openai_api_key_here  # Optional
```

### Settings (`config.py`)

- Year ranges: `LEAGUE_START_YEAR`, `CURRENT_YEAR`
- Directory paths: `DATA_DIR`, `OUTPUT_DIR`
- League constants: `NUM_TEAMS`, `AUCTION_BUDGET`
- Position settings: Starting slots by position

## Customization

### Adjusting Analysis Parameters

You can modify the analysis in various modules:
- `data_cleaner.py`: Playoff cutoff, statistics calculations
- `analysis/var.py`: Replacement level calculations
- `analysis/tiers.py`: Tier definitions and thresholds
- `analysis/strategies.py`: Manager archetype classification rules

### Customizing AI Prompts

Edit `openai_insights.py` to customize:
- Narrative style and tone
- Types of insights generated
- Detail level of profiles and reviews
- Model selection (`gpt-4`, `gpt-3.5-turbo`, `gpt-4-turbo`)

## Yahoo API Authentication

The application uses OAuth 2.0 for Yahoo authentication. On first run with `--refresh`, you may be prompted to:
1. Visit a URL to authorize the application
2. Copy an authorization code
3. Paste it back into the application

The authentication tokens will be cached for future use.

**For detailed OAuth setup, see [OAUTH_SETUP.md](OAUTH_SETUP.md)**

## Troubleshooting

### Authentication Issues

- Verify your Yahoo Client ID and Secret are correct
- Ensure your app is configured correctly in Yahoo Developer Console
- Check that the redirect URI matches your app settings
- Run `bash setup_oauth.sh` for interactive OAuth setup

### API Rate Limits

- Yahoo API has rate limits; the app includes delays between requests
- If you hit limits, wait and retry later
- Cached data can be used to avoid repeated API calls

### Missing Data

- Some older seasons may have incomplete data
- Check `season_YYYY.json` files for error messages
- Adjust `LEAGUE_START_YEAR` if needed
- Player stats may be missing for older seasons due to Yahoo API limitations

### OpenAI API Issues

- Verify your API key is valid and has credits
- Check your OpenAI account for usage limits
- The app will skip AI generation if the key is missing
- AI generation is optional and can be omitted

### Weekly Player Points

- Weekly roster data exists but `points` field may not be populated
- Use the cumulative difference method described in [docs/WEEKLY_DATA_GUIDE.md](docs/WEEKLY_DATA_GUIDE.md)
- Season-total points are available from team rosters

## Documentation

### Core Documentation
- **[DATA_STRUCTURE.md](DATA_STRUCTURE.md)** - Complete data schema documentation
- **[setup_guide.md](setup_guide.md)** - Comprehensive setup instructions
- **[OAUTH_SETUP.md](OAUTH_SETUP.md)** - Detailed OAuth setup guide

### Advanced Guides
- **[docs/WEEKLY_DATA_GUIDE.md](docs/WEEKLY_DATA_GUIDE.md)** - Weekly data extraction guide and recommendations
- **[tests/README.md](tests/README.md)** - 2024 manager value analysis findings and insights

## License

This project is open source and available for personal use.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Disclaimer

This application is not affiliated with Yahoo or OpenAI. Use of the Yahoo Fantasy Sports API is subject to Yahoo's Terms of Service. Use of OpenAI API is subject to OpenAI's Terms of Service.

---

*For Claude Code users: This project uses Yahoo Fantasy API for data fetching, Pandas for analysis, and optional OpenAI integration for narrative generation. All analysis modules are in the `analysis/` directory. Tests are in `tests/`. See commit history for recent enhancements.*
