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
        
# import sqlite3
# import os
# from datetime import datetime

# # Path to call history database
# db_path = os.path.expanduser("~/Library/Application Support/CallHistoryDB/CallHistory.storedata")

# conn = None

# try:
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()
    
#     # First, let's see what tables exist
#     cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
#     tables = cursor.fetchall()
#     print("Available tables:")
#     for table in tables:
#         print(f"  - {table[0]}")
    
#     # Let's examine the ZCALLRECORD table structure
#     cursor.execute("PRAGMA table_info(ZCALLRECORD);")
#     columns = cursor.fetchall()
#     print("\nZCALLRECORD table columns:")
#     for col in columns:
#         print(f"  - {col[1]} ({col[2]})")
    
#     # Let's see a few sample records to understand the data
#     cursor.execute("SELECT * FROM ZCALLRECORD LIMIT 3;")
#     sample_data = cursor.fetchall()
#     print(f"\nSample data (first 3 records):")
#     for i, row in enumerate(sample_data):
#         print(f"Record {i+1}: {row}")
        
# except Exception as e:
#     print(f"Error: {e}")
# finally:
#     if conn:
#         conn.close()