#!/usr/bin/env python3
"""
TomasBot - Automated Response System
Integrates DND detection, missed calls/texts monitoring, and Google Calendar
to send automated responses when Tomas is unavailable.
"""

import sqlite3
import os
import json
import logging
import time
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
import subprocess
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tomas_bot.log'),
        logging.StreamHandler()
    ]
)

class TomasBot:
    def __init__(self):
        self.dnd_enabled = False
        self.last_processed_calls = set()
        self.last_processed_texts = set()
        self.calendar_service = None
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Load whitelist of phone numbers that should receive auto-responses
        self.whitelist = self.load_whitelist()
        
        # Initialize Claude LLM
        self.llm = self.init_claude_llm()
        
        # Initialize Google Calendar service
        self.init_calendar_service()
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self.monitor_communications, daemon=True)
        self.monitoring_thread.start()
    
    def init_claude_llm(self):
        """Initialize Claude LLM using LangChain"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logging.warning("ANTHROPIC_API_KEY not found in environment variables. Claude integration disabled.")
            return None
        
        try:
            llm = ChatAnthropic(
                model="claude-3-5-sonnet-20240620",
                anthropic_api_key=api_key
            )
            logging.info("Claude LLM initialized successfully")
            return llm
        except Exception as e:
            logging.error(f"Failed to initialize Claude LLM: {e}")
            return None
    
    def load_whitelist(self):
        """Load whitelist of phone numbers from file"""
        whitelist_file = 'close_friends_whitelist.json'
        
        if os.path.exists(whitelist_file):
            try:
                with open(whitelist_file, 'r') as f:
                    data = json.load(f)
                    whitelist = data.get('phone_numbers', [])
                    logging.info(f"Loaded {len(whitelist)} phone numbers from whitelist")
                    return whitelist
            except Exception as e:
                logging.error(f"Error loading whitelist: {e}")
        
        # Default empty whitelist
        logging.warning("No whitelist found. Creating default whitelist file.")
        self.create_default_whitelist()
        return []
    
    def create_default_whitelist(self):
        """Create a default whitelist file"""
        whitelist_file = 'close_friends_whitelist.json'
        default_whitelist = {
            "phone_numbers": [
                # Add your close friends' phone numbers here
                # "+1234567890",  # Example: John Doe
                # "+1987654321",  # Example: Jane Smith
            ],
            "description": "Phone numbers that should receive automated responses from TomasBot",
            "note": "Add phone numbers in international format (e.g., +1234567890)"
        }
        
        try:
            with open(whitelist_file, 'w') as f:
                json.dump(default_whitelist, f, indent=2)
            logging.info(f"Created default whitelist file: {whitelist_file}")
        except Exception as e:
            logging.error(f"Error creating whitelist file: {e}")
    
    def is_whitelisted(self, phone_number):
        """Check if a phone number is in the whitelist"""
        if not self.whitelist:
            return False
        
        # Normalize phone number for comparison
        normalized_number = self.normalize_phone_number(phone_number)
        
        for whitelisted_number in self.whitelist:
            normalized_whitelisted = self.normalize_phone_number(whitelisted_number)
            if normalized_number == normalized_whitelisted:
                return True
        
        return False
    
    def normalize_phone_number(self, phone_number):
        """Normalize phone number for comparison"""
        if not phone_number:
            return ""
        
        # Remove all non-digit characters except +
        normalized = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        # Ensure it starts with +
        if not normalized.startswith('+'):
            normalized = '+' + normalized
        
        return normalized
    
    def add_to_whitelist(self, phone_number, name=""):
        """Add a phone number to the whitelist"""
        normalized_number = self.normalize_phone_number(phone_number)
        
        if normalized_number not in self.whitelist:
            self.whitelist.append(normalized_number)
            self.save_whitelist()
            logging.info(f"Added {normalized_number} ({name}) to whitelist")
            return True
        else:
            logging.info(f"{normalized_number} already in whitelist")
            return False
    
    def remove_from_whitelist(self, phone_number):
        """Remove a phone number from the whitelist"""
        normalized_number = self.normalize_phone_number(phone_number)
        
        if normalized_number in self.whitelist:
            self.whitelist.remove(normalized_number)
            self.save_whitelist()
            logging.info(f"Removed {normalized_number} from whitelist")
            return True
        else:
            logging.info(f"{normalized_number} not found in whitelist")
            return False
    
    def save_whitelist(self):
        """Save whitelist to file"""
        whitelist_file = 'close_friends_whitelist.json'
        data = {
            "phone_numbers": self.whitelist,
            "description": "Phone numbers that should receive automated responses from TomasBot",
            "note": "Add phone numbers in international format (e.g., +1234567890)"
        }
        
        try:
            with open(whitelist_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving whitelist: {e}")
    
    def init_calendar_service(self):
        """Initialize Google Calendar service"""
        try:
            creds = self.get_google_credentials()
            self.calendar_service = build('calendar', 'v3', credentials=creds)
            logging.info("Google Calendar service initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize Google Calendar service: {e}")
            self.calendar_service = None
    
    def get_google_credentials(self):
        """Get Google Calendar credentials"""
        creds = None
        token_pickle = 'token.pickle'
        
        # Load existing token if exists
        if os.path.exists(token_pickle):
            with open(token_pickle, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, start OAuth flow
        if not creds or not creds.valid:
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                raise Exception("Google Calendar credentials not found in environment variables")
            
            flow = InstalledAppFlow.from_client_config({
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            }, ['https://www.googleapis.com/auth/calendar.readonly'])
            
            creds = flow.run_local_server(port=0)
            
            # Save token for future use
            with open(token_pickle, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds
    
    def get_current_calendar_event(self):
        """Get the current calendar event if any"""
        if not self.calendar_service:
            return None
        
        try:
            now = datetime.now(timezone.utc)
            time_min = (now - timedelta(minutes=30)).isoformat()
            time_max = (now + timedelta(hours=2)).isoformat()
            
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=1,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if events:
                event = events[0]
                start_time = event['start'].get('dateTime', event['start'].get('date'))
                end_time = event['end'].get('dateTime', event['end'].get('date'))
                summary = event.get('summary', 'Busy')
                
                # Parse times
                if 'T' in start_time:  # Has time component
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    
                    # Check if we're currently in this event
                    if start_dt <= now <= end_dt:
                        return {
                            'summary': summary,
                            'start_time': start_dt,
                            'end_time': end_dt,
                            'location': event.get('location', '')
                        }
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting calendar event: {e}")
            return None
    
    def format_response_message(self, event_info=None):
        """Generate response message using Claude"""
        if not self.llm:
            # Fallback to predefined message if Claude is not available
            return self.format_fallback_message(event_info)
        
        try:
            # Build the prompt for Claude
            system_message = """You are TomasBot, an automated assistant that sends brief, friendly responses when Tomas is unavailable. 

