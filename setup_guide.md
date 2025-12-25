# Setup Guide

This guide will help you set up the Yahoo Fantasy Football League Review App.

## Step 1: Get Yahoo API Credentials

1. Go to [Yahoo Developer Network](https://developer.yahoo.com/)
2. Sign in with your Yahoo account
3. Go to "My Apps" and create a new application
4. Fill in the application details:
   - Application Name: "Fantasy Football League Review" (or any name you prefer)
   - Application Type: "Web Application"
   - Redirect URI: `oob` (for out-of-band, used for desktop apps)
   - Description: Optional
5. After creating the app, you'll receive:
   - **Client ID (Consumer Key)**
   - **Client Secret (Consumer Secret)**
6. Save these credentials - you'll need them for the `.env` file

## Step 2: Get Your League ID

1. Go to your Yahoo Fantasy Football league
2. Look at the URL - it should look like:
   ```
   https://football.fantasysports.yahoo.com/f1/123456
   ```
3. The number at the end (e.g., `123456`) is your **League ID**
4. Alternatively, you can find it in the league settings

## Step 3: Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to "API Keys" in your account settings
4. Click "Create new secret key"
5. Copy the key immediately (you won't be able to see it again)
6. Save this key - you'll need it for the `.env` file

## Step 4: Configure the Application

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Edit the `.env` file and fill in your credentials:
   ```env
   YAHOO_CLIENT_ID=your_actual_client_id_here
   YAHOO_CLIENT_SECRET=your_actual_client_secret_here
   OPENAI_API_KEY=your_actual_openai_key_here
   YAHOO_LEAGUE_ID=your_actual_league_id_here
   YAHOO_GAME_ID=nfl
   ```

## Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 6: First Run

Run the application with the `--refresh` flag to fetch data from Yahoo:

```bash
python main.py --refresh
```

**Note on Authentication:**

On the first run, you may be prompted to:
1. Visit a URL in your browser
2. Sign in to Yahoo and authorize the application
3. Copy the authorization code from the browser
4. Paste it into the terminal

The authentication tokens will be saved for future use.

## Important Notes About Historical Data

### Accessing Historical Seasons

Yahoo's API structure for accessing historical seasons can vary. The current implementation assumes you can access all historical data through the current league object. However, you may need to adjust the code based on your league's structure:

1. **If your league has been continuous since 2012:**
   - The current implementation should work
   - All historical data should be accessible through the league object

2. **If seasons are stored separately:**
   - You may need to use league keys in the format: `{game_id}.l.{league_id}.{year}`
   - Modify `yahoo_client.py` to construct league keys for each year

3. **If you need to access past seasons differently:**
   - Check the `yahoofantasy` library documentation
   - Adjust the `fetch_season_data` method accordingly

### Testing with One Season First

Before fetching all seasons, test with a single year by temporarily modifying `config.py`:

```python
LEAGUE_START_YEAR = 2023  # Test with most recent year
CURRENT_YEAR = 2023
```

## Troubleshooting

### "League not found" Error

- Verify your League ID is correct
- Make sure you're using the numeric League ID, not the league name
- Check that you have access to the league in Yahoo Fantasy

### Authentication Errors

- Verify your Client ID and Client Secret are correct
- Make sure you've authorized the application in Yahoo Developer Console
- Try deleting cached tokens and re-authenticating

### API Rate Limits

- Yahoo API has rate limits
- If you encounter rate limit errors, the app includes delays between requests
- You can also run the app multiple times - it will use cached data if available

### Missing Historical Data

- Some older seasons may have incomplete data
- Check the generated JSON files in `data/league_data/` to see what was successfully retrieved
- You may need to manually adjust which seasons to fetch

### OpenAI API Issues

- Verify your API key is valid and has credits
- Check your OpenAI account usage limits
- The app will skip AI generation if the key is missing or invalid

## Next Steps

Once you have successfully fetched your data:

1. Review the cleaned data in `data/cleaned_data/` (CSV files)
2. Read the generated insights in `data/insights/` (text files)
3. Customize the analysis in `data_cleaner.py` if needed
4. Adjust AI prompts in `openai_insights.py` to change the narrative style

