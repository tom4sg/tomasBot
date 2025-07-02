#!/usr/bin/env python3
"""
Scheduled Send Script for TomasBot
Allows scheduling messages to be sent to whitelisted contacts at a specific date and time.
"""

import json
import os
import sys
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timedelta
import time
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduled_send.log'),
        logging.StreamHandler()
    ]
)

SCHEDULED_MESSAGES_FILE = 'scheduled_messages.json'
WHITELIST_FILE = 'close_friends_whitelist.json'

class ScheduledSender:
    def __init__(self):
        """Initialize the scheduled sender"""
        self.scheduled_messages = self.load_scheduled_messages()
        self.running = False
        self.scheduler_thread = None
    
    def load_scheduled_messages(self):
        """Load scheduled messages from file"""
        if os.path.exists(SCHEDULED_MESSAGES_FILE):
            try:
                with open(SCHEDULED_MESSAGES_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading scheduled messages: {e}")
        return []
    
    def save_scheduled_messages(self):
        """Save scheduled messages to file"""
        try:
            with open(SCHEDULED_MESSAGES_FILE, 'w') as f:
                json.dump(self.scheduled_messages, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving scheduled messages: {e}")
    
    def load_whitelist(self):
        """Load the current whitelist"""
        if os.path.exists(WHITELIST_FILE):
            try:
                with open(WHITELIST_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('phone_numbers', [])
            except Exception as e:
                logging.error(f"Error loading whitelist: {e}")
        return []
    
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
    
    def send_imessage(self, recipient, message):
        """Send an iMessage using AppleScript with temporary file to avoid syntax errors"""
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
                logging.info(f"Scheduled message sent to {recipient}")
                return True
            else:
                logging.error(f"Failed to send scheduled message to {recipient}: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"Error sending scheduled message to {recipient}: {e}")
            # Clean up temp file if it exists
            try:
                if 'temp_file_path' in locals():
                    os.unlink(temp_file_path)
            except:
                pass
            return False
    
    def scheduler_loop(self):
        """Main scheduler loop that checks for messages to send"""
        logging.info("Scheduler started")
        while self.running:
            try:
                current_time = datetime.now()
                messages_to_send = []
                messages_to_remove = []
                
                # Check each scheduled message
                for i, message_data in enumerate(self.scheduled_messages):
                    scheduled_time = datetime.fromisoformat(message_data['scheduled_time'])
                    
                    # If it's time to send the message
                    if current_time >= scheduled_time:
                        messages_to_send.append((i, message_data))
                        messages_to_remove.append(i)
                
                # Send messages
                for i, message_data in messages_to_send:
                    recipient = message_data['recipient']
                    message = message_data['message']
                    
                    logging.info(f"Sending scheduled message to {recipient}")
                    success = self.send_imessage(recipient, message)
                    
                    if success:
                        logging.info(f"Successfully sent scheduled message to {recipient}")
                    else:
                        logging.error(f"Failed to send scheduled message to {recipient}")
                
                # Remove sent messages (in reverse order to maintain indices)
                for i in sorted(messages_to_remove, reverse=True):
                    del self.scheduled_messages[i]
                
                # Save updated list if we sent any messages
                if messages_to_send:
                    self.save_scheduled_messages()
                
                # Sleep for 30 seconds before next check
                time.sleep(30)
                
            except Exception as e:
                logging.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def start_scheduler(self):
        """Start the scheduler in a background thread"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            logging.info("Scheduler started in background")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logging.info("Scheduler stopped")
    
    def schedule_message(self, recipient, message, scheduled_time):
        """Schedule a message to be sent"""
        message_data = {
            'recipient': recipient,
            'message': message,
            'scheduled_time': scheduled_time.isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        self.scheduled_messages.append(message_data)
        self.save_scheduled_messages()
        
        logging.info(f"Scheduled message for {recipient} at {scheduled_time}")
        return True
    
    def view_scheduled_messages(self):
        """View all scheduled messages"""
        if not self.scheduled_messages:
            print("No scheduled messages")
            return
        
        print(f"\nScheduled Messages ({len(self.scheduled_messages)}):")
        print("-" * 80)
        
        for i, message_data in enumerate(self.scheduled_messages, 1):
            scheduled_time = datetime.fromisoformat(message_data['scheduled_time'])
            created_at = datetime.fromisoformat(message_data['created_at'])
            
            print(f"{i}. To: {message_data['recipient']}")
            print(f"   Scheduled: {scheduled_time.strftime('%Y-%m-%d %I:%M %p')}")
            print(f"   Created: {created_at.strftime('%Y-%m-%d %I:%M %p')}")
            print(f"   Message: {message_data['message'][:50]}{'...' if len(message_data['message']) > 50 else ''}")
            print("-" * 80)
    
    def cancel_scheduled_message(self):
        """Cancel a scheduled message"""
        if not self.scheduled_messages:
            print("No scheduled messages to cancel")
            return
        
        self.view_scheduled_messages()
        
        try:
            choice = int(input("\nEnter message number to cancel (1, 2, 3...): ")) - 1
            if 0 <= choice < len(self.scheduled_messages):
                cancelled_message = self.scheduled_messages.pop(choice)
                self.save_scheduled_messages()
                print(f"Cancelled message to {cancelled_message['recipient']}")
            else:
                print("Invalid choice!")
        except ValueError:
            print("Please enter a valid number!")

def get_whitelisted_contact(whitelist):
    """Get user to select a whitelisted contact"""
    if not whitelist:
        print("No contacts in whitelist! Add contacts first using manage_whitelist.py")
        return None
    
    print("\nWhitelisted contacts:")
    for i, number in enumerate(whitelist, 1):
        print(f"{i}. {number}")
    
    try:
        choice = int(input("\nSelect contact (1, 2, 3...): ")) - 1
        if 0 <= choice < len(whitelist):
            return whitelist[choice]
        else:
            print("Invalid choice!")
            return None
    except ValueError:
        print("Please enter a valid number!")
        return None

def get_scheduled_time():
    """Get the scheduled time from user"""
    print("\nWhen would you like to send this message?")
    print("1. Send now")
    print("2. Send at a specific date/time")
    print("3. Send in X minutes")
    
    choice = input("Choose option (1-3): ").strip()
    
    if choice == '1':
        return datetime.now()
    elif choice == '2':
        # Get specific date and time
        date_str = input("Enter date (YYYY-MM-DD): ").strip()
        time_str = input("Enter time (HH:MM): ").strip()
        
        try:
            datetime_str = f"{date_str} {time_str}"
            return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError:
            print("Invalid date/time format!")
            return None
    elif choice == '3':
        # Send in X minutes
        try:
            minutes = int(input("Enter number of minutes from now: ").strip())
            return datetime.now() + timedelta(minutes=minutes)
        except ValueError:
            print("Please enter a valid number of minutes!")
            return None
    else:
        print("Invalid choice!")
        return None

def schedule_new_message(sender):
    """Schedule a new message"""
    # Load whitelist
    whitelist = sender.load_whitelist()
    
    # Get recipient
    recipient = get_whitelisted_contact(whitelist)
    if not recipient:
        return
    
    # Get message
    print(f"\nEnter message to send to {recipient}:")
    message = input("Message: ").strip()
    
    if not message:
        print("Message cannot be empty!")
        return
    
    # Get scheduled time
    scheduled_time = get_scheduled_time()
    if not scheduled_time:
        return
    
    # Check if time is in the past
    if scheduled_time < datetime.now():
        print("Scheduled time is in the past!")
        return
    
    # Schedule the message
    success = sender.schedule_message(recipient, message, scheduled_time)
    
    if success:
        print(f"\nMessage scheduled successfully!")
        print(f"Recipient: {recipient}")
        print(f"Scheduled for: {scheduled_time.strftime('%Y-%m-%d %I:%M %p')}")
        print(f"Message: {message}")

def main():
    """Main function"""
    print("="*60)
    print("TomasBot Scheduled Send")
    print("="*60)
    
    sender = ScheduledSender()
    
    # Start the scheduler
    sender.start_scheduler()
    
    try:
        while True:
            print("\n" + "="*50)
            print("Scheduled Send Menu")
            print("="*50)
            print("1. Schedule new message")
            print("2. View scheduled messages")
            print("3. Cancel scheduled message")
            print("4. Exit")
            print("-"*50)
            
            choice = input("Choose an option (1-4): ").strip()
            
            if choice == '1':
                schedule_new_message(sender)
            elif choice == '2':
                sender.view_scheduled_messages()
            elif choice == '3':
                sender.cancel_scheduled_message()
            elif choice == '4':
                print("Stopping scheduler...")
                break
            else:
                print("Invalid choice! Please enter 1-4")
            
            input("\nPress Enter to continue...")
    
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
    
    finally:
        sender.stop_scheduler()
        print("Goodbye!")

if __name__ == "__main__":
    main() 