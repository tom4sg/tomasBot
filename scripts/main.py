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
    level=logging.INFO,  # Back to INFO level
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tomas_bot.log'),
        logging.StreamHandler()
    ]
)

class TomasBot:
    def __init__(self):
        """Initialize TomasBot"""
        self.app = Flask(__name__)
        self.dnd_enabled = False
        self.whitelist = set()
        self.last_processed_calls = set()
        self.last_processed_texts = set()
        
        # Initialize services
        self.llm = self.init_claude_llm()  # Store the LLM object
        self.load_whitelist()
        self.init_calendar_service()
        
        # Setup routes
        self.setup_routes()
        
        # Start monitoring thread
        logging.info("Starting monitoring thread...")
        self.monitoring_thread = threading.Thread(target=self.monitor_communications, daemon=True)
        self.monitoring_thread.start()
        logging.info("Monitoring thread started successfully")
    
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
                    self.whitelist = set(whitelist)
                    return  # Successfully loaded, don't create default
            except Exception as e:
                logging.error(f"Error loading whitelist: {e}")
        
        # Only create default if file doesn't exist or failed to load
        logging.warning("No whitelist found. Creating default whitelist file.")
        self.create_default_whitelist()
    
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
            self.whitelist.add(normalized_number)
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
            "phone_numbers": list(self.whitelist),
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
- Use the EXACT end time provided from the calendar event - do not change or estimate the time
- Suggest when they should try calling again based on the exact end time
- ALWAYS end your response with a period (.)
- Do NOT include "- TomasBot" in your response - this will be added automatically

If Tomas has a calendar event, mention what he's doing and when he'll be available using the exact end time provided.
If no calendar event is available, simply say he's busy and will get back to them soon.

Keep it formal and professional."""

            if event_info:
                # Format event details for Claude
                end_time = event_info['end_time']
                if end_time.tzinfo:
                    # Convert to local timezone (handles DST automatically)
                    import time
                    local_tz = time.tzname[time.daylight]
                    end_time = end_time.astimezone()
                
                time_str = end_time.strftime("%I:%M%p %Z")  # Use %Z for timezone abbreviation
                location = event_info.get('location', '')
                
                logging.info(f"Calendar event: {event_info['summary']}, End time: {time_str}, Location: {location}")
                
                user_message = f"""Tomas is currently at: {event_info['summary']}
End time: {time_str} (use this EXACT time in your response)
Location: {location if location else 'No location specified'}

