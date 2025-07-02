#!/bin/bash

# TomasBot Scheduled Send Launcher
# This script launches the scheduled send functionality

echo "Starting TomasBot Scheduled Send..."
echo "Make sure you have contacts in your whitelist first!"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: No virtual environment found. Make sure dependencies are installed."
fi

# Run the scheduled send script
python3 scripts/schedule_send.py 