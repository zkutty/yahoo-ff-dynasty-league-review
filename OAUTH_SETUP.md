# OAuth Setup Instructions

If you're getting an "invalid client id" error, there are a few things to check:

## Option 1: Use yahoofantasy CLI (Recommended)

The easiest way to get authenticated is to use the built-in yahoofantasy CLI command:

```bash
# Using the helper script (easiest)
./setup_oauth.sh

# Or manually:
yahoofantasy login --client-id "YOUR_CLIENT_ID" --client-secret "YOUR_CLIENT_SECRET" --redirect-http
```

This will:
1. Open your browser for authorization
2. Handle the OAuth flow automatically
3. Save the refresh token for future use

**Important Notes:**
- The `--redirect-http` flag uses HTTP instead of HTTPS (easier for local setup)
- If you get an "invalid client id" error, double-check you're using the **Client ID (Consumer Key)**, not the App ID
- Make sure your redirect URI in Yahoo Developer Console matches what the CLI uses (default is `https://localhost:8000`)

After running this once, the credentials will be saved by yahoofantasy and you can run `python main.py --refresh` to fetch your data.

## Option 2: Manual OAuth Flow

If the CLI doesn't work, you can manually complete the OAuth flow:

1. **Verify your Client ID and Secret** in the Yahoo Developer Console:
   - Go to https://developer.yahoo.com/
   - Navigate to your app
   - Make sure you're copying the exact Client ID (Consumer Key) and Client Secret (Consumer Secret)
   - Check that there are no extra spaces or characters

2. **Check your Redirect URI**:
   - In your Yahoo app settings, make sure "oob" (out-of-band) is listed as an allowed redirect URI
   - Or use "https://localhost:8000" if that's what you registered

3. **Get Authorization Code**:
   - Visit: `https://api.login.yahoo.com/oauth2/request_auth?client_id=YOUR_CLIENT_ID&redirect_uri=oob&response_type=code`
   - Replace `YOUR_CLIENT_ID` with your actual client ID
   - Authorize the app
   - Copy the authorization code from the page

4. **Exchange for Refresh Token**:
   ```bash
   curl -X POST https://api.login.yahoo.com/oauth2/get_token \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET" \
     -d "code=AUTHORIZATION_CODE" \
     -d "grant_type=authorization_code" \
     -d "redirect_uri=oob"
   ```

5. **Save the refresh_token** to your `.env` file:
   ```
   YAHOO_REFRESH_TOKEN=your_refresh_token_here
   ```

## Common Issues

1. **"invalid client id" error**: 
   - Verify the Client ID is correct in Yahoo Developer Console
   - Make sure you're using the Client ID (Consumer Key), not the App ID
   - Check for any URL encoding issues

2. **"unauthorized_client" error**:
   - Verify your redirect URI matches what's registered in Yahoo
   - Make sure your app is properly configured in Yahoo Developer Console

3. **App Type**:
   - If you're using "oob" redirect URI, make sure your app type supports it
   - You may need to create an "Installed Application" type app instead of "Web Application"

## Getting Your Credentials

1. Go to https://developer.yahoo.com/
2. Sign in and go to "My Apps"
3. Select your app (or create a new one)
4. You'll see:
   - **App ID**: This is NOT the Client ID
   - **Client ID (Consumer Key)**: This is what you need
   - **Client Secret (Consumer Secret)**: This is what you need

Make sure you're using the Client ID and Client Secret, not the App ID!

