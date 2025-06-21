#!/bin/bash

# TomasBot Startup Script
echo "Starting TomasBot..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
python3 -m pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Please create one with your Google Calendar credentials."
    echo "Example .env file:"
    echo "GOOGLE_CLIENT_ID=your_client_id"
    echo "GOOGLE_CLIENT_SECRET=your_client_secret"
    echo "ANTHROPIC_API_KEY=your_claude_api_key"
    echo "PORT=5001"
    echo "HOST=0.0.0.0"
fi

# Start TomasBot
echo "Starting TomasBot..."
python scripts/main.py 