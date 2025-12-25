"""Helper module for Yahoo OAuth authentication."""
import requests
import webbrowser
from urllib.parse import parse_qs, urlparse


def get_refresh_token(client_id: str, client_secret: str) -> str:
    """Get refresh token through OAuth 2.0 flow.
    
    Args:
        client_id: Yahoo API client ID
        client_secret: Yahoo API client secret
        
    Returns:
        Refresh token string
    """
    # Step 1: Get authorization URL
    # Use urlencode to properly encode the parameters (matching yahoofantasy library approach)
    from urllib.parse import urlencode
    params = {
        "client_id": client_id,
        "redirect_uri": "oob",  # Out-of-band for manual code entry
        "response_type": "code",
    }
    auth_url = f"https://api.login.yahoo.com/oauth2/request_auth?{urlencode(params)}"
    
    print("\n" + "="*60)
    print("Yahoo OAuth Authorization Required")
    print("="*60)
    print(f"\nOpening browser for authorization...")
    print(f"If browser doesn't open, visit this URL manually:\n{auth_url}\n")
    
    # Open browser
    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
    
    # Step 2: Get authorization code from user
    try:
        auth_code = input("Enter the authorization code from the browser: ").strip()
    except (EOFError, KeyboardInterrupt):
        raise Exception(
            "OAuth authorization cancelled. Please run the script in an interactive terminal "
            "or manually obtain a refresh token."
        )
    
    # Step 3: Exchange authorization code for tokens
    token_url = "https://api.login.yahoo.com/oauth2/get_token"
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": "oob"
    }
    
    response = requests.post(token_url, data=token_data)
    
    if response.status_code != 200:
        raise Exception(f"Failed to get tokens: {response.status_code} - {response.text}")
    
    tokens = response.json()
    refresh_token = tokens.get("refresh_token")
    
    if not refresh_token:
        raise Exception("No refresh_token in response. Response: " + str(tokens))
    
    print("✓ Successfully obtained refresh token!")
    return refresh_token

