"""Quick script to exchange authorization code for refresh token."""
import sys
from yahoo_oauth import get_refresh_token
import config

if len(sys.argv) > 1:
    auth_code = sys.argv[1]
else:
    auth_code = input("Enter the authorization code: ").strip()

# Exchange code for tokens
import requests

token_url = "https://api.login.yahoo.com/oauth2/get_token"
# Try both redirect URIs (oob for manual codes, localhost for CLI)
for redirect_uri in ["oob", "https://localhost:8000"]:
    token_data = {
        "client_id": config.YAHOO_CLIENT_ID,
        "client_secret": config.YAHOO_CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    response = requests.post(token_url, data=token_data)
    
    if response.status_code == 200:
        tokens = response.json()
        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")
        
        if refresh_token:
            print(f"\n✓ Successfully obtained tokens!")
            print(f"\nRefresh Token: {refresh_token}")
            print(f"\nSave this to your .env file as:")
            print(f"YAHOO_REFRESH_TOKEN={refresh_token}")
            sys.exit(0)
    elif redirect_uri == "oob":
        # If oob fails, try the other one
        continue

# If we get here, both failed
print(f"Error: {response.status_code}")
print(response.text)
sys.exit(1)


