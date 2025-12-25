# Yahoo Fantasy Football Dynasty League Review App

A comprehensive application for analyzing and reviewing your Yahoo Fantasy Football dynasty league history, with AI-powered insights and narratives generated using OpenAI's GPT models.

## Features

- **Historical Data Retrieval**: Fetches all league data from Yahoo Fantasy Football API since 2012
- **Data Organization**: Cleans and structures league data into analyzable formats
- **Key Insights Extraction**: Identifies top performers, champions, trends, and statistics
- **AI-Powered Narratives**: Generates engaging storylines, manager profiles, and season reviews using OpenAI
- **Comprehensive Reports**: Creates detailed overviews of league history and dynamics

## Prerequisites

1. **Yahoo Developer Account**: 
   - Sign up at [Yahoo Developer Network](https://developer.yahoo.com/)
   - Create a new app to get Client ID and Client Secret
   - Set redirect URI (use `oob` for desktop apps)

2. **OpenAI API Key**:
   - Sign up at [OpenAI](https://platform.openai.com/)
   - Generate an API key from your account settings

3. **Python 3.8+**: Required for running the application

4. **League Information**:
   - Your Yahoo Fantasy League ID (found in the league URL)

**📖 For detailed setup instructions, see [SETUP_GUIDE.md](setup_guide.md)**

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
OPENAI_API_KEY=your_openai_api_key_here
YAHOO_LEAGUE_ID=your_league_id_here
YAHOO_GAME_ID=nfl
```

## Configuration

Edit `config.py` to adjust:
- `LEAGUE_START_YEAR`: First year of your league (default: 2012)
- `CURRENT_YEAR`: Current year for fetching data (default: 2024)
- Directory paths for data storage

## Usage

### Initial Data Fetch

To fetch all league data from Yahoo (first run):
```bash
python main.py --refresh
```

This will:
- Authenticate with Yahoo Fantasy API
- Download all league data for each season
- Save data to `data/league_data/` directory
- Clean and organize the data
- Generate AI insights (if OpenAI key is configured)

### Subsequent Runs

To use cached data (faster, no API calls needed):
```bash
python main.py
```

To refresh data from Yahoo:
```bash
python main.py --refresh
```

## Output

The application generates several outputs:

### Data Files

- **Raw League Data**: `data/league_data/season_YYYY.json` - Original data from Yahoo API
- **Cleaned Data**: `data/cleaned_data/*.csv` - Organized data in CSV format:
  - `teams.csv` - Team statistics by season
  - `matchups.csv` - All matchup results
  - `standings.csv` - Final standings by season
  - `managers.csv` - Aggregated manager statistics
  - `season_summary.csv` - Season-level summaries

### Generated Insights

- **League Overview**: `data/insights/league_overview.txt` - Comprehensive league history
- **Key Storylines**: `data/insights/key_storylines.txt` - Interesting narratives and trends
- **Manager Profiles**: `data/insights/manager_profile_*.txt` - Individual manager profiles
- **Season Reviews**: `data/insights/season_review_YYYY.txt` - Detailed season-by-season reviews

## Data Structure

The application organizes data into the following structure:

```
data/
├── league_data/          # Raw JSON data from Yahoo API
│   ├── season_2012.json
│   ├── season_2013.json
│   └── ...
├── cleaned_data/         # Cleaned CSV files
│   ├── teams.csv
│   ├── matchups.csv
│   ├── standings.csv
│   ├── managers.csv
│   └── season_summary.csv
└── insights/             # AI-generated narratives
    ├── league_overview.txt
    ├── key_storylines.txt
    ├── manager_profile_*.txt
    └── season_review_*.txt
```

## Yahoo API Authentication

The application uses OAuth 2.0 for Yahoo authentication. On first run with `--refresh`, you may be prompted to:
1. Visit a URL to authorize the application
2. Copy an authorization code
3. Paste it back into the application

The authentication tokens will be cached for future use.

## Customization

### Adjusting Analysis Parameters

You can modify the analysis in `data_cleaner.py`:
- Playoff cutoff (currently top 4 teams)
- Statistics calculations
- Data aggregation methods

### Customizing AI Prompts

Edit `openai_insights.py` to customize:
- The narrative style and tone
- Types of insights generated
- Detail level of profiles and reviews

### OpenAI Model Selection

In `openai_insights.py`, you can change the model:
- `gpt-4` (default) - Best quality, higher cost
- `gpt-3.5-turbo` - Faster, lower cost
- `gpt-4-turbo` - Balanced option

## Troubleshooting

### Authentication Issues

- Verify your Yahoo Client ID and Secret are correct
- Ensure your app is configured correctly in Yahoo Developer Console
- Check that the redirect URI matches your app settings

### API Rate Limits

- Yahoo API has rate limits; the app includes delays between requests
- If you hit limits, wait and retry later
- Cached data can be used to avoid repeated API calls

### Missing Data

- Some older seasons may have incomplete data
- Check `season_YYYY.json` files for error messages
- Adjust `LEAGUE_START_YEAR` if needed

### OpenAI API Issues

- Verify your API key is valid and has credits
- Check your OpenAI account for usage limits
- The app will skip AI generation if the key is missing

## License

This project is open source and available for personal use.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## Disclaimer

This application is not affiliated with Yahoo or OpenAI. Use of the Yahoo Fantasy Sports API is subject to Yahoo's Terms of Service. Use of OpenAI API is subject to OpenAI's Terms of Service.