Generate a brief, friendly response letting someone know Tomas is busy and when to try calling again. IMPORTANT: Use the exact end time provided ({time_str}) - do not change or estimate the time. Make sure your response ends with a period."""
            else:
                user_message = """Tomas doesn't have any calendar events right now. Generate a brief, friendly response letting someone know he's busy and will get back to them soon. Make sure your response ends with a period."""

            # Call Claude using LangChain
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=user_message)
            ]
            
            response = self.llm.invoke(messages, config={"timeout": 5})  # 5 second timeout
            generated_message = response.content.strip()
            
            # Ensure it ends with a period
            if not generated_message.endswith('.'):
                generated_message += '.'
            
            # Add blank line and "- TomasBot"
            formatted_message = f"{generated_message}\n\n- TomasBot"
            
            logging.info(f"Generated Claude response: {formatted_message}")
            return formatted_message
            
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
                # Convert to local timezone (handles DST automatically)
                end_time = end_time.astimezone()
            
            time_str = end_time.strftime("%I:%M%p %Z")  # Use %Z for timezone abbreviation
            location = event_info.get('location', '')
            
            if location:
                message = f"Tomas is currently at {event_info['summary']} ({location}) until {time_str}... try calling him then!"
            else:
                message = f"Tomas is currently at {event_info['summary']} until {time_str}... try calling him then!"
        else:
            message = "Tomas is currently unavailable and will get back to you soon!"
        
        # Ensure it ends with a period and add blank line before "- TomasBot"
        if not message.endswith('.'):
            message += '.'
        
        return f"{message}\n\n- TomasBot"
    
    def send_imessage(self, recipient, message):
        """Send an iMessage using AppleScript with temporary file to avoid syntax errors"""
        import tempfile
        import os
        
        try:
            # Create a temporary file with the message content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(message)
                temp_file_path = temp_file.name
            
            # Use AppleScript to read from the file and send the message
            applescript = f'''
            tell application "Messages"
                set targetService to 1st account whose service type = iMessage
                set targetBuddy to participant "{recipient}" of targetService
                set messageText to (read POSIX file "{temp_file_path}" as «class utf8»)
                send messageText to targetBuddy
            end tell
            '''
            
            result = subprocess.run(
                ['osascript', '-e', applescript], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            # Clean up the temporary file
            try:
                os.unlink(temp_file_path)
            except:
                pass  # Ignore cleanup errors
            
            if result.returncode == 0:
                logging.info(f"Auto-response sent to {recipient}: {message}")
                return True
            else:
                logging.error(f"Failed to send auto-response to {recipient}: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"Error sending auto-response to {recipient}: {e}")
            # Clean up temp file if it exists
            try:
                if 'temp_file_path' in locals():
                    os.unlink(temp_file_path)
            except:
                pass
            return False
    
    def check_missed_calls(self):
        """Check for new missed calls"""
        if not self.dnd_enabled:
            return
        
        try:
            db_path = os.path.expanduser("~/Library/Application Support/CallHistoryDB/CallHistory.storedata")
            
            if not os.path.exists(db_path):
                logging.warning("Call database not found")
                return
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Calculate timestamp for 15 minutes ago (Call database uses seconds since 2001)
            now = datetime.now()
            current_timestamp = int(now.timestamp() - 978307200)
            fifteen_minutes_ago = int(now.timestamp() - 900 - 978307200)
            
            logging.debug(f"Current call timestamp: {current_timestamp}")
            logging.debug(f"Querying for calls after timestamp: {fifteen_minutes_ago}")
            
            # Get recent missed calls from the last 15 minutes only
            cursor.execute("""
                SELECT ZADDRESS, ZDATE, ZNAME
                FROM ZCALLRECORD 
                WHERE ZANSWERED = 0 AND ZORIGINATED = 0 AND ZDATE > ?
                ORDER BY ZDATE DESC
                LIMIT 5
            """, (fifteen_minutes_ago,))
            
            missed_calls = cursor.fetchall()
            conn.close()
            
            if missed_calls:
                logging.info(f"Found {len(missed_calls)} recent missed calls in database")
            else:
                logging.debug("No recent missed calls found")
            
            for call in missed_calls:
                phone_number, timestamp, contact_name = call
                
                if timestamp:
                    call_time = datetime.fromtimestamp(timestamp + 978307200)
                    time_diff = datetime.now() - call_time
                    
                    logging.info(f"Checking recent call: {contact_name or phone_number} at {call_time} ({time_diff.total_seconds():.0f}s ago)")
                    
                    # Check if this is a recent call (within last 30 seconds for faster response)
                    if time_diff < timedelta(seconds=30):
                        call_id = f"{phone_number}_{timestamp}"
                        
                        if call_id not in self.last_processed_calls:
                            self.last_processed_calls.add(call_id)
                            
                            logging.info(f"Processing recent missed call from: {contact_name or phone_number}")
                            
                            # Check if phone number is whitelisted
                            if self.is_whitelisted(phone_number):
                                logging.info(f"Phone number {phone_number} is whitelisted, sending response")
                                
                                # Get current calendar event
                                event_info = self.get_current_calendar_event()
                                message = self.format_response_message(event_info)
                                
                                # Send response
                                recipient = contact_name if contact_name else phone_number
                                self.send_imessage(recipient, message)
                                
                                logging.info(f"Sent auto-response for missed call from whitelisted contact: {recipient}")
                            else:
                                logging.info(f"Ignored missed call from non-whitelisted number: {phone_number}")
                        else:
                            logging.debug(f"Call {call_id} already processed")
                    else:
                        logging.debug(f"Call too old: {time_diff.total_seconds():.0f}s ago")
            
            # Clean up old processed calls (older than 30 minutes)
            cutoff_time = datetime.now() - timedelta(minutes=30)
            self.last_processed_calls = {
                call_id for call_id in self.last_processed_calls
                if datetime.fromtimestamp(float(call_id.split('_')[1]) + 978307200) > cutoff_time
            }
            
        except Exception as e:
            logging.error(f"Error checking missed calls: {e}")
    
    def check_missed_texts(self):
        """Check for new unread texts"""
        logging.debug("check_missed_texts() called")
        if not self.dnd_enabled:
            logging.debug("DND not enabled, skipping text check")
            return
        
        try:
            logging.debug("Connecting to Messages database...")
            db_path = os.path.expanduser("~/Library/Messages/chat.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Calculate timestamp for 15 minutes ago (original working setting)
            now = datetime.now()
            current_timestamp = int(now.timestamp() * 1000000000 - 978307200 * 1000000000)
            fifteen_minutes_ago = int((now.timestamp() - 900) * 1000000000 - 978307200 * 1000000000)
            
            logging.debug(f"Current timestamp: {current_timestamp}")
            logging.debug(f"Querying for texts after timestamp: {fifteen_minutes_ago}")
            
            # Original working query
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
                WHERE m.is_from_me = 0 
                AND m.is_read = 0 
                AND m.date > ?
                ORDER BY m.date DESC
                LIMIT 10
            """, (fifteen_minutes_ago,))
            
            unread_texts = cursor.fetchall()
            conn.close()
            
            if unread_texts:
                logging.debug(f"Raw unread texts data: {unread_texts}")
            else:
                logging.debug("No recent unread texts found")
            
            logging.debug(f"About to process {len(unread_texts)} unread texts")
            
            # Track if we actually process any new messages
            new_messages_processed = 0
            
            for text in unread_texts:
                message_text, timestamp, phone_number, chat_name = text
                logging.debug(f"Processing text: text='{message_text}', timestamp={timestamp}, phone={phone_number}, chat={chat_name}")
                
                if timestamp:
                    # Convert Messages timestamp
                    text_time = datetime.fromtimestamp(timestamp / 1000000000 + 978307200)
                    
                    # Create unique ID for this message
                    text_id = f"{phone_number}_{timestamp}"
                    
                    # Check if we've already processed this message
                    if text_id in self.last_processed_texts:
                        logging.debug(f"Message {text_id} already processed, skipping")
                        continue
                    
                    # This is a new message we haven't processed before
                    new_messages_processed += 1
                    logging.info(f"Checking recent message: {chat_name or phone_number} at {text_time} ({(datetime.now() - text_time).total_seconds():.0f}s ago) - Text: '{message_text}'")
                    
                    # Original working time check - within last 1 minute
                    if datetime.now() - text_time < timedelta(minutes=1):
                        # Check if phone number is whitelisted
                        if self.is_whitelisted(phone_number):
                            logging.info(f"Phone number {phone_number} is whitelisted, sending response")
                            
                            # Get current calendar event
                            event_info = self.get_current_calendar_event()
                            message = self.format_response_message(event_info)
                            
                            # Send response
                            recipient = chat_name if chat_name else phone_number
                            success = self.send_imessage(recipient, message)
                            
                            if success:
                                # Only mark as processed if message was sent successfully
                                self.last_processed_texts.add(text_id)
                                logging.info(f"Sent auto-response for unread message from whitelisted contact: {recipient}")
                            else:
                                logging.error(f"Failed to send auto-response to {recipient}, will retry")
                        else:
                            # Mark as processed even if not whitelisted to avoid repeated logging
                            self.last_processed_texts.add(text_id)
                            logging.info(f"Ignored unread message from non-whitelisted number: {phone_number}")
                    else:
                        # Mark old messages as processed to prevent repeated logging
                        self.last_processed_texts.add(text_id)
                        logging.debug(f"Message too old: {(datetime.now() - text_time).total_seconds():.0f}s ago")
                else:
                    logging.debug(f"Skipping text with no timestamp: {text}")
            
            # Only log if we actually found and processed new messages
            if new_messages_processed > 0:
                logging.info(f"Found and processed {new_messages_processed} new unread texts")
            
            logging.debug(f"Finished processing {len(unread_texts)} unread texts")
            
            # Clean up old processed texts (older than 30 minutes)
            # Only keep track of recent messages to prevent memory bloat
            cutoff_time = datetime.now() - timedelta(minutes=30)
            old_texts_to_remove = set()
            
            for text_id in self.last_processed_texts:
                try:
                    # Parse the timestamp from text_id format: "phone_number_timestamp"
                    parts = text_id.split('_', 1)  # Split on first underscore only
                    if len(parts) == 2:
                        timestamp_str = parts[1]
                        timestamp_ns = int(timestamp_str)
                        message_time = datetime.fromtimestamp(timestamp_ns / 1000000000 + 978307200)
                        
                        if message_time < cutoff_time:
                            old_texts_to_remove.add(text_id)
                except (ValueError, IndexError) as e:
                    # If we can't parse the text_id, remove it to prevent issues
                    logging.debug(f"Removing malformed text_id: {text_id} (error: {e})")
                    old_texts_to_remove.add(text_id)
            
            # Remove old texts
            self.last_processed_texts -= old_texts_to_remove
            if old_texts_to_remove:
                logging.debug(f"Cleaned up {len(old_texts_to_remove)} old processed texts")
            
        except Exception as e:
            logging.error(f"Error checking missed texts: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
    
    def monitor_communications(self):
        """Main monitoring loop"""
        logging.info("Monitoring thread started")
        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                if cycle_count % 60 == 0:  # Log every 60 cycles (every minute)
                    logging.info(f"Monitoring loop running - cycle {cycle_count}")
                
                if self.dnd_enabled:
                    start_time = datetime.now()
                    
                    logging.debug("Checking missed calls...")
                    self.check_missed_calls()
                    
                    logging.debug("Checking missed texts...")
                    self.check_missed_texts()
                    
                    # Log performance metrics
                    processing_time = (datetime.now() - start_time).total_seconds()
                    if processing_time > 0.5:  # Log if processing takes more than 0.5 seconds
                        logging.info(f"Monitoring cycle took {processing_time:.3f}s")
                else:
                    logging.debug("DND disabled, skipping monitoring")
                
                time.sleep(1)  # Check every 1 second (ultra-fast)
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                import traceback
                logging.error(f"Traceback: {traceback.format_exc()}")
                time.sleep(5)  # Wait longer on error
    
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
                'phone_numbers': list(self.whitelist),
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