Your responses should be:
- Brief and conversational (1-2 sentences max)
- Friendly and helpful
- Include Tomas's current activity if available
- Suggest when they should try calling again based on the end time of the event
- End with "- TomasBot"

If Tomas has a calendar event, mention what he's doing and when he'll be available.
If no calendar event is available, simply say he's busy and will get back to them soon.

Keep it formal and professional."""

            if event_info:
                # Format event details for Claude
                end_time = event_info['end_time']
                if end_time.tzinfo:
                    end_time = end_time.astimezone(timezone(timedelta(hours=-5)))  # EST
                
                time_str = end_time.strftime("%I:%M%p EST")
                location = event_info.get('location', '')
                
                user_message = f"""Tomas is currently at: {event_info['summary']}
End time: {time_str}
Location: {location if location else 'No location specified'}

Generate a brief, friendly response letting someone know Tomas is busy and when to try calling again."""
            else:
                user_message = """Tomas doesn't have any calendar events right now. Generate a brief, friendly response letting someone know he's busy and will get back to them soon."""

            # Call Claude using LangChain
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            response = self.llm.invoke(messages)
            generated_message = response.content.strip()
            
            # Ensure it ends with "- TomasBot"
            if not generated_message.endswith("- TomasBot"):
                generated_message += " - TomasBot"
            
            logging.info(f"Generated Claude response: {generated_message}")
            return generated_message
            
        except Exception as e:
            logging.error(f"Error generating Claude response: {e}")
            # Fallback to predefined message
            return self.format_fallback_message(event_info)
    
    def format_fallback_message(self, event_info=None):
        """Fallback message format when Claude is not available"""
        if event_info:
            # Format end time
            end_time = event_info['end_time']
            if end_time.tzinfo:
                end_time = end_time.astimezone(timezone(timedelta(hours=-5)))  # EST
            
            time_str = end_time.strftime("%I:%M%p EST")
            location = event_info.get('location', '')
            
            if location:
                return f"Tomas is currently at {event_info['summary']} ({location}) until {time_str}... try calling him then! - TomasBot"
            else:
                return f"Tomas is currently at {event_info['summary']} until {time_str}... try calling him then! - TomasBot"
        else:
            return "Tomas is currently unavailable and will get back to you soon! - TomasBot"
    
    def send_imessage(self, recipient, message):
        """Send an iMessage using AppleScript"""
        escaped_message = message.replace('"', '\\"').replace("'", "\\'")
        
        applescript = f'''
        tell application "Messages"
            set targetService to 1st account whose service type = iMessage
            set targetBuddy to participant "{recipient}" of targetService
            send "{escaped_message}" to targetBuddy
        end tell
        '''
        
        try:
            result = subprocess.run(
                ['osascript', '-e', applescript], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logging.info(f"Auto-response sent to {recipient}: {message}")
                return True
            else:
                logging.error(f"Failed to send auto-response to {recipient}: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"Error sending auto-response to {recipient}: {e}")
            return False
    
    def check_missed_calls(self):
        """Check for new missed calls"""
        if not self.dnd_enabled:
            return
        
        try:
            db_path = os.path.expanduser("~/Library/Application Support/CallHistoryDB/CallHistory.storedata")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get recent missed calls
            cursor.execute("""
                SELECT ZADDRESS, ZDATE, ZNAME
                FROM ZCALLRECORD 
                WHERE ZANSWERED = 0 AND ZORIGINATED = 0
                ORDER BY ZDATE DESC
                LIMIT 10
            """)
            
            missed_calls = cursor.fetchall()
            conn.close()
            
            for call in missed_calls:
                phone_number, timestamp, contact_name = call
                
                if timestamp:
                    call_time = datetime.fromtimestamp(timestamp + 978307200)
                    
                    # Check if this is a recent call (within last 5 minutes)
                    if datetime.now() - call_time < timedelta(minutes=5):
                        call_id = f"{phone_number}_{timestamp}"
                        
                        if call_id not in self.last_processed_calls:
                            self.last_processed_calls.add(call_id)
                            
                            # Check if phone number is whitelisted
                            if self.is_whitelisted(phone_number):
                                # Get current calendar event
                                event_info = self.get_current_calendar_event()
                                message = self.format_response_message(event_info)
                                
                                # Send response
                                recipient = contact_name if contact_name else phone_number
                                self.send_imessage(recipient, message)
                                
                                logging.info(f"Sent auto-response for missed call from whitelisted contact: {recipient}")
                            else:
                                logging.info(f"Ignored missed call from non-whitelisted number: {phone_number}")
            
            # Clean up old processed calls (older than 1 hour)
            cutoff_time = datetime.now() - timedelta(hours=1)
            self.last_processed_calls = {
                call_id for call_id in self.last_processed_calls
                if datetime.fromtimestamp(int(call_id.split('_')[1]) + 978307200) > cutoff_time
            }
            
        except Exception as e:
            logging.error(f"Error checking missed calls: {e}")
    
    def check_missed_texts(self):
        """Check for new unread texts"""
        if not self.dnd_enabled:
            return
        
        try:
            db_path = os.path.expanduser("~/Library/Messages/chat.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get recent unread messages
            cursor.execute("""
                SELECT 
                    m.text,
                    m.date,
                    h.id as phone_number,
                    c.display_name as chat_name
                FROM message m
                LEFT JOIN handle h ON m.handle_id = h.ROWID
                LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                LEFT JOIN chat c ON cmj.chat_id = c.ROWID
                WHERE m.is_from_me = 0 AND m.is_read = 0
                ORDER BY m.date DESC
                LIMIT 10
            """)
            
            unread_texts = cursor.fetchall()
            conn.close()
            
            for text in unread_texts:
                message_text, timestamp, phone_number, chat_name = text
                
                if timestamp:
                    # Convert Messages timestamp
                    text_time = datetime.fromtimestamp(timestamp / 1000000000 + 978307200)
                    
                    # Check if this is a recent message (within last 5 minutes)
                    if datetime.now() - text_time < timedelta(minutes=5):
                        text_id = f"{phone_number}_{timestamp}"
                        
                        if text_id not in self.last_processed_texts:
                            self.last_processed_texts.add(text_id)
                            
                            # Check if phone number is whitelisted
                            if self.is_whitelisted(phone_number):
                                # Get current calendar event
                                event_info = self.get_current_calendar_event()
                                message = self.format_response_message(event_info)
                                
                                # Send response
                                recipient = chat_name if chat_name else phone_number
                                self.send_imessage(recipient, message)
                                
                                logging.info(f"Sent auto-response for unread text from whitelisted contact: {recipient}")
                            else:
                                logging.info(f"Ignored unread text from non-whitelisted number: {phone_number}")
            
            # Clean up old processed texts (older than 1 hour)
            cutoff_time = datetime.now() - timedelta(hours=1)
            self.last_processed_texts = {
                text_id for text_id in self.last_processed_texts
                if datetime.fromtimestamp(int(text_id.split('_')[1]) / 1000000000 + 978307200) > cutoff_time
            }
            
        except Exception as e:
            logging.error(f"Error checking missed texts: {e}")
    
    def monitor_communications(self):
        """Main monitoring loop"""
        while True:
            try:
                if self.dnd_enabled:
                    self.check_missed_calls()
                    self.check_missed_texts()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/webhook/dnd', methods=['POST'])
        def handle_dnd_webhook():
            """Handle Do Not Disturb status updates"""
            try:
                data = request.get_json()
                
                if not data:
                    return jsonify({'error': 'No JSON data received'}), 400
                
                is_dnd_enabled = data.get('dnd_enabled', False)
                self.dnd_enabled = is_dnd_enabled
                
                status = "enabled" if is_dnd_enabled else "disabled"
                logging.info(f"DND Status: {status}")
                
                return jsonify({
                    'status': 'success',
                    'dnd_enabled': is_dnd_enabled,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                logging.error(f"Error processing DND webhook: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/status', methods=['GET'])
        def get_status():
            """Get current bot status"""
            event_info = self.get_current_calendar_event()
            
            return jsonify({
                'dnd_enabled': self.dnd_enabled,
                'current_event': event_info,
                'whitelist_count': len(self.whitelist),
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/whitelist', methods=['GET'])
        def get_whitelist():
            """Get current whitelist"""
            return jsonify({
                'phone_numbers': self.whitelist,
                'count': len(self.whitelist)
            })
        
        @self.app.route('/whitelist/add', methods=['POST'])
        def add_whitelist():
            """Add phone number to whitelist"""
            try:
                data = request.get_json()
                phone_number = data.get('phone_number')
                name = data.get('name', '')
                
                if not phone_number:
                    return jsonify({'error': 'Phone number required'}), 400
                
                success = self.add_to_whitelist(phone_number, name)
                
                return jsonify({
                    'success': success,
                    'phone_number': phone_number,
                    'message': 'Added to whitelist' if success else 'Already in whitelist'
                })
                
            except Exception as e:
                logging.error(f"Error adding to whitelist: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/whitelist/remove', methods=['POST'])
        def remove_whitelist():
            """Remove phone number from whitelist"""
            try:
                data = request.get_json()
                phone_number = data.get('phone_number')
                
                if not phone_number:
                    return jsonify({'error': 'Phone number required'}), 400
                
                success = self.remove_from_whitelist(phone_number)
                
                return jsonify({
                    'success': success,
                    'phone_number': phone_number,
                    'message': 'Removed from whitelist' if success else 'Not found in whitelist'
                })
                
            except Exception as e:
                logging.error(f"Error removing from whitelist: {e}")
                return jsonify({'error': 'Internal server error'}), 500
        
        @self.app.route('/test', methods=['GET'])
        def test_endpoint():
            """Test endpoint"""
            return jsonify({
                'message': 'TomasBot is running!',
                'dnd_enabled': self.dnd_enabled,
                'whitelist_count': len(self.whitelist),
                'timestamp': datetime.now().isoformat()
            })

def main():
    """Main function"""
    port = int(os.environ.get('PORT', 5001))
    host = os.environ.get('HOST', '0.0.0.0')
    
    bot = TomasBot()
    
    logging.info(f"Starting TomasBot on {host}:{port}")
    logging.info(f"DND Webhook URL: http://{host}:{port}/webhook/dnd")
    logging.info(f"Status URL: http://{host}:{port}/status")
    
    bot.app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    main() 