#!/bin/bash
# Helper script to set up OAuth using yahoofantasy CLI

echo "Yahoo Fantasy OAuth Setup"
echo "========================"
echo ""
echo "This script will use the yahoofantasy CLI to authenticate."
echo "Make sure you have your Client ID and Client Secret ready."
echo ""

# Read from .env if available
if [ -f .env ]; then
    source .env
fi

# Prompt for credentials if not in .env
if [ -z "$YAHOO_CLIENT_ID" ]; then
    read -p "Enter your Yahoo Client ID (Consumer Key): " YAHOO_CLIENT_ID
fi

if [ -z "$YAHOO_CLIENT_SECRET" ]; then
    read -p "Enter your Yahoo Client Secret (Consumer Secret): " YAHOO_CLIENT_SECRET
fi

echo ""
echo "Starting OAuth flow..."
echo "A browser window will open for you to authorize the application."
echo ""

# Use yahoofantasy CLI login command
yahoofantasy login --client-id "$YAHOO_CLIENT_ID" --client-secret "$YAHOO_CLIENT_SECRET" --redirect-http

echo ""
echo "OAuth setup complete!"
echo ""
echo "The refresh token has been saved by yahoofantasy."
echo "You can now run: python main.py --refresh"


