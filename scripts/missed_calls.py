import sqlite3
import os
from datetime import datetime

# Path to call history database
db_path = os.path.expanduser("~/Library/Application Support/CallHistoryDB/CallHistory.storedata")

conn = None

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query call history with correct column names
    cursor.execute("""
        SELECT ZADDRESS, ZDATE, ZDURATION, ZANSWERED, ZORIGINATED, ZNAME, ZCALLTYPE
        FROM ZCALLRECORD 
        ORDER BY ZDATE DESC
        LIMIT 20
    """)
    
    print("Recent Call History:")
    print("-" * 80)
    
    for row in cursor.fetchall():
        phone_number, timestamp, duration, answered, originated, contact_name, call_type = row
        
        # Convert Core Data timestamp to readable date
        if timestamp:
            date = datetime.fromtimestamp(timestamp + 978307200)  # Core Data epoch adjustment
        else:
            date = "Unknown"
        
        # Determine call direction and status
        if originated == 1:
            direction = "Outgoing"
            status = "Called"
        else:
            direction = "Incoming"
            status = "Answered" if answered == 1 else "Missed"
        
        # Format duration
        if duration and duration > 0:
            duration_str = f"{int(duration)}s"
        else:
            duration_str = "0s"
        
        # Use contact name if available, otherwise phone number
        display_name = contact_name if contact_name else phone_number
        
        print(f"{date} | {direction:8} | {status:8} | {display_name:20} | {duration_str}")
        
except Exception as e:
    print(f"Error accessing call history: {e}")
finally:
    if conn:
        conn.close()    