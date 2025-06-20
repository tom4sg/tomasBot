#!/usr/bin/env python3
"""
iPhone Do Not Disturb Webhook Server
This script creates a webhook server that receives notifications from iPhone Shortcuts
when Do Not Disturb mode changes.
"""

from flask import Flask, request, jsonify
from datetime import datetime
import json
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dnd_log.txt'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# Store DND status in memory (you could use a database for persistence)
dnd_status = {
    'is_enabled': False,
    'last_update': None,
    'history': []
}

@app.route('/webhook/dnd', methods=['POST'])
def handle_dnd_webhook():
    """Handle Do Not Disturb status updates from iPhone Shortcuts"""
    try:
        # Get JSON data from the request
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        # Extract DND status
        is_dnd_enabled = data.get('dnd_enabled', False)
        timestamp = datetime.now().isoformat()
        
        # Log the status change
        logging.info(f"DND Status Update: {'Enabled' if is_dnd_enabled else 'Disabled'} at {timestamp}")
        
        # Update global status
        dnd_status['is_enabled'] = is_dnd_enabled
        dnd_status['last_update'] = timestamp
        
        # Add to history
        dnd_status['history'].append({
            'status': is_dnd_enabled,
            'timestamp': timestamp
        })
        
        # Keep only last 100 entries in history
        if len(dnd_status['history']) > 100:
            dnd_status['history'] = dnd_status['history'][-100:]
        
        # Save to file for persistence
        save_status_to_file()
        
        # You can add custom actions here based on DND status
        if is_dnd_enabled:
            on_dnd_enabled()
        else:
            on_dnd_disabled()
        
        return jsonify({
            'status': 'success',
            'message': f"DND status updated: {'Enabled' if is_dnd_enabled else 'Disabled'}",
            'timestamp': timestamp
        })
        
    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Get current DND status"""
    return jsonify(dnd_status)

@app.route('/history', methods=['GET'])
def get_history():
    """Get DND status history"""
    return jsonify({
        'history': dnd_status['history'][-20:],  # Last 20 entries
        'total_entries': len(dnd_status['history'])
    })

def on_dnd_enabled():
    """Custom action when DND is enabled"""
    logging.info("🔕 Do Not Disturb has been ENABLED")
    # Add your custom logic here
    # Examples:
    # - Send notification to other devices
    # - Update status in other apps
    # - Trigger automation
    pass

def on_dnd_disabled():
    """Custom action when DND is disabled"""
    logging.info("🔔 Do Not Disturb has been DISABLED")
    # Add your custom logic here
    pass

def save_status_to_file():
    """Save current status to a JSON file"""
    try:
        with open('dnd_status.json', 'w') as f:
            json.dump(dnd_status, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving status to file: {str(e)}")

def load_status_from_file():
    """Load status from JSON file on startup"""
    global dnd_status
    try:
        if os.path.exists('dnd_status.json'):
            with open('dnd_status.json', 'r') as f:
                loaded_status = json.load(f)
                dnd_status.update(loaded_status)
                logging.info("Loaded previous DND status from file")
    except Exception as e:
        logging.error(f"Error loading status from file: {str(e)}")

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify server is running"""
    return jsonify({
        'message': 'DND Webhook Server is running!',
        'timestamp': datetime.now().isoformat(),
        'current_status': dnd_status['is_enabled']
    })

if __name__ == '__main__':
    # Load previous status on startup
    load_status_from_file()
    
    # Start the Flask server
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logging.info(f"Starting DND Webhook Server on {host}:{port}")
    logging.info(f"Webhook URL: http://{host}:{port}/webhook/dnd")
    logging.info(f"Status URL: http://{host}:{port}/status")
    
    app.run(host=host, port=port, debug=False)