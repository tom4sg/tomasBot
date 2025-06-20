import subprocess

def send_imessage(recipient, message):
    """
    Send an iMessage using AppleScript
    
    Args:
        recipient (str): Phone number (e.g., "+1234567890") or email address
        message (str): The message text to send
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    # Escape any quotes in the message to prevent AppleScript errors
    escaped_message = message.replace('"', '\\"').replace("'", "\\'")
    
    # AppleScript to send iMessage
    applescript = f'''
    tell application "Messages"
        set targetService to 1st account whose service type = iMessage
        set targetBuddy to participant "{recipient}" of targetService
        send "{escaped_message}" to targetBuddy
    end tell
    '''
    
    try:
        # Execute the AppleScript
        result = subprocess.run(
            ['osascript', '-e', applescript], 
            capture_output=True, 
            text=True,
            timeout=10  # 10 second timeout
        )
        
        if result.returncode == 0:
            print(f"Message sent successfully to {recipient}")
            print(f"Message: {message}")
            return True
        else:
            print(f"Failed to send message")
            print(f"Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("Timeout: Message sending took too long")
        return False
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def main():
    print("iMessage Sender")
    print()
    
    # Get recipient from user
    recipient = input("Enter recipient (phone number with +1 or email): ").strip()
    
    # Get message from user
    message = input("Enter your message: ").strip()
    
    # Confirm before sending
    print()
    print(f"Ready to send:")
    print(f"To: {recipient}")
    print(f"Message: {message}")
    print()
    
    confirm = input("Send this message? (y/n): ").strip().lower()
    
    if confirm in ['y', 'yes']:
        print("Sending message...")
        success = send_imessage(recipient, message)
        
        if success:
            print("Done!")
        else:
            print("Message failed to send")
    else:
        print("Message cancelled.")

if __name__ == "__main__":
    main()